"""Local eSpeak NG IPA. No audio synthesis and no network requests."""
import ctypes
from functools import lru_cache
from pathlib import Path
import sys
import threading

_lock = threading.RLock()


@lru_cache(maxsize=1)
def _engine():
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    directory = root / "vendor/espeak-ng"
    # Only load dependencies from this DLL's directory and Windows system dirs.
    # The host's PATH can contain incompatible tool-runtime DLLs.
    lib = ctypes.CDLL(str(directory / "libespeak-ng.dll"), winmode=0x100 | 0x800)
    lib.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.espeak_Initialize.restype = ctypes.c_int
    lib.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
    lib.espeak_SetVoiceByName.restype = ctypes.c_int
    lib.espeak_TextToPhonemes.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_int, ctypes.c_int]
    lib.espeak_TextToPhonemes.restype = ctypes.c_char_p
    if lib.espeak_Initialize(2, 0, str(directory).encode("utf-8"), 0x8000) < 0:
        raise RuntimeError("离线音标词库未加载，请保留完整程序文件夹")
    return lib


@lru_cache(maxsize=4096)
def ipa(text, language):
    voices = {"fr": "fr", "en": "en-us", "ru": "ru", "ko": "ko"}
    if language not in voices or not text.strip():
        return ""
    with _lock:
        lib = _engine()
        if lib.espeak_SetVoiceByName(voices[language].encode()) != 0:
            raise RuntimeError("离线音标引擎不支持所选语言")
        buffer = ctypes.create_string_buffer(text.encode("utf-8"))
        pointer = ctypes.c_void_p(ctypes.addressof(buffer))
        result = []
        while pointer.value:
            previous = pointer.value
            output = lib.espeak_TextToPhonemes(ctypes.byref(pointer), 1, 2)
            if output:
                result.append(output.decode("utf-8"))
            if pointer.value == previous:
                raise RuntimeError("音标引擎未能处理当前文字")
        return " · ".join(result).strip()
