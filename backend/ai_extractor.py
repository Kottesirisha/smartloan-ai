"""Hybrid GenAI / regex structured extraction for loan documents."""

from __future__ import annotations

import json
import os
import re
from typing import Any


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").replace("₹", "").strip())
    except (TypeError, ValueError):
        return None


def _search(patterns: list[str], text: str, flags=re.IGNORECASE) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            value = match.group(1).strip()
            value = re.split(r"\s{2,}|\n", value)[0].strip(" :-")
            if value:
                return value
    return None


def _field_confidence(fields: dict[str, Any], required: list[str]) -> float:
    if not required:
        return 0.0
    present = sum(1 for key in required if fields.get(key) not in (None, "", []))
    return round((present / len(required)) * 100.0, 2)


def extract_payslip(text: str) -> dict[str, Any]:
    text = clean_text(text)
    employee_name = _search(
        [
            r"Employee\s*Name\s*:?\s*([A-Za-z][A-Za-z .'-]+)",
            r"Employee\s*:?\s*([A-Za-z][A-Za-z .'-]+)",
            r"Name\s*of\s*Employee\s*:?\s*([A-Za-z][A-Za-z .'-]+)",
        ],
        text,
    )
    employer = _search(
        [
            r"Employer\s*:?\s*([A-Za-z0-9][A-Za-z0-9 &.,'-]+)",
            r"Company\s*:?\s*([A-Za-z0-9][A-Za-z0-9 &.,'-]+)",
            r"Organisation\s*:?\s*([A-Za-z0-9][A-Za-z0-9 &.,'-]+)",
        ],
        text,
    )
    pay_period = _search(
        [
            r"Pay\s*Period\s*:?\s*([A-Za-z0-9 /\-]+)",
            r"Salary\s*Month\s*:?\s*([A-Za-z0-9 /\-]+)",
            r"For\s*the\s*month\s*of\s*:?\s*([A-Za-z0-9 /\-]+)",
        ],
        text,
    )

    basic_salary = _to_float(
        _search(
            [
                r"Basic\s*(?:Pay|Salary)\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
                r"Basic\s*[₹Rs.\s]*([\d,]+\.?\d*)",
            ],
            text,
        )
    )
    gross_salary = _to_float(
        _search(
            [
                r"(?:Gross\s*Salary|Total\s*Earnings|Gross\s*Pay)\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
            ],
            text,
        )
    )
    total_deductions = _to_float(
        _search(
            [
                r"Total\s*Deductions?\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
            ],
            text,
        )
    )
    net_pay = _to_float(
        _search(
            [
                r"(?:Net\s*Pay|Net\s*Salary|Take\s*Home)\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
            ],
            text,
        )
    )

    # Fallback: summary block after Total Earnings
    if gross_salary is None or total_deductions is None or net_pay is None:
        summary_match = re.search(r"Total\s+Earnings(.*)", text, re.IGNORECASE | re.DOTALL)
        if summary_match:
            numbers = re.findall(r"\b\d[\d,]*(?:\.\d+)?\b", summary_match.group(1))
            numbers = [n.replace(",", "") for n in numbers]
            if len(numbers) >= 3:
                gross_salary = gross_salary or float(numbers[0])
                total_deductions = total_deductions or float(numbers[1])
                net_pay = net_pay or float(numbers[2])

    fields = {
        "employee_name": employee_name,
        "employer": employer,
        "pay_period": pay_period,
        "basic_salary": basic_salary,
        "gross_salary": gross_salary,
        "total_deductions": total_deductions,
        "net_pay": net_pay,
        "annualized_salary": round(gross_salary * 12, 2) if gross_salary else None,
    }
    required = ["employee_name", "gross_salary", "net_pay"]
    return {
        "document_type": "Payslip",
        "fields": fields,
        "confidence": _field_confidence(fields, required),
        "extraction_method": "regex_fallback",
    }


def extract_bank_statement(text: str) -> dict[str, Any]:
    text = clean_text(text)
    account_holder = _search(
        [
            r"Account\s*Holder\s*:?\s*([A-Za-z][A-Za-z .'-]+)",
            r"Customer\s*Name\s*:?\s*([A-Za-z][A-Za-z .'-]+)",
            r"Name\s*:?\s*([A-Za-z][A-Za-z .'-]+)",
        ],
        text,
    )
    bank_name = _search(
        [
            r"Bank\s*Name\s*:?\s*([A-Za-z][A-Za-z0-9 &.,'-]+)",
            r"(HDFC|ICICI|SBI|Axis|Kotak|Yes Bank|Bank of Baroda)[^\n]*",
        ],
        text,
    )
    account_number = _search(
        [
            r"Account\s*(?:No|Number|#)\s*:?\s*([X*\d\- ]{6,})",
        ],
        text,
    )
    ifsc = _search([r"IFSC\s*(?:Code)?\s*:?\s*([A-Z0-9]{8,11})"], text)
    opening_balance = _to_float(
        _search([r"Opening\s*Balance\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)"], text)
    )
    closing_balance = _to_float(
        _search([r"Closing\s*Balance\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)"], text)
    )
    average_monthly_balance = _to_float(
        _search(
            [
                r"Average\s*(?:Monthly\s*)?Balance\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
                r"AMB\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
            ],
            text,
        )
    )
    salary_credits = _to_float(
        _search(
            [
                r"Salary\s*Credit[s]?\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
                r"Salary\s*(?:Cr|Credit)\s*[₹Rs.\s]*([\d,]+\.?\d*)",
            ],
            text,
        )
    )

    fields = {
        "account_holder": account_holder,
        "bank_name": bank_name,
        "account_number": account_number,
        "ifsc": ifsc,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "average_monthly_balance": average_monthly_balance,
        "salary_credits": salary_credits,
    }
    required = ["account_holder", "account_number", "closing_balance"]
    return {
        "document_type": "Bank Statement",
        "fields": fields,
        "confidence": _field_confidence(fields, required),
        "extraction_method": "regex_fallback",
    }


def extract_tax_return(text: str) -> dict[str, Any]:
    text = clean_text(text)
    assessee_name = _search(
        [
            r"Assessee\s*Name\s*:?\s*([A-Za-z][A-Za-z .'-]+)",
            r"Name\s*of\s*Assessee\s*:?\s*([A-Za-z][A-Za-z .'-]+)",
            r"Taxpayer\s*Name\s*:?\s*([A-Za-z][A-Za-z .'-]+)",
        ],
        text,
    )
    pan = _search([r"PAN\s*:?\s*([A-Z]{5}\d{4}[A-Z])"], text)
    assessment_year = _search(
        [
            r"Assessment\s*Year\s*:?\s*([\d]{4}\-?[\d]{2,4})",
            r"A\.?Y\.?\s*:?\s*([\d]{4}\-?[\d]{2,4})",
        ],
        text,
    )
    gross_total_income = _to_float(
        _search(
            [
                r"Gross\s*Total\s*Income\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
                r"Total\s*Income\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
            ],
            text,
        )
    )
    total_tax_deductions = _to_float(
        _search(
            [
                r"Total\s*(?:Tax\s*)?Deductions?\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
                r"Chapter\s*VIA\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
            ],
            text,
        )
    )
    net_taxable_income = _to_float(
        _search(
            [
                r"Net\s*Taxable\s*Income\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
                r"Taxable\s*Income\s*:?\s*[₹Rs.\s]*([\d,]+\.?\d*)",
            ],
            text,
        )
    )

    fields = {
        "assessee_name": assessee_name,
        "pan": pan,
        "assessment_year": assessment_year,
        "gross_total_income": gross_total_income,
        "total_tax_deductions": total_tax_deductions,
        "net_taxable_income": net_taxable_income,
    }
    required = ["assessee_name", "pan", "gross_total_income"]
    return {
        "document_type": "Tax Return",
        "fields": fields,
        "confidence": _field_confidence(fields, required),
        "extraction_method": "regex_fallback",
    }


def extract_kyc(text: str) -> dict[str, Any]:
    text = clean_text(text)
    text_lower = text.lower()

    if "aadhaar" in text_lower or "aadhar" in text_lower:
        doc_subtype = "Aadhaar"
    elif "passport" in text_lower:
        doc_subtype = "Passport"
    elif "pan" in text_lower:
        doc_subtype = "PAN Card"
    elif "voter" in text_lower:
        doc_subtype = "Voter ID"
    else:
        doc_subtype = "Identity Document"

    holder_name = _search(
        [
            r"(?:Name|Holder\s*Name)\s*:?\s*([A-Za-z][A-Za-z .'-]+)",
        ],
        text,
    )
    id_number = _search(
        [
            r"(?:Aadhaar|Aadhar)\s*(?:No|Number|#)?\s*:?\s*([\dX*]{4}[\s\-]?[\dX*]{4}[\s\-]?[\dX*]{4})",
            r"Passport\s*(?:No|Number|#)?\s*:?\s*([A-Z0-9]{6,12})",
            r"PAN\s*:?\s*([A-Z]{5}\d{4}[A-Z])",
            r"(?:ID|Identity)\s*(?:No|Number|#)\s*:?\s*([A-Z0-9\- ]{6,})",
        ],
        text,
    )
    if id_number and len(re.sub(r"\D", "", id_number)) >= 8:
        digits = re.sub(r"\D", "", id_number)
        id_number = f"XXXX-XXXX-{digits[-4:]}"

    dob = _search(
        [
            r"(?:DOB|Date\s*of\s*Birth)\s*:?\s*([\d]{1,2}[/\-][\d]{1,2}[/\-][\d]{2,4})",
        ],
        text,
    )
    address = _search(
        [
            r"Address\s*:?\s*([A-Za-z0-9 ,.\-/#]+)",
        ],
        text,
    )
    nationality = _search(
        [
            r"Nationality\s*:?\s*([A-Za-z ]+)",
        ],
        text,
    ) or ("Indian" if "government of india" in text_lower else None)

    fields = {
        "document_subtype": doc_subtype,
        "holder_name": holder_name,
        "id_number": id_number,
        "dob": dob,
        "address": address,
        "nationality": nationality,
    }
    required = ["holder_name", "id_number"]
    return {
        "document_type": "KYC Document",
        "fields": fields,
        "confidence": _field_confidence(fields, required),
        "extraction_method": "regex_fallback",
    }


def _extract_with_regex(text: str, document_type: str) -> dict[str, Any]:
    normalized = (document_type or "").lower()
    if "payslip" in normalized or "pay slip" in normalized:
        return extract_payslip(text)
    if "bank" in normalized:
        return extract_bank_statement(text)
    if "tax" in normalized or "itr" in normalized:
        return extract_tax_return(text)
    if "kyc" in normalized or "aadhaar" in normalized or "passport" in normalized:
        return extract_kyc(text)

    # Auto-detect best effort
    candidates = [
        extract_payslip(text),
        extract_bank_statement(text),
        extract_tax_return(text),
        extract_kyc(text),
    ]
    return max(candidates, key=lambda item: item.get("confidence", 0))


def _try_llm_extraction(text: str, document_type: str) -> dict[str, Any] | None:
    """Optional Gemini / OpenAI structured extraction when API keys exist."""
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    schema_hint = {
        "Payslip": [
            "employee_name", "employer", "pay_period", "basic_salary",
            "gross_salary", "total_deductions", "net_pay",
        ],
        "Bank Statement": [
            "account_holder", "bank_name", "account_number", "ifsc",
            "opening_balance", "closing_balance", "average_monthly_balance",
            "salary_credits",
        ],
        "Tax Return": [
            "assessee_name", "pan", "assessment_year", "gross_total_income",
            "total_tax_deductions", "net_taxable_income",
        ],
        "KYC Document": [
            "document_subtype", "holder_name", "id_number", "dob",
            "address", "nationality",
        ],
    }.get(document_type, ["name"])

    prompt = (
        f"Extract structured fields for a {document_type} loan document. "
        f"Return ONLY valid JSON with keys: {schema_hint}. "
        f"Document text:\n{text[:6000]}"
    )

    if gemini_key:
        try:
            import urllib.request

            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-1.5-flash:generateContent?key={gemini_key}"
            )
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            }).encode("utf-8")
            request = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
            raw = body["candidates"][0]["content"]["parts"][0]["text"]
            fields = json.loads(raw)
            confidence = _field_confidence(fields, schema_hint)
            return {
                "document_type": document_type,
                "fields": fields,
                "confidence": confidence,
                "extraction_method": "gemini",
            }
        except Exception:
            pass

    if openai_key:
        try:
            import urllib.request

            payload = json.dumps({
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Return only JSON."},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
            }).encode("utf-8")
            request = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
            fields = json.loads(body["choices"][0]["message"]["content"])
            confidence = _field_confidence(fields, schema_hint)
            return {
                "document_type": document_type,
                "fields": fields,
                "confidence": confidence,
                "extraction_method": "openai",
            }
        except Exception:
            pass

    return None


def extract_document_fields(text: str, document_type: str = "Unknown") -> dict[str, Any]:
    """Hybrid extraction: try LLM when keyed, always fall back to regex engine."""
    llm_result = _try_llm_extraction(text, document_type)
    if llm_result and llm_result.get("confidence", 0) >= 40:
        return llm_result
    return _extract_with_regex(text, document_type)
