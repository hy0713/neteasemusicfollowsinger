"""Reversible check against the already-connected desktop player."""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from followsinger.media import DirectClient

c = DirectClient()
before = c.poll()
assert before and before["canPlay"] and before["canRate"], before
identity = before["trackId"]
checks = []
try:
    c.command("rate", .75, identity)
    time.sleep(.35)
    state = c.poll()
    assert state and state["trackId"] == identity and state["rate"] == .75, state
    checks.append("client rate 0.75 acknowledged")
    c.command("toggle", 0, identity)
    time.sleep(.4)
    state = c.poll()
    assert state and state["trackId"] == identity and state["playing"] != before["playing"], state
    checks.append("client play/pause toggled")
finally:
    state = c.poll()
    if state and state["trackId"] == identity:
        if state["playing"] != before["playing"]:
            c.command("toggle", 0, identity)
            time.sleep(.3)
        c.command("rate", before["rate"], identity)
        if not before["playing"]:
            c.command("seek", before["position"], identity)
        time.sleep(.3)
    restored = c.poll()
    c.close()
assert restored and restored["rate"] == before["rate"] and restored["playing"] == before["playing"], restored
print(json.dumps({"passed": True, "checks": checks, "restored": True}))
