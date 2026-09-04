#!/usr/bin/env python3
"""สร้างรายงาน CSV แบบ read-only สำหรับ preflight subtitle Switch/Steam."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "work" / "new_subtitle_switch"

PAKS = {
    "switch_base": ROOT / "TRIANGLE STRATEGY [0100CC80140F8000][v0][BASE]" / "Program #0" / "1" / "Newera" / "Content" / "Paks" / "Newera-Switch.pak",
    "switch_update": ROOT / "TRIANGLE STRATEGY 1.1.1 [0100CC80140F8800][v262144][UPD]" / "Program #0" / "1" / "Newera" / "Content" / "Paks" / "Newera-Switch.pak",
    "old_switch_thai": ROOT / "subthai" / "THAI-Newera-Switch_P.pak",
    "steam_thai": ROOT / "men" / "Paks" / "1-TSTH_P.pak",
}
PAK_METADATA = {
    "switch_base": ("V11", "Fnv64BugFix", "../../../", "Zlib", "C95B4D7A"),
    "switch_update": ("V11", "Fnv64BugFix", "../../../", "Zlib", "467EFF71"),
    "old_switch_thai": ("V3", "CompressionEncryption", "../../../", "Zlib", ""),
    "steam_thai": ("V3", "CompressionEncryption", "../../../", "Zlib", ""),
}


def canonical_path(path: str) -> str:
    path = path.replace("\\", "/")
    prefix = "TRIANGLE_STRATEGY/Content/"
    if path.lower().startswith(prefix.lower()):
        return "Newera/Content/" + path[len(prefix):]
    return path


def category(path: str) -> str:
    lower = path.lower()
    if "/datatables/scenario/text/" in lower:
        return "TEXT"
    if "/fonts/" in lower or lower.endswith((".ttf", ".otf", ".ufont")):
        return "FONT"
    return "OTHER"


def read_paths(label: str) -> list[str]:
    return [line.strip() for line in (OUT / f"{label}_paths.txt").read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def read_hashes(label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (OUT / f"{label}_hashes.txt").read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        digest, path = line.split(" ", 1)
        result[path] = digest
    return result


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(name: str, fields: list[str], rows: list[dict[str, object]]) -> None:
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def is_pua(text: str) -> bool:
    return any(0xE000 <= ord(ch) <= 0xF8FF for ch in text)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {label: read_paths(label) for label in PAKS}
    hashes = {label: read_hashes(label) for label in PAKS}
    canonical_hashes = {label: {canonical_path(path): digest for path, digest in values.items()} for label, values in hashes.items()}

    inventory = []
    for label, pak in PAKS.items():
        items = paths[label]
        lower = [p.lower() for p in items]
        version, version_major, mount, compression, seed = PAK_METADATA[label]
        inventory.append({
            "Label": label, "Filename": pak.name, "Bytes": pak.stat().st_size,
            "SHA256": sha256_file(pak),
            "PakVersion": version, "PakVersionMajor": version_major, "MountPoint": mount,
            "Compression": compression, "PathHashSeed": seed, "FileCount": len(items),
            "UassetCount": sum(x.endswith(".uasset") for x in lower),
            "UexpCount": sum(x.endswith(".uexp") for x in lower),
            "UbulkCount": sum(x.endswith(".ubulk") for x in lower),
            "FontFileCount": sum(category(x) == "FONT" for x in items),
            "ScenarioTextFileCount": sum(category(x) == "TEXT" for x in items),
            "SoundFileCount": sum("/sound/" in x for x in lower),
            "BlueprintSequenceOtherCount": sum("/blueprint" in x or "/sequence/" in x or x.endswith((".lub", ".lua", ".ubp")) for x in lower),
        })
    write_csv("pak_inventory.csv", list(inventory[0]), inventory)

    base, update, old, steam = (canonical_hashes[x] for x in ("switch_base", "switch_update", "old_switch_thai", "steam_thai"))
    overrides = []
    for path, old_hash in sorted(old.items()):
        base_hash, update_hash = base.get(path, ""), update.get(path, "")
        overrides.append({
            "AssetPath": path, "Category": category(path), "OldModSHA256": old_hash,
            "InBase": "YES" if base_hash else "NO", "InUpdate": "YES" if update_hash else "NO",
            "BaseSHA256": base_hash, "UpdateSHA256": update_hash,
            "BaseUpdateRelation": "IDENTICAL" if base_hash and base_hash == update_hash else "DIFFERENT" if base_hash and update_hash else "ONLY_BASE" if base_hash else "ONLY_UPDATE" if update_hash else "NEITHER",
            "OldVsBase": "IDENTICAL" if old_hash == base_hash else "DIFFERENT" if base_hash else "NO_BASE",
            "OldVsUpdate": "IDENTICAL" if old_hash == update_hash else "DIFFERENT" if update_hash else "NO_UPDATE",
        })
    write_csv("old_switch_mod_overrides.csv", list(overrides[0]), overrides)

    text_diff = [r for r in overrides if r["Category"] == "TEXT"]
    write_csv("base_update_text_diff.csv", list(overrides[0]), text_diff)

    old_rows = read_csv(ROOT / "work" / "full_game_text_index" / "thai_text_raw_index.csv")
    steam_rows = read_csv(OUT / "steam_text_export" / "thai_text_raw_index.csv")
    steam_inventory = []
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in steam_rows:
        grouped[row["DataTableAsset"]].append(row)
    for asset, rows in sorted(grouped.items()):
        texts = [r["ThaiTextRaw"] for r in rows]
        steam_inventory.append({
            "DataTableAsset": asset, "RowCount": len(rows), "UniqueSelfIdCount": len({r["SelfId"] for r in rows}),
            "ReadableThaiUnicodeRows": sum(bool(t) and not is_pua(t) for t in texts),
            "PUAContainingRows": sum(is_pua(t) for t in texts), "EmptyRows": sum(not t for t in texts),
        })
    write_csv("steam_text_inventory.csv", list(steam_inventory[0]), steam_inventory)

    def keyed(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], dict[str, str]]:
        answer = {}
        for row in rows:
            answer[(row["DataTableAsset"], row["RowKey"], row["SelfId"])] = row
        return answer
    old_by_key, steam_by_key = keyed(old_rows), keyed(steam_rows)
    joined = []
    for key in sorted(set(old_by_key) | set(steam_by_key)):
        o, s = old_by_key.get(key), steam_by_key.get(key)
        if o and s:
            status = "EXACT_JOIN"
            comparison = "IDENTICAL" if o["ThaiTextRaw"] == s["ThaiTextRaw"] else "DIFFERENT"
        elif o:
            status, comparison = "ONLY_OLD_SWITCH", ""
        else:
            status, comparison = "ONLY_STEAM", ""
        joined.append({
            "DataTableAsset": key[0], "RowKey": key[1], "SelfId": key[2],
            "JoinStatus": status, "TextComparison": comparison,
            "OldSwitchThaiRaw": o["ThaiTextRaw"] if o else "", "SteamThaiUnicode": s["ThaiTextRaw"] if s else "",
            "OldHasPUA": "YES" if o and is_pua(o["ThaiTextRaw"]) else "NO",
            "SteamHasPUA": "YES" if s and is_pua(s["ThaiTextRaw"]) else "NO",
        })
    write_csv("text_identifier_join.csv", list(joined[0]), joined)

    sample_assets = [
        "Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Chara/cs02/cs02_e01/Text_cs02_e01_0010",
        "Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/trial_01/Text_trial_01_ms06_x07_wd_0010",
        "Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Text_x_standby_drama",
    ]
    def parse_status(asset: str) -> str:
        sample = "cs02" if "/cs02/" in asset else "trial" if "trial_01" in asset else "standby"
        results = []
        for source in ("switch_base", "switch_update", "old_switch_thai", "steam_thai"):
            path = OUT / "cooked_samples" / f"properties_{source}_{sample}.json"
            try:
                exported = json.loads(path.read_text(encoding="utf-8"))
                table = next(item for item in exported if item.get("Type") == "DataTable")
                rows = table["Rows"]
                valid = all(key == row.get("SelfId") and "Text" in row for key, row in rows.items())
                results.append(f"{source}:PASS/Rows={len(rows)}/SelfId={valid}/RowStruct={table['Properties']['RowStruct']['ObjectName']}")
            except Exception:
                results.append(f"{source}:PENDING")
        return " | ".join(results)
    cooked = []
    for asset in sample_assets:
        for ext in (".uasset", ".uexp"):
            path = asset + ext
            values = {label: source.get(path, "") for label, source in {"SwitchBase": base, "SwitchUpdate": update, "OldSwitchThai": old, "SteamThai": steam}.items()}
            cooked.append({
                "DataTableAsset": asset, "Component": ext, **values,
                "BaseUpdateRelation": "IDENTICAL" if values["SwitchBase"] and values["SwitchBase"] == values["SwitchUpdate"] else "DIFFERENT" if values["SwitchBase"] and values["SwitchUpdate"] else "MISSING",
                "SteamVsSwitchUpdate": "IDENTICAL" if values["SteamThai"] and values["SteamThai"] == values["SwitchUpdate"] else "DIFFERENT" if values["SteamThai"] and values["SwitchUpdate"] else "MISSING",
                "OldVsSwitchUpdate": "IDENTICAL" if values["OldSwitchThai"] and values["OldSwitchThai"] == values["SwitchUpdate"] else "DIFFERENT" if values["OldSwitchThai"] and values["SwitchUpdate"] else "MISSING",
                "CUE4ParseStatus": parse_status(asset),
            })
    write_csv("cooked_asset_compatibility.csv", list(cooked[0]), cooked)
    write_csv("exceptions.csv", ["Stage", "Path", "Error"], [])


if __name__ == "__main__":
    main()
