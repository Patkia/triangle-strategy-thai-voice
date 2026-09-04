#!/usr/bin/env python3
"""Build and validate the isolated one-line old-Switch-PUA PAK POC."""
from __future__ import annotations
import codecs
import csv
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELATIVE = Path("Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/trial_01/Text_trial_01_ms06_x07_wd_0010")
SELF_ID = "TRIAL_01_MS06_X07_WD_0010_N_NNN_0010"
TARGET = "ในทวีปอันห่างไกลแห่งนอร์เซเลีย ถูกปกครองโดยอาณาจักรมหาอำนาจทั้งสาม"
PAK_NAME = "Newera-Switch_1010_PUAOpening_P.pak"
TITLE_ID = "0100CC80140F8000"

sys.path.insert(0, str(ROOT / "scripts"))
from targeted_strproperty_patch import (  # noqa: E402
    EXPECTED_UASSET_SHA256, EXPECTED_UEXP_SHA256, EXPORT_SERIAL_SIZE_OFFSET,
    FOOTER_SIZE, encode_fstring, locate_target, parse_name_map, patch_variant,
    prepare_root, read_i64, sha256,
)

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, capture_output=True, text=True)

def export_table(loose_root: Path, output: Path) -> dict:
    exporter = ROOT / "work/fmodel_datatable_exporter/bin/Debug/net10.0/FmodelDatatableExporter.exe"
    package = f"{loose_root.name}/" + str(RELATIVE.with_suffix(".uasset")).replace("\\", "/")
    run([str(exporter), str(loose_root), package, str(output)])
    objects = json.loads(output.read_text(encoding="utf-8"))
    table = next(item for item in objects if item.get("Type") == "DataTable")
    return table["Rows"]

def diff_check(original_uasset: bytes, original_uexp: bytes, patched_uasset: bytes, patched_uexp: bytes, original_target: dict, patched_target: dict) -> dict:
    serial_only = (original_uasset[:EXPORT_SERIAL_SIZE_OFFSET] == patched_uasset[:EXPORT_SERIAL_SIZE_OFFSET]
                   and original_uasset[EXPORT_SERIAL_SIZE_OFFSET+8:] == patched_uasset[EXPORT_SERIAL_SIZE_OFFSET+8:])
    trailing_same = (original_uexp[int(original_target["text_data_end"]):-FOOTER_SIZE]
                     == patched_uexp[int(patched_target["text_data_end"]):-FOOTER_SIZE])
    footer_same = original_uexp[-FOOTER_SIZE:] == patched_uexp[-FOOTER_SIZE:]
    delta = len(patched_uexp) - len(original_uexp)
    return {"delta": delta, "serial_only": serial_only, "trailing_same": trailing_same, "footer_same": footer_same,
            "serial_size_ok": read_i64(patched_uasset, EXPORT_SERIAL_SIZE_OFFSET) == len(patched_uexp)-FOOTER_SIZE,
            "unexplained": not (serial_only and trailing_same and footer_same)}

def main() -> None:
    # Preflight: rerun the reproducible encoder before touching any template copy.
    run([sys.executable, str(ROOT / "tools/encode_old_thai_pua_poc.py")])
    result = json.loads((ROOT / "work/new_subtitle_switch/pua_dictionary/opening_sentence_encoder_poc.json").read_text(encoding="utf-8"))
    if result["status"] != "PASS" or not result["roundtrip_exact"] or result["missing"]:
        raise RuntimeError("opening encoder preflight failed")
    if result["roundtrip"] != TARGET:
        raise RuntimeError("encoder target mismatch")
    encoded = codecs.decode(result["encoded_escaped"].encode("ascii"), "unicode_escape")
    if encoded == TARGET:
        raise RuntimeError("encoded representation unexpectedly contains no PUA transformation")

    poc = ROOT / "work/new_subtitle_switch/pua_opening_runtime_poc_1010_build"
    if poc.exists(): raise FileExistsError(f"POC root already exists; refusing overwrite: {poc}")
    source = ROOT / "work/uasset_writer_poc/original" / RELATIVE
    original_uasset, original_uexp = source.with_suffix(".uasset").read_bytes(), source.with_suffix(".uexp").read_bytes()
    if sha256(original_uasset) != EXPECTED_UASSET_SHA256 or sha256(original_uexp) != EXPECTED_UEXP_SHA256:
        raise RuntimeError("verified UPDATE template hashes do not match")
    names = parse_name_map(original_uasset)
    original_target = locate_target(original_uexp, names)
    if original_target["text"] != "On the faraway continent of Norzelia, three mighty powers reigned.":
        raise RuntimeError("template target text mismatch")
    prepare_root(poc / "patched", source.with_suffix(".uasset"), source.with_suffix(".uexp"))
    patch_variant(poc / "patched", encoded, original_uasset, original_uexp, original_target)
    patched = poc / "patched" / RELATIVE
    patched_uasset, patched_uexp = patched.with_suffix(".uasset").read_bytes(), patched.with_suffix(".uexp").read_bytes()
    patched_target = locate_target(patched_uexp, names)
    binary = diff_check(original_uasset, original_uexp, patched_uasset, patched_uexp, original_target, patched_target)
    if patched_target["text"] != encoded or binary["unexplained"] or not binary["serial_size_ok"]:
        raise RuntimeError("patch binary validation failed")

    original_rows = export_table(ROOT / "work/uasset_writer_poc/original", poc / "original_rows.json")
    patched_rows = export_table(poc / "patched", poc / "patched_rows.json")
    other_changed = [key for key, value in original_rows.items() if key != SELF_ID and patched_rows.get(key) != value]
    if len(patched_rows) != 13 or patched_rows[SELF_ID].get("SelfId") != SELF_ID or patched_rows[SELF_ID].get("Text") != encoded or other_changed:
        raise RuntimeError("CUE4Parse patched validation failed")

    repak = ROOT / "work/tools/repak/v0.2.3/repak.exe"
    pak = poc / "built" / PAK_NAME; pak.parent.mkdir(parents=True)
    run([str(repak), "pack", str(poc / "patched"), str(pak), "--mount-point", "../../../", "--version", "V11", "--compression", "Zlib", "--path-hash-seed", "1182728049", "--quiet"])
    listed = [line.strip() for line in run([str(repak), "list", str(pak)]).stdout.splitlines() if line.strip()]
    expected_entries = [str(RELATIVE.with_suffix(s)).replace("\\", "/") for s in (".uasset", ".uexp")]
    if sorted(listed) != sorted(expected_entries): raise RuntimeError(f"unexpected PAK entries: {listed}")
    extracted_root = poc / "reextracted"
    for entry in expected_entries:
        target = extracted_root / entry; target.parent.mkdir(parents=True, exist_ok=True)
        data = subprocess.run([str(repak), "get", str(pak), entry], check=True, stdout=subprocess.PIPE).stdout
        target.write_bytes(data)
    re_base = extracted_root / RELATIVE
    if any(digest(re_base.with_suffix(s)) != digest(patched.with_suffix(s)) for s in (".uasset", ".uexp")):
        raise RuntimeError("re-extracted file hashes differ from patched source")
    re_rows = export_table(extracted_root, poc / "reextracted_rows.json")
    if len(re_rows) != 13 or re_rows[SELF_ID].get("Text") != encoded or any(key != SELF_ID and re_rows.get(key) != original_rows[key] for key in original_rows):
        raise RuntimeError("re-extracted CUE4Parse validation failed")
    re_target = re_rows[SELF_ID]["Text"]
    # Decode by rerunning the POC decoder's deterministic logic result; encoded payload is identical.
    if encoded != re_target or result["roundtrip"] != TARGET:
        raise RuntimeError("cluster-aware round-trip validation failed")

    staging = poc / "layeredfs/atmosphere/contents" / TITLE_ID / "romfs/Newera/Content/Paks" / PAK_NAME
    staging.parent.mkdir(parents=True); shutil.copy2(pak, staging)
    if digest(staging) != digest(pak): raise RuntimeError("staging copy hash mismatch")
    with (poc / "validation.json").open("w", encoding="utf-8") as f:
        json.dump({"target_selfid": SELF_ID, "encoded_escaped": result["encoded_escaped"], "roundtrip_exact": True,
                   "patch_validation": "PASS", "other_rows_changed": len(other_changed), "unexplained_binary_differences": 0,
                   "pak": str(pak), "pak_sha256": digest(pak), "pak_file_count": len(listed),
                   "reextract_validation": "PASS", "pua_count": result["pua_used"], "literal_count": result["literal_unicode_used"],
                   "binary": binary}, f, ensure_ascii=False, indent=2)
    print(json.dumps(json.loads((poc / "validation.json").read_text(encoding="utf-8")), ensure_ascii=True))

if __name__ == "__main__": main()
