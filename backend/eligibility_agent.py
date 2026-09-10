"""ML eligibility agent with document verification + GenAI-style audit summary."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "loan_model.pkl"
DATASET_PATH = BASE_DIR / "loan_approval_dataset.csv"
TRAIN_SCRIPT = BASE_DIR / "train_model.py"

_model = None


def ensure_model():
    """Load the Random Forest model, training it automatically if missing."""
    global _model
    if _model is not None:
        return _model

    if not MODEL_PATH.exists():
        if not TRAIN_SCRIPT.exists():
            raise FileNotFoundError(
                f"Trained model not found at {MODEL_PATH} and train_model.py is missing."
            )
        result = subprocess.run(
            [sys.executable, str(TRAIN_SCRIPT)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not MODEL_PATH.exists():
            raise RuntimeError(
                "Unable to train loan model automatically.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )

    _model = joblib.load(MODEL_PATH)
    return _model


def load_dataset() -> pd.DataFrame:
    dataset = pd.read_csv(DATASET_PATH)
    dataset.columns = dataset.columns.str.strip()
    for column in dataset.select_dtypes(include=["object"]).columns:
        dataset[column] = dataset[column].astype(str).str.strip()
    return dataset


def _build_feature_row(application: dict, record: pd.Series | None = None) -> pd.DataFrame:
    def pick(app_key, record_key=None, default=0):
        record_key = record_key or app_key
        if application.get(app_key) is not None:
            return application.get(app_key)
        if record is not None and record_key in record.index:
            return record[record_key]
        return default

    return pd.DataFrame(
        [
            {
                "no_of_dependents": pick("no_of_dependents", default=0),
                "education": pick("education", default="Graduate"),
                "self_employed": pick("self_employed", default="No"),
                "income_annum": float(application.get("annual_income") or 0),
                "loan_amount": float(application.get("loan_amount") or 0),
                "loan_term": pick("loan_term", default=12),
                "cibil_score": pick("cibil_score", default=650),
                "residential_assets_value": pick("residential_assets_value", default=0),
                "commercial_assets_value": pick("commercial_assets_value", default=0),
                "luxury_assets_value": pick("luxury_assets_value", default=0),
                "bank_asset_value": pick("bank_asset_value", default=0),
            }
        ]
    )


def _predict(application: dict, loan_id: int | None = None) -> dict[str, Any]:
    model = ensure_model()
    dataset = load_dataset()
    record = None
    dataset_status = None

    if loan_id is not None:
        matching = dataset[dataset["loan_id"] == int(loan_id)]
        if not matching.empty:
            record = matching.iloc[0]
            dataset_status = str(record.get("loan_status", "")).strip()

    model_input = _build_feature_row(application, record)
    prediction = model.predict(model_input)[0]
    probabilities = model.predict_proba(model_input)[0]
    classes = list(model.classes_)
    confidence = round(float(max(probabilities)) * 100, 2)
    proba_map = {
        str(label).strip(): round(float(prob) * 100, 2)
        for label, prob in zip(classes, probabilities)
    }

    prediction_text = str(prediction).strip()
    approved = prediction_text.lower() == "approved"

    return {
        "model_prediction": prediction_text,
        "confidence": confidence,
        "approval_probability": proba_map.get("Approved", 0 if not approved else confidence),
        "rejection_probability": proba_map.get("Rejected", 0 if approved else confidence),
        "dataset_loan_id": int(loan_id) if loan_id is not None else None,
        "dataset_status": dataset_status,
        "feature_snapshot": model_input.iloc[0].to_dict(),
    }


def generate_ai_summary(
    application: dict,
    ml_result: dict,
    cross_validation: dict,
    final_status: str,
    risk_level: str,
) -> dict[str, Any]:
    applicant = application.get("applicant_name", "Applicant")
    high = cross_validation.get("severity_counts", {}).get("High", 0)
    medium = cross_validation.get("severity_counts", {}).get("Medium", 0)
    missing = cross_validation.get("missing_documents", [])
    score = cross_validation.get("verification_score", 0)

    verdict = (
        f"{applicant}'s application is recommended as **{final_status}** "
        f"with {risk_level} risk. Document verification score: {score}/100. "
        f"Random Forest approval probability: {ml_result.get('approval_probability')}%."
    )

    next_steps = []
    if missing:
        next_steps.append(f"Request missing documents: {', '.join(missing)}.")
    if high:
        next_steps.append("Investigate high-severity discrepancies before approval.")
    if medium:
        next_steps.append("Clarify medium-severity extraction or consistency warnings.")
    if final_status == "Eligible":
        next_steps.append("Officer may approve with standard underwriting checks.")
    elif final_status == "Not Eligible":
        next_steps.append("Communicate decline rationale and offer remediation paths.")
    else:
        next_steps.append("Route to Manual Review workspace for officer decision.")

    if not next_steps:
        next_steps.append("No outstanding actions — proceed with standard policy.")

    scorecard = {
        "documents_present": cross_validation.get("present_documents", []),
        "documents_missing": missing,
        "verification_score": score,
        "discrepancy_counts": cross_validation.get("severity_counts", {}),
        "income_variance_pct": cross_validation.get("income_variance_pct"),
    }

    return {
        "executive_summary": verdict,
        "document_scorecard": scorecard,
        "discrepancies": cross_validation.get("discrepancies", []),
        "ml_risk_analysis": {
            "prediction": ml_result.get("model_prediction"),
            "confidence": ml_result.get("confidence"),
            "approval_probability": ml_result.get("approval_probability"),
            "rejection_probability": ml_result.get("rejection_probability"),
            "dataset_status": ml_result.get("dataset_status"),
            "cibil_score": application.get("cibil_score")
            or ml_result.get("feature_snapshot", {}).get("cibil_score"),
        },
        "recommended_actions": next_steps,
        "audit_trail": [
            "Application intake completed",
            "Documents classified and fields extracted",
            "Cross-document inconsistency analysis executed",
            "Kaggle Random Forest eligibility scored",
            "GenAI processing summary generated",
        ],
    }


def calculate_eligibility(
    annual_income,
    loan_amount,
    validation_result=None,
    applicant_name=None,
    loan_id=None,
    application: dict | None = None,
    cross_validation: dict | None = None,
):
    """
    Combine ML prediction with document verification findings.

    Backward compatible with older callers that only pass validation_result.
    """
    application = dict(application or {})
    application.setdefault("applicant_name", applicant_name)
    application.setdefault("annual_income", annual_income)
    application.setdefault("loan_amount", loan_amount)
    if loan_id is not None:
        application.setdefault("loan_id", loan_id)

    cross_validation = cross_validation or {
        "discrepancies": [],
        "missing_documents": [],
        "verification_score": 100 if (validation_result or {}).get("is_valid") else 40,
        "severity_counts": {"High": 0, "Medium": 0, "Low": 0},
        "present_documents": [],
        "income_variance_pct": None,
        "extracted_by_type": {},
    }

    # Legacy single-doc invalid path
    if validation_result is not None and not validation_result.get("is_valid", True):
        if not cross_validation.get("discrepancies"):
            cross_validation = {
                **cross_validation,
                "verification_score": min(cross_validation.get("verification_score", 40), 40),
                "severity_counts": {"High": 1, "Medium": 0, "Low": 0},
                "discrepancies": [
                    {
                        "code": "DOC_INVALID",
                        "severity": "High",
                        "message": validation_result.get(
                            "validation_message",
                            "Document could not be validated.",
                        ),
                    }
                ],
            }

    high = cross_validation.get("severity_counts", {}).get("High", 0)
    missing = cross_validation.get("missing_documents", [])
    score = cross_validation.get("verification_score", 0)

    try:
        ml_result = _predict(application, application.get("loan_id"))
    except Exception as error:
        ml_result = {
            "model_prediction": "Manual Review",
            "confidence": 0,
            "approval_probability": 0,
            "rejection_probability": 0,
            "dataset_loan_id": application.get("loan_id"),
            "dataset_status": None,
            "feature_snapshot": {},
            "error": str(error),
        }

    approved_by_ml = str(ml_result.get("model_prediction", "")).lower() == "approved"
    approval_prob = float(ml_result.get("approval_probability") or 0)

    if missing or high >= 2 or score < 50:
        status = "Manual Review"
        risk_level = "High"
        eligible = False
        reason = (
            "Document verification found missing documents or high-severity "
            "discrepancies requiring officer review."
        )
    elif high == 1 or (50 <= score < 70):
        status = "Manual Review"
        risk_level = "Medium"
        eligible = False
        reason = (
            "Partial document consistency issues detected. "
            "Routed for loan officer review."
        )
    elif approved_by_ml and approval_prob >= 55 and score >= 70:
        status = "Eligible"
        risk_level = "Low"
        eligible = True
        reason = (
            "Documents are consistent and the Random Forest model predicts approval."
        )
    elif not approved_by_ml and score >= 70:
        status = "Not Eligible"
        risk_level = "High"
        eligible = False
        reason = (
            "Documents verified, but the ML model predicts rejection based on "
            "Kaggle-trained risk features (CIBIL, income, assets, tenure)."
        )
    else:
        status = "Manual Review"
        risk_level = "Medium"
        eligible = False
        reason = "Mixed ML and document signals require human review."

    ai_summary = generate_ai_summary(
        application=application,
        ml_result=ml_result,
        cross_validation=cross_validation,
        final_status=status,
        risk_level=risk_level,
    )

    return {
        "status": status,
        "risk_level": risk_level,
        "reason": reason,
        "applicant_name": application.get("applicant_name"),
        "dataset_loan_id": ml_result.get("dataset_loan_id"),
        "model_prediction": ml_result.get("model_prediction"),
        "confidence": ml_result.get("confidence"),
        "approval_probability": ml_result.get("approval_probability"),
        "rejection_probability": ml_result.get("rejection_probability"),
        "eligible": eligible,
        "verification_score": score,
        "cross_validation": cross_validation,
        "ai_summary": ai_summary,
        "ml_features": ml_result.get("feature_snapshot"),
        "dataset_status": ml_result.get("dataset_status"),
    }
