"""Generate realistic dummy PDFs for Payslip, Bank Statement, Tax Return, KYC."""

from __future__ import annotations

import random
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


BASE_DIR = Path(__file__).parent
DEFAULT_OUTPUT = BASE_DIR / "uploads" / "dummy"


def _money(value: float) -> str:
    return f"₹{value:,.2f}"


def _draw_header(c: canvas.Canvas, title: str, subtitle: str = ""):
    width, height = A4
    c.setFillColorRGB(0.08, 0.18, 0.35)
    c.rect(0, height - 28 * mm, width, 28 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, height - 14 * mm, title)
    if subtitle:
        c.setFont("Helvetica", 10)
        c.drawString(20 * mm, height - 21 * mm, subtitle)
    c.setFillColorRGB(0, 0, 0)


def _footer(c: canvas.Canvas, label: str):
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(20 * mm, 12 * mm, f"SmartLoan AI Demo Document · {label}")
    c.drawRightString(A4[0] - 20 * mm, 12 * mm, datetime.now().strftime("%d %b %Y"))


def generate_payslip(path: Path, profile: dict[str, Any], anomaly: bool = False) -> Path:
    name = profile.get("applicant_name", "Rahul Sharma")
    if anomaly:
        name = profile.get("anomaly_name", "Ramesh Verma")

    annual = float(profile.get("annual_income", 600000))
    if anomaly:
        annual = annual * float(profile.get("income_factor", 0.55))

    monthly_gross = round(annual / 12, 2)
    basic = round(monthly_gross * 0.5, 2)
    hra = round(monthly_gross * 0.2, 2)
    allowances = round(monthly_gross - basic - hra, 2)
    deductions = round(monthly_gross * 0.12, 2)
    net = round(monthly_gross - deductions, 2)
    employer = profile.get("employer", "NovaTech Solutions Pvt Ltd")
    period = profile.get("pay_period", "August 2025")

    c = canvas.Canvas(str(path), pagesize=A4)
    _draw_header(c, "SALARY PAYSLIP", employer)
    y = A4[1] - 40 * mm
    lines = [
        f"Employee Name: {name}",
        f"Employee ID: EMP-{profile.get('loan_id', 1001)}",
        f"Designation: Software Engineer",
        f"Pay Period: {period}",
        f"Basic Salary: {_money(basic)}",
        f"HRA: {_money(hra)}",
        f"Other Allowances: {_money(allowances)}",
        f"Gross Salary / Total Earnings: {_money(monthly_gross)}",
        f"Total Deductions: {_money(deductions)}",
        f"Net Pay: {_money(net)}",
        f"Net Salary: {_money(net)}",
    ]
    c.setFont("Helvetica", 11)
    for line in lines:
        c.drawString(25 * mm, y, line)
        y -= 8 * mm
    _footer(c, "Payslip")
    c.save()
    return path


def generate_bank_statement(path: Path, profile: dict[str, Any], anomaly: bool = False) -> Path:
    name = profile.get("applicant_name", "Rahul Sharma")
    if anomaly and profile.get("bank_name_mismatch"):
        name = profile.get("anomaly_name", "Ramesh Verma")

    annual = float(profile.get("annual_income", 600000))
    monthly = round(annual / 12, 2)
    if anomaly and profile.get("bank_salary_mismatch"):
        monthly = round(monthly * 0.4, 2)

    opening = round(monthly * 2.1, 2)
    closing = round(opening + monthly * 0.3, 2)
    bank = profile.get("bank_name", "HDFC Bank")
    account = profile.get("account_number", f"XXXXXX{1000 + int(profile.get('loan_id', 1))}")
    ifsc = profile.get("ifsc", "HDFC0001234")

    c = canvas.Canvas(str(path), pagesize=A4)
    _draw_header(c, "BANK STATEMENT", bank)
    y = A4[1] - 40 * mm
    lines = [
        f"Account Holder: {name}",
        f"Bank Name: {bank}",
        f"Account Number: {account}",
        f"IFSC Code: {ifsc}",
        f"Statement Period: 01 Aug 2025 - 31 Aug 2025",
        f"Opening Balance: {_money(opening)}",
        f"Salary Credit: {_money(monthly)}",
        f"Closing Balance: {_money(closing)}",
        f"Average Monthly Balance: {_money((opening + closing) / 2)}",
        "",
        "Transactions:",
        f"05 Aug 2025  CREDIT  Salary Cr  {_money(monthly)}",
        f"12 Aug 2025  DEBIT   UPI Rent   {_money(round(monthly * 0.25, 2))}",
        f"20 Aug 2025  DEBIT   Card Spend {_money(round(monthly * 0.1, 2))}",
    ]
    c.setFont("Helvetica", 11)
    for line in lines:
        c.drawString(25 * mm, y, line)
        y -= 7 * mm
    _footer(c, "Bank Statement")
    c.save()
    return path


def generate_tax_return(path: Path, profile: dict[str, Any], anomaly: bool = False) -> Path:
    name = profile.get("applicant_name", "Rahul Sharma")
    annual = float(profile.get("annual_income", 600000))
    if anomaly:
        annual = round(annual * float(profile.get("tax_income_factor", 1.45)), 2)

    deductions = round(min(150000, annual * 0.1), 2)
    taxable = round(annual - deductions, 2)
    pan = profile.get("pan", "ABCDE1234F")
    ay = profile.get("assessment_year", "2024-25")

    c = canvas.Canvas(str(path), pagesize=A4)
    _draw_header(c, "INCOME TAX RETURN (ITR-V)", "Indian Income Tax Department")
    y = A4[1] - 40 * mm
    lines = [
        f"Assessee Name: {name}",
        f"PAN: {pan}",
        f"Assessment Year: {ay}",
        f"Form: ITR-V Acknowledgement",
        f"Gross Total Income: {_money(annual)}",
        f"Total Income: {_money(annual)}",
        f"Total Tax Deductions: {_money(deductions)}",
        f"Net Taxable Income: {_money(taxable)}",
        f"Tax Payable: {_money(round(max(0, taxable - 250000) * 0.05, 2))}",
        "Status: Verified e-Filing acknowledgement",
    ]
    c.setFont("Helvetica", 11)
    for line in lines:
        c.drawString(25 * mm, y, line)
        y -= 8 * mm
    _footer(c, "Tax Return")
    c.save()
    return path


def generate_kyc(path: Path, profile: dict[str, Any], anomaly: bool = False) -> Path:
    name = profile.get("applicant_name", "Rahul Sharma")
    if anomaly and profile.get("kyc_name_mismatch"):
        name = profile.get("anomaly_name", "Ramesh Verma")

    subtype = profile.get("kyc_type", "Aadhaar")
    dob = profile.get("dob", "15/08/1994")
    address = profile.get("address", "12 MG Road, Bengaluru, Karnataka 560001")
    aadhaar = profile.get("aadhaar", "XXXX XXXX 4521")

    c = canvas.Canvas(str(path), pagesize=A4)
    _draw_header(c, "KYC DOCUMENT", "Government of India")
    y = A4[1] - 40 * mm
    lines = [
        f"Document Type: {subtype}",
        "Unique Identification Authority of India" if subtype == "Aadhaar" else "Identity Document",
        f"Name: {name}",
        f"Holder Name: {name}",
        f"Aadhaar Number: {aadhaar}",
        f"Date of Birth / DOB: {dob}",
        f"Address: {address}",
        "Nationality: Indian",
        "This KYC document is issued for identity verification.",
    ]
    c.setFont("Helvetica", 11)
    for line in lines:
        c.drawString(25 * mm, y, line)
        y -= 8 * mm
    _footer(c, "KYC Document")
    c.save()
    return path


def build_profile_from_application(application: dict, mode: str = "clean") -> dict[str, Any]:
    anomaly = mode == "anomaly"
    return {
        "applicant_name": application.get("applicant_name", "Applicant"),
        "annual_income": application.get("annual_income", 600000),
        "loan_id": application.get("loan_id") or random.randint(1, 9999),
        "employer": "NovaTech Solutions Pvt Ltd",
        "pay_period": "August 2025",
        "bank_name": "HDFC Bank",
        "pan": "ABCDE1234F",
        "assessment_year": "2024-25",
        "kyc_type": "Aadhaar",
        "dob": "15/08/1994",
        "address": "12 MG Road, Bengaluru, Karnataka 560001",
        "anomaly_name": "Ramesh Verma",
        "income_factor": 0.55,
        "tax_income_factor": 1.5,
        "bank_salary_mismatch": anomaly,
        "bank_name_mismatch": anomaly,
        "kyc_name_mismatch": anomaly,
    }


def generate_document_suite(
    application: dict,
    output_dir: Path | None = None,
    mode: str = "clean",
    skip_tax: bool = False,
) -> list[dict[str, Any]]:
    """
    Generate a suite of PDFs.

    mode:
      - clean: consistent documents
      - anomaly: name/income mismatches; optionally skip tax
    """
    output_dir = Path(output_dir or DEFAULT_OUTPUT)
    output_dir.mkdir(parents=True, exist_ok=True)

    profile = build_profile_from_application(application, mode=mode)
    anomaly = mode == "anomaly"
    app_id = application.get("application_id", "demo")
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")

    generators = [
        ("Payslip", f"{app_id}_{stamp}_payslip.pdf", generate_payslip),
        ("Bank Statement", f"{app_id}_{stamp}_bank.pdf", generate_bank_statement),
        ("Tax Return", f"{app_id}_{stamp}_tax.pdf", generate_tax_return),
        ("KYC Document", f"{app_id}_{stamp}_kyc.pdf", generate_kyc),
    ]

    created = []
    for doc_type, filename, generator in generators:
        if anomaly and skip_tax and doc_type == "Tax Return":
            continue
        path = output_dir / filename
        generator(path, profile, anomaly=anomaly)
        created.append({
            "document_type": doc_type,
            "path": path,
            "filename": filename,
            "mode": mode,
        })

    return created


if __name__ == "__main__":
    demo_app = {
        "application_id": "demo",
        "applicant_name": "Rahul Sharma",
        "annual_income": 720000,
        "loan_id": 1,
    }
    clean = generate_document_suite(demo_app, mode="clean")
    anomaly = generate_document_suite(demo_app, mode="anomaly", skip_tax=True)
    print("Generated clean docs:", [item["filename"] for item in clean])
    print("Generated anomaly docs:", [item["filename"] for item in anomaly])
