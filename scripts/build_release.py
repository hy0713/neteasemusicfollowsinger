"""Build a self-contained Windows desktop EXE with resources and source."""

from pathlib import Path
import importlib.metadata
import os
import shutil
import struct
import subprocess
import sys
import argparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", default="dist")
    args = parser.parse_args()
    destination = ROOT / args.dist_dir
    from PySide6.QtWidgets import QApplication
    from followsinger.design import app_icon
    app = QApplication([])
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    png = assets / "icon.png"
    app_icon(256).save(str(png))
    content = png.read_bytes()
    (assets / "icon.ico").write_bytes(struct.pack("<HHH", 0, 1, 1)
        + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(content), 22) + content)
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
               "--name", "FollowSinger", "--distpath", str(destination), "--icon", str(assets / "icon.ico"),
               "--add-data", f"{ROOT / 'samples'};samples", "--add-data", f"{assets};assets",
               "--add-data", f"{ROOT / 'vendor/espeak-ng'};vendor/espeak-ng",
               "--collect-all", "pykakasi", "--collect-all", "cmudict", "--collect-all", "jaconv",
               "--collect-submodules", "winrt", str(ROOT / "main.py")]
    environment = os.environ.copy()
    windows = Path(environment.get("SystemRoot", "C:/Windows"))
    # DLL discovery must not search host Poppler/libheif or other tool runtimes.
    environment["PATH"] = os.pathsep.join(str(path) for path in (
        Path(sys.executable).parent, Path(sys.base_prefix), windows / "System32", windows))
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    release = destination / "FollowSinger"
    for name in ("VCRUNTIME140.dll", "VCRUNTIME140_1.dll"):
        # Python and Qt must load the same, newer redistributable version.
        shutil.copy2(release / "_internal" / "PySide6" / name, release / "_internal" / name)
    for name in ("icuuc.dll", "icudt78.dll", "ucrtbase.dll"):
        if (release / "_internal" / name).exists():
            raise RuntimeError(f"Unexpected host runtime in release: {name}")
    shutil.copy2(ROOT / "LICENSE", release / "LICENSE")
    shutil.copy2(ROOT / "README.md", release / "README.md")
    source = release / "SOURCE"
    source.mkdir(exist_ok=True)
    for folder in ("followsinger", "scripts", "tests", "samples", "assets", "vendor"):
        shutil.copytree(ROOT / folder, source / folder, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("main.py", "pyproject.toml", "requirements.txt", "README.md", "LICENSE", "start.bat"):
        shutil.copy2(ROOT / name, source / name)
    licenses = release / "THIRD-PARTY-LICENSES"
    licenses.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "vendor/espeak-ng", licenses / "espeak-ng",
                    ignore=lambda path, names: [name for name in names if name != "COPYING"])
    shutil.copy2(ROOT / "vendor/README.md", licenses / "espeak-ng/README.md")
    for distribution in importlib.metadata.distributions():
        for relative in distribution.files or []:
            if not any(term in str(relative).lower() for term in ("license", "copying", "copyright")):
                continue
            original = distribution.locate_file(relative)
            if original.is_file():
                name = distribution.metadata["Name"]
                target = licenses / name / Path(str(relative)).name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, target)
    print(release / "FollowSinger.exe")


if __name__ == "__main__":
    main()
