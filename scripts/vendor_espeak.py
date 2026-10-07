"""Extract upstream eSpeak NG's MSI into project resources without installing it.

Usage: python scripts/vendor_espeak.py path/to/espeak-ng.msi
Download: https://github.com/espeak-ng/espeak-ng/releases/tag/1.52.0
"""
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import shutil
import sys
import msilib

root = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]).resolve()
scratch = root / ".tmp/espeak-files"
scratch.mkdir(parents=True, exist_ok=True)
msi = ctypes.WinDLL("msi")
handle = wintypes.UINT()
view = wintypes.UINT()
record = wintypes.UINT()
assert msi.MsiOpenDatabaseW(str(source), None, ctypes.byref(handle)) == 0
assert msi.MsiDatabaseOpenViewW(handle, "SELECT `Data` FROM `_Streams` WHERE `Name`='cab1.cab'", ctypes.byref(view)) == 0
assert msi.MsiViewExecute(view, 0) == 0
assert msi.MsiViewFetch(view, ctypes.byref(record)) == 0
cab = scratch / "files.cab"
with cab.open("wb") as stream:
    while True:
        buffer = ctypes.create_string_buffer(65536)
        length = wintypes.DWORD(65536)
        assert msi.MsiRecordReadStream(record, 1, buffer, ctypes.byref(length)) == 0
        if not length.value:
            break
        stream.write(buffer.raw[:length.value])
for value in (record, view, handle):
    msi.MsiCloseHandle(value)
subprocess.run(["expand.exe", "-F:*", str(cab), str(scratch)], check=True, capture_output=True)
database = msilib.OpenDatabase(str(source), 0)

def rows(query, count):
    v = database.OpenView(query)
    v.Execute(None)
    r = v.Fetch()
    while r:
        yield tuple(r.GetString(i) for i in range(1, count + 1))
        r = v.Fetch()

directories = {key: (parent, name.split("|")[-1]) for key, parent, name in rows("SELECT Directory, Directory_Parent, DefaultDir FROM Directory", 3)}
components = dict(rows("SELECT Component, Directory_ FROM Component", 2))
destination = root / "vendor/espeak-ng"
destination.mkdir(parents=True, exist_ok=True)
for key, component, filename in rows("SELECT File, Component_, FileName FROM File", 3):
    directory = components[component]
    pieces = []
    while directory in directories:
        parent, name = directories[directory]
        if name not in {".", "SourceDir", "PFiles", "PFiles64", "ProgramFiles", "ProgramFiles64"}:
            pieces.insert(0, name)
        directory = parent
    # Strip the install-root and preserve espeak-ng-data's relative layout.
    if "espeak-ng" in pieces:
        pieces = pieces[pieces.index("espeak-ng") + 1:]
    elif "eSpeak NG" in pieces:
        pieces = pieces[pieces.index("eSpeak NG") + 1:]
    target = destination.joinpath(*pieces, filename.split("|")[-1])
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(scratch / key, target)
print(destination)
