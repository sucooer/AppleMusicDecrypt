from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from src.models.song_data import Artwork, PlayParams


class MusicVideoAttributes(BaseModel):
    albumName: Optional[str] = None
    artistName: Optional[str] = None
    artwork: Optional[Artwork] = None
    contentRating: Optional[str] = None
    discNumber: Optional[int] = None
    durationInMillis: Optional[int] = None
    genreNames: List[str] = []
    has4K: Optional[bool] = None
    hasHDR: Optional[bool] = None
    isrc: Optional[str] = None
    name: Optional[str] = None
    playParams: Optional[PlayParams] = None
    releaseDate: Optional[str] = None
    trackNumber: Optional[int] = None
    url: Optional[str] = None


class MusicVideoArtistDatum(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    href: Optional[str] = None


class MusicVideoArtists(BaseModel):
    href: Optional[str] = None
    data: List[MusicVideoArtistDatum] = []


class MusicVideoAlbumAttributes(BaseModel):
    artistName: Optional[str] = None
    copyright: Optional[str] = None
    name: Optional[str] = None
    releaseDate: Optional[str] = None
    trackCount: Optional[int] = None
    upc: Optional[str] = None


class MusicVideoAlbumDatum(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    href: Optional[str] = None
    attributes: Optional[MusicVideoAlbumAttributes] = None


class MusicVideoAlbums(BaseModel):
    href: Optional[str] = None
    data: List[MusicVideoAlbumDatum] = []


class MusicVideoRelationships(BaseModel):
    albums: Optional[MusicVideoAlbums] = None
    artists: Optional[MusicVideoArtists] = None


class MusicVideoDatum(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    href: Optional[str] = None
    attributes: MusicVideoAttributes
    relationships: Optional[MusicVideoRelationships] = None


class MusicVideoData(BaseModel):
    data: List[MusicVideoDatum]
