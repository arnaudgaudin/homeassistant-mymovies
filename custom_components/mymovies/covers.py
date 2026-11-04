"""Covers chosen or uploaded by the user: image checks and files."""

from __future__ import annotations

from pathlib import Path
import re
import struct

from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.core import HomeAssistant

from .const import DOMAIN

MAX_UPLOAD = 10 * 1024 * 1024
_KEY = re.compile(r"^[0-9a-f-]{8,64}$")
_JPEG_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


class InvalidImageError(Exception):
    """The upload is not a JPEG or PNG image of acceptable size."""


def image_size(data: bytes) -> tuple[str, int, int]:
    """(extension, width, height) of a JPEG or PNG image."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        width, height = struct.unpack(">II", data[16:24])
        return "png", width, height
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 <= len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in _JPEG_SOF:
                height, width = struct.unpack(">HH", data[i + 5 : i + 9])
                return "jpg", width, height
            if marker in (0xD8, 0xD9, 0x01) or 0xD0 <= marker <= 0xD7 or marker == 0xFF:
                i += 2 if marker != 0xFF else 1
                continue
            i += 2 + struct.unpack(">H", data[i + 2 : i + 4])[0]
    raise InvalidImageError("not a JPEG or PNG image")


def valid_key(key: str) -> bool:
    """Title and film IDs are lower-case GUIDs: nothing else reaches the file system."""
    return bool(_KEY.match(key))


def covers_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(DOMAIN, "covers"))


def save_upload(hass: HomeAssistant, entry_id: str, key: str, data: bytes) -> dict:
    """Store an uploaded cover; return its override record. Blocking: run in the executor."""
    if not valid_key(key):
        raise InvalidImageError("invalid title")
    if len(data) > MAX_UPLOAD:
        raise InvalidImageError("image larger than 10 MB")
    ext, width, height = image_size(data)
    folder = covers_dir(hass)
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob(f"{entry_id}_{key}.*"):
        old.unlink()
    name = f"{entry_id}_{key}.{ext}"
    (folder / name).write_bytes(data)
    return {"source": "upload", "file": name, "width": width, "height": height}


def read_upload(hass: HomeAssistant, file_id: str) -> bytes:
    """Bytes of an image uploaded through Home Assistant. Blocking: run in the executor."""
    with process_uploaded_file(hass, file_id) as path:
        if path.stat().st_size > MAX_UPLOAD:
            raise InvalidImageError("image larger than 10 MB")
        return path.read_bytes()


def remove_upload(hass: HomeAssistant, name: str) -> None:
    """Delete an uploaded cover file. Blocking."""
    (covers_dir(hass) / Path(name).name).unlink(missing_ok=True)


def remove_entry_uploads(hass: HomeAssistant, entry_id: str) -> None:
    """Delete every uploaded cover of an account. Blocking."""
    folder = covers_dir(hass)
    if folder.is_dir():
        for path in folder.glob(f"{entry_id}_*"):
            path.unlink()
