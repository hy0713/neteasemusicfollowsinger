"""Archive a portable build without machine-specific settings or logs."""
import hashlib
from pathlib import Path
import shutil
import zipfile
import argparse

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--version", default="0.3.1")
args = parser.parse_args()
release = root / "dist" / args.version / "FollowSinger"
shutil.copy2(root / "README.md", release / "README.md")
shutil.copy2(root / "README.md", release / "SOURCE/README.md")
shutil.copy2(root / "tests/test_controls.py", release / "SOURCE/tests/test_controls.py")
shutil.copy2(__file__, release / "SOURCE/scripts/zip_release.py")
archive = root / "dist" / f"FollowSinger-{args.version}-windows-x64.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as package:
    for path in release.rglob("*"):
        relative = path.relative_to(release)
        if not path.is_file() or relative.parts[0] in {"data", "output"} or "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        package.write(path, Path("FollowSinger") / relative)
with zipfile.ZipFile(archive) as package:
    assert package.testzip() is None
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
(root / "dist" / f"SHA256SUMS-{args.version}.txt").write_text(f"{checksum}  {archive.name}\n", encoding="utf-8")
print(f"{archive}: {archive.stat().st_size / 1024**2:.1f} MiB")
