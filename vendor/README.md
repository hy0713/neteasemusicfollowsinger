# eSpeak NG offline phonetics

- Version: 1.52.0, Windows x64.
- Original binary: https://github.com/espeak-ng/espeak-ng/releases/download/1.52.0/espeak-ng.msi
- Source: https://github.com/espeak-ng/espeak-ng/tree/1.52.0
- Corresponding source archive is supplied alongside this file as `espeak-ng-source-1.52.0.tar.gz`; includes build files, dictionary sources and phoneme data.
- License: GPL v3 or later; see `espeak-ng/COPYING` and the original source for notices.
- Extracted locally without installation using `scripts/vendor_espeak.py`; unmodified DLL and data files.
- FollowSinger uses the `espeak_TextToPhonemes` API to generate local IPA. No audio output, account data or online pronunciation service is used.

To rebuild the vendored DLL, follow `docs/building.md` in the supplied upstream source. The bundled DLL is loaded with Windows system and library-directory dependency lookup only.
