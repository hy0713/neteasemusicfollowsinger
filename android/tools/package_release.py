"""Package an already verified APK and the exact source, without local build secrets/caches."""
from pathlib import Path
import gzip
import hashlib
import shutil
import tarfile
import zipfile

root = Path(__file__).resolve().parents[2]
version = "0.1.0"
output = root / "dist/android" / version
output.mkdir(parents=True, exist_ok=True)
apk = root / "android/app/build/outputs/apk/debug/app-debug.apk"
engine_source = root / "vendor/ephone/ephone-js-1.0.2-source.tar.gz"
if not engine_source.exists():
    raise SystemExit("Corresponding ephone source archive missing")
# Validate the gzip CRC and ensure the source really contains the compiler/build instructions.
with gzip.open(engine_source, "rb") as compressed:
    while compressed.read(1024 * 1024):
        pass
with tarfile.open(engine_source) as archive:
    members = archive.getnames()
    assert any(name.endswith("/emscripten/build.sh") for name in members)
    assert any(name.endswith("/COPYING") for name in members)
with zipfile.ZipFile(apk) as archive:
    # Verify every shipped frontend/dictionary byte against the final APK.
    for path in (root / "android/app/src/main/assets").rglob("*"):
        if path.is_file():
            assert archive.read("assets/" + path.relative_to(root / "android/app/src/main/assets").as_posix()) == path.read_bytes(), path
destination = output / f"FollowSinger-Android-{version}.apk"
shutil.copy2(apk, destination)
source_zip = output / f"FollowSinger-Android-{version}-source.zip"
excluded = {".gradle", ".gradle-user-home", ".tools", "build", "node_modules", "artifacts", "__pycache__"}
with zipfile.ZipFile(source_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in sorted((root / "android").rglob("*")):
        if not path.is_file() or excluded.intersection(path.relative_to(root / "android").parts):
            continue
        if path.name == "local.properties" or path.suffix in {".keystore", ".jks", ".pyc"}:
            continue
        archive.write(path, path.relative_to(root).as_posix())
    for path in sorted((root / "vendor/ephone").rglob("*")):
        if path.is_file():
            archive.write(path, path.relative_to(root).as_posix())
    for relative in ["LICENSE", "README.md", "requirements.txt", "followsinger/__init__.py", "followsinger/beginner.py", "followsinger/pronunciation.py", "followsinger/phonetics.py"]:
        archive.write(root / relative, relative)
for name in ["README.md", "BUILD_REPORT.md"]:
    shutil.copy2(root / "android" / name, output / name)
lines = []
for path in [destination, source_zip]:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    lines.append(f"{digest}  {path.name}")
    print(f"{path.name}: {path.stat().st_size:,} bytes, SHA256 {digest}")
(output / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="ascii")
print("Final APK assets verified against source")
