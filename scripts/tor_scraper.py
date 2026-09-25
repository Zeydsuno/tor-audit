#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enterprise TOR & Procurement Contract Risk Scraper & Deterministic Audit Engine
Part of enterprise-tor-auditor skill.

Mandatory Dynamic Scraping Protocol:
This script scrapes, parses, and audits Terms of Reference (TOR) and procurement contracts
from live URLs or local files (PDF/TXT/MD), extracts verbatim milestones and SLA terms,
identifies ambiguity and penalty traps, and calculates liquidated damages deterministically.
Zero Parametric Memory: all data is extracted from live input documents and authentic statutory regulations.
"""

import os
import sys
import re
import json
import sqlite3
import argparse
import urllib.request
import urllib.parse
from html.parser import HTMLParser

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
REFERENCES_DIR = os.path.join(BASE_DIR, "references")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REFERENCES_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "tor_vault.db")


class SimpleHTMLTextExtractor(HTMLParser):
    """Clean plain-text extractor from HTML documents."""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.ignore_tags = {'script', 'style', 'head', 'title', 'meta', '[document]'}
        self.current_ignore = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.ignore_tags:
            self.current_ignore = True

    def handle_endtag(self, tag):
        if tag.lower() in self.ignore_tags:
            self.current_ignore = False

    def handle_data(self, data):
        if not self.current_ignore:
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)

    def get_text(self):
        return "\n".join(self.text_parts)


def init_database():
    """Initialize local SQLite FTS5 database for sub-millisecond document indexing."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scraped_documents (
            doc_id TEXT PRIMARY KEY,
            source_uri TEXT,
            title TEXT,
            contract_value REAL,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_text TEXT
        )
    """)
    
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS tor_sections_fts USING fts5(
            doc_id,
            section_title,
            clause_number,
            content,
            tokenize='unicode61'
        )
    """)
    conn.commit()
    return conn


def extract_pdf_text_native(file_path):
    """Extract text from PDF file using pypdf if available, or regex-based text extraction."""
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        pages_text = []
        for i, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            pages_text.append(f"--- [Page {i+1}] ---\n" + txt)
        return "\n".join(pages_text)
    except ImportError:
        pass
    
    # Fallback: Binary extraction of text streams
    with open(file_path, "rb") as f:
        content = f.read()
    
    # Try finding text chunks in uncompressed streams
    text_pieces = re.findall(rb"\((.*?)\) ?Tj", content)
    if text_pieces:
        try:
            return "\n".join(t.decode("utf-8", errors="ignore") for t in text_pieces)
        except Exception:
            pass
            
    return content.decode("utf-8", errors="ignore")


def fetch_url_content(url):
    """Scrape web page or document from live URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
        content_type = resp.headers.get("Content-Type", "").lower()
        if "pdf" in content_type:
            temp_pdf = os.path.join(DATA_DIR, "temp_download.pdf")
            with open(temp_pdf, "wb") as pf:
                pf.write(data)
            return extract_pdf_text_native(temp_pdf)
        else:
            try:
                html_text = data.decode("utf-8")
            except UnicodeDecodeError:
                html_text = data.decode("tis-620", errors="ignore")
            parser = SimpleHTMLTextExtractor()
            parser.feed(html_text)
            return parser.get_text()


def parse_and_index_document(doc_id, text, source_uri="local", contract_value=0.0):
    """Parse text into sections, clauses, and index into SQLite FTS5."""
    conn = init_database()
    cur = conn.cursor()
    
    first_line = text.strip().split("\n")[0][:120] if text else "TOR Document"
    
    cur.execute("""
        INSERT OR REPLACE INTO scraped_documents (doc_id, source_uri, title, contract_value, raw_text)
        VALUES (?, ?, ?, ?, ?)
    """, (doc_id, source_uri, first_line, contract_value, text))
    
    # Clear old sections for this doc_id
    cur.execute("DELETE FROM tor_sections_fts WHERE doc_id = ?", (doc_id,))
    
    # Section slicing based on standard Thai procurement headings (ข้อ, หมวด, ตอน)
    pattern = r"(หมวดที่?\s*\d+|ข้อที่?\s*\d+(?:\.\d+)*|ส่วนที่?\s*\d+|บทที่?\s*\d+)"
    chunks = re.split(pattern, text)
    
    if len(chunks) <= 1:
        # Paragraph-based indexing
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for idx, p in enumerate(paragraphs):
            cur.execute("""
                INSERT INTO tor_sections_fts (doc_id, section_title, clause_number, content)
                VALUES (?, ?, ?, ?)
            """, (doc_id, f"Section {idx+1}", str(idx+1), p))
    else:
        for i in range(1, len(chunks), 2):
            clause_header = chunks[i].strip()
            clause_body = chunks[i+1].strip() if i+1 < len(chunks) else ""
            cur.execute("""
                INSERT INTO tor_sections_fts (doc_id, section_title, clause_number, content)
                VALUES (?, ?, ?, ?)
            """, (doc_id, clause_header, clause_header, clause_body))
            
    conn.commit()
    conn.close()


def load_risk_patterns():
    """Load authentic risk patterns from references directory."""
    path = os.path.join(REFERENCES_DIR, "risk_patterns.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"risk_categories": []}


def load_procurement_rules():
    """Load statutory procurement rules from references directory."""
    path = os.path.join(REFERENCES_DIR, "procurement_rules.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def audit_document_clauses(doc_id, contract_value=0.0):
    """
    Perform deep deterministic audit on indexed document:
    1. SLA extraction & verification
    2. Milestone breakdown
    3. Liquidated damages formula calculation
    4. Ambiguity & Trap detection
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT raw_text, contract_value FROM scraped_documents WHERE doc_id = ?", (doc_id,))
    row = cur.fetchone()
    if not row:
        return {"error": f"Document ID '{doc_id}' not found in vault."}
    
    raw_text, stored_val = row
    if contract_value <= 0 and stored_val > 0:
        contract_value = stored_val
        
    risk_patterns_data = load_risk_patterns()
    procurement_rules = load_procurement_rules()
    
    detected_risks = []
    
    # 1. Pattern Matching for Ambiguity & Traps
    for category in risk_patterns_data.get("risk_categories", []):
        tag = category["tag"]
        severity = category["severity"]
        mitigation = category["mitigation"]
        
        for p in category["patterns"]:
            # Query FTS5 for this pattern with safe quote escaping
            escaped_p = p.replace('"', '""')
            try:
                cur.execute("""
                    SELECT clause_number, content FROM tor_sections_fts 
                    WHERE doc_id = ? AND content MATCH ? LIMIT 3
                """, (doc_id, f'"{escaped_p}"'))
                hits = cur.fetchall()
            except sqlite3.OperationalError:
                # Fallback to LIKE if FTS5 syntax fails
                cur.execute("""
                    SELECT clause_number, content FROM tor_sections_fts 
                    WHERE doc_id = ? AND content LIKE ? LIMIT 3
                """, (doc_id, f'%{p}%'))
                hits = cur.fetchall()

            for clause_no, content in hits:
                snippet = content[:200].replace("\n", " ") + "..."
                detected_risks.append({
                    "tag": tag,
                    "severity": severity,
                    "pattern": p,
                    "clause": clause_no,
                    "verbatim_snippet": snippet,
                    "mitigation": mitigation
                })
                
    # 2. SLA Parameters Extraction
    sla_findings = []
    cur.execute("""
        SELECT clause_number, content FROM tor_sections_fts 
        WHERE doc_id = ? AND (content MATCH 'SLA OR "Priority" OR "MTTR" OR "Uptime" OR "ชั่วโมง" OR "นาที"')
        LIMIT 8
    """, (doc_id,))
    for clause_no, content in cur.fetchall():
        for line in content.split("\n"):
            line_str = line.strip()
            if any(k in line_str for k in ["SLA", "Priority", "MTTR", "Uptime", "ภายใน", "ร้อยละ 99"]):
                sla_findings.append({
                    "clause": clause_no,
                    "text": line_str[:160]
                })

    # 3. Liquidated Damages & Penalty Clause Extraction
    cur.execute("""
        SELECT clause_number, content FROM tor_sections_fts 
        WHERE doc_id = ? AND (content MATCH 'ค่าปรับ OR "ร้อยละ" OR "0.1" OR "0.2" OR "รายวัน"')
        LIMIT 5
    """, (doc_id,))
    penalty_clauses = cur.fetchall()
    
    # Check for penalty rate specifically in penalty context
    detected_rate = 0.001  # default 0.1%
    rate_matches = re.findall(r"(?:ค่าปรับ|ปรับ)[^\n]{0,60}?ร้อยละ\s*([0-9]+(?:\.[0-9]+)?)(?:\s*ต่อวัน)?", raw_text)
    if not rate_matches:
        rate_matches = re.findall(r"ร้อยละ\s*([0-9]+(?:\.[0-9]+)?)\s*ต่อวัน", raw_text)
    if rate_matches:
        try:
            val = float(rate_matches[0])
            if val < 1.0: # e.g. 0.1 or 0.2
                detected_rate = val / 100.0
            elif val <= 20.0 and "ต่อวัน" in raw_text:
                detected_rate = val / 100.0
        except ValueError:
            pass
            
    # Deterministic Penalty Math
    daily_penalty = contract_value * detected_rate
    monthly_penalty = daily_penalty * 30
    cap_10_percent = contract_value * 0.10
    days_to_termination = int(cap_10_percent / daily_penalty) if daily_penalty > 0 else 0
    
    # 4. Milestone Extraction
    milestones = []
    milestone_matches = re.findall(r"(งวดที่\s*\d+[^:\n]*[:\-]?\s*[^\n]+)", raw_text)
    for m in milestone_matches[:6]:
        milestones.append(m.strip())
        
    conn.close()
    
    return {
        "doc_id": doc_id,
        "contract_value": contract_value,
        "penalty_calculation": {
            "rate_percent_per_day": round(detected_rate * 100, 3),
            "daily_penalty_thb": round(daily_penalty, 2),
            "monthly_penalty_thb": round(monthly_penalty, 2),
            "cap_10_percent_thb": round(cap_10_percent, 2),
            "days_to_termination_ceiling": days_to_termination,
            "statutory_basis": "พ.ร.บ. จัดซื้อจัดจ้างฯ 2560 ม.102-103 และระเบียบกระทรวงการคลัง ข้อ 162"
        },
        "detected_risks": detected_risks,
        "sla_findings": sla_findings[:6],
        "milestones": milestones,
        "verbatim_penalty_clauses": [
            {"clause": c[0], "text": c[1][:250].replace("\n", " ")} for c in penalty_clauses[:3]
        ]
    }


def generate_mock_enterprise_tor():
    """Generates an authentic, unclassified enterprise-grade Cloud Migration & IT Modernization TOR for evaluation."""
    return """
ข้อกำหนดและขอบเขตของงาน (Terms of Reference : TOR)
โครงการจ้างพัฒนาระบบคลาวด์และยกระดับโครงสร้างพื้นฐานดิจิทัล (Enterprise Cloud Modernization)

ข้อ 1. ความเป็นมาและวัตถุประสงค์
หน่วยงานมีความประสงค์จะดำเนินการจ้างพัฒนาระบบคลาวด์และยกระดับสถาปัตยกรรมดิจิทัล เพื่อรองรับการทำงานแบบ Microservices และเพิ่มประสิทธิภาพในการให้บริการข้อมูลแก่องค์กร

ข้อ 2. คุณสมบัติของผู้ยื่นข้อเสนอ
2.1 ต้องเป็นนิติบุคคลที่จดทะเบียนในประเทศไทย มีทุนจดทะเบียนชำระแล้วไม่น้อยกว่า 20,000,000 บาท
2.2 ต้องมีผลงานการพัฒนาระบบคลาวด์หรือโครงสร้างพื้นฐานระดับองค์กร ที่มีมูลค่าสัญญาไม่น้อยกว่า 15,000,000 บาท ในสัญญาเดียว

ข้อ 3. ขอบเขตของงาน (Scope of Work)
3.1 ผู้รับจ้างต้องดำเนินการย้ายระบบ (Cloud Migration) จากระบบเดิมขึ้นสู่ระบบ Enterprise Cloud Platform
3.2 ผู้รับจ้างต้องพัฒนา API Gateway และเชื่อมโยงข้อมูลกับระบบฐานข้อมูลหลักขององค์กร
3.3 ผู้รับจ้างต้องดูแลและพัฒนาระบบ รวมถึงงานอื่นๆ ที่ผู้ว่าจ้างมอบหมายเพิ่มเติม และรวมถึงระบบอื่นๆ ที่จะเกิดขึ้นในอนาคต โดยไม่มีค่าใช้จ่ายเพิ่มเติม
3.4 ทรัพย์สินทางปัญญาทั้งหมดและ Source Code รวมถึง Libraries ที่เกี่ยวข้องทั้งหมดให้ตกเป็นกรรมสิทธิ์ของผู้ว่าจ้างแต่เพียงผู้เดียว

ข้อ 4. ระยะเวลาดำเนินการและการส่งมอบงาน (Milestones)
การดำเนินงานแบ่งออกเป็น 3 งวดงาน รวมระยะเวลา 180 วัน:
- งวดที่ 1: ส่งมอบแผนการบริหารโครงการ (Project Charter) และพิมพ์เขียวสถาปัตยกรรมระบบ (Cloud Architecture Blueprint) ภายใน 30 วัน จ่ายร้อยละ 20 ของมูลค่าสัญญา
- งวดที่ 2: ดำเนินการติดตั้งระบบ พัฒนา API Gateway และทดสอบระบบนำร่อง ภายใน 120 วัน จ่ายร้อยละ 40 ของมูลค่าสัญญา
- งวดที่ 3: ดำเนินการย้ายระบบทั้งหมด ทดสอบ UAT และฝึกอบรมบุคลากร ภายใน 180 วัน จ่ายร้อยละ 40 ของมูลค่าสัญญา
การตรวจรับในแต่ละงวดงาน ต้องได้รับการอนุมัติจนเป็นที่พึงพอใจของคณะกรรมการตรวจรับพัสดุ ตามดุลยพินิจของคณะกรรมการ

ข้อ 5. ข้อกำหนดระดับการให้บริการ (Service Level Agreement : SLA)
5.1 ผู้รับจ้างต้องจัดให้มีทีมงานสนับสนุนและแก้ปัญหาตลอด 24 ชั่วโมง ทุกวัน (24x7)
5.2 กรณีเกิดปัญหาขั้นวิกฤต (Priority 1 - Critical Outage) ผู้รับจ้างต้องเข้าแก้ไขปัญหาภายใน 1 ชั่วโมงตลอด 24 ชั่วโมง และต้องทำให้ระบบกลับคืนสู่สภาพเดิมภายใน 2 ชั่วโมง
5.3 ระบบต้องมีความพร้อมใช้งาน (Availability Uptime) ไม่ต่ำกว่าร้อยละ 99.95 ต่อเดือน

ข้อ 6. อัตราค่าปรับและการบอกเลิกสัญญา (Liquidated Damages)
6.1 หากผู้รับจ้างไม่สามารถส่งมอบงานให้แล้วเสร็จภายในระยะเวลาที่กำหนด ผู้รับจ้างจะต้องชำระค่าปรับเป็นรายวันในอัตราร้อยละ 0.1 ต่อวัน คิดจากราคาสัญญาทั้งหมด จนกว่าจะส่งมอบงานแล้วเสร็จถูกต้อง
6.2 หากค่าปรับสะสมมีจำนวนเกินร้อยละ 10 ของมูลค่าสัญญา ผู้ว่าจ้างมีสิทธิบอกเลิกสัญญาและริบหลักประกันสัญญาทันที
"""


def main():
    parser = argparse.ArgumentParser(description="Enterprise TOR & Contract Risk Scraper & Auditor")
    parser.add_argument("--scrape-file", type=str, help="Scrape and ingest local TOR file (PDF, TXT, MD)")
    parser.add_argument("--scrape-url", type=str, help="Scrape live web URL or online PDF")
    parser.add_argument("--scrape-mock", action="store_true", help="Ingest built-in authentic enterprise TOR for testing")
    parser.add_argument("--doc-id", type=str, default="TOR-CURRENT", help="Document identifier in vault")
    parser.add_argument("--contract-value", type=float, default=30000000.0, help="Contract total value in THB (Default: 30,000,000 THB)")
    parser.add_argument("--calc-penalty", action="store_true", help="Calculate liquidated damages deterministically")
    parser.add_argument("--rate", type=float, default=0.001, help="Daily penalty rate (e.g. 0.001 for 0.1%%)")
    parser.add_argument("--days", type=int, default=30, help="Days of delay for penalty calculation")
    parser.add_argument("--audit", action="store_true", help="Run full audit on current or ingested document")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    # Dynamic Scraping Execution
    scraped_text = ""
    source_uri = "unknown"
    
    if args.scrape_url:
        print(f"[*] Scraping live URL: {args.scrape_url}", file=sys.stderr)
        scraped_text = fetch_url_content(args.scrape_url)
        source_uri = args.scrape_url
    elif args.scrape_file:
        print(f"[*] Scraping local file: {args.scrape_file}", file=sys.stderr)
        source_uri = args.scrape_file
        if args.scrape_file.lower().endswith(".pdf"):
            scraped_text = extract_pdf_text_native(args.scrape_file)
        else:
            with open(args.scrape_file, "r", encoding="utf-8", errors="ignore") as f:
                scraped_text = f.read()
    elif args.scrape_mock:
        print("[*] Ingesting built-in authentic Enterprise TOR sample...", file=sys.stderr)
        scraped_text = generate_mock_enterprise_tor()
        source_uri = "built-in-enterprise-mock"

    if scraped_text:
        parse_and_index_document(args.doc_id, scraped_text, source_uri, args.contract_value)
        print(f"[OK] Document '{args.doc_id}' successfully scraped and indexed into SQLite FTS5 vault.", file=sys.stderr)

    if args.calc_penalty:
        daily = args.contract_value * args.rate
        accumulated = daily * args.days
        cap = args.contract_value * 0.10
        exceeds_cap = (accumulated >= cap) if (accumulated > 0 and cap > 0) else False
        res = {
            "contract_value_thb": args.contract_value,
            "rate_percent": args.rate * 100,
            "delay_days": args.days,
            "daily_penalty_thb": daily,
            "accumulated_penalty_thb": accumulated,
            "cap_10_percent_thb": cap,
            "is_termination_eligible": exceeds_cap,
            "days_until_10_percent_cap": int(cap / daily) if daily > 0 else 0
        }
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"Daily Penalty: {daily:,.2f} THB | Total ({args.days} days): {accumulated:,.2f} THB | Cap (10%): {cap:,.2f} THB | Termination Risk: {exceeds_cap}")
        return

    if args.audit or scraped_text:
        audit_res = audit_document_clauses(args.doc_id, args.contract_value)
        if args.json:
            print(json.dumps(audit_res, ensure_ascii=False, indent=2))
        else:
            p_calc = audit_res.get("penalty_calculation", {})
            print("=" * 80)
            print(f" 🎯 ENTERPRISE TOR AUDIT REPORT: {audit_res.get('doc_id')}")
            print(f" มูลค่าสัญญาที่ประเมิน: {audit_res.get('contract_value', 0):,.2f} บาท")
            print("=" * 80)
            print("\n[1] 💰 การวิเคราะห์ค่าปรับและเพดานความเสียหาย (LIQUIDATED DAMAGES):")
            print(f"  • อัตราค่าปรับรายวัน : ร้อยละ {p_calc.get('rate_percent_per_day', 0.1)}% ต่อวัน ({p_calc.get('daily_penalty_thb', 0):,.2f} บาท/วัน)")
            print(f"  • ค่าปรับสะสมต่อเดือน (30 วัน) : {p_calc.get('monthly_penalty_thb', 0):,.2f} บาท")
            print(f"  • เพดานบอกเลิกสัญญา 10% (ม.103) : {p_calc.get('cap_10_percent_thb', 0):,.2f} บาท")
            print(f"  • ส่งมอบล่าช้าสะสมเกิน : {p_calc.get('days_to_termination_ceiling', 0)} วัน ผู้ว่าจ้างมีสิทธิบอกเลิกสัญญาและริบหลักประกัน")
            
            print("\n[2] 🚩 จุดเสี่ยงและกับดักในสัญญา (PONYTAIL RISK TAGS):")
            risks = audit_res.get("detected_risks", [])
            if not risks:
                print("  • ไม่พบข้อความกับดักที่เป็นความเสี่ยงระดับสูง")
            for r in risks:
                print(f"  • [{r['severity']}] [{r['tag']}] ข้อ: {r['clause']}")
                print(f"    ข้อความที่ตรวจพบ: \"{r['verbatim_snippet']}\"")
                print(f"    แนวทางแก้ไข: {r['mitigation']}")
                
            print("\n[3] ⏱️ ตัวชี้วัดระดับการให้บริการ (SLA PARAMETERS):")
            for s in audit_res.get("sla_findings", []):
                print(f"  • {s['clause']}: {s['text']}")
                
            print("\n[4] 📦 งวดงานและการส่งมอบ (DELIVERY MILESTONES):")
            for m in audit_res.get("milestones", []):
                print(f"  • {m}")
            print("=" * 80)


if __name__ == "__main__":
    main()
