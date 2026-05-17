import pytest
from pydantic import ValidationError

from src.web.schemas import DownloadRequest, TaskSnapshot


def test_download_request_defaults_force_to_false():
    payload = DownloadRequest(url="https://music.apple.com/jp/song/caribbean-blue/339592231")

    assert payload.codec == "alac"
    assert payload.force is False


def test_download_request_rejects_blank_url():
    with pytest.raises(ValidationError):
        DownloadRequest(url="   ")


def test_task_snapshot_defaults_to_idle_state():
    snapshot = TaskSnapshot()

    assert snapshot.state == "idle"
    assert snapshot.logs == []
    assert snapshot.saved_path is None
