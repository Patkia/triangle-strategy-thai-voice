#!/usr/bin/env python3
"""Fail-closed Unicode-to-old-Switch-PUA encoder POC for the opening sentence."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

TARGET = "ในทวีปอันห่างไกลแห่งนอร์เซเลีย ถูกปกครองโดยอาณาจักรมหาอำนาจทั้งสาม"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def cps(value: str) -> str:
    return " ".join(f"U+{ord(char):04X}" for char in value)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    dictionary = root / "work/new_subtitle_switch/pua_dictionary"
    mapping = read_csv(dictionary / "pua_mapping.csv")
    clusters = read_csv(dictionary / "pua_cluster_mapping.csv")
    verified = [row for row in mapping if row.get("status", "").upper() == "VERIFIED" and row.get("replacement") not in {"", "-", "UNMAPPED"}]
    reverse: dict[str, list[str]] = defaultdict(list)
    forward = {}
    for row in verified:
        codepoint = row["codepoint"]
        glyph = chr(int(codepoint[2:], 16))
        reverse[row["replacement"]].append(codepoint)
        forward[glyph] = row["replacement"]
    ambiguities = {text: values for text, values in reverse.items() if len(values) > 1}
    literal = set()
    for row in read_csv(root / "work/full_game_text_index/thai_text_raw_index.csv"):
        literal.update(char for char in row["ThaiTextRaw"] if not (0xE000 <= ord(char) <= 0xF8FF))
    verified_clusters = [row for row in clusters if row.get("status") == "VERIFIED"]
    candidate_clusters = [row for row in clusters if row.get("status") == "CLUSTER_CANDIDATE"]
    verified_clusters.sort(key=lambda row: len(row["source_codepoints"].split()), reverse=True)
    candidate_clusters.sort(key=lambda row: len(row["replacement"]), reverse=True)
    cluster_reverse = {row["replacement"]: row["source_sequence"] for row in verified_clusters}
    replacements = sorted(reverse, key=len, reverse=True)

    encoded: list[str] = []
    steps = []
    missing = []
    dependencies = []
    index = 0
    while index < len(TARGET):
        # Cluster matching is deliberately first and consumes the entire source
        # sequence, preventing a duplicated trailing U+0E32.
        cluster_match = next((row for row in verified_clusters if TARGET.startswith(row["replacement"], index)), None)
        if cluster_match is not None:
            encoded.append(cluster_match["source_sequence"])
            steps.append({"position": index, "source": cluster_match["replacement"], "source_codepoints": cps(cluster_match["replacement"]), "method": "VERIFIED_CLUSTER", "output": cps(cluster_match["source_sequence"])})
            index += len(cluster_match["replacement"]); continue
        matched = next((value for value in replacements if TARGET.startswith(value, index)), None)
        if matched is not None:
            values = reverse[matched]
            if len(values) != 1:
                missing.append({"position": index, "substring": matched, "codepoints": cps(matched), "reason": "ambiguous VERIFIED reverse mapping"})
                index += len(matched); continue
            glyph = chr(int(values[0][2:], 16))
            encoded.append(glyph)
            steps.append({"position": index, "source": matched, "source_codepoints": cps(matched), "method": "VERIFIED", "output": values[0]})
            index += len(matched); continue
        cluster = next((row for row in candidate_clusters if TARGET.startswith(row["replacement"], index)), None)
        if cluster is not None:
            dependencies.append({"position": index, "substring": cluster["replacement"], "codepoints": cps(cluster["replacement"]), "required_rule": cluster["source_codepoints"], "status": cluster["status"]})
            missing.append({"position": index, "substring": cluster["replacement"], "codepoints": cps(cluster["replacement"]), "reason": f"requires unverified cluster rule {cluster['source_codepoints']}"})
            index += len(cluster["replacement"]); continue
        char = TARGET[index]
        if char in literal:
            encoded.append(char)
            steps.append({"position": index, "source": char, "source_codepoints": cps(char), "method": "LITERAL_OBSERVED_IN_CORPUS", "output": cps(char)})
        else:
            missing.append({"position": index, "substring": char, "codepoints": cps(char), "reason": "no VERIFIED reverse mapping and literal Unicode character not observed in old corpus"})
        index += 1

    encoded_value = "".join(encoded)
    decoded_parts = []
    cursor = 0
    while cursor < len(encoded_value):
        cluster = next((row for row in verified_clusters if encoded_value.startswith(row["source_sequence"], cursor)), None)
        if cluster is not None:
            decoded_parts.append(cluster["replacement"]); cursor += len(cluster["source_sequence"]); continue
        decoded_parts.append(forward.get(encoded_value[cursor], encoded_value[cursor])); cursor += 1
    decoded = "".join(decoded_parts)
    result = {
        "status": "PASS" if not missing and decoded == TARGET else "BLOCKED",
        "target": TARGET,
        "target_codepoints": cps(TARGET),
        "verified_mapping_count": len(verified),
        "clusters_considered": [{"source_codepoints": row["source_codepoints"], "replacement": row["replacement"], "status": row["status"]} for row in candidate_clusters],
        "encodable_steps": len(steps),
        "target_codepoint_count": len(TARGET),
        "missing": missing,
        "ambiguities": ambiguities,
        "cluster_dependencies": dependencies,
        "encoded_codepoints": cps(encoded_value),
        "encoded_escaped": encoded_value.encode("unicode_escape").decode("ascii"),
        "roundtrip": decoded,
        "roundtrip_exact": decoded == TARGET and not missing,
        "pua_used": sum(0xE000 <= ord(char) <= 0xF8FF for char in encoded_value),
        "literal_unicode_used": sum(not (0xE000 <= ord(char) <= 0xF8FF) for char in encoded_value),
        "steps": steps,
    }
    out = dictionary / "opening_sentence_encoder_poc.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "encodable_steps", "target_codepoint_count", "missing", "ambiguities", "cluster_dependencies", "roundtrip_exact", "pua_used", "literal_unicode_used")}, ensure_ascii=True))


if __name__ == "__main__":
    main()
