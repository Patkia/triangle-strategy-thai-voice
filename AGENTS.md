# AGENTS.md

# Triangle Strategy Thai Voice Project

## เป้าหมายหลักของโครงการ

โครงการนี้มีเป้าหมายเพื่อสร้าง Mod พากย์เสียงภาษาไทยสำหรับเกม
Triangle Strategy เวอร์ชัน Nintendo Switch

เป้าหมายสุดท้ายคือ:

> สามารถแทนที่เสียงพูดภาษาอังกฤษของ Triangle Strategy
> ด้วยเสียงพากย์ภาษาไทย และนำไปใช้งานจริงบน Nintendo Switch ได้

การทำงานต้องพัฒนาเป็นขั้นตอน โดยพิสูจน์ pipeline ขนาดเล็กก่อน
แล้วจึงค่อยขยายไปยังเสียงพูดทั้งหมดของเกม

---

# กฎด้านภาษา

เอกสารทั้งหมดของโครงการต้องเขียนเป็นภาษาไทย

รวมถึง:

- README.md
- เอกสารใน docs/
- รายงาน Mission
- Investigation notes
- Technical notes
- Test reports
- Workflow documentation
- คู่มือการใช้งาน
- Troubleshooting
- comments ที่เป็นคำอธิบายยาวใน script

ชื่อไฟล์ ตัวแปร command และศัพท์เทคนิคสามารถใช้ภาษาอังกฤษได้ตามความเหมาะสม

ตัวอย่าง:

AWB
HCA
ACB
Unreal Engine
FModel
vgmstream
LayeredFS
stream_index
cue_id

ไม่จำเป็นต้องแปลศัพท์เทคนิคจนทำให้ความหมายคลุมเครือ

---

# หลักการสำคัญ

## 1. Evidence First

ห้ามเดาโครงสร้างของเกม

ทุกข้อสรุปเกี่ยวกับ:

- Voice Asset
- AWB
- HCA
- ACB
- Cue Sheet
- Unreal Asset
- Dialogue Mapping
- Stream Mapping
- Repacking
- LayeredFS

ต้องมีหลักฐานจากไฟล์จริงหรือผลการทดลอง

หากยังพิสูจน์ไม่ได้ ให้ระบุว่า:

"ยังไม่สามารถยืนยันได้"

พร้อมเสนอการทดลองที่เล็กที่สุดเพื่อพิสูจน์สมมติฐานนั้น

---

## 2. ห้ามแก้ไฟล์ต้นฉบับ

ไฟล์จาก ROMFS dump ถือเป็น read-only

ห้าม overwrite หรือ modify โดยตรง

โดยเฉพาะ:

Newera-Switch.pak

และไฟล์ทั้งหมดภายใน:

TRIANGLE STRATEGY 1.1.1 [0100CC80140F8800][v262144][UPD]

หากต้องทดลอง ให้ copy ไฟล์ไปยังพื้นที่ทำงานก่อน

แนะนำ:

work/

หรือ:

output/

---

## 3. ห้ามทำงานขนาดใหญ่โดยไม่จำเป็น

อย่า extract/rebuild archive หลาย GB ซ้ำโดยไม่มีเหตุผล

เริ่มจาก asset ขนาดเล็กที่สุดที่สามารถพิสูจน์ pipeline ได้

เป้าหมายแรกคือ:

1 voice line

ไม่ใช่ทั้งเกม

---

# Pipeline เป้าหมาย

Pipeline ที่โครงการต้องพิสูจน์ให้สำเร็จคือ:

Game ROMFS
↓
Newera-Switch.pak
↓
Unreal Voice Asset
↓
CRI Voice Data
↓
AWB
↓
HCA Streams
↓
WAV
↓
ระบุ Dialogue / Character / Scene
↓
สร้างเสียงพากย์ไทย
↓
WAV ภาษาไทย
↓
Encode HCA
↓
Rebuild AWB
↓
Rebuild Asset ที่จำเป็น
↓
สร้าง LayeredFS Mod
↓
Nintendo Switch
↓
เสียงภาษาไทยเล่นในเกมจริง

ทุกขั้นต้องสามารถทำซ้ำได้

---

# Proof of Concept

ก่อนทำทั้งเกม ต้องพิสูจน์ POC นี้ให้สำเร็จ:

English Voice Line 1 เสียง
↓
ระบุตำแหน่งในเกม
↓
แทนด้วยเสียงทดสอบ
↓
Rebuild
↓
LayeredFS
↓
เปิดเกมบน Switch
↓
เสียงใหม่เล่นแทนเสียงเดิม

หาก POC นี้ยังไม่สำเร็จ ห้ามขยายไปทำเสียงจำนวนมาก

---

# โครงสร้าง Workspace

Workspace หลัก:

<PROJECT_ROOT>

ข้อมูลปัจจุบันประกอบด้วย:

Output/
TRIANGLE STRATEGY 1.1.1 [0100CC80140F8800][v262144][UPD]/
vgmstream-win64/
FModel.exe

สามารถสร้างเพิ่มได้:

docs/
scripts/
work/
output/
tests/
tools/

---

# ข้อมูลที่พิสูจน์แล้ว

เกมใช้ Unreal Engine

พบ archive:

Newera-Switch.pak

พบ Voice Assets ที่:

Newera/Content/Newera/Sound/Stream/VOICE/EN/

ตัวอย่าง:

CS02_EN
CS03_EN
CS04_EN

พบอีกกลุ่มที่:

Newera/Content/Newera/Sound/VOICE/EN/

ซึ่งต้องตรวจสอบความสัมพันธ์กับ Stream Voice Assets ต่อไป

FModel สามารถ export:

CS02_EN.awb

ได้สำเร็จ

CS02_EN.awb ใช้:

CRI HCA

ข้อมูลที่ตรวจพบ:

Sample Rate: 48000 Hz
Channels: 1
Stream Count: 62

vgmstream สามารถ decode streams ภายใน AWB เป็น WAV ได้สำเร็จ

ตัวอย่าง:

CS02_EN_1.wav
CS02_EN_2.wav
CS02_EN_3.wav

และตรวจฟังแล้วพบว่าเป็นเสียงพูดจริงของเกม

---

# สิ่งที่ยังไม่ทราบ

ยังต้องพิสูจน์:

- stream แต่ละตัวตรงกับ dialogue ใด
- stream แต่ละตัวเป็นตัวละครใด
- CS02 หมายถึงอะไร
- ลำดับ stream สัมพันธ์กับ event/dialogue อย่างไร
- Sound/VOICE และ Sound/Stream/VOICE เชื่อมกันอย่างไร
- Cue Sheet อยู่ที่ใด
- มี ACB หรือ metadata แบบอื่นหรือไม่
- วิธี encode WAV กลับเป็น HCA
- วิธี rebuild AWB โดยรักษา index เดิม
- ต้องแก้ Unreal Asset เพิ่มหรือไม่
- วิธีสร้าง LayeredFS ที่เกมยอมรับ
- สามารถ override เฉพาะ asset โดยไม่ rebuild PAK ทั้งก้อนได้หรือไม่

ห้ามถือว่าสิ่งเหล่านี้เป็นข้อเท็จจริงจนกว่าจะพิสูจน์ได้

---

# Scripts

Scripts ที่สร้างต้อง:

- ไม่แก้ original files
- ใช้ relative path เมื่อเป็นไปได้
- รองรับ Windows
- มี error handling
- แสดงผลชัดเจน
- สามารถรันซ้ำได้
- ไม่ทำ destructive operation โดยอัตโนมัติ

หาก script จะ overwrite ไฟล์ ต้องเขียน output ไปยัง work/ หรือ output/

---

# Tools

Tools ที่มีอยู่แล้ว เช่น:

FModel
vgmstream

สามารถใช้เพื่อ investigation ได้

ก่อนเพิ่ม dependency หรือดาวน์โหลด tool ใหม่:

1. อธิบายว่าต้องใช้ทำอะไร
2. ตรวจสอบว่ามี tool ที่มีอยู่แล้วทำได้หรือไม่
3. เลือกเครื่องมือ open-source ที่เหมาะสมหากจำเป็น
4. ห้ามดาวน์โหลด executable ที่ไม่ทราบแหล่งที่มาโดยอัตโนมัติ

---

# Mission Workflow

ทำงานเป็น Mission

ตัวอย่าง:

Mission 1
Voice Asset Mapping

Mission 2
Single Voice Replacement POC

Mission 3
AWB Rebuild

Mission 4
LayeredFS Test

Mission ต่อไปกำหนดตามหลักฐานที่ได้จริง

เมื่อ Mission จบ ต้องหยุดและรายงานผลก่อน

ห้ามเริ่ม Mission ถัดไปเอง

---

# Mission Report

เมื่อจบแต่ละ Mission ต้องรายงาน:

## MISSION STATUS

### สถานะ
COMPLETE / PARTIAL / BLOCKED

### สิ่งที่ค้นพบ

### หลักฐาน

### ไฟล์ที่สร้างหรือแก้ไข

### Tests ที่ดำเนินการ

### สิ่งที่พิสูจน์แล้ว

### สิ่งที่ยังพิสูจน์ไม่ได้

### Blockers

### ความเสี่ยง

### Mission ถัดไปที่แนะนำ

---

# Definition of Done ของโครงการ

โครงการจะถือว่าสำเร็จเมื่อ:

1. สามารถ extract เสียงต้นฉบับได้
2. สามารถ map เสียงกับ dialogue ได้
3. สามารถสร้างเสียงภาษาไทยทดแทนได้
4. สามารถ encode กลับเป็น format ของเกมได้
5. สามารถ rebuild asset ที่จำเป็นได้
6. สามารถสร้าง LayeredFS Mod ได้
7. Nintendo Switch โหลด Mod ได้
8. เสียงภาษาไทยเล่นตรง dialogue ที่ต้องการ
9. ไม่มี crash หรือ audio corruption
10. workflow สามารถทำซ้ำกับเสียงอื่นได้
11. มีเอกสารภาษาไทยอธิบายขั้นตอนทั้งหมด
12. สามารถขยาย workflow ไปสู่การพากย์ทั้งเกมได้
