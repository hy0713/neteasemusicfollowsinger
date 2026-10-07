import unittest
from followsinger.beginner import beginner_reading
from followsinger.phonetics import ipa
from followsinger.lyrics import LyricLine
import test_controls


class BeginnerPhoneticTests(unittest.TestCase):
    def test_hi_and_word_boundaries(self):
        self.assertEqual(beginner_reading("Hi", "en"), "嗨")
        self.assertEqual(beginner_reading("", "fr"), "")
        self.assertIn(" · ", beginner_reading("Hello world", "en"))

    def test_french_nasal_and_all_scripts(self):
        self.assertIn("ɔ̃", ipa("Bonjour", "fr"))
        cases = [("Bonjour", "fr"), ("Привет", "ru"), ("안녕하세요", "ko"), ("こんにちは", "ja")]
        for text, code in cases:
            with self.subTest(language=code):
                self.assertRegex(beginner_reading(text, code), r"^[\u4e00-\u9fff ·]+$")


class BeginnerInterfaceTests(test_controls.ControlsTest):
    # Only use the shared Qt fixture; control regression tests live elsewhere.
    test_click_space_and_editor_space = None
    test_rate_modes_and_disconnect = None
    test_five_themes_persist = None

    def test_default_off_and_extra_hint_keeps_ipa(self):
        self.w._set_lines([LyricLine(0, "Bonjour")], "test")
        self.assertEqual(self.w._language_code(), "fr")
        self.assertFalse(self.w.beginner_check.isChecked())
        row = self.w.rows[0]
        original_ipa = row.annotation.text()
        self.w.beginner_check.setChecked(True)
        self.assertIs(self.w.rows[0], row)
        self.assertEqual(row.annotation.text(), original_ipa)
        self.assertIn("邦茹尔", row.beginner.text())
        self.w.beginner_check.setChecked(False)
        self.assertTrue(row.beginner.isHidden())

    def test_manual_french_stays_selected_on_new_lyrics(self):
        self.w.language.setCurrentIndex(self.w.language.findData("fr"))
        self.w._set_lines([LyricLine(0, "La vie")], "test")
        self.assertEqual(self.w._language_code(), "fr")
        self.assertNotIn("—", self.w.rows[0].annotation.text())
        self.w._set_lines([LyricLine(0, "Paris")], "next")
        self.assertEqual(self.w._language_code(), "fr")
