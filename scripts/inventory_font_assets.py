from __future__ import annotations

import csv
import subprocess
from pathlib import Path


SOURCES = {
    "switch_base": "TRIANGLE STRATEGY [0100CC80140F8000][v0][BASE]/Program #0/1/Newera/Content/Paks/Newera-Switch.pak",
    "switch_update": "TRIANGLE STRATEGY 1.1.1 [0100CC80140F8800][v262144][UPD]/Program #0/1/Newera/Content/Paks/Newera-Switch.pak",
    "old_switch_thai": "subthai/THAI-Newera-Switch_P.pak",
    "steam_thai": "men/Paks/1-TSTH_P.pak",
}


def related(path: str) -> bool:
    lower = path.lower()
    return lower.endswith((".ttf", ".otf", ".ufont")) or "font" in lower or "typeface" in lower or "fallback" in lower


def main() -> None:
    root = Path.cwd()
    repak = root / "work/tools/repak/v0.2.3/repak.exe"
    rows = []
    for label, pak in SOURCES.items():
        output = subprocess.run([str(repak), "list", str(root / pak)], check=True, text=True, capture_output=True).stdout.splitlines()
        for path in output:
            if related(path):
                suffix = Path(path).suffix.lower()
                kind = "raw_font" if suffix in (".ttf", ".otf", ".ufont") else "font_related_asset"
                rows.append((label, kind, path))
    destination = root / "work/new_subtitle_switch/unicode_font_poc/font_asset_inventory.csv"
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Source", "Kind", "InternalPath"))
        writer.writerows(rows)


if __name__ == "__main__":
    main()
