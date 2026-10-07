"""Playback clock that reconciles coarse remote samples without rewinding.

Repeated slider readings are not new playback anchors. Small corrections
cannot undo an already displayed lyric transition. Real seeks, track changes,
pause and transport changes remain authoritative.
"""
import math
import time


class FollowClock:
    STALE_SECONDS = 1.0
    BACKWARD_SEEK_MS = 60

    def __init__(self):
        self.reset()

    def reset(self):
        self.epoch = None
        self.last_sample = float("-inf")
        self.raw_position = 0
        self.anchor_position = 0
        self.anchor_time = 0
        self.changed_at = 0
        self.duration = 0
        self.playing = False
        self.rate = 1.0
        self.pending_seek = None

    def expect_seek(self, target_ms, now=None):
        self.pending_seek = (int(target_ms), time.monotonic() if now is None else now)

    def cancel_seek(self):
        self.pending_seek = None

    def position(self, now=None):
        now = time.monotonic() if now is None else now
        elapsed = max(0, min(now, self.changed_at + self.STALE_SECONDS) - self.anchor_time)
        position = self.anchor_position + (elapsed * 1000 * self.rate if self.playing else 0)
        if self.playing:
            # Buffering/coarse readings must not let prediction drift indefinitely.
            ceiling = max(self.anchor_position, self.raw_position + self.STALE_SECONDS * 1000 * self.rate)
            position = min(position, ceiling)
        return round(min(self.duration, max(0, position)))

    def update(self, snapshot, now=None):
        now = time.monotonic() if now is None else now
        sampled = float(snapshot.get("sample", now))
        if not math.isfinite(sampled) or sampled < self.last_sample:
            return False
        sampled = min(sampled, now)
        if not snapshot.get("connected") or not snapshot.get("timeline"):
            self.reset()
            self.last_sample = sampled
            return True
        epoch = (snapshot.get("identity", ""), snapshot.get("transport", ""))
        duration = max(0, int(snapshot.get("duration") or 0))
        raw = min(duration, max(0, int(snapshot.get("position") or 0)))
        rate = float(snapshot.get("rate") or 1)
        rate = rate if math.isfinite(rate) and rate > 0 else 1
        playing = bool(snapshot.get("playing"))
        changed = raw != self.raw_position
        new_epoch = epoch != self.epoch
        acknowledged = False
        if self.pending_seek and not new_epoch:
            target, requested = self.pending_seek
            advanced = max(0, sampled - requested) * 1000 * rate if playing else 0
            acknowledged = (target - 100 <= raw <= target + advanced + 100
                            and (changed or raw == target))
            if acknowledged or now - requested >= 1.5:
                self.pending_seek = None
            elif playing == self.playing:
                # Old samples can arrive before the seek command is applied.
                self.last_sample = sampled
                return True
        previous = self.position(sampled)
        reset = (new_epoch or acknowledged or raw < self.raw_position - self.BACKWARD_SEEK_MS
                 or raw - previous > 1500 or playing != self.playing)
        if reset or changed or rate != self.rate:
            self.anchor_position = raw if reset or not playing else max(raw, previous)
            self.anchor_time = sampled
            self.changed_at = sampled
        self.epoch = epoch
        self.raw_position = raw
        self.last_sample = sampled
        self.duration = duration
        self.playing = playing
        self.rate = rate
        return True
