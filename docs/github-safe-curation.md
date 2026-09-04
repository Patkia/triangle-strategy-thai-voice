# GitHub-safe Repository Curation

## สถานะ

**PASS** — workspace ถูกเตรียมด้วย allowlist-minded `.gitignore` และ safe derivative metadata โดยไม่ใช้ Git, ไม่ลบไฟล์ local และไม่แก้ game/mod asset

## ไฟล์ที่สร้างหรือแก้ไข

- `.gitignore` — deny-by-default; เปิดเฉพาะ source/docs/data ที่ review แล้ว
- `README.md` — ขอบเขต, architecture, runtime milestone, credits และ legal disclaimer ภาษาไทย
- `tools/export_safe_pua_mapping.py` — exporter read-only สำหรับ metadata ปลอด dialogue
- `data/pua_mapping.safe.csv` — simple mapping ที่ sanitize แล้ว
- `data/pua_cluster_mapping.safe.csv` — cluster mapping ที่ sanitize แล้ว
- `docs/github-safe-curation.md` — รายงานนี้

## SAFE_TO_COMMIT allowlist

```text
.gitignore
README.md
AGENTS.md
scripts/**/*.py
scripts/**/*.ps1
tools/**/*.py
data/*.safe.csv
docs/github-readiness-audit.md
docs/github-safe-curation.md
```

source tooling ใช้ relative project root/argument paths; scan ไม่พบ hardcoded `C:\...` ภายใต้ `scripts/` และ `tools/` ที่อยู่ใน allowlist. Script เหล่านี้ยังต้องใช้ input ที่ผู้ใช้จัดหาเองแบบ local ตามกฎหมาย และไม่ควรมี input เหล่านั้นใน repository

## LOCAL_ONLY

```text
TRIANGLE STRATEGY */
subthai/
men/
Output/
work/
vgmstream-win64/
FModel.exe
*.pak *.uasset *.uexp *.ubulk *.awb *.acb *.hca *.wav *.lub *.nso *.ufont
```

รวมถึง generated PAK, LayeredFS staging, ExeFS/NSO, extracted texture/font/audio, downloaded tools, models, cache, FModel export, Steam Thai asset และ old Switch Thai PAK ทั้งหมด

## Docs classification

เพื่อ fail closed เอกสาร existing ทั้งหมดที่ไม่ใช่สองรายการด้านล่างถูกจัดเป็น **LOCAL_ONLY** ใน phase นี้ แม้บางไฟล์อาจเป็น methodology ได้ เพราะอย่างน้อย 29 ไฟล์มี dialogue/cue/text corpus หรือ evidence จากเกม และยังไม่ได้ redaction ทีละไฟล์

| กลุ่ม | สถานะ |
| --- | --- |
| `docs/github-readiness-audit.md` | SAFE |
| `docs/github-safe-curation.md` | SAFE |
| `docs/*.md`, `docs/*.csv` อื่นทั้งหมด | LOCAL_ONLY |
| sanitized copy ของเอกสาร existing | ยังไม่มี; สร้างเฉพาะเมื่อ redact แล้วผ่าน review |

## Mapping sanitization

source of truth local ยังอยู่ที่ `work/new_subtitle_switch/pua_dictionary/` และไม่ได้แก้ไข

| Safe file | เนื้อหา | จำนวน |
| --- | --- | ---: |
| `data/pua_mapping.safe.csv` | `codepoint,replacement,status,rule_type,notes_safe` เท่านั้น | 546 simple rules: VERIFIED 110, UNMAPPED 436 |
| `data/pua_cluster_mapping.safe.csv` | `input_codepoints,output_sequence,status,rule_type,notes_safe` เท่านั้น | 3 cluster rules: VERIFIED 1, CLUSTER_CANDIDATE 2 |

safe derivative ไม่มี raw text, decoded dialogue, Steam Thai sentence, English game dialogue, SelfId, asset path หรือ sample context. `pua_mapping.csv`, `decoded_rows.csv`, `manual_lookup.csv`, `review_queue.csv`, `exhaustive_validation.csv` และ text indexes ทั้งหมดยังคง LOCAL_ONLY

## Secret, size และ copyright scans ของ proposed set

- secret scan: ไม่พบ credential value; พบ symbolic `token` ใน 2 source files (`extract_nso_segments.py`, `decode_old_thai_pua.py`) ซึ่งเป็น parser/placeholder logic ไม่ใช่ key/password/token สำหรับ service
- large-file scan: ไม่มี proposed file เกิน 1 MB
- copyright scan: พบชื่อ asset/cue/field และข้อความ POC เดี่ยวใน source บางไฟล์; ไม่พบ ROM, PAK, binary, audio, raw corpus, text index หรือ dialogue collection ใน allowlist
- ข้อจำกัด: source ที่กล่าวถึง asset internal path ยังเป็น technical methodology; ผู้ใช้ต้อง supply input ที่ได้มาโดยชอบด้วยกฎหมายเอง

## Credits และ legal scope

README ระบุเครดิตอย่างจำกัดหลักฐาน:

- LAN&HACKv2 และ [Facebook Group](https://www.facebook.com/groups/624645023291178) เป็น original Thai Switch technical/reference baseline; local `THAI-Newera-Switch_P.pak` กับ runtime `Newera-Switch_P.pak` คือไฟล์/ม็อดเดียวกันคนละชื่อเพื่อแยกแยะ
- ไม่พบโพสต์แจกต้นฉบับในปัจจุบัน จึงไม่ claim provenance เพิ่ม
- [เม่นแปลเกม (Hedgy Translator)](https://www.facebook.com/HedgyTranslator/) เป็น translation/localization reference เท่านั้น

README ยังระบุชัดว่า repository ไม่แจก ROM, original asset, third-party Thai mod PAK หรือ Steam translation PAK

## ความพร้อม

- **PRIVATE_REPO_READY: YES** สำหรับ proposed allowlist เท่านั้น; ห้าม `git add .`
- **PUBLIC_REPO_READY: YES** สำหรับ proposed allowlist เดียวกัน โดยมีเงื่อนไขว่าต้องตรวจ diff ก่อน commit ทุกครั้ง และไม่ขยาย allowlist ไปยัง `work/`, `Output/`, PAK หรือ corpus

## ขั้นตอนถัดไปที่แนะนำ

ให้ผู้ใช้ review รายชื่อ allowlist แล้วจึงทำ mission แยกสำหรับ `git init` และ staged-file verification แบบ explicit. ก่อนถึงขั้นนั้น ห้ามสร้าง repository, commit หรือ push
