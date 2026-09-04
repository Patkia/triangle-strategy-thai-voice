from __future__ import annotations

import csv
import struct
from pathlib import Path


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def tag(data: bytes, offset: int) -> str:
    return data[offset:offset + 4].decode("latin-1")


def tables(data: bytes) -> dict[str, tuple[int, int]]:
    count = u16(data, 4)
    result = {}
    for index in range(count):
        offset = 12 + index * 16
        result[tag(data, offset)] = (u32(data, offset + 8), u32(data, offset + 12))
    return result


def font_names(data: bytes, directory: dict[str, tuple[int, int]]) -> str:
    if "name" not in directory:
        return ""
    base, _ = directory["name"]
    count = u16(data, base + 2)
    strings = base + u16(data, base + 4)
    preferred = []
    for index in range(count):
        record = base + 6 + index * 12
        platform, encoding, language, name_id, length, offset = struct.unpack_from(">HHHHHH", data, record)
        if name_id not in (1, 2):
            continue
        raw = data[strings + offset:strings + offset + length]
        try:
            value = raw.decode("utf-16-be") if platform in (0, 3) else raw.decode("mac_roman")
        except UnicodeDecodeError:
            continue
        preferred.append((name_id, platform == 3 and language in (0, 0x409), value))
    family = next((value for name_id, best, value in preferred if name_id == 1 and best), "")
    style = next((value for name_id, best, value in preferred if name_id == 2 and best), "")
    return (family + " " + style).strip()


def cmap_coverage(data: bytes, directory: dict[str, tuple[int, int]]) -> set[int]:
    base, _ = directory["cmap"]
    count = u16(data, base + 2)
    values: set[int] = set()
    for index in range(count):
        subtable = base + u32(data, base + 8 + index * 8)
        fmt = u16(data, subtable)
        if fmt == 4:
            seg_count = u16(data, subtable + 6) // 2
            end_codes = subtable + 14
            start_codes = end_codes + seg_count * 2 + 2
            deltas = start_codes + seg_count * 2
            ranges = deltas + seg_count * 2
            for segment in range(seg_count):
                start, end = u16(data, start_codes + segment * 2), u16(data, end_codes + segment * 2)
                if start <= end:
                    values.update(range(start, end + 1))
        elif fmt == 12:
            groups = u32(data, subtable + 12)
            for group in range(groups):
                start, end = struct.unpack_from(">II", data, subtable + 16 + group * 12)
                values.update(range(start, end + 1))
    return values


def layout(data: bytes, directory: dict[str, tuple[int, int]], table_tag: str) -> dict[str, object]:
    if table_tag not in directory:
        return {"present": False}
    base, _ = directory[table_tag]
    script_list, feature_list, lookup_list = (base + u16(data, base + item) for item in (4, 6, 8))
    features: list[tuple[str, list[int]]] = []
    feature_count = u16(data, feature_list)
    for index in range(feature_count):
        record = feature_list + 2 + index * 6
        feature_tag = tag(data, record)
        feature = feature_list + u16(data, record + 4)
        lookup_count = u16(data, feature + 2)
        features.append((feature_tag, [u16(data, feature + 4 + item * 2) for item in range(lookup_count)]))
    scripts: dict[str, list[int]] = {}
    script_count = u16(data, script_list)
    for index in range(script_count):
        record = script_list + 2 + index * 6
        script_tag = tag(data, record)
        script = script_list + u16(data, record + 4)
        lang_offsets = [u16(data, script)]
        language_count = u16(data, script + 2)
        lang_offsets += [u16(data, script + 4 + item * 6 + 4) for item in range(language_count)]
        feature_indexes: set[int] = set()
        for lang_offset in lang_offsets:
            if not lang_offset:
                continue
            langsys = script + lang_offset
            required = u16(data, langsys + 2)
            count = u16(data, langsys + 4)
            if required != 0xFFFF:
                feature_indexes.add(required)
            feature_indexes.update(u16(data, langsys + 6 + item * 2) for item in range(count))
        scripts[script_tag] = sorted(feature_indexes)
    lookup_base = lookup_list
    lookup_offsets = [u16(data, lookup_base + 2 + item * 2) for item in range(u16(data, lookup_base))]
    lookup_types = []
    for offset in lookup_offsets:
        lookup_types.append(u16(data, lookup_base + offset))
    thai_features = [features[index] for index in scripts.get("thai", []) if index < len(features)]
    thai_feature_tags = [item[0] for item in thai_features]
    thai_lookups = [lookup for _, indices in thai_features for lookup in indices]
    thai_types = [lookup_types[index] for index in thai_lookups if index < len(lookup_types)]
    return {
        "present": True,
        "scripts": sorted(scripts),
        "features": [item[0] for item in features],
        "thai_features": thai_feature_tags,
        "thai_lookup_types": thai_types,
        "mark": "mark" in thai_feature_tags,
        "mkmk": "mkmk" in thai_feature_tags,
        "mark_to_base": thai_types.count(4),
        "mark_to_ligature": thai_types.count(5),
        "mark_to_mark": thai_types.count(6),
    }


def analyze(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    directory = tables(data)
    cmap = cmap_coverage(data, directory)
    gsub = layout(data, directory, "GSUB")
    gpos = layout(data, directory, "GPOS")
    return {
        "Path": path.as_posix(),
        "Bytes": len(data),
        "FontName": font_names(data, directory),
        "ThaiUnicodeCoverage": sum(codepoint in cmap for codepoint in range(0x0E00, 0x0E7F + 1)),
        "PUACoverage": sum(codepoint in cmap for codepoint in range(0xE000, 0xF8FF + 1)),
        "GSUB": "YES" if gsub["present"] else "NO",
        "GSUBThaiScript": "YES" if "thai" in gsub.get("scripts", []) else "NO",
        "GSUBThaiFeatures": ";".join(gsub.get("thai_features", [])),
        "GPOS": "YES" if gpos["present"] else "NO",
        "GPOSThaiScript": "YES" if "thai" in gpos.get("scripts", []) else "NO",
        "GPOSThaiFeatures": ";".join(gpos.get("thai_features", [])),
        "ThaiMarkFeature": "YES" if gpos.get("mark") else "NO",
        "ThaiMkmkFeature": "YES" if gpos.get("mkmk") else "NO",
        "ThaiMarkToBaseLookups": gpos.get("mark_to_base", 0),
        "ThaiMarkToLigatureLookups": gpos.get("mark_to_ligature", 0),
        "ThaiMarkToMarkLookups": gpos.get("mark_to_mark", 0),
        "TableTags": ";".join(sorted(directory)),
    }


def main() -> None:
    root = Path.cwd() / "work/new_subtitle_switch/unicode_font_poc"
    font_paths = [
        path for path in sorted((root / "extracted_sources").rglob("*"))
        if path.is_file() and path.read_bytes()[:4] in (b"\x00\x01\x00\x00", b"OTTO")
    ]
    rows = [analyze(path) for path in font_paths]
    with (root / "font_shaping_analysis.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
