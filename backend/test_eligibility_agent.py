"""Tests for eligibility agent and cross-document validation."""

import json
import unittest
from pathlib import Path

from document_validator import analyze_cross_document, names_similar
from eligibility_agent import calculate_eligibility, ensure_model


class EligibilityAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_model()

    def test_names_similar(self):
        self.assertTrue(names_similar("Rahul Sharma", "Rahul Sharma"))
        self.assertTrue(names_similar("R. Sharma", "Rahul Sharma"))
        self.assertFalse(names_similar("Rahul Sharma", "Ramesh Verma"))

    def test_calculate_eligibility_returns_boolean(self):
        application = {
            "applicant_name": "Test User",
            "annual_income": 5000000,
            "loan_amount": 1000000,
            "loan_id": 1,
            "cibil_score": 750,
            "loan_term": 12,
            "education": "Graduate",
            "self_employed": "No",
            "no_of_dependents": 0,
            "residential_assets_value": 1000000,
            "commercial_assets_value": 0,
            "luxury_assets_value": 0,
            "bank_asset_value": 500000,
        }
        cross = {
            "discrepancies": [],
            "missing_documents": [],
            "verification_score": 95,
            "severity_counts": {"High": 0, "Medium": 0, "Low": 0},
            "present_documents": [
                "Payslip",
                "Bank Statement",
                "Tax Return",
                "KYC Document",
            ],
            "income_variance_pct": 5,
            "extracted_by_type": {},
        }
        result = calculate_eligibility(
            annual_income=application["annual_income"],
            loan_amount=application["loan_amount"],
            applicant_name=application["applicant_name"],
            loan_id=application["loan_id"],
            application=application,
            cross_validation=cross,
        )
        self.assertIn("eligible", result)
        self.assertIsInstance(result["eligible"], bool)
        self.assertIn("ai_summary", result)
        self.assertIn("confidence", result)

    def test_cross_document_detects_missing_and_name_mismatch(self):
        application = {
            "applicant_name": "Rahul Sharma",
            "annual_income": 720000,
        }
        documents = [
            {
                "document_type": "Payslip",
                "document_id": "1",
                "confidence_score": 90,
                "extracted_json": {
                    "fields": {
                        "employee_name": "Ramesh Verma",
                        "gross_salary": 30000,
                        "net_pay": 25000,
                        "annualized_salary": 360000,
                    }
                },
            },
            {
                "document_type": "KYC Document",
                "document_id": "2",
                "confidence_score": 85,
                "extracted_json": {
                    "fields": {
                        "holder_name": "Rahul Sharma",
                        "id_number": "XXXX-XXXX-4521",
                    }
                },
            },
        ]
        result = analyze_cross_document(application, documents)
        codes = {item["code"] for item in result["discrepancies"]}
        self.assertIn("MISSING_DOCUMENT", codes)
        self.assertIn("NAME_MISMATCH", codes)
        self.assertLess(result["verification_score"], 70)


if __name__ == "__main__":
    unittest.main()
