from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
from urllib.parse import urljoin

import httpx
import m3u8
import regex
from creart import it
from pydantic import BaseModel

from src.api import WebAPI
from src.config import Config
from src.legacy.decrypt import WidevineDecrypt
from src.measurer import Measurer
from src.models.music_video import MusicVideoDatum
from src.utils import get_path_safe_dict, get_valid_filename, get_valid_dir_name, run_sync


class MusicVideoStream(BaseModel):
    url: str
    label: str


class EncryptedMusicVideoStream(BaseModel):
    key_uri: str
    pssh_base64: str
    segment_urls: list[str]


class MusicVideoMetadata(BaseModel):
    adam_id: str
    title: str
    artist: str
    album: Optional[str] = None
    album_artist: Optional[str] = None
    genre: Optional[str] = None
    created: Optional[str] = None
    isrc: Optional[str] = None
    tracknum: Optional[int] = None
    disk: Optional[int] = None
    rtng: int = 0
    cover_url: Optional[str] = None
    cover: Optional[bytes] = None

    @classmethod
    def parse(cls, adam_id: str, data: MusicVideoDatum) -> "MusicVideoMetadata":
        attrs = data.attributes
        album_attrs = None
        if data.relationships and data.relationships.albums and data.relationships.albums.data:
            album_attrs = data.relationships.albums.data[0].attributes

        return cls(
            adam_id=adam_id,
            title=attrs.name or adam_id,
            artist=attrs.artistName or "Unknown Artist",
            album=attrs.albumName or (album_attrs.name if album_attrs else None),
            album_artist=(album_attrs.artistName if album_attrs else None) or attrs.artistName,
            genre=attrs.genreNames[0] if attrs.genreNames else None,
            created=attrs.releaseDate,
            isrc=attrs.isrc,
            tracknum=attrs.trackNumber,
            disk=attrs.discNumber,
            rtng=_rating(attrs.contentRating),
            cover_url=attrs.artwork.url if attrs.artwork else None,
        )

    def path_params(self) -> dict:
        return get_path_safe_dict(self.model_dump())

    def to_itags(self, cover_path: Path | None = None) -> str:
        tags = [
            "tool=",
            f"artist={self.artist}",
            f"title={self.title}",
            f"rating={self.rtng}",
        ]
        optional_tags = {
            "album": self.album,
            "album_artist": self.album_artist,
            "genre": self.genre,
            "created": self.created,
            "ISRC": self.isrc,
            "track": self.tracknum,
            "tracknum": self.tracknum,
            "disk": self.disk,
            "performer": self.artist,
        }
        for key, value in optional_tags.items():
            if value:
                tags.append(f"{key}={value}")
        if cover_path:
            tags.append(f"cover={cover_path}")
        return ":".join(tags)


def _rating(content_rating: Optional[str]) -> int:
    if content_rating == "explicit":
        return 1
    if content_rating == "clean":
        return 2
    return 0


def select_mv_video_stream(master_text: str, master_url: str, max_height: int) -> MusicVideoStream:
    parsed = m3u8.loads(master_text, uri=master_url)
    playlists = sorted(
        parsed.playlists,
        key=lambda playlist: playlist.stream_info.average_bandwidth or playlist.stream_info.bandwidth or 0,
        reverse=True,
    )
    for playlist in playlists:
        resolution = playlist.stream_info.resolution
        if not resolution:
            match = regex.search(r"_(\d+)x(\d+)", playlist.uri)
            if not match:
                continue
            width, height = int(match[1]), int(match[2])
        else:
            width, height = resolution
        if height <= max_height:
            video_range = playlist.stream_info.video_range or ""
            label = f"{width}x{height} {video_range}".strip()
            return MusicVideoStream(url=playlist.absolute_uri, label=label)
    raise ValueError("没有找到符合 maxHeight 的 MV 视频流")


def select_mv_audio_stream(master_text: str, master_url: str, audio_type: str) -> MusicVideoStream:
    parsed = m3u8.loads(master_text, uri=master_url)
    priorities = {
        "auto": ["audio-atmos", "audio-ac3", "audio-stereo-256"],
        "atmos": ["audio-atmos", "audio-ac3", "audio-stereo-256"],
        "ac3": ["audio-ac3", "audio-stereo-256"],
        "aac": ["audio-stereo-256"],
    }.get(audio_type, ["audio-atmos", "audio-ac3", "audio-stereo-256"])

    candidates = []
    for media in parsed.media:
        if media.type != "AUDIO" or not media.uri or media.group_id not in priorities:
            continue
        rank_match = regex.search(r"_gr(\d+)_", media.uri)
        rank = int(rank_match[1]) if rank_match else 0
        priority = priorities.index(media.group_id)
        candidates.append((priority, -rank, media))

    if not candidates:
        raise ValueError("没有找到符合 audioType 的 MV 音频流")

    _, _, selected = sorted(candidates, key=lambda item: (item[0], item[1]))[0]
    return MusicVideoStream(url=urljoin(master_url, selected.uri), label=selected.group_id)


async def extract_encrypted_mv_stream(playlist_url: str) -> EncryptedMusicVideoStream:
    stream = m3u8.loads(await it(WebAPI).download_m3u8(playlist_url), uri=playlist_url)
    key_uri = next(
        (
            key.uri
            for key in stream.keys
            if key
            and key.uri
            and getattr(key, "keyformat", "") == "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"
        ),
        None,
    )
    if not key_uri:
        raise ValueError("MV 播放列表缺少 Widevine key 信息")
    key_parts = key_uri.split(",", 1)
    if len(key_parts) != 2:
        raise ValueError("MV Widevine key 信息格式无效")

    segment_urls = []
    if stream.segment_map:
        segment_urls.append(stream.segment_map[0].absolute_uri)
    segment_urls.extend(segment.absolute_uri for segment in stream.segments if segment)
    if not segment_urls:
        raise ValueError("MV 播放列表没有可下载的媒体分片")

    return EncryptedMusicVideoStream(key_uri=key_uri, pssh_base64=key_parts[1], segment_urls=segment_urls)


async def download_segment_urls(segment_urls: list[str], output_path: Path, parallel_num: int) -> None:
    timeout = httpx.Timeout(20.0, read=120.0, connect=20.0, pool=30.0)
    semaphore = asyncio.Semaphore(max(1, parallel_num))
    proxy = it(Config).download.proxy or None

    async with httpx.AsyncClient(proxy=proxy, timeout=timeout) as client:
        async def fetch(index: int, url: str) -> tuple[int, bytes]:
            response = await client.get(url)
            response.raise_for_status()
            it(Measurer).record_download(len(response.content))
            return index, response.content

        def schedule(index: int) -> asyncio.Task:
            async def limited_fetch():
                async with semaphore:
                    return await fetch(index, segment_urls[index])

            return asyncio.create_task(limited_fetch())

        pending = set()
        next_schedule = 0
        while next_schedule < min(len(segment_urls), max(1, parallel_num)):
            pending.add(schedule(next_schedule))
            next_schedule += 1

        next_write = 0
        buffered_parts = {}
        with open(output_path, "wb") as file:
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    index, data = task.result()
                    buffered_parts[index] = data
                    if next_schedule < len(segment_urls):
                        pending.add(schedule(next_schedule))
                        next_schedule += 1

                while next_write in buffered_parts:
                    file.write(buffered_parts.pop(next_write))
                    next_write += 1


async def acquire_mv_decryption_key(adam_id: str, stream: EncryptedMusicVideoStream, media_user_token: str) -> str:
    wv_decrypt = WidevineDecrypt()
    challenge = wv_decrypt.generate_challenge_from_pssh(stream.pssh_base64)
    license_data = await it(WebAPI).acquire_web_playback_license(
        adam_id=adam_id,
        challenge=challenge,
        uri=stream.key_uri,
        media_user_token=media_user_token,
    )
    keys = wv_decrypt.generate_key(license_data)
    for key in keys:
        key_type = str(getattr(key, "type", "")).upper()
        key_value = getattr(key, "key", None)
        if key_value and key_type != "SIGNING":
            return key_value.hex()
    raise ValueError("MV 授权返回中没有可用的内容密钥")


async def decrypt_mv_playlist(adam_id: str, playlist_url: str, output_path: Path,
                              media_user_token: str, logger=None, label: str = "MV") -> None:
    stream = await extract_encrypted_mv_stream(playlist_url)
    key = await acquire_mv_decryption_key(adam_id, stream, media_user_token)
    encrypted_path = output_path.with_name(f"{output_path.stem}_encrypted{output_path.suffix}")
    await download_segment_urls(stream.segment_urls, encrypted_path, it(Config).musicVideo.segmentParallelNum)
    if logger:
        logger.logger.info(f"Decrypting {label}...")
    result = subprocess.run(
        ["mp4decrypt", "--key", f"1:{key}", encrypted_path.absolute(), output_path.absolute()],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    encrypted_path.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"MV 解密失败: {result.stderr.decode(errors='ignore')}")


def get_music_video_name_and_dir_path(metadata: MusicVideoMetadata) -> tuple[str, Path]:
    params = metadata.path_params()
    file_name = it(Config).musicVideo.fileNameFormat.format(**params)
    dir_path = Path(it(Config).musicVideo.dirPathFormat.format(**params))
    file_name = get_valid_filename(file_name)
    is_abs = dir_path.is_absolute()
    sanitized_parts = [
        part if i == 0 and is_abs else get_valid_dir_name(part)
        for i, part in enumerate(dir_path.parts)
    ]
    return file_name, Path(*sanitized_parts)


async def download_music_video_cover(metadata: MusicVideoMetadata, temp_dir: Path) -> Path | None:
    if not metadata.cover_url:
        return None
    cover = await it(WebAPI).get_cover(
        metadata.cover_url,
        it(Config).download.coverFormat,
        it(Config).download.coverSize,
    )
    metadata.cover = cover
    cover_path = temp_dir / f"{uuid.uuid4().hex}.{it(Config).download.coverFormat}"
    with open(cover_path, "wb") as file:
        file.write(cover)
    return cover_path


def mux_music_video(video_path: Path, audio_path: Path, output_path: Path,
                    metadata: MusicVideoMetadata, cover_path: Path | None) -> None:
    result = subprocess.run(
        [
            "MP4Box",
            "-itags", metadata.to_itags(cover_path),
            "-quiet",
            "-add", video_path.absolute(),
            "-add", audio_path.absolute(),
            "-keep-utc",
            "-new", output_path.absolute(),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(f"MV 合并失败: {result.stderr.decode(errors='ignore')}")


async def save_music_video(adam_id: str, master_m3u8_url: str, metadata: MusicVideoMetadata,
                           logger, media_user_token: str) -> Path:
    master_text = await it(WebAPI).download_m3u8(master_m3u8_url)
    video_stream = select_mv_video_stream(master_text, master_m3u8_url, it(Config).musicVideo.maxHeight)
    audio_stream = select_mv_audio_stream(master_text, master_m3u8_url, it(Config).musicVideo.audioType)
    logger.logger.info(f"Selected MV video: {video_stream.label}")
    logger.logger.info(f"Selected MV audio: {audio_stream.label}")

    file_name, dir_path = get_music_video_name_and_dir_path(metadata)
    os.makedirs(dir_path.absolute(), exist_ok=True)
    output_path = dir_path / f"{file_name}.mp4"
    if output_path.exists():
        logger.logger.info("MV already exists")
        return output_path.absolute()

    with TemporaryDirectory() as temp_name:
        temp_dir = Path(temp_name)
        video_path = temp_dir / f"{adam_id}_video.mp4"
        audio_path = temp_dir / f"{adam_id}_audio.mp4"

        logger.logger.info("Downloading MV video...")
        await decrypt_mv_playlist(adam_id, video_stream.url, video_path, media_user_token, logger, "MV video")
        logger.logger.info("Downloading MV audio...")
        await decrypt_mv_playlist(adam_id, audio_stream.url, audio_path, media_user_token, logger, "MV audio")
        logger.logger.info("Remuxing MV...")
        cover_path = await download_music_video_cover(metadata, temp_dir)
        await run_sync(mux_music_video, video_path, audio_path, output_path, metadata, cover_path)

    return output_path.absolute()
