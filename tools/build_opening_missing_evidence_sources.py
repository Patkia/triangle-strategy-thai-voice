#!/usr/bin/env python3
"""Build a small exact-SelfId source cache for the opening-mapping human review."""
from __future__ import annotations
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pua_review_source_indexes import build

F082 = "\uf082"
F282 = "\uf282"

def main() -> None:
    root = Path(__file__).resolve().parents[1]
    corpus = root / "work/full_game_text_index/thai_text_raw_index.csv"
    selected = ["Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/trial_01/Text_trial_01_ms06_x07_wd_0010.uasset"]
    seen = {selected[0]}
    with corpus.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            text, asset = row["ThaiTextRaw"], row["DataTableAsset"]
            if (F082 in text or F282 + "า" in text) and asset not in seen:
                selected.append(asset + ".uasset"); seen.add(asset)
            if len(selected) >= 11: break
    out = root / "work/new_subtitle_switch/pua_dictionary/opening_evidence_sources"
    repak = root / "work/tools/repak/v0.2.3/repak.exe"
    exporter = root / "work/fmodel_datatable_exporter/bin/Debug/net10.0/FmodelDatatableExporter.exe"
    sources = [
        ("update", root / "TRIANGLE STRATEGY 1.1.1 [0100CC80140F8800][v262144][UPD]/Program #0/1/Newera/Content/Paks/Newera-Switch.pak", selected),
        ("base", root / "TRIANGLE STRATEGY [0100CC80140F8000][v0][BASE]/Program #0/1/Newera/Content/Paks/Newera-Switch.pak", selected),
        ("steam", root / "men/Paks/1-TSTH_P.pak", ["TRIANGLE_STRATEGY/Content/" + p[len("Newera/Content/"):] for p in selected]),
    ]
    all_errors = []
    for name, pak, paths in sources:
        rows, errors = build(name, pak, out / "loose", paths, repak, exporter)
        with (out / f"{name}_selfid_index.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["self_id", "asset_path", "row_key", "text"])
            writer.writeheader(); writer.writerows(rows)
        all_errors.extend(errors)
    with (out / "exceptions.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "asset_path", "error"])
        writer.writeheader(); writer.writerows(all_errors)
    print(f"assets={len(selected)} errors={len(all_errors)}")

if __name__ == "__main__": main()
