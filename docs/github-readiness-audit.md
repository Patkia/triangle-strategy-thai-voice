# GitHub Readiness Audit — Triangle Strategy Thai

## สถานะ

**AUDIT COMPLETE — ยังไม่พร้อมเผยแพร่ทั้ง private และ public ในสภาพ workspace ปัจจุบัน**

การตรวจนี้เป็น read-only ยกเว้นการสร้างรายงานฉบับนี้ ไม่มี `git init`, `git add`, commit, push, ลบ หรือย้ายไฟล์

## ขอบเขตที่ตรวจ

- ไฟล์ทั้งหมดนอก `.git`: 32,533 ไฟล์, ประมาณ 26.18 GB
- binary/game-related ที่ตรวจพบ: 12,079 ไฟล์, ประมาณ 14.38 GB
- เอกสาร `docs/`: 61 ไฟล์, 340,790 bytes; อย่างน้อย 29 ไฟล์มี dialogue/transcript หรือข้อมูล cue/text จากเกม
- source ที่เป็น `.py/.ps1/.cs/.csproj/.sln` ภายใต้ `scripts/` และ `tools/`: 68 ไฟล์, ประมาณ 358 KiB

## A. SAFE_TO_COMMIT (หลังตรวจเนื้อหารายไฟล์ก่อนเลือก)

| Path/pattern | จำนวน/ขนาดโดยประมาณ | เหตุผล/เงื่อนไข |
| --- | ---: | --- |
| `AGENTS.md`, `README.md` | 2 ไฟล์, ~14 KiB | เอกสารโครงการที่เขียนเอง; README ต้องปรับ disclaimer/credit ก่อน public |
| `scripts/*.py`, `scripts/*.ps1`, `tools/*.py` | 68 ไฟล์, ~358 KiB | tooling ที่เขียนเอง; scan ไม่พบ hardcoded Windows absolute path ใน source เหล่านี้ แต่หลาย script ต้องรับ game/mod input จากผู้ใช้เอง |
| `work/new_subtitle_switch/pua_dictionary/pua_cluster_mapping.csv` | 1 ไฟล์, 674 B | metadata cluster สั้น ไม่มี corpus หลายแถว; ตรวจ license/provenance อีกครั้งก่อน public |
| เอกสาร methodology ที่ไม่มี transcript หรือ payload เกม | subset ของ `docs/` | ควรคัดเลือกแบบ allowlist ไม่ใช่ commit `docs/**` ทั้งหมด |

## B. MUST_IGNORE

| Path/pattern | จำนวน/ขนาดโดยประมาณ | ความเสี่ยง |
| --- | ---: | --- |
| `TRIANGLE STRATEGY 1.1.1 */**`, `TRIANGLE STRATEGY [*][BASE]/**` | ROM dump และ `Newera-Switch.pak`; หลาย GB | copyrighted game dump/assets |
| `subthai/**`, โดยเฉพาะ `THAI-Newera-Switch_P.pak` | PAK ~40 MB พร้อม extracted assets | third-party Thai mod และ payload จากเกม |
| `men/**`, โดยเฉพาะ `men/Paks/1-TSTH_P.pak`, `youtube.mp4` | third-party mod/video | copyright/provenance ไม่ใช่ของโครงการ |
| `Output/**` | exports/cache ของ FModel รวม asset/text/audio | extracted copyrighted content และ cache |
| `work/**` | tooling cache, extraction, Ghidra/JDK/STT, POC builds, LayeredFS staging | มี game assets, generated PAK, audio, text corpus, binary และไฟล์ขนาดใหญ่ปะปน |
| `*.pak`, `*.uasset`, `*.uexp`, `*.ubulk`, `*.awb`, `*.acb`, `*.hca`, `*.wav`, `*.lub`, `*.nso`, `main` | อย่างน้อย 12,079 binary game-related files | copyrighted game/mod assets; custom PAK ยังบรรจุ cooked game asset ที่ดัดแปลง |
| `*.ufont`, `*.ttf`, `*.otf`, `*.png`, `*.dds` จาก extraction/POC | font/texture/media ที่มาจากเกมหรือม็อด | copyright/license ต้องแยกพิสูจน์ ไม่ควร commit จาก workspace นี้ |
| `FModel.exe`, `vgmstream-win64/**`, `work/tools/**` ที่เป็น binary/download | executable/dependency/cache | size/license/reproducibility; ให้ติดตั้งตามเอกสารแทน |
| `atmosphere/**`, `**/layeredfs/**` | staging สำหรับ SD | มี PAK/game assets และเสี่ยงแจก deploy bundle |

ไฟล์ใหญ่ที่เด่น:

- มากกว่า 50 MB: Update/Base `Newera-Switch.pak`, `men/youtube.mp4`, AWB, Ghidra projects/tool archives, NSO analysis output และ STT models
- 10–50 MB: `FModel.exe` (51.4 MB), old Thai PAK (~40 MB), Steam Thai PAK, `main`, AWB หลาย bank, text-index/validation ใหญ่ และ .NET tooling

## C. REVIEW_BEFORE_COMMIT

| Path/pattern | ความเสี่ยง/ข้อสรุป |
| --- | --- |
| `work/new_subtitle_switch/pua_dictionary/pua_mapping.csv` (~1.05 MiB) | **ไม่ควร commit ตรง ๆ**: มี sample contexts, SelfId, asset path, raw/decoded Thai dialogue และ third-party translation content หลายรายการ; หากจำเป็นต้องเผยแพร่ ให้สร้าง schema/minimal verified mapping ใหม่ใน phase ถัดไป |
| `decoded_rows.csv` (~9.86 MiB), `manual_lookup.csv` (~1.04 MiB), `review_queue.csv`, `exhaustive_validation.csv` (~10.64 MiB) | corpus/game dialogue และ translation lookup; ต้อง ignore |
| `english_text_index.csv`, `thai_text_raw_index.csv`, `text_identifier_join.csv`, source indexes, FModel Properties JSON | reproduce text/assets จากเกมหรือม็อด; ต้อง ignore |
| `docs/` ที่มี transcript/cue inventories | พบอย่างน้อย 29 ไฟล์ที่ match dialogue/cue indicators; review/ย่อเป็น methodology ก่อน public |
| screenshots, PNG/audio previews, inventory/report ที่ embed asset metadata | ตรวจแหล่งที่มาและ license เป็นรายไฟล์; default เป็น ignore |
| scripts ที่ชี้ path ภายใน game เช่น asset internal paths | โค้ดเผยแพร่ได้ในหลักการ แต่ต้องเปลี่ยนเป็น CLI/config template และระบุว่า user supply input ที่ได้มาโดยชอบด้วยกฎหมาย |

## Secret scan

- สแกนชื่อไฟล์และ 857 text-like files ขนาดไม่เกิน 5 MB ด้วย pattern credential assignment โดยไม่บันทึกค่า
- พบ 6 files ที่ match คำทั่วไป `token`/`secret`/`password` เป็นต้น: source/tool logs; ต้อง human-review ก่อน allowlist
- ใน `scripts/` และ `tools/` พบเฉพาะ references เชิง logic/documentation ของ token/secret ไม่พบ hardcoded absolute path `C:\...`
- ไม่มีหลักฐานเพียงพอที่จะรับรองว่าไม่มี secret ทุกชนิดใน binary/cache ดังนั้น `work/**`, `Output/**`, downloaded tool caches และ `.env` ต้อง ignore ทั้งหมด

## ความพร้อมของ repository

- **PRIVATE_REPO_READY: NO** — แม้ private ก็ไม่ควร upload ROM dump, game/mod asset, PAK, corpus หรือ executable ที่ยังไม่ได้ตรวจ license; ต้องใช้ allowlist และ `.gitignore` ก่อน
- **PUBLIC_REPO_READY: NO** — ต้องคัด source/docs ใหม่, ตัด transcript/indexes/translation corpus, ตรวจ licenses ของ dependency ที่อ้างถึง และเพิ่ม legal/credit notice ก่อน

หลัง remediation repository สามารถ reproducible ได้ในขอบเขต **tooling + methodology**: ผู้ใช้ต้อง supply game, update, old Thai mod และ third-party tools ที่ได้มาอย่างถูกต้องเองผ่าน local paths/config; repository ไม่ควรแจก input เหล่านั้นหรือ PAK output

## Preview `.gitignore` (ยังไม่ได้สร้าง)

```gitignore
# Game, ROM, mods, exports, and all generated investigation state
/TRIANGLE STRATEGY */
/subthai/
/men/
/Output/
/work/
/vgmstream-win64/
/FModel.exe

# Derived game/media assets and deploy packages
*.pak
*.uasset
*.uexp
*.ubulk
*.awb
*.acb
*.hca
*.wav
*.lub
*.nso
*.ufont

# Secrets and local configuration
.env
.env.*
*.pem
*.pfx
*.ppk
secrets.*
```

หากต้อง version generated safe metadata ในอนาคต ให้ย้าย/สร้างเฉพาะไฟล์ที่ผ่าน review ออกมาใน directory ใหม่ เช่น `metadata/`; ไม่ควรยกเลิก ignore `work/**` แบบกว้าง

## Preview โครงสร้าง repository (ยังไม่ได้สร้าง)

```text
README.md
AGENTS.md
LICENSE
docs/                 # methodology ที่ผ่าน content review
scripts/              # orchestration ที่รับ local input paths
tools/                # source utilities เท่านั้น
schemas/              # CSV/JSON schema และ synthetic fixtures
examples/             # synthetic/non-game examples
requirements/         # dependency versions และ install instructions
```

## README ที่ควรมีใน phase ถัดไป

1. ขอบเขต: tooling/methodology ไม่แจกเกม, ROM, audio, PAK, font หรือ translation corpus
2. Prerequisites: ผู้ใช้ supply game/update/mod ที่ได้มาโดยชอบด้วยกฎหมายเอง
3. Reproducibility: ให้ระบุ local input ผ่าน config template/CLI; ห้าม hardcode user path
4. Runtime milestone: Thai title logo และ opening sentence ผ่าน runtime test โดยไม่แนบ PAK output
5. Credits:
   - Original Thai for Nintendo Switch: LAN&HACKv2 — [Facebook Group](https://www.facebook.com/groups/624645023291178). ไม่มีโพสต์แจกต้นฉบับที่ตรวจพบในปัจจุบัน จึงไม่ควร claim provenance เพิ่มกว่านี้
   - Translation reference: เม่นแปลเกม (Hedgy Translator) — [Facebook](https://www.facebook.com/HedgyTranslator/)
6. Legal/Disclaimer: ไม่เกี่ยวข้องกับ Square Enix/Artdink/Nintendo; ไม่แจก copyrighted game assets หรือ third-party mod assets; ผู้ใช้รับผิดชอบสิทธิ์ของ input และการใช้งาน mod ในเขตอำนาจของตน

## Proposed next action

Mission ถัดไปควรเป็น **GitHub-safe repository curation**: สร้าง `.gitignore`, allowlist source/docs, synthetic fixture และ README/legal/credits ใหม่หลังผู้ใช้อนุมัติ scope; ไม่ควรใช้ `git add .` หรือย้าย asset โดยอัตโนมัติ
