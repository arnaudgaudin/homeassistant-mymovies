"""Minimal async client for the My Movies cloud API (api.mymovies.dk, SOAP 1.1).

Authentication uses the account's own username and password; the HandShake
parameter is sent empty. Only the user's own collection and watched state are read
or written.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import aiohttp

API_URL = "https://api.mymovies.dk/default.asmx"
API_NS = "https://api.mymovies.dk/"
CLIENT_NAME = "homeassistant-mymovies"
CLIENT_VERSION = "0.1.0"
TIMEOUT = aiohttp.ClientTimeout(total=60)


class MyMoviesError(Exception):
    """The API could not be reached or returned an unexpected answer."""


class MyMoviesAuthError(MyMoviesError):
    """The API rejected the credentials."""


@dataclass(slots=True)
class CollectionTitle:
    """One disc title in the user's collection, as listed by GetTitlesInCollection."""

    id: str
    collection_number: int
    watched: bool
    group: str
    added: str
    data_changed: str
    covers_changed: str


@dataclass(slots=True)
class BoxSetChild:
    """One film inside a box set of the collection."""

    id: str
    parent_id: str
    title: str
    original_title: str
    year: int | None
    edition: str
    disc_type: str
    thumbnail: str  # My Movies cover URL (200 px wide at best)


class MyMoviesClient:
    """Talk to the My Movies SOAP API with the account's credentials."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password

    async def _post(self, operation: str, params: dict[str, object]) -> ET.Element:
        """Call one SOAP operation and return the parsed envelope."""
        inner = "".join(f"<{k}>{escape(str(v))}</{k}>" for k, v in params.items())
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<soap:Body><{operation} xmlns="{API_NS}">{inner}</{operation}></soap:Body>'
            "</soap:Envelope>"
        )
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f"{API_NS}{operation}",
        }
        try:
            async with self._session.post(
                API_URL, data=body.encode("utf-8"), headers=headers, timeout=TIMEOUT
            ) as resp:
                text = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MyMoviesError(f"{operation}: {err}") from err

        try:
            return ET.fromstring(text)
        except ET.ParseError as err:
            raise MyMoviesError(f"{operation}: invalid XML answer ({text[:200]})") from err

    async def _call(
        self, operation: str, params: dict[str, object], *, refusal_means_auth: bool = False
    ) -> ET.Element:
        """Call one SOAP operation and return its <Response> element (status ok).

        refusal_means_auth: the operation is never locked for a valid account, so any
        refusal means bad credentials (an unknown username answers passwordchanged="false").
        """
        root = await self._post(operation, params)
        # The result wraps real nested XML; <Response> carries xmlns="" (no namespace).
        response = next((el for el in root.iter() if el.tag == "Response"), None)
        if response is None:
            raise MyMoviesError(f"{operation}: no Response element")
        if response.get("status") != "ok":
            # Wrong credentials answer passwordchanged="true"; operations reserved to
            # the official apps answer validationfailed="true" with passwordchanged="false".
            if refusal_means_auth or response.get("passwordchanged") == "true":
                raise MyMoviesAuthError(f"{operation}: credentials rejected")
            raise MyMoviesError(f"{operation}: refused ({dict(response.attrib)})")
        return response

    def _auth(self) -> dict[str, object]:
        return {"HandShake": "", "UserName": self._username, "Password": self._password}

    async def async_get_titles(self) -> list[CollectionTitle]:
        """Return every disc title in the collection with its watched flag."""
        response = await self._call(
            "GetTitlesInCollection",
            {
                **self._auth(),
                "Limit": 100000,
                "Client": CLIENT_NAME,
                "Version": CLIENT_VERSION,
                "Locale": 0,
            },
            refusal_means_auth=True,
        )
        titles = []
        for el in response.iter("Title"):
            number = el.get("CollectionNumber") or ""
            titles.append(
                CollectionTitle(
                    id=el.get("ID", ""),
                    collection_number=int(number) if number.lstrip("-").isdigit() else -1,
                    watched=el.get("Watched") == "True",
                    group=el.get("Group", ""),
                    added=el.get("Added", ""),
                    data_changed=el.get("DataChanged", ""),
                    covers_changed=el.get("CoversChanged", ""),
                )
            )
        return titles

    async def async_get_box_set_children(self) -> dict[str, list[BoxSetChild]]:
        """Films of every box set in the collection, keyed by lower-case box set ID."""
        response = await self._call(
            "GetBoxSetChildTitlesForUser",
            {
                "Handshake": "",
                "UserName": self._username,
                "Password": self._password,
                "Reference": "",
                "Locale": 0,
            },
        )
        box_sets: dict[str, list[BoxSetChild]] = {}
        for el in response.iter("Title"):
            parent = (el.get("ParentID") or "").lower()
            if not parent:
                continue
            year = el.get("Year") or ""
            box_sets.setdefault(parent, []).append(
                BoxSetChild(
                    id=el.get("ChildID", ""),
                    parent_id=parent,
                    title=el.get("Title", ""),
                    original_title=el.get("OriginalTitle", ""),
                    year=int(year) if year.isdigit() else None,
                    edition=(el.get("Edition") or "").strip(),
                    disc_type=el.get("Type", ""),
                    thumbnail=el.get("BigThumbnail") or el.get("Thumbnail") or "",
                )
            )
        for children in box_sets.values():
            children.sort(key=lambda c: (c.year or 0, c.title))
        return box_sets

    async def async_mark_watched(self, title_id: str, when: datetime, notes: str = "") -> None:
        """Log one viewing of a title (sets its watched flag)."""
        await self._call(
            "AddTitleWatchedV2",
            {
                **self._auth(),
                "TitleId": title_id,
                "DateWatched": when.strftime("%Y-%m-%dT%H:%M:%S"),
                "Name": "",
                "Notes": notes,
                "How": "",
                "Locale": 0,
            },
        )

    async def async_clear_watched(self, title_id: str) -> None:
        """Remove every logged viewing of a title (clears its watched flag)."""
        await self._call("ClearTitleWatched", {**self._auth(), "TitleId": title_id, "Locale": 0})

    async def async_get_thumbnail(self, title_id: str) -> bytes | None:
        """Return the cover thumbnail (JPEG) of a title, or None when it has none."""
        root = await self._post("GetTitleThumbnail", {"Id": title_id, "Locale": 0})
        result = next((el for el in root.iter() if el.tag.endswith("GetTitleThumbnailResult")), None)
        if result is None or not (result.text or "").strip():
            return None
        try:
            return base64.b64decode(result.text)
        except binascii.Error as err:
            raise MyMoviesError(f"GetTitleThumbnail: invalid image data for {title_id}") from err
