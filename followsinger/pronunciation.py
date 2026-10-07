"""Reading aids for five languages. These are not singing-voice transcription."""

from __future__ import annotations

from functools import lru_cache
import re


LANGUAGES = {
    "ja": ("日语", "假名 / 罗马音"),
    "en": ("英语", "美式词典 IPA"),
    "ru": ("俄语", "拉丁转写（不标重音）"),
    "fr": ("法语", "法语 IPA（本地生成）"),
    "ko": ("韩语", "韩文罗马字（不含音变）"),
}


def detect_language(text: str) -> str:
    if re.search(r"[\uac00-\ud7af]", text):
        return "ko"
    if re.search(r"[\u0400-\u04ff]", text):
        return "ru"
    if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text):
        return "ja"
    if re.search(r"[àâæçéèêëîïôœùûüÿ]", text, re.IGNORECASE):
        return "fr"
    words = set(re.findall(r"[a-z]+", text.casefold()))
    strong = {"bonjour", "bonsoir", "chanson", "amour", "coeur", "toujours", "pourquoi", "jamais", "avec", "veux", "chante"}
    common = {"je", "tu", "nous", "vous", "toi", "moi", "une", "les", "des", "est", "dans", "pas", "mon", "mes", "pour", "que", "qui"}
    if words & strong or len(words & common) >= 2:
        return "fr"
    return "en"


@lru_cache(maxsize=1)
def _kakasi():
    import pykakasi
    return pykakasi.kakasi()


def japanese(text: str, romaji: bool = False) -> str:
    parts = _kakasi().convert(text)
    key = "hepburn" if romaji else "hira"
    return " ".join(part[key] for part in parts if part[key].strip())


ARPA = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ",
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "EH": "ɛ", "ER": "ɝ",
    "EY": "eɪ", "F": "f", "G": "ɡ", "HH": "h", "IH": "ɪ", "IY": "i",
    "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ",
    "OW": "oʊ", "OY": "ɔɪ", "P": "p", "R": "ɹ", "S": "s", "SH": "ʃ",
    "T": "t", "TH": "θ", "UH": "ʊ", "UW": "u", "V": "v", "W": "w",
    "Y": "j", "Z": "z", "ZH": "ʒ",
}


@lru_cache(maxsize=1)
def _english_words():
    import cmudict
    return cmudict.dict()


def english(text: str) -> str:
    words = _english_words()
    output = []
    for word in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text):
        pronunciations = words.get(word.lower())
        if not pronunciations:
            output.append(f"{word}: —")
            continue
        symbols = []
        for phoneme in pronunciations[0]:
            base = re.sub(r"\d", "", phoneme)
            stress = "ˈ" if phoneme.endswith("1") else "ˌ" if phoneme.endswith("2") else ""
            symbols.append(stress + ARPA.get(base, base.lower()))
        output.append(f"{word}: /{''.join(symbols)}/")
    return "   ".join(output)


RU_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "ʺ",
    "ы": "y", "ь": "ʹ", "э": "e", "ю": "yu", "я": "ya",
}


def russian(text: str) -> str:
    return "".join((RU_LATIN.get(char.lower(), char).capitalize() if char.isupper()
                    else RU_LATIN.get(char, char)) for char in text)


KO_INITIAL = ("g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h")
KO_VOWEL = ("a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i")
KO_FINAL = ("", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "p", "l", "l", "p", "l", "m", "p", "p", "t", "t", "ng", "t", "t", "k", "t", "p", "t")


def korean(text: str) -> str:
    result = []
    for char in text:
        code = ord(char) - 0xAC00
        if 0 <= code < 11172:
            initial, rest = divmod(code, 21 * 28)
            vowel, final = divmod(rest, 28)
            result.append(KO_INITIAL[initial] + KO_VOWEL[vowel] + KO_FINAL[final])
        else:
            result.append(char)
    return "".join(result)


def french(text: str) -> str:
    from .phonetics import ipa
    return ipa(text, "fr")


@lru_cache(maxsize=4096)
def reading(text: str, language: str, japanese_romaji: bool = False) -> str:
    if not text.strip():
        return ""
    match language:
        case "ja": return japanese(text, japanese_romaji)
        case "en": return english(text)
        case "ru": return russian(text)
        case "fr": return f"/{french(text)}/" if re.search(r"[A-Za-zÀ-ÿŒœ]", text) else ""
        case "ko": return korean(text)
        case _: return ""
