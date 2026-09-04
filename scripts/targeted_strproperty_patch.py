from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import struct
from pathlib import Path

RELATIVE = Path("Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/trial_01/Text_trial_01_ms06_x07_wd_0010")
SELF_ID = "TRIAL_01_MS06_X07_WD_0010_N_NNN_0010"
ORIGINAL_TEXT = "On the faraway continent of Norzelia, three mighty powers reigned."
THAI_TEXT = "ในทวีปอันห่างไกลแห่งนอร์เซเลีย ถูกปกครองโดยอาณาจักรมหาอำนาจทั้งสาม"
CONTROL_TEXT = "A" * len(ORIGINAL_TEXT)
EXPECTED_UASSET_SHA256 = "a6414d8e3e886ae60c6c6bc14c9cf63ed76d77b098bb3558b5a75e9bc1eaa677"
EXPECTED_UEXP_SHA256 = "ab289a3ea1c82c3a81323b0a683ed153e9124722b0a1f1beeb42f2e2b4708a7f"
NAME_MAP_OFFSET = 193
NAME_MAP_COUNT = 31
EXPORT_SERIAL_SIZE_OFFSET = 1413
EXPORT_SERIAL_OFFSET = 1421
FOOTER_SIZE = 4


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def read_i64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<q", data, offset)[0]


def write_i32(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<i", data, offset, value)


def write_i64(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<q", data, offset, value)


def parse_name_map(data: bytes) -> list[str]:
    offset = NAME_MAP_OFFSET
    names: list[str] = []
    for _ in range(NAME_MAP_COUNT):
        count = read_i32(data, offset)
        offset += 4
        byte_count = count if count > 0 else -count * 2
        raw = data[offset:offset + byte_count]
        offset += byte_count
        if len(raw) != byte_count or not raw.endswith(b"\x00" if count > 0 else b"\x00\x00"):
            raise ValueError("ชื่อใน NameMap มี FString ไม่สมบูรณ์")
        names.append(raw[:-1].decode("utf-8") if count > 0 else raw[:-2].decode("utf-16le"))
        offset += 4
    if names[9] != "None" or names[14] != "SelfId" or names[15] != "StrProperty" or names[16] != "Text":
        raise ValueError("NameMap ไม่ตรงกับ asset เป้าหมายที่พิสูจน์แล้ว")
    return names


def read_fname(data: bytes, offset: int, names: list[str]) -> tuple[str, int]:
    index, number = struct.unpack_from("<II", data, offset)
    if index >= len(names):
        raise ValueError(f"FName index นอก NameMap ที่ offset {offset}")
    if number != 0:
        raise ValueError(f"FName number ที่ไม่คาดไว้ที่ offset {offset}")
    return names[index], offset + 8


def read_fstring(data: bytes, offset: int) -> tuple[str, int, str, int]:
    count = read_i32(data, offset)
    if count == 0:
        return "", offset + 4, "EMPTY", count
    if count > 0:
        raw = data[offset + 4:offset + 4 + count]
        if len(raw) != count or raw[-1:] != b"\x00":
            raise ValueError("ANSI FString ไม่มี terminator")
        return raw[:-1].decode("utf-8"), offset + 4 + count, "ANSI/UTF-8", count
    byte_count = -count * 2
    raw = data[offset + 4:offset + 4 + byte_count]
    if len(raw) != byte_count or raw[-2:] != b"\x00\x00":
        raise ValueError("UTF-16 FString ไม่มี terminator")
    return raw[:-2].decode("utf-16le"), offset + 4 + byte_count, "UTF-16LE", count


def encode_fstring(value: str) -> tuple[bytes, str, int]:
    if value.isascii():
        payload = value.encode("utf-8") + b"\x00"
        return struct.pack("<i", len(payload)) + payload, "ANSI/UTF-8", len(payload)
    units = len(value.encode("utf-16le")) // 2
    payload = value.encode("utf-16le") + b"\x00\x00"
    return struct.pack("<i", -(units + 1)) + payload, "UTF-16LE", -(units + 1)


def locate_target(uexp: bytes, names: list[str]) -> dict[str, int | str]:
    name, offset = read_fname(uexp, 0, names)
    type_name, offset = read_fname(uexp, offset, names)
    size = read_i32(uexp, offset)
    offset += 4
    array_index = read_i32(uexp, offset)
    offset += 4
    has_guid = uexp[offset]
    offset += 1
    if (name, type_name, size, array_index, has_guid) != ("RowStruct", "ObjectProperty", 4, 0, 0):
        raise ValueError("UDataTable RowStruct tag ไม่ตรงกับ serialization ที่พิสูจน์แล้ว")
    offset += size
    terminator, offset = read_fname(uexp, offset, names)
    if terminator != "None":
        raise ValueError("ไม่พบ property terminator ของ UDataTable")
    unknown_prefix_offset = offset
    unknown_prefix = read_i32(uexp, offset)
    offset += 4
    row_count_offset = offset
    row_count = read_i32(uexp, offset)
    offset += 4
    if row_count != 13:
        raise ValueError(f"จำนวน rows ไม่ตรง: {row_count}")

    target: dict[str, int | str] | None = None
    for _ in range(row_count):
        row_start = offset
        row_name, offset = read_fname(uexp, offset, names)
        properties: list[dict[str, int | str]] = []
        while True:
            property_start = offset
            property_name, offset = read_fname(uexp, offset, names)
            if property_name == "None":
                break
            property_type, offset = read_fname(uexp, offset, names)
            property_size_offset = offset
            property_size = read_i32(uexp, offset)
            offset += 4
            property_array_index = read_i32(uexp, offset)
            offset += 4
            property_has_guid = uexp[offset]
            offset += 1
            if property_array_index != 0 or property_has_guid != 0:
                raise ValueError("PropertyTag ของ row มี field เพิ่มที่ยังไม่ได้พิสูจน์")
            data_start = offset
            data_end = data_start + property_size
            if data_end > len(uexp):
                raise ValueError("PropertyTag เกินขอบเขต .uexp")
            properties.append({
                "start": property_start,
                "name": property_name,
                "type": property_type,
                "size_offset": property_size_offset,
                "size": property_size,
                "data_start": data_start,
                "data_end": data_end,
            })
            offset = data_end
        if row_name != SELF_ID:
            continue
        if len(properties) != 2:
            raise ValueError("target row ไม่มี property สองรายการตามที่พิสูจน์แล้ว")
        self_id_property = next((item for item in properties if item["name"] == "SelfId"), None)
        text_property = next((item for item in properties if item["name"] == "Text"), None)
        if self_id_property is None or text_property is None:
            raise ValueError("target row ไม่มี SelfId หรือ Text")
        if self_id_property["type"] != "NameProperty" or self_id_property["size"] != 8:
            raise ValueError("SelfId PropertyTag ไม่ตรงกับ serialization ที่พิสูจน์แล้ว")
        self_id, _ = read_fname(uexp, int(self_id_property["data_start"]), names)
        if self_id != SELF_ID:
            raise ValueError("SelfId value ไม่ตรงกับ row key")
        if text_property["type"] != "StrProperty":
            raise ValueError("Text ไม่ใช่ StrProperty")
        text, text_end, encoding, length_value = read_fstring(uexp, int(text_property["data_start"]))
        if text_end != text_property["data_end"] or text_property["size"] != text_end - int(text_property["data_start"]):
            raise ValueError("StrProperty.Size ไม่สอดคล้องกับ FString")
        target = {
            "row_start": row_start,
            "row_end": offset,
            "unknown_prefix_offset": unknown_prefix_offset,
            "unknown_prefix": unknown_prefix,
            "row_count_offset": row_count_offset,
            "row_count": row_count,
            "self_id_start": int(self_id_property["start"]),
            "self_id_end": int(self_id_property["data_end"]),
            "text_property_start": int(text_property["start"]),
            "text_size_offset": int(text_property["size_offset"]),
            "text_data_start": int(text_property["data_start"]),
            "text_data_end": int(text_property["data_end"]),
            "text_property_end": int(text_property["data_end"]),
            "text_property_size": int(text_property["size"]),
            "text": text,
            "text_encoding": encoding,
            "text_length_value": length_value,
        }
    if target is None:
        raise ValueError("ไม่พบ target row")
    if offset != len(uexp) - FOOTER_SIZE:
        raise ValueError("ท้าย export ไม่ตรงกับ expected footer boundary")
    return target


def write_map(path: Path, uasset: bytes, uexp: bytes, target: dict[str, int | str]) -> None:
    rows = [
        ("uasset", "file size", len(uasset), "PROVEN", "source copy SHA-256 verified"),
        ("uexp", "file size", len(uexp), "PROVEN", "source copy SHA-256 verified"),
        ("uasset", "Export.SerialSize offset", EXPORT_SERIAL_SIZE_OFFSET, "PROVEN", f"int64={read_i64(uasset, EXPORT_SERIAL_SIZE_OFFSET)}"),
        ("uasset", "Export.SerialOffset offset", EXPORT_SERIAL_OFFSET, "PROVEN", f"int64={read_i64(uasset, EXPORT_SERIAL_OFFSET)}; absolute file offset equals original .uasset size"),
        ("uexp", "serialized export size", len(uexp) - FOOTER_SIZE, "PROVEN", "total .uexp bytes minus unchanged four-byte footer"),
        ("uexp", "footer", f"{len(uexp) - FOOTER_SIZE}-{len(uexp) - 1}", "NOT AFFECTED", uexp[-FOOTER_SIZE:].hex()),
        ("uexp", "unknown pre-row field", f"{target['unknown_prefix_offset']} value={target['unknown_prefix']}", "NOT AFFECTED", "before row map and no offset points into payload"),
        ("uexp", "row count", f"{target['row_count_offset']} value={target['row_count']}", "NOT AFFECTED", "row count unchanged"),
        ("uexp", "target row", f"{target['row_start']}-{target['row_end'] - 1}", "PROVEN", SELF_ID),
        ("uexp", "SelfId NameProperty", f"{target['self_id_start']}-{target['self_id_end'] - 1}", "NOT AFFECTED", "NameProperty size=8; value and row key unchanged"),
        ("uexp", "Text StrProperty", f"{target['text_property_start']}-{target['text_property_end'] - 1}", "PROVEN", f"size={target['text_property_size']}; {target['text_encoding']}; FString length={target['text_length_value']}"),
        ("uexp", "Text StrProperty.Size", target["text_size_offset"], "PROVEN AND AFFECTED", "int32 serialized payload size"),
        ("uexp", "Text FString", f"{target['text_data_start']}-{target['text_data_end'] - 1}", "PROVEN AND AFFECTED", "int32 FString length followed by terminated character data"),
        ("uexp", "row/struct size field", "none present in this row encoding", "NOT AFFECTED", "row boundary is property tags ending in FName None"),
        ("uasset", "other package metadata", "unchanged", "NOT AFFECTED", "one export; SerialOffset remains 1509; header length unchanged"),
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("File", "Field", "Offset or range", "Status", "Evidence"))
        writer.writerows(rows)


def prepare_root(output_root: Path, source_uasset: Path, source_uexp: Path) -> None:
    for suffix, source in ((".uasset", source_uasset), (".uexp", source_uexp)):
        destination = output_root / RELATIVE.with_suffix(suffix)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"ปลายทางมีอยู่แล้ว: {destination}")
        shutil.copy2(source, destination)


def patch_variant(root: Path, replacement: str, original_uasset: bytes, original_uexp: bytes, target: dict[str, int | str]) -> None:
    encoded, _, _ = encode_fstring(replacement)
    delta = len(encoded) - int(target["text_property_size"])
    patched_uexp = bytearray()
    patched_uexp += original_uexp[:int(target["text_size_offset"])]
    patched_uexp += struct.pack("<i", len(encoded))
    patched_uexp += original_uexp[int(target["text_size_offset"]) + 4:int(target["text_data_start"])]
    patched_uexp += encoded
    patched_uexp += original_uexp[int(target["text_data_end"]):]
    patched_uasset = bytearray(original_uasset)
    if delta:
        write_i64(patched_uasset, EXPORT_SERIAL_SIZE_OFFSET, read_i64(original_uasset, EXPORT_SERIAL_SIZE_OFFSET) + delta)
    expected_serial_size = len(patched_uexp) - FOOTER_SIZE
    if read_i64(patched_uasset, EXPORT_SERIAL_SIZE_OFFSET) != expected_serial_size:
        raise ValueError("Export.SerialSize หลัง patch ไม่ตรงกับ .uexp payload")
    if read_i64(patched_uasset, EXPORT_SERIAL_OFFSET) != len(original_uasset):
        raise ValueError("Export.SerialOffset ไม่เท่าจุดเริ่ม .uexp เดิม")
    target_base = root / RELATIVE
    target_base.with_suffix(".uasset").write_bytes(patched_uasset)
    target_base.with_suffix(".uexp").write_bytes(patched_uexp)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("control", "unicode"))
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    source_base = workspace / "work/uasset_writer_poc/original" / RELATIVE
    original_uasset = source_base.with_suffix(".uasset").read_bytes()
    original_uexp = source_base.with_suffix(".uexp").read_bytes()
    if sha256(original_uasset) != EXPECTED_UASSET_SHA256 or sha256(original_uexp) != EXPECTED_UEXP_SHA256:
        raise ValueError("source copy hash ไม่ตรงกับ target ที่ Mission 3 ตรวจแล้ว")
    names = parse_name_map(original_uasset)
    target = locate_target(original_uexp, names)
    if target["text"] != ORIGINAL_TEXT:
        raise ValueError("target Text ต้นฉบับไม่ตรงกับข้อความที่ Mission ระบุ")
    if read_i64(original_uasset, EXPORT_SERIAL_SIZE_OFFSET) != len(original_uexp) - FOOTER_SIZE:
        raise ValueError("Export.SerialSize ต้นฉบับไม่ตรงกับ .uexp")
    poc_root = workspace / "work/new_subtitle_switch/targeted_patch_poc"
    if args.mode == "control":
        prepare_root(poc_root / "original", source_base.with_suffix(".uasset"), source_base.with_suffix(".uexp"))
        prepare_root(poc_root / "control", source_base.with_suffix(".uasset"), source_base.with_suffix(".uexp"))
        patch_variant(poc_root / "control", CONTROL_TEXT, original_uasset, original_uexp, target)
        write_map(poc_root / "serialization_map.csv", original_uasset, original_uexp, target)
    else:
        control_base = poc_root / "control" / RELATIVE
        if not control_base.with_suffix(".uasset").exists() or not control_base.with_suffix(".uexp").exists():
            raise ValueError("ต้องสร้างและตรวจ control ก่อนสร้าง Unicode variant")
        prepare_root(poc_root / "unicode", source_base.with_suffix(".uasset"), source_base.with_suffix(".uexp"))
        patch_variant(poc_root / "unicode", THAI_TEXT, original_uasset, original_uexp, target)


if __name__ == "__main__":
    main()
