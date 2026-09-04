#!/usr/bin/env python3
"""สร้าง exact-SelfId cache สำหรับ PUA review จาก PAK แบบอ่านอย่างเดียว.

ไม่มี fuzzy join และไม่ใช้ข้อความต้นทางเพื่อสร้าง replacement.
"""
from __future__ import annotations

import csv
import json
import subprocess
from collections import defaultdict
from pathlib import Path


def extract(repak: Path, pak: Path, internal: str, root: Path) -> None:
    for suffix in (".uasset", ".uexp"):
        item = internal[:-7] + suffix
        target = root / item
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            result = subprocess.run([str(repak), "get", str(pak), item], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode:
                raise RuntimeError(f"repak get failed: {item}: {result.stderr.decode(errors='replace')}")
            target.write_bytes(result.stdout)


def build(name: str, pak: Path, root: Path, paths: list[str], repak: Path, exporter: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    loose = root / name
    rows: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for path in paths:
        try:
            extract(repak, pak, path, loose)
            key = f"{name}/{path}"
            output = root / f"{name}_{Path(path).stem}.json"
            result = subprocess.run([str(exporter), str(loose), key, str(output)], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip())
            data = json.loads(output.read_text(encoding="utf-8"))
            table = next(item for item in data if item.get("Type") == "DataTable")
            for row_key, value in table["Rows"].items():
                rows.append({"self_id": value.get("SelfId", ""), "asset_path": path.removesuffix(".uasset"), "text": value.get("Text", ""), "row_key": row_key})
        except Exception as error:  # retain source-specific failure for report, never substitute another source
            errors.append({"source": name, "asset_path": path, "error": str(error)})
    return rows, errors


def main() -> None:
    workspace = Path(__file__).resolve().parents[1]
    dictionary = workspace / "work/new_subtitle_switch/pua_dictionary"
    index_root = dictionary / "source_indexes"
    index_root.mkdir(parents=True, exist_ok=True)
    mapping = list(csv.DictReader((dictionary / "pua_mapping.csv").open(encoding="utf-8-sig", newline="")))
    review = [row for row in mapping if row["status"].upper() == "UNMAPPED"][:30]
    switch_paths = sorted({row[f"sample_{index}_asset_path"] + ".uasset" for row in review for index in range(1, 6) if row.get(f"sample_{index}_asset_path")})
    steam_paths = ["TRIANGLE_STRATEGY/Content/" + path[len("Newera/Content/"):] for path in switch_paths]
    repak = workspace / "work/tools/repak/v0.2.3/repak.exe"
    exporter = workspace / "work/fmodel_datatable_exporter/bin/Debug/net10.0/FmodelDatatableExporter.exe"
    sources = [
        ("update", workspace / "TRIANGLE STRATEGY 1.1.1 [0100CC80140F8800][v262144][UPD]/Program #0/1/Newera/Content/Paks/Newera-Switch.pak", switch_paths),
        ("base", workspace / "TRIANGLE STRATEGY [0100CC80140F8000][v0][BASE]/Program #0/1/Newera/Content/Paks/Newera-Switch.pak", switch_paths),
        ("steam", workspace / "men/Paks/1-TSTH_P.pak", steam_paths),
    ]
    all_errors = []
    for name, pak, paths in sources:
        rows, errors = build(name, pak, index_root / "loose", paths, repak, exporter)
        with (index_root / f"{name}_selfid_index.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["self_id", "asset_path", "row_key", "text"])
            writer.writeheader(); writer.writerows(rows)
        all_errors.extend(errors)
    with (index_root / "source_index_exceptions.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "asset_path", "error"])
        writer.writeheader(); writer.writerows(all_errors)
    print(f"review_assets={len(switch_paths)} errors={len(all_errors)}")


if __name__ == "__main__":
    main()
