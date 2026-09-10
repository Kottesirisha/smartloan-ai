"""Keyword-weighted document classifier for loan document types."""

from typing import Any


KEYWORD_WEIGHTS: dict[str, list[tuple[str, int]]] = {
    "Payslip": [
        ("payslip", 4),
        ("pay slip", 4),
        ("salary slip", 4),
        ("earnings", 3),
        ("deductions", 3),
        ("net salary", 3),
        ("net pay", 3),
        ("basic pay", 3),
        ("basic salary", 3),
        ("gross salary", 3),
        ("pay period", 3),
        ("employee name", 2),
        ("employee id", 2),
        ("take home", 2),
        ("hra", 1),
        ("pf contribution", 2),
    ],
    "Bank Statement": [
        ("bank statement", 4),
        ("account statement", 3),
        ("account number", 3),
        ("ifsc", 3),
        ("swift", 2),
        ("opening balance", 3),
        ("closing balance", 3),
        ("transactions", 2),
        ("debit", 2),
        ("credit", 2),
        ("withdrawal", 2),
        ("deposit", 2),
        ("available balance", 2),
        ("transaction date", 2),
        ("branch", 1),
    ],
    "Tax Return": [
        ("itr", 4),
        ("itr-v", 4),
        ("form 16", 4),
        ("income tax return", 4),
        ("tax return", 3),
        ("assessment year", 3),
        ("pan", 2),
        ("total income", 3),
        ("tax payable", 3),
        ("taxable income", 3),
        ("gross total income", 3),
        ("taxpayer", 2),
        ("income tax", 2),
        ("tax deduction", 2),
        ("assessee", 2),
    ],
    "KYC Document": [
        ("aadhaar", 4),
        ("aadhar", 4),
        ("passport", 4),
        ("pan card", 4),
        ("voter id", 3),
        ("government of india", 3),
        ("date of birth", 2),
        ("dob", 2),
        ("identity document", 2),
        ("nationality", 2),
        ("address proof", 2),
        ("unique identification", 3),
        ("driving licence", 2),
        ("driving license", 2),
        ("permanent account number", 3),
    ],
}


def classify_document(text: str) -> str:
    """Return the best-matching document type label."""
    result = classify_document_with_confidence(text)
    return result["document_type"]


def classify_document_with_confidence(text: str) -> dict[str, Any]:
    """Classify document type and return a confidence score (0-100)."""
    if not text or not text.strip():
        return {
            "document_type": "Unknown",
            "confidence": 0.0,
            "scores": {},
        }

    text_lower = text.lower()
    scores: dict[str, float] = {}

    for document_type, keywords in KEYWORD_WEIGHTS.items():
        score = 0.0
        for keyword, weight in keywords:
            if keyword in text_lower:
                score += weight
        scores[document_type] = score

    highest_score = max(scores.values()) if scores else 0.0
    if highest_score <= 0:
        return {
            "document_type": "Unknown",
            "confidence": 0.0,
            "scores": scores,
        }

    detected_type = max(scores, key=scores.get)
    max_possible = sum(weight for _, weight in KEYWORD_WEIGHTS[detected_type])
    confidence = round(min(100.0, (highest_score / max_possible) * 100.0), 2)

    # Soften confidence when runners-up are close
    ranked = sorted(scores.values(), reverse=True)
    if len(ranked) > 1 and ranked[0] > 0:
        margin = (ranked[0] - ranked[1]) / ranked[0]
        confidence = round(confidence * (0.7 + 0.3 * margin), 2)

    return {
        "document_type": detected_type,
        "confidence": confidence,
        "scores": scores,
    }
