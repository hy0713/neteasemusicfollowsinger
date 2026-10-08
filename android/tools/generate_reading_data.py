"""Generate small rule tables from the desktop implementation, without loading its DLL."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from followsinger import beginner, pronunciation

kakasi = pronunciation._kakasi()
kana = [chr(i) for i in range(0x3041, 0x3097)]
kana += [a + b for a in "きぎしじちぢにひびぴみり" for b in "ゃゅょ"]
kana += ["ふ" + b for b in "ぁぃぇぉ"]
rules = {
    "candidates": beginner._candidates(),
    "vowels": sorted(beginner.VOWELS), "multi": beginner.MULTI,
    "nasals": beginner.NASALS, "isolated": beginner.ISOLATED,
    "neighbors": [sorted(group) for group in beginner.NEIGHBORS],
    "russian": pronunciation.RU_LATIN,
    "koInitial": pronunciation.KO_INITIAL, "koVowel": pronunciation.KO_VOWEL,
    "koFinal": pronunciation.KO_FINAL,
    "kana": {text: "".join(part["hepburn"] for part in kakasi.convert(text)) for text in kana},
}
destination = root / "android/app/src/main/assets/web/reading-data.json"
destination.write_text(json.dumps(rules, ensure_ascii=False), encoding="utf-8")
print(f"Generated {len(rules['candidates'])} Mandarin candidates and {len(rules['kana'])} kana rules")
