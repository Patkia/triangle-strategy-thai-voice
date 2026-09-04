#!/usr/bin/env python3
"""Prototype แบบ read-only สำหรับตรวจ CueInfo.Name กับ Scenario DataTable.

ไม่สร้าง audio mapping และไม่แก้ PAK/AWB/ROMFS.  ผลลัพธ์ทั้งหมดเขียนใต้ work/
จากข้อมูล Properties JSON ที่ FModel export และรายการ path จาก repak เท่านั้น.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "Output" / "Exports" / "Newera" / "Content" / "Newera"
CUE_DIR = EXPORTS / "Sound" / "VOICE" / "EN"
OUT = ROOT / "work" / "automated_mapper"
BASE_PAK = ROOT / "TRIANGLE STRATEGY [0100CC80140F8000][v0][BASE]" / "Program #0" / "1" / "Newera" / "Content" / "Paks" / "Newera-Switch.pak"
REPAK = ROOT / "work" / "tools" / "repak" / "v0.2.3" / "repak.exe"
THAI_ROOT = ROOT / "work" / "first_thai_voice_poc" / "subthai_text_assets"

PATTERN = re.compile(
    r"^(?P<scenario>CS\d{2})_(?P<event>E\d{2})_(?P<block>\d{4})_(?P<speaker_type>[A-Z])_(?P<speaker>[A-Z0-9]+)_(?P<line>\d{4})$"
)

# หลักฐานที่ผู้ใช้ยืนยันเองใน mission นี้: ใช้เติมได้เฉพาะสอง row นี้
# ไม่ใช่ rule สำหรับ row อื่น และไม่ใช่หลักฐาน stream index.
HUMAN_ROW_EVIDENCE = {
    "CS03_E01_0010_F_ANA_0010": {
        "EnglishText": "Thank Benedict for that. We'd still be searching for weaknesses in our perimeter had he not been guiding us.",
        "source": "USER_HUMAN_VERIFIED",
    },
    "CS05_E01_0020_F_YRA_0010": {
        "EnglishText": "...Yes, my lord.",
        "source": "USER_HUMAN_VERIFIED",
    },
}


def list_base_paths() -> set[str]:
    result = subprocess.run([str(REPAK), "list", str(BASE_PAK)], check=True, text=True, capture_output=True)
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def data_table_json(asset_no_ext: str) -> Path:
    return EXPORTS / (asset_no_ext + ".json")


def parse_export_rows(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data[0].get("Rows", {})


def thai_identifier_exists(asset_no_ext: str, cue_name: str) -> tuple[str, str, str]:
    """ตรวจ exact identifier จาก cooked Thai asset; ไม่จับคู่หรือ decode payload เอง."""
    thai_relative = "Newera/Content/Newera/" + asset_no_ext
    asset = THAI_ROOT / (thai_relative + ".uasset")
    payload = THAI_ROOT / (thai_relative + ".uexp")
    if not asset.exists():
        return "NO", "", "NOT_EXPORTED"
    raw = asset.read_bytes() + (payload.read_bytes() if payload.exists() else b"")
    if cue_name.encode("ascii") not in raw:
        return "NO", "", "IDENTIFIER_NOT_FOUND"
    # Thai PUA glyph data exists in this cooked asset; do not infer its per-row text.
    utf16le_pua = any(b"\x00\xe0" <= raw[i : i + 2] <= b"\xff\xf8" for i in range(0, len(raw) - 1, 2))
    status = "PUA" if utf16le_pua else "RAW_UNDECODED"
    return "YES", "", status


def main() -> None:
    if not BASE_PAK.is_file() or not REPAK.is_file():
        raise SystemExit("ไม่พบ Base PAK หรือ repak.exe ที่ต้องใช้ตรวจ path แบบ read-only")
    OUT.mkdir(parents=True, exist_ok=True)
    base_paths = list_base_paths()
    rows_out: list[dict[str, str]] = []
    exceptions: list[dict[str, str]] = []

    for sheet in ("CS02_EN", "CS03_EN", "CS04_EN", "CS05_EN"):
        cue_json = CUE_DIR / f"{sheet}.json"
        cue_infos = json.loads(cue_json.read_text(encoding="utf-8"))[0]["Properties"]["CueInfos"]
        for cue in cue_infos:
            name = cue["Name"]
            match = PATTERN.fullmatch(name)
            record = {key: "" for key in FIELDNAMES}
            record.update({"CueSheet": sheet, "CueId": str(cue["Id"]), "CueName": name})
            if not match:
                exceptions.append({"CueSheet": sheet, "CueId": str(cue["Id"]), "CueName": name, "Reason": "NAME_NOT_PARSEABLE", "Detail": "ไม่ตรงรูปแบบ CSnn_Enn_block_type_speaker_line"})
                rows_out.append(record)
                continue

            scenario = match["scenario"].lower()
            event = f"{scenario}_{match['event'].lower()}"
            block = match["block"]
            asset_no_ext = f"Data/DataTables/Scenario/Text/en/Chara/{scenario}/{event}/Text_{event}_{block}"
            pak_asset = f"Newera/Content/Newera/{asset_no_ext}.uasset"
            record.update({"Scenario": scenario, "Event": event, "TextBlock": block, "DataTableAsset": f"Text_{event}_{block}"})
            if pak_asset not in base_paths:
                exceptions.append({"CueSheet": sheet, "CueId": str(cue["Id"]), "CueName": name, "Reason": "DERIVED_DATATABLE_NOT_IN_BASE_PAK", "Detail": pak_asset})
                rows_out.append(record)
                continue

            exported = data_table_json(asset_no_ext)
            if exported.exists():
                record["DataTablePropertiesAvailable"] = "YES"
                table_rows = parse_export_rows(exported)
                row = table_rows.get(name)
                if row is None:
                    record["ExactRowMatch"] = "NO"
                    exceptions.append({"CueSheet": sheet, "CueId": str(cue["Id"]), "CueName": name, "Reason": "NO_EXACT_ROW_IN_EXPORTED_DATATABLE", "Detail": str(exported.relative_to(ROOT))})
                    rows_out.append(record)
                    continue
                record.update({"RowKey": name, "SelfId": str(row.get("SelfId", "")), "EnglishText": str(row.get("Text", ""))})
                record["ExactRowMatch"] = "YES"
                record["SelfIdMatch"] = "YES" if record["SelfId"] == name else "NO"
                record["MappingEvidence"] = "FMODEL_PROPERTIES_JSON"
                if record["SelfId"] != name:
                    exceptions.append({"CueSheet": sheet, "CueId": str(cue["Id"]), "CueName": name, "Reason": "SELFID_MISMATCH", "Detail": record["SelfId"]})
            elif name in HUMAN_ROW_EVIDENCE:
                record.update({
                    "RowKey": name, "SelfId": name, "EnglishText": HUMAN_ROW_EVIDENCE[name]["EnglishText"],
                    "ExactRowMatch": "YES", "SelfIdMatch": "YES", "MappingEvidence": HUMAN_ROW_EVIDENCE[name]["source"],
                })
            else:
                exceptions.append({"CueSheet": sheet, "CueId": str(cue["Id"]), "CueName": name, "Reason": "ROW_LEVEL_DATATABLE_EXPORT_MISSING", "Detail": f"ต้องการ Properties JSON ของ {asset_no_ext}"})
                rows_out.append(record)
                continue

            thai_match, thai_raw, thai_status = thai_identifier_exists(asset_no_ext, name)
            record.update({"ThaiRowMatch": thai_match, "ThaiTextRaw": thai_raw, "ThaiTextStatus": thai_status})
            rows_out.append(record)

    with (OUT / "mapping_prototype.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows_out)
    with (OUT / "exceptions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["CueSheet", "CueId", "CueName", "Reason", "Detail"])
        writer.writeheader()
        writer.writerows(exceptions)

    properties_assets = {r["DataTableAsset"] for r in rows_out if r["DataTablePropertiesAvailable"] == "YES"}
    properties_cues = sum(r["DataTablePropertiesAvailable"] == "YES" for r in rows_out)
    print(json.dumps({
        "total_cues": len(rows_out),
        "parseable": sum(bool(r["Scenario"]) for r in rows_out),
        "datatable_found": sum(bool(r["DataTableAsset"]) for r in rows_out),
        "datatable_properties_assets": len(properties_assets),
        "datatable_properties_cue_candidates": properties_cues,
        "exact_row_match": sum(r["ExactRowMatch"] == "YES" for r in rows_out),
        "selfid_match": sum(r["SelfIdMatch"] == "YES" for r in rows_out),
        "true_no_match": sum(r["ExactRowMatch"] == "NO" for r in rows_out),
        "thai_row_match": sum(r["ThaiRowMatch"] == "YES" for r in rows_out),
        "exceptions": len(exceptions),
    }, ensure_ascii=False))


FIELDNAMES = [
    "CueSheet", "CueId", "CueName", "Scenario", "Event", "TextBlock", "DataTableAsset",
    "DataTablePropertiesAvailable", "RowKey", "SelfId", "EnglishText", "ExactRowMatch", "SelfIdMatch",
    "MappingEvidence", "ThaiRowMatch", "ThaiTextRaw", "ThaiTextStatus",
]


if __name__ == "__main__":
    main()
