"""Small, deterministic LRC parser and translation alignment."""

from __future__ import annotations

from bisect import bisect_right
import codecs
from dataclasses import dataclass
from pathlib import Path
import re


TIME_TAG = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]")
OFFSET_TAG = re.compile(r"\[offset:\s*([+-]?\d+)\s*\]", re.IGNORECASE)
INLINE_TAG = re.compile(r"<\d{1,3}:\d{2}(?:[.:]\d{1,3})?>")
YRC_ROW = re.compile(r"^\[(\d+),\d+\](.*)$")
YRC_WORD = re.compile(r"\(\d+,\d+(?:,\d+)?\)")


@dataclass(frozen=True)
class LyricLine:
    time_ms: int
    text: str
    translation: str = ""


def _fraction_ms(value: str | None) -> int:
    if not value:
        return 0
    return int((value + "00")[:3])


def parse_lrc(content: str) -> list[LyricLine]:
    """Parse ordinary LRC, including multiple timestamps and offset tags.

    Enhanced LRC inline tags are removed; this app does not claim word timing.
    """
    offset_match = OFFSET_TAG.search(content)
    offset = int(offset_match.group(1)) if offset_match else 0
    lines: list[LyricLine] = []
    for raw in content.splitlines():
        tags = list(TIME_TAG.finditer(raw))
        if not tags:
            continue
        body = INLINE_TAG.sub("", raw[tags[-1].end():]).strip()
        if not body:
            continue
        for tag in tags:
            minute, second = int(tag.group(1)), int(tag.group(2))
            if second >= 60:
                continue
            at = max(0, (minute * 60 + second) * 1000 + _fraction_ms(tag.group(3)) + offset)
            lines.append(LyricLine(at, body))
    return sorted(lines, key=lambda line: line.time_ms)


def parse_yrc_as_lines(content: str) -> list[LyricLine]:
    """Keep YRC line timing when no LRC exists; do not invent word highlighting."""
    lines = []
    for raw in content.splitlines():
        match = YRC_ROW.match(raw.strip())
        if match:
            body = YRC_WORD.sub("", match.group(2)).strip()
            if body:
                lines.append(LyricLine(int(match.group(1)), body))
    return sorted(lines, key=lambda line: line.time_ms)


def read_text(path: Path) -> str:
    content = path.read_bytes()
    if content.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return content.decode("utf-16")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeError:
            continue
    raise ValueError(f"无法识别歌词编码：{path.name}")


def attach_translations(lines: list[LyricLine], translated: list[LyricLine], tolerance_ms: int = 600) -> list[LyricLine]:
    """Match translated lines by time without reusing one translation twice."""
    remaining = list(enumerate(translated))
    result: list[LyricLine] = []
    for line in lines:
        candidates = [(abs(item.time_ms - line.time_ms), index, item)
                      for index, item in remaining if abs(item.time_ms - line.time_ms) <= tolerance_ms]
        if candidates:
            _, chosen, translation = min(candidates, key=lambda item: (item[0], item[1]))
            remaining = [(index, item) for index, item in remaining if index != chosen]
            result.append(LyricLine(line.time_ms, line.text, translation.text))
        else:
            result.append(line)
    return result


def active_index(lines: list[LyricLine], position_ms: int, offset_ms: int = 0) -> int:
    if not lines:
        return -1
    return bisect_right([line.time_ms for line in lines], position_ms - offset_ms) - 1
