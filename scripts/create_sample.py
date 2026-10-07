"""Generate a synthetic cue track; no copyrighted recordings are included."""

from pathlib import Path
import math
import struct
import wave


target = Path(__file__).resolve().parent.parent / "samples" / "practice.wav"
rate = 16000
duration = 12
with wave.open(str(target), "wb") as output:
    output.setnchannels(1)
    output.setsampwidth(2)
    output.setframerate(rate)
    for i in range(rate * duration):
        seconds = i / rate
        cue = seconds % 2.5
        envelope = max(0, 1 - cue / .22) if cue < .22 else 0
        value = int(5000 * envelope * math.sin(2 * math.pi * 440 * seconds))
        output.writeframesraw(struct.pack("<h", value))
print(target)
