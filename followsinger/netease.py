"""Public lyric lookup. No account cookies, audio downloads, or login data."""

from __future__ import annotations

from difflib import SequenceMatcher
import re
from urllib.parse import parse_qs, urlparse

import requests

from .lyrics import LyricLine, attach_translations, parse_lrc, parse_yrc_as_lines


def song_id_from_input(value: str) -> str:
    value = value.strip()
    if value.isdigit():
        return value
    parsed = urlparse(value)
    if parsed.hostname not in {"music.163.com", "y.music.163.com"}:
        raise ValueError("请输入网易云歌曲 ID 或 music.163.com 歌曲链接。")
    match = re.search(r"(?:^|[?&#])id=(\d+)", value)
    if not match:
        ids = parse_qs(parsed.query).get("id", [])
        if not ids or not ids[0].isdigit():
            raise ValueError("链接中没有歌曲 ID。")
        return ids[0]
    return match.group(1)


def _normal(text: str) -> str:
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE).casefold()


def select_match(candidates: list[dict], title: str, artist: str, duration_ms: int = 0) -> dict | None:
    """Accept a public search hit only when metadata resembles the playing track."""
    wanted = _normal(title)
    artist_key = _normal(artist.split("/")[0])
    ranked = []
    for song in candidates:
        title_score = SequenceMatcher(None, wanted, _normal(song.get("name", ""))).ratio()
        artists = " ".join(item.get("name", "") for item in song.get("artists", []))
        artist_score = SequenceMatcher(None, artist_key, _normal(artists)).ratio() if artist_key else 1.0
        candidate_duration = int(song.get("duration") or 0)
        delta = abs(candidate_duration - duration_ms) if duration_ms and candidate_duration else 0
        duration_score = 1.0 if not delta else max(0.0, 1 - delta / 15000)
        score = title_score * .65 + artist_score * .25 + duration_score * .10
        ranked.append((score, title_score, artist_score, song))
    if not ranked:
        return None
    score, title_score, artist_score, song = max(ranked, key=lambda item: item[0])
    if title_score < .75 or (artist_key and artist_score < .5) or score < .72:
        return None
    return song


class NeteaseLyrics:
    def __init__(self):
        self.cache: dict[str, list[LyricLine]] = {}

    def _json(self, url: str, params: dict) -> dict:
        response = requests.get(url, params=params, timeout=(4, 10),
                                headers={"User-Agent": "Mozilla/5.0 FollowSinger/0.1",
                                         "Referer": "https://music.163.com/"})
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 200:
            raise ValueError("网易云接口暂不可用，可手动导入 LRC。")
        return data

    def identify(self, title: str, artist: str, duration_ms: int = 0) -> str | None:
        data = self._json("https://music.163.com/api/search/get",
                          {"s": f"{title} {artist}", "type": 1, "limit": 12})
        matched = select_match(data.get("result", {}).get("songs", []), title, artist, duration_ms)
        return str(matched["id"]) if matched else None

    def lyrics(self, song_id: str) -> list[LyricLine]:
        if not re.fullmatch(r"\d{1,20}", song_id):
            raise ValueError("无效歌曲 ID。")
        if song_id in self.cache:
            return self.cache[song_id]
        data = self._json("https://music.163.com/api/song/lyric",
                          {"id": song_id, "lv": -1, "tv": -1, "yv": -1})
        original = parse_lrc(data.get("lrc", {}).get("lyric", ""))
        if not original:
            original = parse_yrc_as_lines(data.get("yrc", {}).get("lyric", ""))
        if not original:
            raise ValueError("这首歌没有逐行歌词，可手动导入 LRC。")
        translation = parse_lrc(data.get("tlyric", {}).get("lyric", ""))
        result = attach_translations(original, translation)
        self.cache[song_id] = result
        return result

    def cover(self, song_id: str) -> bytes:
        if not re.fullmatch(r"\d{1,20}", song_id):
            return b""
        detail = self._json("https://music.163.com/api/song/detail/", {"ids": f"[{song_id}]"})
        song = detail.get("songs", [{}])[0]
        address = song.get("album", song.get("al", {})).get("picUrl", "")
        parsed = urlparse(address)
        if not parsed.hostname or not parsed.hostname.endswith(".music.126.net"):
            return b""
        address = parsed._replace(scheme="https").geturl()
        with requests.get(address, params={"param": "360y360"}, stream=True,
                          timeout=(4, 8), allow_redirects=False) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_content(65536):
                content.extend(chunk)
                if len(content) > 2 * 1024 * 1024:
                    return b""
        return bytes(content)
