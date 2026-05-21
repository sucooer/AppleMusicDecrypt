# AppleMusicDecrypt

Apple Music decryption tool, inspired by [zhaarey/apple-music-alac-atmos-downloader](https://github.com/zhaarey/apple-music-alac-atmos-downloader)

Discussion Group: https://t.me/apple_music_alac 

# Usage

```shell
# Download song/album with default codec (alac)
download https://music.apple.com/jp/album/nameless-name-single/1688539265
# Or a shorter command
dl https://music.apple.com/jp/album/nameless-name-single/1688539265
# Download song/album with specified codec
dl -c aac https://music.apple.com/jp/song/caribbean-blue/339592231
# Overwrite existing files
dl -f https://music.apple.com/jp/song/caribbean-blue/339592231
# Specify song metadata language
dl -l en-US https://music.apple.com/jp/album/nameless-name-single/1688539265
# Download specify artist's all albums
dl https://music.apple.com/jp/artist/%E3%83%88%E3%82%B2%E3%83%8A%E3%82%B7%E3%83%88%E3%82%B2%E3%82%A2%E3%83%AA/1688539273
# Download specify artist's all songs
dl --include-participate-songs https://music.apple.com/jp/artist/%E3%83%88%E3%82%B2%E3%83%8A%E3%82%B7%E3%83%88%E3%82%B2%E3%82%A2%E3%83%AA/1688539273
# Download all songs of specified playlist
dl https://music.apple.com/jp/playlist/bocchi-the-rock/pl.u-Ympg5s39LRqp
# Download a music video, requires [musicVideo].mediaUserToken in config.toml
dl https://music.apple.com/us/music-video/example/1234567890
# Download multiple songs with the same options, without retyping the command
dl -c aac -l en-US -b
https://music.apple.com/jp/playlist/bocchi-the-rock/pl.u-Ympg5s39LRqp
https://music.apple.com/jp/album/nameless-name-single/1688539265
# Download multiple songs in one line
dl https://music.apple.com/jp/playlist/bocchi-the-rock/pl.u-Ympg5s39LRqp https://music.apple.com/jp/album/nameless-name-single/1688539265
# Check the available quality of the song
quality https://music.apple.com/jp/playlist/bocchi-the-rock/pl.u-Ympg5s39LRqp
# Or a shorter command
qa https://music.apple.com/jp/playlist/bocchi-the-rock/pl.u-Ympg5s39LRqp
# You can hide a column by enabling it in the options.
qa --codec-id https://music.apple.com/jp/playlist/bocchi-the-rock/pl.u-Ympg5s39LRqp
# When you add --invert, it works the opposite way, showing the column for whichever option you enable.
qa --invert --codec-id https://music.apple.com/jp/playlist/bocchi-the-rock/pl.u-Ympg5s39LRqp
```

# Support Codec

- `alac (audio-alac-stereo)`
- `ec3 (audio-atmos / audio-ec3)`
- `ac3 (audio-ac3)`
- `aac (audio-stereo)`
- `aac-binaural (audio-stereo-binaural)`
- `aac-downmix (audio-stereo-downmix)`
- `aac-legacy (audio-stereo, non-lossless audio)`

# Support Link

- Apple Music Song Share Link (https://music.apple.com/jp/album/%E5%90%8D%E3%82%82%E3%81%AA%E3%81%8D%E4%BD%95%E3%82%82%E3%81%8B%E3%82%82/1688539265?i=1688539274)
- Apple Music Album Share Link (https://music.apple.com/jp/album/nameless-name-single/1688539265)
- Apple Music Song Link (https://music.apple.com/jp/song/caribbean-blue/339592231)
- Apple Music Artist Link (https://music.apple.com/jp/artist/%E3%82%A8%E3%83%B3%E3%83%A4/160847)
- Apple Music Playlist Link (https://music.apple.com/jp/playlist/bocchi-the-rock/pl.u-Ympg5s39LRqp)
- Apple Music MV Link (https://music.apple.com/us/music-video/example/1234567890)

# About V2
AppleMusicDecrypt v2 provides support for remote fast decryption through [WorldObservationLog/wrapper](https://github.com/WorldObservationLog/wrapper) and [WorldObservationLog/wrapper-manager](https://github.com/WorldObservationLog/wrapper-manager)

By connecting to a public wrapper-manager instance on the Internet, ripping can be completed without an Apple account or an active Apple Music subscription.

For faster decryption, wrapper-manager can also be deployed locally. The decryption speed of a single wrapper instance can reach up to 40MB/s

A wrapper-manager instance for testing: 
```toml
[instance] # Mantainced by @WorldObservationLog
url = "wm.wol.moe"
secure = true
# or
[instance] # Mantainced by @itouakira
url = "wm1.wol.moe"
secure = true
```

## Run
For Android users: [android-deploy.md](/android-deploy.md)

For Windows users: use [the pre-configured version](https://nightly.link/WorldObservationLog/AppleMusicDecrypt/workflows/win-build/v2/AppleMusicDecrypt-Windows.zip) that works out of the box
```shell
git clone https://github.com/WorldObservationLog/AppleMusicDecrypt.git
cd AppleMusicDecrypt
bash ./tools/install-deps.sh
poetry install
cp config.example.toml config.toml
poetry run python main.py
```

## FAQ
### Song did not pass the integrity check
There are two possible causes for this problem:
1. Potential wrapper decryption error. This problem usually disappears after a few days. You can try restarting the wrapper-manager, changing the wrapper-manager instance, or waiting for a few days.
2. The audio source file provided by Apple Music is damaged. See more: https://t.me/abcthoughts/6294

### The bit depth of the ripped audio file does not match the selected codec
Some audio files provided by Apple Music are incorrectly encoded to a higher bit depth. This does not affect the content of the audio itself.

## Web UI

Run the local web UI:

```bash
poetry run python web_main.py
```

If you use the local virtual environment directly:

```bash
.venv/bin/python web_main.py
```

Open `http://127.0.0.1:9527`.

The Web UI provides:

- Song, album, artist, playlist, and MV download from an Apple Music URL
- Quality lookup
- Live task state, download speed, decrypt speed, and logs
- Album progress display, including total tracks and completed tracks
- Failed-track list for album downloads
- Manual retry for failed album tracks

MV download requires a valid Apple Music `media-user-token` in `config.toml`:

How to get `media-user-token`:

1. Open Apple Music in your browser and sign in.
2. Open Developer Tools.
3. Go to `Application -> Storage -> Cookies -> https://music.apple.com`.
4. Find the Cookie named `media-user-token` and copy its value.

```toml
[musicVideo]
mediaUserToken = "your_media_user_token"
maxHeight = 2160
audioType = "auto"
```

Docker starts the Web UI by default:

```bash
docker build -t applemusicdecrypt-all .
docker run -d --name amd-all --restart unless-stopped -p 9527:9527 -v /path/to/downloads:/app/downloads applemusicdecrypt-all
```

If `/app/config.toml` is missing, the container automatically creates it from `config.example.toml` on startup.

To persist custom settings such as wrapper-manager, notifications, or `media-user-token`, mount your own `config.toml`:

```bash
docker run -d --name amd-all --restart unless-stopped \
  -p 9527:9527 \
  -v /path/to/config.toml:/app/config.toml:ro \
  -v /path/to/downloads:/app/downloads \
  applemusicdecrypt-all
```

You can also use Docker Compose. `docker-compose.yml` always mounts `./config.toml` into the container:

```bash
mkdir -p downloads
docker compose up -d --build
```

### ServerChan3 Notifications

The Web UI can send ServerChan3 notifications when a download completes, when a task fails, or when a track in an album fails.

Edit `config.toml`:

```toml
[notification]
enable = true
serverChan3SendKey = "your_serverchan3_sendkey"
tags = "AppleMusicDecrypt|下载通知"
```

Notification messages include the task name, type, codec, album progress, saved path, failed-track list, and time. The `sendkey` is sensitive; keep it in `config.toml` and do not commit it.
