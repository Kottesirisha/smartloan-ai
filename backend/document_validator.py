"""Universal document validation and cross-document inconsistency analysis."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from ai_extractor import extract_document_fields


REQUIRED_DOCUMENT_TYPES = [
    "Payslip",
    "Bank Statement",
    "Tax Return",
    "KYC Document",
]

MANDATORY_FIELDS = {
    "Payslip": ["employee_name", "gross_salary", "net_pay"],
    "Bank Statement": ["account_holder", "account_number", "closing_balance"],
    "Tax Return": ["assessee_name", "pan", "gross_total_income"],
    "KYC Document": ["holder_name", "id_number"],
}


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    tokens = [t for t in name.split() if t not in {"mr", "mrs", "ms", "dr"}]
    return " ".join(tokens)


def names_similar(a: str | None, b: str | None, threshold: float = 0.72) -> bool:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # Initials / partial match: first token match + last token similarity
    a_tokens, b_tokens = na.split(), nb.split()
    if a_tokens and b_tokens:
        if a_tokens[0][0] == b_tokens[0][0] and a_tokens[-1] == b_tokens[-1]:
            return True
    return SequenceMatcher(None, na, nb).ratio() >= threshold


def validate_document(
    extracted_text: str,
    document_type: str = "Payslip",
    extracted_fields: dict | None = None,
) -> dict[str, Any]:
    if not extracted_text or not extracted_text.strip():
        return {
            "document_type": document_type or "Unknown",
            "is_valid": False,
            "missing_fields": ["extracted_text"],
            "extracted_details": {},
            "confidence": 0.0,
            "validation_message": "No text could be extracted from the document.",
        }

    extraction = extracted_fields or extract_document_fields(extracted_text, document_type)
    fields = extraction.get("fields", {})
    resolved_type = extraction.get("document_type") or document_type
    mandatory = MANDATORY_FIELDS.get(resolved_type, [])

    missing = [field for field in mandatory if fields.get(field) in (None, "", [])]
    is_valid = len(missing) == 0
    confidence = extraction.get("confidence", 0.0)

    if is_valid:
        message = f"{resolved_type} validated successfully."
    else:
        message = (
            f"{resolved_type} validation incomplete. Missing fields: "
            + ", ".join(missing)
        )

    return {
        "document_type": resolved_type,
        "is_valid": is_valid,
        "missing_fields": missing,
        "extracted_details": fields,
        "confidence": confidence,
        "extraction_method": extraction.get("extraction_method"),
        "validation_message": message,
    }


def _get_name_from_doc(doc_type: str, fields: dict) -> str | None:
    mapping = {
        "Payslip": "employee_name",
        "Bank Statement": "account_holder",
        "Tax Return": "assessee_name",
        "KYC Document": "holder_name",
    }
    return fields.get(mapping.get(doc_type, ""))


def analyze_cross_document(
    application: dict,
    documents: list[dict],
) -> dict[str, Any]:
    """Cross-document inconsistency analyzer for the full document suite."""
    discrepancies: list[dict[str, Any]] = []
    present_types = set()
    extracted_by_type: dict[str, dict] = {}

    for document in documents:
        doc_type = document.get("document_type") or "Unknown"
        present_types.add(doc_type)
        fields = document.get("extracted_json") or {}
        if isinstance(fields, dict) and "fields" in fields:
            fields = fields["fields"]
        if not fields and document.get("extracted_text"):
            result = extract_document_fields(document["extracted_text"], doc_type)
            fields = result.get("fields", {})
            confidence = result.get("confidence", 0)
        else:
            confidence = document.get("confidence_score") or 0

        extracted_by_type[doc_type] = {
            "fields": fields or {},
            "confidence": confidence,
            "document_id": document.get("document_id"),
        }

        if confidence and confidence < 55:
            discrepancies.append({
                "code": "LOW_CONFIDENCE",
                "severity": "Medium",
                "document_type": doc_type,
                "message": (
                    f"{doc_type} extraction confidence is low "
                    f"({confidence}%). Manual review recommended."
                ),
            })

    missing_docs = [dtype for dtype in REQUIRED_DOCUMENT_TYPES if dtype not in present_types]
    for dtype in missing_docs:
        discrepancies.append({
            "code": "MISSING_DOCUMENT",
            "severity": "High",
            "document_type": dtype,
            "message": f"Required document missing: {dtype}.",
        })

    # Name consistency
    applicant_name = application.get("applicant_name")
    names = []
    for dtype, payload in extracted_by_type.items():
        name = _get_name_from_doc(dtype, payload["fields"])
        if name:
            names.append((dtype, name))
            if applicant_name and not names_similar(applicant_name, name):
                discrepancies.append({
                    "code": "NAME_MISMATCH",
                    "severity": "High",
                    "document_type": dtype,
                    "message": (
                        f"Name on {dtype} ('{name}') does not match "
                        f"applicant name ('{applicant_name}')."
                    ),
                    "declared": applicant_name,
                    "extracted": name,
                })

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            type_a, name_a = names[i]
            type_b, name_b = names[j]
            if not names_similar(name_a, name_b):
                discrepancies.append({
                    "code": "CROSS_NAME_MISMATCH",
                    "severity": "High",
                    "document_type": f"{type_a} vs {type_b}",
                    "message": (
                        f"Name mismatch between {type_a} ('{name_a}') "
                        f"and {type_b} ('{name_b}')."
                    ),
                })

    # Income consistency
    declared_income = application.get("annual_income")
    payslip = extracted_by_type.get("Payslip", {}).get("fields", {})
    tax = extracted_by_type.get("Tax Return", {}).get("fields", {})
    bank = extracted_by_type.get("Bank Statement", {}).get("fields", {})

    annualized_payslip = payslip.get("annualized_salary")
    if annualized_payslip is None and payslip.get("gross_salary"):
        annualized_payslip = float(payslip["gross_salary"]) * 12

    tax_income = tax.get("gross_total_income")
    bank_salary = bank.get("salary_credits")
    bank_annual = float(bank_salary) * 12 if bank_salary else None

    income_points = []
    if declared_income:
        income_points.append(("Declared", float(declared_income)))
    if annualized_payslip:
        income_points.append(("Payslip (annualized)", float(annualized_payslip)))
    if tax_income:
        income_points.append(("Tax Return", float(tax_income)))
    if bank_annual:
        income_points.append(("Bank salary credits (annualized)", float(bank_annual)))

    income_variance_pct = None
    if len(income_points) >= 2:
        values = [v for _, v in income_points]
        base = max(values) or 1
        income_variance_pct = round(((max(values) - min(values)) / base) * 100, 2)
        if income_variance_pct > 20:
            discrepancies.append({
                "code": "INCOME_MISMATCH",
                "severity": "High" if income_variance_pct > 35 else "Medium",
                "document_type": "Income Consistency",
                "message": (
                    f"Income variance of {income_variance_pct}% detected across sources."
                ),
                "comparison": [
                    {"source": label, "value": value} for label, value in income_points
                ],
                "variance_pct": income_variance_pct,
            })

    # KYC / account light checks
    kyc_fields = extracted_by_type.get("KYC Document", {}).get("fields", {})
    if kyc_fields and not kyc_fields.get("id_number"):
        discrepancies.append({
            "code": "KYC_INCOMPLETE",
            "severity": "Medium",
            "document_type": "KYC Document",
            "message": "KYC ID number could not be extracted.",
        })

    high = sum(1 for d in discrepancies if d["severity"] == "High")
    medium = sum(1 for d in discrepancies if d["severity"] == "Medium")
    low = sum(1 for d in discrepancies if d["severity"] == "Low")

    verification_score = max(0, 100 - high * 25 - medium * 12 - low * 5)
    if missing_docs:
        verification_score = min(verification_score, 55)

    return {
        "required_documents": REQUIRED_DOCUMENT_TYPES,
        "present_documents": sorted(present_types),
        "missing_documents": missing_docs,
        "discrepancies": discrepancies,
        "income_comparison": [
            {"source": label, "value": value} for label, value in income_points
        ],
        "income_variance_pct": income_variance_pct,
        "verification_score": verification_score,
        "severity_counts": {"High": high, "Medium": medium, "Low": low},
        "extracted_by_type": {
            dtype: payload["fields"] for dtype, payload in extracted_by_type.items()
        },
    }
