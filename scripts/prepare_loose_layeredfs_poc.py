from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path

RELATIVE = Path("Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/trial_01/Text_trial_01_ms06_x07_wd_0010")
TITLE_ID = "0100CC80140F8000"
EXPECTED_HASHES = {
    ".uasset": "626731290b72c8ce398f0c3dac11fe33ef91e6ab52377bbb948dd17c1da7df97",
    ".uexp": "41ee0694078592486b403374995e47b74f6f5c6d9ca3d3132fc7e55c9f954c4b",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    workspace = Path.cwd()
    source = workspace / "work/new_subtitle_switch/targeted_patch_poc/unicode" / RELATIVE
    destination_root = workspace / "work/new_subtitle_switch/loose_layeredfs_poc"
    romfs_root = destination_root / "atmosphere/contents" / TITLE_ID / "romfs"
    rows: list[tuple[str, str, int, str, str]] = []
    for suffix, expected_hash in EXPECTED_HASHES.items():
        source_file = source.with_suffix(suffix)
        actual_hash = digest(source_file)
        if actual_hash != expected_hash:
            raise ValueError(f"Unicode source hash ไม่ตรงกับ Mission 4: {source_file}")
        destination = romfs_root / RELATIVE.with_suffix(suffix)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"ปลายทางมีอยู่แล้ว; ไม่ overwrite: {destination}")
        shutil.copy2(source_file, destination)
        copied_hash = digest(destination)
        if copied_hash != expected_hash:
            raise ValueError(f"hash หลัง copy ไม่ตรง: {destination}")
        switch_path = "/atmosphere/contents/" + TITLE_ID + "/romfs/" + RELATIVE.with_suffix(suffix).as_posix()
        rows.append((suffix, source_file.as_posix(), destination.as_posix(), switch_path, copied_hash))
    with (destination_root / "manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Extension", "Source", "StagingPath", "CandidateSwitchPath", "SHA256"))
        writer.writerows(rows)


if __name__ == "__main__":
    main()
