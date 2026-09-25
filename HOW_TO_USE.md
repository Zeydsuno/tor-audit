# 📘 คู่มือการใช้งาน Enterprise TOR & Contract Risk Auditor (`enterprise-tor-auditor`)

> **ระบบตรวจสอบร่างสัญญาจัดซื้อจัดจ้าง (TOR), สกัดระดับการให้บริการ (SLA), และคำนวณเพดานค่าปรับล่าช้าอัตโนมัติ**  
> สถาปัตยกรรม: **Sovereign Offline-First | SQLite FTS5 | Deterministic Python Math | Zero Parametric Memory**

---

## 📌 สารบัญ (Table of Contents)
1. [ภาพรวมสถาปัตยกรรม (Architecture Overview)](#1-ภาพรวมสถาปัตยกรรม)
2. [วิธีใช้งานผ่าน Terminal / PowerShell (โหมดปิดเน็ต 100% ไม่ใช้ AI)](#2-วิธีใช้งานผ่าน-terminal--powershell-โหมดปิดเน็ต-100-ไม่ใช้-ai)
3. [วิธีใช้งานผ่านหน้าต่าง AI Chat (โหมดแชทอัจฉริยะ)](#3-วิธีใช้งานผ่านหน้าต่าง-ai-chat-โหมดแชทอัจฉริยะ)
4. [แหล่งดาวน์โหลดไฟล์ TOR จริงของ ปตท. และ e-GP (ถูกกฎหมาย 100%)](#4-แหล่งดาวน์โหลดไฟล์-tor-จริงของ-ปตท-และ-e-gp-ถูกกฎหมาย-100)
5. [โครงสร้างไฟล์และ Ground Truth (ไม้บรรทัดอ้างอิง)](#5-โครงสร้างไฟล์และ-ground-truth-ไม้บรรทัดอ้างอิง)
6. [สถาปัตยกรรมความปลอดภัยและการปรับแต่ง (Security & Rule Customization)](#6-สถาปัตยกรรมความปลอดภัยและการปรับแต่ง-security--rule-customization)

---

## 1. ภาพรวมสถาปัตยกรรม

ระบบนี้ถูกออกแบบมาเพื่อแก้ปัญหา **"การตรวจสัญญา TOR หนา 100–200 หน้า"** ขององค์กรระดับ Enterprise โดยไม่พึ่งพาความจำมโนของ AI (Zero Parametric Memory):

* **สกัดข้อความอัตโนมัติ:** อ่านไฟล์ PDF / Web URL / Text แล้วยัดเข้า **SQLite FTS5 (`tor_vault.db`)**
* **คิดเลขแม่นยำ 100%:** ใช้ Python Math คำนวณค่าปรับรายวันตามระเบียบกระทรวงการคลัง และคำนวณจุดตัดเพดานบอกเลิกสัญญา 10% ตาม พ.ร.บ. จัดซื้อจัดจ้างฯ มาตรา 103
* **ตรวจจับกับดักสัญญา (Ponytail Risk Tags):**
  * `[SCOPE-CREEP-TRAP]` ข้อความปลายเปิดให้สั่งงานเพิ่มฟรี
  * `[AMBIGUOUS-ACCEPTANCE]` เกณฑ์ตรวจรับงานตามดุลยพินิจอัตวิสัย
  * `[UNREALISTIC-SLA]` กำหนดแก้ปัญหาไวเกินจริงโดยไม่มีงบ On-call 24x7
  * `[PENALTY-TRAP]` คิดค่าปรับจากสัญญาทั้งหมดแทนที่จะคิดจากส่วนที่ยังไม่ส่งมอบ

---

## 2. วิธีใช้งานผ่าน Terminal / PowerShell (โหมดปิดเน็ต 100% ไม่ใช้ AI)

คุณสามารถเปิด **PowerShell** หรือ **Command Prompt** แล้วรันสคริปต์ได้โดยตรง **แม้จะปิดเน็ตหรือไม่มี AI ก็ทำงานได้ 100%**:

### 🔹 2.1 ทดสอบระบบเดโมเสมือนจริง (Enterprise IT Cloud Modernization):
```powershell
python E:\Brainstrom\.agents\skills\enterprise-tor-auditor\scripts\tor_scraper.py --scrape-mock --contract-value 50000000 --audit
```

### 🔹 2.2 สแกนไฟล์ PDF สัญญาจริงในเครื่องของคุณ:
```powershell
python E:\Brainstrom\.agents\skills\enterprise-tor-auditor\scripts\tor_scraper.py --scrape-file "C:\Users\Downloads\PTT_TOR.pdf" --contract-value 30000000 --audit
```

### 🔹 2.3 สแกนตรงจากลิงก์เว็บประกาศจัดซื้อจัดจ้าง:
```powershell
python E:\Brainstrom\.agents\skills\enterprise-tor-auditor\scripts\tor_scraper.py --scrape-url "https://example.com/procurement/tor_spec.html" --contract-value 25000000 --audit
```

### 🔹 2.4 คำนวณเฉพาะค่าปรับและวันบอกเลิกสัญญา (Calculator Only):
```powershell
# คำนวณสัญญา 40 ล้านบาท ปรับวันละ 0.1% หากส่งงานช้าสะสม 60 วัน:
python E:\Brainstrom\.agents\skills\enterprise-tor-auditor\scripts\tor_scraper.py --calc-penalty --contract-value 40000000 --rate 0.001 --days 60
```

### 🔹 2.5 พ่นผลลัพธ์เป็น JSON บริสุทธิ์ (สำหรับส่งต่อไปยัง Web Dashboard / API / LINE Bot):
```powershell
python E:\Brainstrom\.agents\skills\enterprise-tor-auditor\scripts\tor_scraper.py --audit --contract-value 50000000 --json
```

---

## 3. วิธีใช้งานผ่านหน้าต่าง AI Chat (โหมดแชทอัจฉริยะ)

เวลาใช้งานในหน้าต่าง Chat ของ Antigravity สามารถพิมพ์สั่งงานด้วยภาษาไทยธรรมชาติ หรือใช้คำสั่ง Slash Command:

* **คำสั่งลัด:**
  * `/tor-audit` : สั่งตรวจสัญญาทั้งฉบับ
  * `/tor-penalty` : คำนวณเพดานค่าปรับและวันบอกเลิกสัญญา
  * `/tor-sla` : สกัดเฉพาะเงื่อนไข SLA และเวลาตอบสนอง MTTR
* **ตัวอย่างประโยคสั่งงาน:**
  * *"ช่วยตรวจไฟล์ TOR นี้ให้หน่อย มีข้อสัญญาดักอะไรไหม"*
  * *"สัญญาจ้างไอทีมูลค่า 30 ล้าน ปรับวันละ 0.1% ถ้าส่งช้า 40 วัน จะโดนปรับเท่าไหร่และมีสิทธิ์โดนยกเลิกสัญญาไหม"*
  * *"สกัดตารางงวดงานและเกณฑ์ SLA จากเอกสาร TOR ฉบับนี้ให้ที"*

---

## 4. แหล่งดาวน์โหลดไฟล์ TOR จริงของ ปตท. และ e-GP (ถูกกฎหมาย 100%)

คุณสามารถดาวน์โหลดเอกสารจริงมาทดสอบในเครื่องได้ฟรีตามกฎหมายความโปร่งใสภาครัฐ:

1. **เว็บไซต์จัดซื้อจัดจ้าง ปตท. โดยตรง (PTT Procurement):**
   * URL ทางการ: [https://procurement.pttplc.com](https://procurement.pttplc.com)
   * เมนู: *"ประกาศจัดซื้อจัดจ้าง" ➔ "ร่างขอบเขตของงาน (TOR)"*
   * หมวดที่น่าสนใจ: งานจ้างพัฒนาระบบเทคโนโลยีสารสนเทศ, งานติดตั้งโครงสร้างพื้นฐานดิจิทัล
2. **ระบบ e-GP กรมบัญชีกลาง (ระบบจัดซื้อจัดจ้างภาครัฐ):**
   * URL ทางการ: [http://www.gprocurement.go.th](http://www.gprocurement.go.th) (ต้องใส่ `www.` เสมอตามระบบ DNS ของราชการ)
   * ค้นหาโครงการ: ใส่คำว่า *"ปตท."* หรือ *"ระบบคลาวด์"* หรือ *"ซอฟต์แวร์"* แล้วโหลดไฟล์ PDF ร่าง TOR
3. **จรรยาบรรณคู่ค้าและนโยบายจัดซื้อจัดจ้าง SCG:**
   * ค้นหาบน Google: `SCG Supplier Code of Conduct filetype:pdf`
   * เป็นเอกสารมาตรฐานคู่ค้าสำหรับตรวจเช็กข้อกำหนดด้านความปลอดภัยและ ESG

---

## 5. โครงสร้างไฟล์และ Ground Truth (ไม้บรรทัดอ้างอิง)

ทุกอย่างถูกเก็บไว้ในโฟลเดอร์ของ Skill: `E:\Brainstrom\.agents\skills\enterprise-tor-auditor\`

```
enterprise-tor-auditor/
├── HOW_TO_USE.md                     # 📖 คู่มือการใช้งานฉบับนี้
├── SKILL.md                          # 🧠 กฎและพฤติกรรมของ Agent (ผ่าน Linter 100%)
├── scripts/
│   └── tor_scraper.py                # ⚙️ สคริปต์หลัก: ดูด Text, รัน FTS5, คำนวณค่าปรับ
├── references/
│   ├── procurement_rules.json        # ⚖️ Ground Truth กฎหมายจัดซื้อจัดจ้างฯ 2560 ม.9, 102, 103 + ข้อ 162
│   └── risk_patterns.json            # 🎯 Ground Truth คำกับดักสัญญา (Scope Creep, อัตวิสัย)
└── data/
    └── tor_vault.db                  # 🗄️ ฐานข้อมูล SQLite FTS5 รันค้นหาในเครื่อง Sub-5ms
```

## 6. สถาปัตยกรรมความปลอดภัยและการปรับแต่ง (Security & Rule Customization)

### 🔒 6.1 นโยบายความปลอดภัยและการคุ้มครองข้อมูล (Data Governance & Air-Gapped)
* **Zero Cloud Leak:** ตัวเอนจินทำงานแบบ Local-First 100% ฐานข้อมูล SQLite FTS5 และการคำนวณทั้งหมดอยู่บนเครื่องคอมพิวเตอร์ของคุณ
* **Non-Destructive Processing:** สคริปต์ทำหน้าที่อ่านข้อมูลอย่างเดียว (Read-Only Analysis) ไม่มีการแก้ไขหรือเขียนทับไฟล์สัญญาต้นฉบับ
* **Air-Gapped Compatible:** รองรับการติดตั้งและประมวลผลบนเครือข่ายความมั่นคงสูงที่ตัดการเชื่อมต่อจากอินเทอร์เน็ตภายนอก 100%

### ⚙️ 6.2 การเพิ่มคำกับดักและปรับแต่งเกณฑ์เฉพาะองค์กร (Extending Risk Rules)
คุณสามารถปรับแต่งหรือเพิ่มคำกับดักสัญญาเฉพาะองค์กรได้โดยตรงที่ไฟล์ [`references/risk_patterns.json`](references/risk_patterns.json):
```json
{
  "tag": "CUSTOM-VENDOR-RISK",
  "severity": "HIGH",
  "description": "ข้อกำหนดเฉพาะที่องค์กรต้องการตรวจจับ",
  "patterns": [
    "คำค้นหาที่ 1",
    "คำค้นหาที่ 2"
  ],
  "mitigation": "แนวทางปฏิบัติหรือการเจรจาแก้ไขสัญญาที่แนะนำ"
}
```
เมื่อแก้ไขเสร็จ สคริปต์ `tor_scraper.py` จะนำเกณฑ์ใหม่ไปตรวจจับในรอบถัดไปโดยอัตโนมัติ ไม่ต้องคอมไพล์โค้ดใหม่
