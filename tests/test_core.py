import unittest
from pathlib import Path

from followsinger.lyrics import active_index, attach_translations, parse_lrc, parse_yrc_as_lines, read_text
from followsinger.netease import select_match, song_id_from_input
from followsinger.pronunciation import LANGUAGES, detect_language, french, korean, reading, russian


class LyricsTests(unittest.TestCase):
    def test_timestamps_offset_and_repeated_tags(self):
        lines = parse_lrc("[offset: -100]\n[00:01.20][00:02.050]hello\n[00:03]world")
        self.assertEqual([(line.time_ms, line.text) for line in lines],
                         [(1100, "hello"), (1950, "hello"), (2900, "world")])

    def test_translation_consumed_once(self):
        lines = parse_lrc("[00:01.00]a\n[00:01.20]b")
        translated = parse_lrc("[00:01.10]甲")
        merged = attach_translations(lines, translated)
        self.assertEqual([line.translation for line in merged], ["甲", ""])

    def test_active_index_before_first_and_offset(self):
        lines = parse_lrc("[00:01.00]a\n[00:02.00]b")
        self.assertEqual(active_index(lines, 900), -1)
        self.assertEqual(active_index(lines, 1100), 0)
        self.assertEqual(active_index(lines, 1100, 200), -1)

    def test_yrc_line_fallback(self):
        lines = parse_yrc_as_lines("[1000,1500](1000,300,0)Hello(1300,700,0) world")
        self.assertEqual([(line.time_ms, line.text) for line in lines], [(1000, "Hello world")])

    def test_gb18030_input(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(dir=Path(__file__).resolve().parent.parent) as folder:
            path = Path(folder) / "song.lrc"
            path.write_bytes("[00:01.00]中文歌词".encode("gb18030"))
            self.assertEqual(parse_lrc(read_text(path))[0].text, "中文歌词")


class LanguageTests(unittest.TestCase):
    def test_script_detection(self):
        self.assertEqual(detect_language("Привет"), "ru")
        self.assertEqual(detect_language("안녕하세요"), "ko")
        self.assertEqual(detect_language("こんにちは"), "ja")
        self.assertEqual(detect_language("Bonjour, très bien"), "fr")

    def test_russian_and_korean_aids(self):
        self.assertEqual(russian("Привет"), "Privet")
        self.assertEqual(korean("안녕"), "annyeong")

    def test_french_local_ipa(self):
        self.assertIn("ʃ", french("chanson"))
        self.assertIn("lym", french("lumière"))
        self.assertEqual(french("une"), "ˈyn")
        self.assertIn("bɔ̃ʒ", french("Bonjour"))
        self.assertIn("ʃ", reading("chante", "fr"))
        self.assertTrue(reading("Bonjour", "fr").startswith("/"))
        self.assertEqual(detect_language("Je chante avec toi"), "fr")
        self.assertEqual(detect_language("Hello, I sing with you"), "en")

    def test_all_five_sample_readings(self):
        sample_dir = Path(__file__).resolve().parent.parent / "samples"
        for code in LANGUAGES:
            with self.subTest(language=code):
                lines = parse_lrc((sample_dir / f"{code}.lrc").read_text(encoding="utf-8"))
                self.assertEqual(len(lines), 4)
                self.assertTrue(all(reading(line.text, code) for line in lines))


class SearchTests(unittest.TestCase):
    def test_song_id_validation(self):
        self.assertEqual(song_id_from_input("https://music.163.com/#/song?id=12345"), "12345")
        with self.assertRaises(ValueError):
            song_id_from_input("https://example.com/?id=12345")

    def test_reject_unrelated_song(self):
        candidates = [{"id": 1, "name": "Other song", "artists": [{"name": "Nobody"}], "duration": 100000}]
        self.assertIsNone(select_match(candidates, "My song", "My artist", 100000))


if __name__ == "__main__":
    unittest.main()
