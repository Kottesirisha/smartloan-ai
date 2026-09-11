"""SmartLoan AI — GenAI loan document processing & verification API."""

from __future__ import annotations

import io
import json
import re
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field

from ai_extractor import extract_document_fields
from database import (
    create_tables,
    get_all_applications,
    get_application_by_id,
    get_application_summary,
    get_document_by_id,
    get_documents_by_application,
    insert_application,
    insert_document,
    update_application_fields,
    update_application_status,
    update_document,
)
from document_classifier import classify_document_with_confidence
from document_validator import analyze_cross_document, validate_document
from dummy_generator import generate_document_suite
from eligibility_agent import calculate_eligibility, ensure_model, load_dataset
from pdf_reader import extract_text_from_pdf


app = FastAPI(
    title="SmartLoan AI API",
    description="GenAI-powered multi-document loan verification & ML eligibility",
    version="2.0.0",
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Local frontend
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",

        # Deployed Vercel frontend
        "https://smartloan-937bnmhfb-sirisha-kotte-projects1.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PATH CONFIGURATION
# ============================================================

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

DATASET_PATH = Path(__file__).parent / "loan_approval_dataset.csv"


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():
    create_tables()

    try:
        ensure_model()
    except Exception as error:
        print(f"Warning: model bootstrap deferred — {error}")


# ============================================================
# PYDANTIC MODELS
# ============================================================

class ApplicationCreate(BaseModel):
    applicant_name: str = Field(..., min_length=2)
    email: EmailStr
    phone: str = Field(..., min_length=10)

    annual_income: float = Field(..., gt=0)
    loan_amount: float = Field(..., gt=0)

    loan_id: int | None = None
    cibil_score: float | None = None
    loan_term: int | None = None
    education: str | None = None
    self_employed: str | None = None
    no_of_dependents: int | None = None

    residential_assets_value: float | None = None
    commercial_assets_value: float | None = None
    luxury_assets_value: float | None = None
    bank_asset_value: float | None = None


class OfficerReviewRequest(BaseModel):
    decision: str = Field(
        ...,
        description="approve | reject | request_reupload"
    )
    notes: str = ""
    reviewed_by: str = "Loan Officer"


class DummyDocsRequest(BaseModel):
    mode: str = Field(
        "clean",
        description="clean | anomaly"
    )
    skip_tax: bool = False


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def find_application(application_id: str):
    return get_application_by_id(application_id)


def find_document(document_id: str):
    return get_document_by_id(document_id)


def get_document_file_path(document):
    return UPLOAD_DIR / document["saved_filename"]


def _process_single_document(document: dict) -> dict:
    file_path = get_document_file_path(document)

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Uploaded file does not exist"
        )

    extracted_text = extract_text_from_pdf(str(file_path))

    classification = classify_document_with_confidence(
        extracted_text
    )

    document_type = classification["document_type"]

    extraction = extract_document_fields(
        extracted_text,
        document_type
    )

    validation = validate_document(
        extracted_text,
        document_type=document_type,
        extracted_fields=extraction,
    )

    update_document(
        document["document_id"],
        {
            "document_type": document_type,
            "extracted_text": extracted_text,
            "extracted_json": extraction,
            "confidence_score": extraction.get("confidence"),
            "classification_confidence": classification.get(
                "confidence"
            ),
        },
    )

    return {
        "document_id": document["document_id"],
        "document_type": document_type,
        "classification_confidence": classification.get(
            "confidence"
        ),
        "extraction": extraction,
        "validation_result": validation,
        "extracted_text": extracted_text,
    }


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "SmartLoan AI backend is running",
        "version": "2.0.0",
        "docs": "http://127.0.0.1:8001/docs",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    model_ready = (
        Path(__file__).parent / "loan_model.pkl"
    ).exists()

    return {
        "status": "healthy",
        "service": "SmartLoan AI",
        "model_ready": model_ready,
    }


# ============================================================
# DATASET
# ============================================================

@app.get("/dataset/samples")
def get_dataset_samples(
    q: str | None = None,
    status: str | None = None,
    limit: int = 25,
    offset: int = 0,
):
    if not DATASET_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Dataset not found"
        )

    df = load_dataset()

    if status:
        df = df[
            df["loan_status"].str.lower()
            == status.lower()
        ]

    if q:
        query = q.strip().lower()

        mask = (
            df["loan_id"]
            .astype(str)
            .str.contains(query)
        )

        if "education" in df.columns:
            mask = (
                mask
                | df["education"]
                .astype(str)
                .str.lower()
                .str.contains(query)
            )

        df = df[mask]

    total = len(df)

    page = df.iloc[
        offset : offset + limit
    ]

    records = []

    for _, row in page.iterrows():
        records.append(
            {
                "loan_id": int(row["loan_id"]),
                "no_of_dependents": int(
                    row["no_of_dependents"]
                ),
                "education": row["education"],
                "self_employed": row["self_employed"],
                "income_annum": float(
                    row["income_annum"]
                ),
                "loan_amount": float(
                    row["loan_amount"]
                ),
                "loan_term": int(
                    row["loan_term"]
                ),
                "cibil_score": float(
                    row["cibil_score"]
                ),
                "residential_assets_value": float(
                    row["residential_assets_value"]
                ),
                "commercial_assets_value": float(
                    row["commercial_assets_value"]
                ),
                "luxury_assets_value": float(
                    row["luxury_assets_value"]
                ),
                "bank_asset_value": float(
                    row["bank_asset_value"]
                ),
                "loan_status": row["loan_status"],
            }
        )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "records": records,
    }


# ============================================================
# CREATE APPLICATION
# ============================================================

@app.post("/applications")
def create_new_application(
    application: ApplicationCreate
):
    application_id = str(uuid.uuid4())

    # Autofill from Kaggle record when loan_id
    # is provided and fields are omitted

    dataset_record = None

    if application.loan_id is not None:
        try:
            df = load_dataset()

            match = df[
                df["loan_id"]
                == int(application.loan_id)
            ]

            if not match.empty:
                dataset_record = match.iloc[0]

        except Exception:
            dataset_record = None

    def coalesce(value, key, cast=float):
        if value is not None:
            return value

        if (
            dataset_record is not None
            and key in dataset_record.index
        ):
            return cast(dataset_record[key])

        return None

    application_data = {
        "application_id": application_id,
        "loan_id": application.loan_id,
        "applicant_name": application.applicant_name,
        "email": str(application.email),
        "phone": application.phone,

        "annual_income": application.annual_income,
        "loan_amount": application.loan_amount,

        "cibil_score": coalesce(
            application.cibil_score,
            "cibil_score"
        ),

        "loan_term": coalesce(
            application.loan_term,
            "loan_term",
            int
        ),

        "education": (
            application.education
            or (
                str(dataset_record["education"])
                if dataset_record is not None
                else None
            )
        ),

        "self_employed": (
            application.self_employed
            or (
                str(dataset_record["self_employed"])
                if dataset_record is not None
                else None
            )
        ),

        "no_of_dependents": coalesce(
            application.no_of_dependents,
            "no_of_dependents",
            int
        ),

        "residential_assets_value": coalesce(
            application.residential_assets_value,
            "residential_assets_value"
        ),

        "commercial_assets_value": coalesce(
            application.commercial_assets_value,
            "commercial_assets_value"
        ),

        "luxury_assets_value": coalesce(
            application.luxury_assets_value,
            "luxury_assets_value"
        ),

        "bank_asset_value": coalesce(
            application.bank_asset_value,
            "bank_asset_value"
        ),

        "status": "Document Pending",
    }

    insert_application(application_data)

    return {
        "message": "Application created successfully",
        **application_data,
    }


# ============================================================
# APPLICATION LIST
# ============================================================

@app.get("/applications")
def get_applications(
    status: str | None = None
):
    return {
        "applications": get_all_applications(
            status=status
        )
    }


# ============================================================
# SINGLE APPLICATION
# ============================================================

@app.get("/applications/{application_id}")
def get_single_application(
    application_id: str
):
    application = find_application(
        application_id
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    return application


# ============================================================
# APPLICATION SUMMARY
# ============================================================

@app.get("/applications/{application_id}/summary")
def get_summary(
    application_id: str
):
    summary = get_application_summary(
        application_id
    )

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    documents = summary.get(
        "documents",
        []
    )

    cross = analyze_cross_document(
        summary,
        documents
    )

    return {
        "application": {
            k: v
            for k, v in summary.items()
            if k != "documents"
        },
        "documents": documents,
        "cross_validation": cross,
        "ai_summary": summary.get(
            "ai_summary"
        ),
    }


# ============================================================
# UPLOAD DOCUMENT
# ============================================================

@app.post(
    "/applications/{application_id}/documents"
)
async def upload_application_document(
    application_id: str,
    file: UploadFile = File(...),
    document_type: str | None = Form(None),
):
    application = find_application(
        application_id
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected"
        )

    if (
        Path(file.filename)
        .suffix
        .lower()
        != ".pdf"
    ):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    document_id = str(uuid.uuid4())

    saved_filename = (
        f"{document_id}.pdf"
    )

    saved_path = (
        UPLOAD_DIR / saved_filename
    )

    try:
        with saved_path.open("wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to save document: {error}"
        )

    file_size = saved_path.stat().st_size

    document_data = {
        "document_id": document_id,
        "application_id": application_id,
        "original_filename": file.filename,
        "saved_filename": saved_filename,
        "document_type": (
            document_type
            or "Unknown"
        ),
        "extracted_text": "",
        "file_size": file_size,
    }

    insert_document(
        document_data
    )

    update_application_status(
        application_id,
        "Document Uploaded"
    )

    return {
        "message": "Document uploaded successfully",
        "document_id": document_id,
        "application_id": application_id,
        "filename": file.filename,
        "document_type": document_data[
            "document_type"
        ],
        "file_size": file_size,
        "status": "Document Uploaded",
    }


# ============================================================
# GENERATE DUMMY DOCUMENTS
# ============================================================

@app.post(
    "/applications/{application_id}/generate-dummy-docs"
)
def generate_dummy_docs(
    application_id: str,
    request: DummyDocsRequest | None = None
):
    application = find_application(
        application_id
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    payload = (
        request
        or DummyDocsRequest()
    )

    mode = (
        payload.mode
        if payload.mode
        in {"clean", "anomaly"}
        else "clean"
    )

    skip_tax = (
        bool(payload.skip_tax)
        or mode == "anomaly"
    )

    created_files = generate_document_suite(
        application,
        output_dir=UPLOAD_DIR,
        mode=mode,
        skip_tax=(
            skip_tax
            if mode == "anomaly"
            else False
        ),
    )

    attached = []

    for item in created_files:
        document_id = str(uuid.uuid4())

        saved_filename = (
            f"{document_id}.pdf"
        )

        target = (
            UPLOAD_DIR / saved_filename
        )

        shutil.copy(
            item["path"],
            target
        )

        # Remove intermediate named file
        # if different

        if (
            item["path"] != target
            and item["path"].exists()
        ):
            try:
                item["path"].unlink()
            except OSError:
                pass

        insert_document(
            {
                "document_id": document_id,
                "application_id": application_id,
                "original_filename": item[
                    "filename"
                ],
                "saved_filename": saved_filename,
                "document_type": item[
                    "document_type"
                ],
                "extracted_text": "",
                "file_size": target.stat().st_size,
            }
        )

        attached.append(
            {
                "document_id": document_id,
                "document_type": item[
                    "document_type"
                ],
                "filename": item[
                    "filename"
                ],
            }
        )

    update_application_status(
        application_id,
        "Document Uploaded"
    )

    return {
        "message": (
            f"Generated {len(attached)} "
            f"dummy documents ({mode})"
        ),
        "mode": mode,
        "documents": attached,
    }


# ============================================================
# VALIDATE DOCUMENT
# ============================================================

@app.post(
    "/documents/{document_id}/validate"
)
def validate_uploaded_document(
    document_id: str
):
    document = find_document(
        document_id
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    try:
        result = _process_single_document(
            document
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to process document: "
                f"{error}"
            )
        )

    application_id = document[
        "application_id"
    ]

    new_status = (
        "Document Validated"
        if result[
            "validation_result"
        ].get("is_valid")
        else "Manual Review"
    )

    update_application_status(
        application_id,
        new_status
    )

    return {
        "message": (
            "Document validation completed"
        ),
        "application_id": application_id,
        "status": new_status,
        **result,
    }


# ============================================================
# PROCESS ALL DOCUMENTS
# ============================================================

@app.post(
    "/applications/{application_id}/process-all"
)
def process_all_documents(
    application_id: str
):
    application = find_application(
        application_id
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    documents = get_documents_by_application(
        application_id
    )

    if not documents:
        raise HTTPException(
            status_code=400,
            detail="No documents uploaded"
        )

    processed = []

    for document in documents:
        try:
            processed.append(
                _process_single_document(
                    document
                )
            )

        except Exception as error:
            processed.append(
                {
                    "document_id": document[
                        "document_id"
                    ],
                    "error": str(error),
                    "document_type": document.get(
                        "document_type"
                    ),
                }
            )

    refreshed = get_documents_by_application(
        application_id
    )

    cross = analyze_cross_document(
        application,
        refreshed
    )

    eligibility = calculate_eligibility(
        annual_income=application[
            "annual_income"
        ],
        loan_amount=application[
            "loan_amount"
        ],
        applicant_name=application[
            "applicant_name"
        ],
        loan_id=application.get(
            "loan_id"
        ),
        application=application,
        cross_validation=cross,
    )

    final_status = eligibility.get(
        "status",
        "Manual Review"
    )

    update_application_fields(
        application_id,
        {
            "status": final_status,
            "ai_summary": json.dumps(
                eligibility.get(
                    "ai_summary"
                )
            ),
        },
    )

    return {
        "message": (
            "Full document suite processed"
        ),
        "application_id": application_id,
        "processed_documents": processed,
        "cross_validation": cross,
        "eligibility_result": eligibility,
        "eligible": eligibility.get(
            "eligible"
        ),
        "risk_level": eligibility.get(
            "risk_level"
        ),
        "reason": eligibility.get(
            "reason"
        ),
        "status": final_status,
        "ai_summary": eligibility.get(
            "ai_summary"
        ),
        "verification_score": eligibility.get(
            "verification_score"
        ),
        "applicant_name": application[
            "applicant_name"
        ],
        "loan_id": application.get(
            "loan_id"
        ),
        "annual_income": application[
            "annual_income"
        ],
        "loan_amount": application[
            "loan_amount"
        ],
    }


# ============================================================
# ELIGIBILITY
# ============================================================

@app.post(
    "/applications/{application_id}/eligibility"
)
def check_application_eligibility(
    application_id: str
):
    """
    Backward-compatible eligibility endpoint —
    prefers multi-doc process-all logic.
    """

    application = find_application(
        application_id
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    documents = get_documents_by_application(
        application_id
    )

    if not documents:
        update_application_status(
            application_id,
            "Manual Review"
        )

        return {
            "application_id": application_id,
            "loan_id": application.get(
                "loan_id"
            ),
            "applicant_name": application[
                "applicant_name"
            ],
            "eligible": False,
            "risk_level": "High",
            "reason": "No documents uploaded",
            "status": "Manual Review",
        }

    # Process documents that have not
    # already been extracted

    for document in documents:

        if (
            not document.get(
                "extracted_json"
            )
            and not document.get(
                "extracted_text"
            )
        ):
            try:
                _process_single_document(
                    document
                )

            except Exception:
                pass

    refreshed = get_documents_by_application(
        application_id
    )

    cross = analyze_cross_document(
        application,
        refreshed
    )

    eligibility = calculate_eligibility(
        annual_income=application[
            "annual_income"
        ],
        loan_amount=application[
            "loan_amount"
        ],
        applicant_name=application[
            "applicant_name"
        ],
        loan_id=application.get(
            "loan_id"
        ),
        application=application,
        cross_validation=cross,
    )

    final_status = eligibility.get(
        "status",
        "Manual Review"
    )

    update_application_fields(
        application_id,
        {
            "status": final_status,
            "ai_summary": json.dumps(
                eligibility.get(
                    "ai_summary"
                )
            ),
        },
    )

    return {
        "application_id": application_id,
        "loan_id": application.get(
            "loan_id"
        ),
        "applicant_name": application[
            "applicant_name"
        ],
        "annual_income": application[
            "annual_income"
        ],
        "loan_amount": application[
            "loan_amount"
        ],
        "cross_validation": cross,
        "eligibility_result": eligibility,
        "eligible": eligibility.get(
            "eligible"
        ),
        "risk_level": eligibility.get(
            "risk_level"
        ),
        "reason": eligibility.get(
            "reason"
        ),
        "status": final_status,
        "ai_summary": eligibility.get(
            "ai_summary"
        ),
        "verification_score": eligibility.get(
            "verification_score"
        ),
        "documents": refreshed,
    }


# ============================================================
# OFFICER REVIEW
# ============================================================

@app.post(
    "/applications/{application_id}/officer-review"
)
def officer_review(
    application_id: str,
    request: OfficerReviewRequest
):
    application = find_application(
        application_id
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    decision = (
        request.decision
        .lower()
        .strip()
    )

    mapping = {
        "approve": "Approved",
        "approved": "Approved",
        "reject": "Rejected",
        "rejected": "Rejected",
        "request_reupload": "Document Pending",
        "reupload": "Document Pending",
        "manual_review": "Manual Review",
    }

    if decision not in mapping:
        raise HTTPException(
            status_code=400,
            detail=(
                "decision must be approve, "
                "reject, or request_reupload"
            ),
        )

    new_status = mapping[
        decision
    ]

    reviewed_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    update_application_fields(
        application_id,
        {
            "status": new_status,
            "review_notes": request.notes,
            "reviewed_by": request.reviewed_by,
            "reviewed_at": reviewed_at,
        },
    )

    return {
        "message": (
            "Officer review recorded"
        ),
        "application_id": application_id,
        "status": new_status,
        "review_notes": request.notes,
        "reviewed_by": request.reviewed_by,
        "reviewed_at": reviewed_at,
    }


# ============================================================
# DOWNLOAD SINGLE DOCUMENT
# ============================================================

@app.get(
    "/documents/{document_id}/download"
)
def download_document(
    document_id: str
):
    document = find_document(
        document_id
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    file_path = get_document_file_path(
        document
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="File missing on disk"
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=(
            document.get(
                "original_filename"
            )
            or f"{document_id}.pdf"
        ),
    )


# ============================================================
# ZIP HELPER
# ============================================================

def _safe_zip_name(
    document: dict,
    used_names: set[str]
) -> str:

    doc_type = re.sub(
        r"[^\w\-]+",
        "_",
        (
            document.get(
                "document_type"
            )
            or "document"
        ).strip(),
    ) or "document"

    original = Path(
        document.get(
            "original_filename"
        )
        or "file.pdf"
    ).name

    base = (
        f"{doc_type}__{original}"
    )

    name = base

    index = 2

    while name.lower() in used_names:

        stem = Path(base).stem

        suffix = (
            Path(base).suffix
            or ".pdf"
        )

        name = (
            f"{stem}_{index}{suffix}"
        )

        index += 1

    used_names.add(
        name.lower()
    )

    return name


# ============================================================
# DOWNLOAD ALL DOCUMENTS AS ZIP
# ============================================================

@app.get(
    "/applications/{application_id}/documents/zip"
)
def download_documents_zip(
    application_id: str
):
    """Download all application PDFs as a single ZIP archive."""

    application = find_application(
        application_id
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    documents = get_documents_by_application(
        application_id
    )

    if not documents:
        raise HTTPException(
            status_code=404,
            detail="No documents to download"
        )

    buffer = io.BytesIO()

    used_names: set[str] = set()

    added = 0

    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        for document in documents:

            file_path = (
                get_document_file_path(
                    document
                )
            )

            if not file_path.exists():
                continue

            archive.write(
                file_path,
                arcname=_safe_zip_name(
                    document,
                    used_names
                ),
            )

            added += 1

    if added == 0:
        raise HTTPException(
            status_code=404,
            detail=(
                "Document files missing on disk"
            )
        )

    buffer.seek(0)

    applicant = re.sub(
        r"[^\w\-]+",
        "_",
        (
            application.get(
                "applicant_name"
            )
            or "application"
        ).strip(),
    ) or "application"

    filename = (
        f"{applicant}_documents.zip"
    )

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )


# ============================================================
# GET APPLICATION DOCUMENTS
# ============================================================

@app.get(
    "/applications/{application_id}/documents"
)
def get_application_documents(
    application_id: str
):
    application = find_application(
        application_id
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    return {
        "application_id": application_id,
        "documents": get_documents_by_application(
            application_id
        ),
    }