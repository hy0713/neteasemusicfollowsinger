"""Local NetEase CDP or Windows media-session follower."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from queue import Empty, SimpleQueue
import threading
import time
from urllib.parse import urlparse

from PySide6.QtCore import QThread, Signal
import requests
import websocket


PORT = 9222
PAGE_URL = "orpheus://orpheus/pub/app.html"


# This adapter reads the mounted player component on NetEase 3.x. It is
# deliberately limited to the footer player and may need updating for new UI.
SNAPSHOT_JS = r"""(() => {
  const footer = document.querySelector('footer');
  const slider = footer?.querySelector('input[type="range"]');
  if (!slider) return null;
  const key = Object.keys(slider).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
  let fiber = key && slider[key];
  for (let i = 0; fiber && i < 28; i++, fiber = fiber.return) {
    const p = fiber.memoizedProps;
    if (!p?.curTrack || typeof p.dispatch !== 'function') continue;
    const track = p.curTrack;
    const button = footer.querySelector('#btn_pc_minibar_play, [data-testid="tid_playbar_play_btn"]');
    const icon = button?.querySelector('[role="img"]')?.getAttribute('aria-label');
    const duration = Number(slider.max) * 1000;
    const position = Number(slider.value) * 1000;
    if (!Number.isFinite(duration) || duration <= 0 || !Number.isFinite(position)) return null;
    let ancestor = fiber, state = null;
    for (let j = 0; ancestor && j < 100; j++, ancestor = ancestor.return) {
      if (ancestor.memoizedProps?.store?.getState) {state = ancestor.memoizedProps.store.getState().playing; break;}
    }
    return {trackId: String(track.id), title: track.name || '',
      artist: (track.artists || track.ar || []).map(a => a.name).join(' / '),
      position: position, duration: duration, playing: icon === 'pause',
      canSeek: !slider.disabled, canPlay: !!button && !button.disabled && button.getAttribute('aria-disabled') !== 'true',
      canRate: !!state?.isEnableSpeedTrack && state.resourceType === 'track',
      rate: state?.playingSpeedTrack || 1, transport: 'direct'};
  }
  return null;
})()"""

COMMAND_JS = r"""(async () => {
  const name = __NAME__, target = __TARGET__, expected = __EXPECTED__;
  const footer = document.querySelector('footer');
  const slider = footer?.querySelector('input[type="range"]');
  const key = slider && Object.keys(slider).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
  let fiber = key && slider[key], props = null;
  for (let i = 0; fiber && i < 28; i++, fiber = fiber.return) {
    if (fiber.memoizedProps?.curTrack && typeof fiber.memoizedProps.dispatch === 'function') {
      props = fiber.memoizedProps; break;
    }
  }
  if (!props || String(props.curTrack.id) !== expected) throw Error('歌曲已切换');
  const button = footer.querySelector('#btn_pc_minibar_play, [data-testid="tid_playbar_play_btn"]');
  if (name === 'seek') {
    if (slider.disabled || !Number.isFinite(target)) throw Error('当前歌曲不可跳转');
    await props.dispatch({type: 'playing/setPlayingPosition', payload: {duration: Math.max(0, Math.min(Number(slider.max), target / 1000))}});
  } else if (name === 'toggle') {
    if (!button || button.disabled || button.getAttribute('aria-disabled') === 'true') throw Error('播放按钮不可用');
    button.click();
  } else if (name === 'rate') {
    let ancestor = fiber, state = null;
    for (let j = 0; ancestor && j < 100; j++, ancestor = ancestor.return) {
      if (ancestor.memoizedProps?.store?.getState) {state = ancestor.memoizedProps.store.getState().playing; break;}
    }
    if (!state?.isEnableSpeedTrack || state.resourceType !== 'track' || !Number.isFinite(target) || target < .5 || target > 1.5) throw Error('当前客户端不支持歌曲倍速');
    await props.dispatch({type: 'playing/switchPlayingSpeed', payload: {playingSpeed: target, isTrack: true}});
  } else throw Error('未知操作');
  return true;
})()"""


class DirectClient:
    def __init__(self):
        self.http = requests.Session()
        self.http.trust_env = False
        self.ws = None
        self.sequence = 0
        self.retry_at = 0.0

    def close(self):
        if self.ws:
            self.ws.close()
        self.ws = None

    def _connect(self):
        response = self.http.get(f"http://127.0.0.1:{PORT}/json", timeout=.5,
                                 allow_redirects=False)
        response.raise_for_status()
        pages = response.json()
        page = next((item for item in pages if item.get("type") == "page"
                     and item.get("url", "").split("#")[0] == PAGE_URL), None)
        if page is None:
            raise ValueError("调试端口不是网易云主页面")
        address = page.get("webSocketDebuggerUrl", "")
        parsed = urlparse(address)
        if parsed.scheme != "ws" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port != PORT:
            raise ValueError("拒绝连接非本机通道")
        self.ws = websocket.create_connection(address, timeout=2, suppress_origin=True,
                                              http_no_proxy=["127.0.0.1", "localhost"])

    def evaluate(self, expression: str):
        self.sequence += 1
        self.ws.send(json.dumps({"id": self.sequence, "method": "Runtime.evaluate",
                                 "params": {"expression": expression, "returnByValue": True,
                                            "awaitPromise": True}}))
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            message = json.loads(self.ws.recv())
            if message.get("id") != self.sequence:
                continue
            result = message.get("result", {})
            if message.get("error") or result.get("exceptionDetails"):
                raise ValueError("客户端未接受指令，可能已切换歌曲或界面版本不兼容")
            return result.get("result", {}).get("value")
        raise TimeoutError("客户端响应超时")

    def poll(self) -> dict | None:
        if not self.ws and time.monotonic() < self.retry_at:
            return None
        try:
            if not self.ws:
                self._connect()
            return self.evaluate(SNAPSHOT_JS)
        except Exception:
            self.close()
            self.retry_at = time.monotonic() + 3
            return None

    def command(self, name: str, target_ms: int, expected_id: str):
        expression = (COMMAND_JS.replace("__NAME__", json.dumps(name))
                      .replace("__TARGET__", json.dumps(float(target_ms), allow_nan=False))
                      .replace("__EXPECTED__", json.dumps(expected_id)))
        if self.evaluate(expression) is not True:
            raise ValueError("客户端未确认操作")


class CloudFollower(QThread):
    snapshot = Signal(dict)
    problem = Signal(str)

    def __init__(self):
        super().__init__()
        self._stop = threading.Event()
        self._commands: SimpleQueue[tuple[str, int, str]] = SimpleQueue()
        self.direct = DirectClient()
        self.current: dict = {}

    def send(self, command: str, target_ms: int = 0, identity: str = ""):
        self._commands.put((command, target_ms, identity))

    def stop(self):
        self._stop.set()
        self.wait(3500)

    def run(self):
        try:
            asyncio.run(self._watch())
        finally:
            self.direct.close()

    async def _watch(self):
        try:
            from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
            manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        except Exception as exc:
            manager = None
            media_error = f"Windows 媒体接口不可用：{exc}"
            self.problem.emit(media_error)
        else:
            media_error = ""
        session = None
        last_state = ""
        while not self._stop.is_set():
            try:
                direct = self.direct.poll()
                if direct:
                    state = {**direct, "connected": True, "timeline": True,
                             "identity": direct["trackId"], "sample": time.monotonic()}
                else:
                    session = self._find_session(manager)
                    state = await self._read_session(session) if session else {"connected": False,
                                "message": media_error or "未检测到网易云播放会话。"}
                self.current = state
                if state != last_state:
                    self.snapshot.emit(state)
                    last_state = state.copy()
                while True:
                    try:
                        command, target_ms, identity = self._commands.get_nowait()
                    except Empty:
                        break
                    try:
                        if identity != self.current.get("identity"):
                            raise ValueError("歌曲已切换，请重试")
                        if self.current.get("transport") == "direct":
                            self.direct.command(command, target_ms, identity)
                        else:
                            await self._session_command(session, command, target_ms)
                    except Exception as exc:
                        self.problem.emit(str(exc))
            except Exception as exc:
                self.problem.emit(f"网易云跟随暂不可用：{exc}")
            await asyncio.sleep(.25)

    @staticmethod
    def _find_session(manager):
        if manager is None:
            return None
        for item in manager.get_sessions():
            identifier = item.source_app_user_model_id.lower()
            if any(name in identifier for name in ("cloudmusic", "netease", "orpheus")):
                return item
        return None

    @staticmethod
    async def _read_session(session):
        media = await session.try_get_media_properties_async()
        timeline = session.get_timeline_properties()
        info = session.get_playback_info()
        duration = max(0, round(timeline.end_time.total_seconds() * 1000))
        position = max(0, round(timeline.position.total_seconds() * 1000))
        valid = duration > 0 and timeline.last_updated_time.year > 2000
        playing = int(info.playback_status) == 4
        rate = info.playback_rate or 1
        if valid and playing:
            elapsed = (datetime.now(timezone.utc) - timeline.last_updated_time).total_seconds()
            position = min(duration, max(0, round(position + max(0, elapsed) * 1000 * rate)))
        identity = f"{media.title}|{media.artist}|{media.album_title}"
        return {"connected": True, "title": media.title or "", "artist": media.artist or "",
                "position": position, "duration": duration, "playing": playing,
                "canSeek": bool(info.controls.is_playback_position_enabled) and valid,
                "canPlay": bool(info.controls.is_play_pause_toggle_enabled),
                "canRate": bool(info.controls.is_playback_rate_enabled),
                "rate": rate,
                "timeline": valid, "identity": identity, "transport": "smtc",
                "sample": time.monotonic()}

    @staticmethod
    async def _session_command(session, name: str, target_ms: int):
        if session is None:
            raise ValueError("网易云会话已断开")
        if name == "toggle":
            success = await session.try_toggle_play_pause_async()
        elif name == "seek":
            success = await session.try_change_playback_position_async(int(target_ms * 10000))
        elif name == "rate":
            success = await session.try_change_playback_rate_async(float(target_ms))
        else:
            raise ValueError("未知操作")
        if not success:
            raise ValueError("当前网易云版本未接受控制")
