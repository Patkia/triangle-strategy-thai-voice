# Triangle Strategy Thai

โครงการนี้ศึกษาวิธีทำภาษาไทยและเสียงไทยสำหรับ TRIANGLE STRATEGY เวอร์ชัน Nintendo Switch โดยเก็บเฉพาะ tooling, methodology และ metadata ที่ปลอดภัยต่อการเผยแพร่

หลักทำงานคือ **Evidence First**: ข้อสรุปเกี่ยวกับ asset, text, PAK และ runtime ต้องมาจากไฟล์จริงหรือการทดสอบจริง ไม่เดาโครงสร้างเกม

## สถาปัตยกรรมที่พิสูจน์แล้วในปัจจุบัน

```text
Unicode Thai master
  → fail-closed PUA encoder
  → targeted Switch DataTable patch
  → numeric-priority PAK
  → original known-working Thai font system
```

เป้าหมายในอนาคตสำหรับเสียงใช้ Unicode master เดียวกัน:

```text
Unicode Thai master → OmniVoice Thai → WAV/HCA/AWB
```

## Runtime milestones

- โลโก้ภาษาไทยบน Title Screen ผ่าน runtime test
- PUA opening sentence ผ่าน runtime test
- PAK รวมที่มีเฉพาะ logo และ opening PUA ผ่าน runtime test

ประโยค POC ที่ใช้ตรวจระบบ:

> ในทวีปอันห่างไกลแห่งนอร์เซเลีย ถูกปกครองโดยอาณาจักรมหาอำนาจทั้งสาม

## ขอบเขต repository

Repository นี้ **ไม่แจก** ROM, game PAK, assets, audio, font, PAK ของม็อด, Steam translation PAK หรือ output ที่สร้างจาก asset ของเกม ผู้ใช้ต้องจัดหา input ที่ได้มาโดยชอบด้วยกฎหมายด้วยตนเอง และใช้ config/path ในเครื่องของตนเอง

TRIANGLE STRATEGY และ game assets เป็นทรัพย์สินของเจ้าของสิทธิ์ที่เกี่ยวข้อง โครงการนี้ไม่เกี่ยวข้องหรือได้รับการรับรองจากเจ้าของสิทธิ์ดังกล่าว Third-party translation/mod เป็นผลงานของเจ้าของผลงานนั้น ๆ

## Credits

- ภาษาไทยต้นฉบับสำหรับ Nintendo Switch: LAN&HACKv2 — [Facebook Group](https://www.facebook.com/groups/624645023291178)
  - ไฟล์ม็อดที่ใช้เป็น technical/reference baseline ถูกเก็บใน workspace local ใต้ชื่อ `THAI-Newera-Switch_P.pak` เพื่อแยกแยะเท่านั้น; ชื่อที่ใช้จริงบน Switch คือ `Newera-Switch_P.pak` และเป็นไฟล์/ม็อดเดียวกัน ไม่ใช่สองม็อด
  - ผู้จัดทำไม่พบโพสต์แจกต้นฉบับในปัจจุบัน จึงไม่ claim provenance เกินหลักฐานนี้
- Translation/localization reference: [เม่นแปลเกม (Hedgy Translator)](https://www.facebook.com/HedgyTranslator/) ใช้เป็นแหล่งอ้างอิงสำนวนและภาษาไทยใหม่เท่านั้น ไม่ได้ claim ownership ของคำแปล

## เอกสารสำหรับผู้พัฒนา

- [GitHub readiness audit](docs/github-readiness-audit.md)
- [GitHub-safe curation](docs/github-safe-curation.md)

ก่อนเผยแพร่หรือสร้าง Git repository ให้ตรวจ proposed tracked set ตามเอกสาร curation และห้ามใช้ `git add .`
