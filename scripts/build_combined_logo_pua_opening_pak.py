#!/usr/bin/env python3
"""สร้าง PAK รวม logo 1002 และ opening PUA 1010 จากไฟล์ที่ผ่าน POC แล้วเท่านั้น."""
from __future__ import annotations

import codecs
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAK_NAME = "Newera-Switch_1010_P.pak"
TITLE_ID = "0100CC80140F8000"
LOGO = Path("Newera/Content/Newera/UI/Menu/Title/Texture/T_UI_Title_Menu_GameTitleLogo_BC")
OPENING = Path("Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/trial_01/Text_trial_01_ms06_x07_wd_0010")
SELF_ID = "TRIAL_01_MS06_X07_WD_0010_N_NNN_0010"
TARGET = "ในทวีปอันห่างไกลแห่งนอร์เซเลีย ถูกปกครองโดยอาณาจักรมหาอำนาจทั้งสาม"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, capture_output=capture)


def export_rows(loose_root: Path, output: Path) -> dict:
    exporter = ROOT / "work/fmodel_datatable_exporter/bin/Debug/net10.0/FmodelDatatableExporter.exe"
    package = f"{loose_root.name}/" + str(OPENING.with_suffix(".uasset")).replace("\\", "/")
    run([str(exporter), str(loose_root), package, str(output)])
    objects = json.loads(output.read_text(encoding="utf-8"))
    return next(item for item in objects if item.get("Type") == "DataTable")["Rows"]


def decode_cluster_aware(value: str) -> str:
    import csv
    dictionary = ROOT / "work/new_subtitle_switch/pua_dictionary"
    with (dictionary / "pua_mapping.csv").open(encoding="utf-8-sig", newline="") as handle:
        simple = {chr(int(row["codepoint"][2:], 16)): row["replacement"] for row in csv.DictReader(handle)
                  if row.get("status", "").upper() == "VERIFIED" and row.get("replacement") not in {"", "-", "UNMAPPED"}}
    with (dictionary / "pua_cluster_mapping.csv").open(encoding="utf-8-sig", newline="") as handle:
        clusters = [row for row in csv.DictReader(handle) if row.get("status", "").upper() == "VERIFIED"]
    clusters.sort(key=lambda row: len(row["source_sequence"]), reverse=True)
    out, index = [], 0
    while index < len(value):
        cluster = next((row for row in clusters if value.startswith(row["source_sequence"], index)), None)
        if cluster:
            out.append(cluster["replacement"]); index += len(cluster["source_sequence"])
        else:
            out.append(simple.get(value[index], value[index])); index += 1
    return "".join(out)


def main() -> None:
    # Re-run only the existing reproducible encoder; no mapping or asset is changed.
    run([sys.executable, str(ROOT / "tools/encode_old_thai_pua_poc.py")])
    encoder = json.loads((ROOT / "work/new_subtitle_switch/pua_dictionary/opening_sentence_encoder_poc.json").read_text(encoding="utf-8"))
    if encoder["status"] != "PASS" or not encoder["roundtrip_exact"] or encoder["missing"] or encoder["roundtrip"] != TARGET:
        raise RuntimeError("opening encoder preflight did not pass")
    encoded = codecs.decode(encoder["encoded_escaped"].encode("ascii"), "unicode_escape")

    logo_source = ROOT / "work/new_subtitle_switch/title_logo_poc/input" / LOGO
    opening_source = ROOT / "work/new_subtitle_switch/pua_opening_runtime_poc_1010_build/patched" / OPENING
    for source in (logo_source, opening_source):
        for suffix in (".uasset", ".uexp"):
            if not source.with_suffix(suffix).is_file():
                raise FileNotFoundError(source.with_suffix(suffix))

    # Refuse to overwrite either a previously built PAK or this mission's work root.
    existing = list((ROOT / "work").rglob(PAK_NAME))
    if existing:
        raise FileExistsError("refusing to overwrite existing PAK: " + "; ".join(map(str, existing)))
    poc = ROOT / "work/new_subtitle_switch/combined_logo_pua_opening_pak"
    if poc.exists():
        raise FileExistsError(f"refusing to overwrite existing work root: {poc}")
    input_root = poc / "input"
    for relative, source in ((LOGO, logo_source), (OPENING, opening_source)):
        destination = input_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        for suffix in (".uasset", ".uexp"):
            shutil.copy2(source.with_suffix(suffix), destination.with_suffix(suffix))

    source_hashes = {str(relative.with_suffix(suffix)).replace("\\", "/"): sha256(source.with_suffix(suffix))
                     for relative, source in ((LOGO, logo_source), (OPENING, opening_source)) for suffix in (".uasset", ".uexp")}
    repak = ROOT / "work/tools/repak/v0.2.3/repak.exe"
    pak = poc / "built" / PAK_NAME
    pak.parent.mkdir(parents=True)
    run([str(repak), "pack", str(input_root), str(pak), "--mount-point", "../../../", "--version", "V11", "--compression", "Zlib", "--path-hash-seed", "1182728049", "--quiet"])
    entries = [line.strip() for line in run([str(repak), "list", str(pak)]).stdout.splitlines() if line.strip()]
    expected = sorted(source_hashes)
    if sorted(entries) != expected:
        raise RuntimeError(f"unexpected PAK entries: {entries}")

    extracted = poc / "reextracted"
    for entry in expected:
        output = extracted / entry
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(subprocess.run([str(repak), "get", str(pak), entry], check=True, stdout=subprocess.PIPE).stdout)
    extracted_hashes = {entry: sha256(extracted / entry) for entry in expected}
    if extracted_hashes != source_hashes:
        raise RuntimeError("re-extracted pair hash mismatch")

    rows = export_rows(extracted, poc / "reextracted_opening.json")
    if len(rows) != 13 or rows.get(SELF_ID, {}).get("SelfId") != SELF_ID or rows[SELF_ID].get("Text") != encoded:
        raise RuntimeError("CUE4Parse opening validation failed")
    decoded = decode_cluster_aware(rows[SELF_ID]["Text"])
    if decoded != TARGET:
        raise RuntimeError("cluster-aware decoded opening does not equal target")

    staging = poc / "layeredfs/atmosphere/contents" / TITLE_ID / "romfs/Newera/Content/Paks" / PAK_NAME
    staging.parent.mkdir(parents=True)
    shutil.copy2(pak, staging)
    if sha256(staging) != sha256(pak):
        raise RuntimeError("staging hash mismatch")
    result = {
        "pak": str(pak), "pak_sha256": sha256(pak), "pak_file_count": len(entries),
        "logo_hash_match": all(extracted_hashes[str(LOGO.with_suffix(s)).replace("\\", "/")] == source_hashes[str(LOGO.with_suffix(s)).replace("\\", "/")] for s in (".uasset", ".uexp")),
        "opening_hash_match": all(extracted_hashes[str(OPENING.with_suffix(s)).replace("\\", "/")] == source_hashes[str(OPENING.with_suffix(s)).replace("\\", "/")] for s in (".uasset", ".uexp")),
        "opening_rows": len(rows), "target_selfid": SELF_ID, "opening_roundtrip_exact": decoded == TARGET,
        "entries": entries, "staging": str(staging), "settings": "V11 / Fnv64BugFix; ../../../; Zlib; 0x467EFF71",
    }
    (poc / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
