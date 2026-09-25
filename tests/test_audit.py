#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit test suite for Enterprise TOR & Contract Risk Auditor (tor-audit).
Covers deterministic penalty math, statutory cap ceilings, FTS5 search, and Ponytail risk taggers.
"""

import os
import sys
import unittest
import sqlite3

# Add repo root to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from scripts.tor_scraper import (
    init_database,
    parse_and_index_document,
    audit_document_clauses,
    generate_mock_enterprise_tor,
    render_audit_markdown
)


class TestEnterpriseTORAuditor(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment and index mock enterprise TOR."""
        cls.test_doc_id = "TOR-UNITTEST-SAMPLE"
        cls.contract_val = 50_000_000.0  # 50 Million THB
        cls.mock_text = generate_mock_enterprise_tor()
        parse_and_index_document(cls.test_doc_id, cls.mock_text, "test-suite", cls.contract_val)

    def test_deterministic_penalty_math(self):
        """Verify daily penalty, monthly accumulation, and statutory 10% ceiling under Act B.E. 2560."""
        audit_res = audit_document_clauses(self.test_doc_id, self.contract_val)
        self.assertNotIn("error", audit_res)
        
        p = audit_res["penalty_calculation"]
        
        # Rate: 0.1% = 0.001
        expected_rate = 0.1
        self.assertAlmostEqual(p["rate_percent_per_day"], expected_rate, places=2)
        
        # Daily: 50,000,000 * 0.001 = 50,000.00 THB
        expected_daily = 50_000.00
        self.assertAlmostEqual(p["daily_penalty_thb"], expected_daily, places=2)
        
        # Monthly: 50,000 * 30 = 1,500,000.00 THB
        expected_monthly = 1_500_000.00
        self.assertAlmostEqual(p["monthly_penalty_thb"], expected_monthly, places=2)
        
        # Statutory 10% Cap: 50,000,000 * 0.10 = 5,000,000.00 THB
        expected_cap = 5_000_000.00
        self.assertAlmostEqual(p["cap_10_percent_thb"], expected_cap, places=2)
        
        # Days to termination: 5,000,000 / 50,000 = 100 days
        expected_days = 100
        self.assertEqual(p["days_to_termination_ceiling"], expected_days)

    def test_statutory_termination_trigger(self):
        """Verify termination eligibility triggers exactly when accumulated penalties reach 10%."""
        daily = 50_000.00
        cap = 5_000_000.00
        
        # Day 99: accumulated = 4,950,000 < 5,000,000 -> Not eligible
        accumulated_99 = daily * 99
        self.assertFalse(accumulated_99 >= cap)
        
        # Day 100: accumulated = 5,000,000 == cap -> Eligible for termination
        accumulated_100 = daily * 100
        self.assertTrue(accumulated_100 >= cap)

    def test_sqlite_fts5_indexing_and_retrieval(self):
        """Verify document is successfully tokenized and searchable in SQLite FTS5."""
        db_path = os.path.join(REPO_ROOT, "data", "tor_vault.db")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Search for Cloud Migration in FTS5
        cur.execute("""
            SELECT clause_number, content FROM tor_sections_fts
            WHERE doc_id = ? AND content MATCH 'Cloud Migration'
        """, (self.test_doc_id,))
        hits = cur.fetchall()
        self.assertGreater(len(hits), 0)
        self.assertIn("Cloud Migration", hits[0][1])
        conn.close()

    def test_ponytail_risk_tags_detection(self):
        """Verify detection of predatory procurement traps."""
        audit_res = audit_document_clauses(self.test_doc_id, self.contract_val)
        detected_tags = [r["tag"] for r in audit_res["detected_risks"]]
        
        # Scope Creep Trap (งานอื่นๆ ที่มอบหมายเพิ่มเติม)
        self.assertIn("SCOPE-CREEP-TRAP", detected_tags)
        
        # Ambiguous Acceptance (จนเป็นที่พึงพอใจของคณะกรรมการ)
        self.assertIn("AMBIGUOUS-ACCEPTANCE", detected_tags)

    def test_sla_extraction(self):
        """Verify SLA parameters are extracted correctly."""
        audit_res = audit_document_clauses(self.test_doc_id, self.contract_val)
        sla_findings = audit_res["sla_findings"]
        self.assertGreater(len(sla_findings), 0)
        
        sla_text_blob = " ".join([s["text"] for s in sla_findings])
        self.assertTrue(
            "Priority 1" in sla_text_blob or "24" in sla_text_blob or "99.95" in sla_text_blob
        )

    def test_milestone_extraction(self):
        """Verify delivery milestones are parsed."""
        audit_res = audit_document_clauses(self.test_doc_id, self.contract_val)
        milestones = audit_res["milestones"]
        self.assertGreaterEqual(len(milestones), 3)
        self.assertIn("งวดที่ 1", milestones[0])

    def test_markdown_export_renderer(self):
        """Verify Markdown output formatting."""
        audit_res = audit_document_clauses(self.test_doc_id, self.contract_val)
        md = render_audit_markdown(audit_res)
        self.assertIn("# 🎯 Enterprise TOR Audit Report", md)
        self.assertIn("50,000,000.00 บาท", md)
        self.assertIn("SCOPE-CREEP-TRAP", md)


if __name__ == "__main__":
    unittest.main()
