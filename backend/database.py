import json
import sqlite3
from pathlib import Path


DATABASE_FILE = Path(__file__).parent / "smartloan.db"


APPLICATION_COLUMNS = {
    "cibil_score": "REAL",
    "loan_term": "INTEGER",
    "education": "TEXT",
    "self_employed": "TEXT",
    "no_of_dependents": "INTEGER",
    "residential_assets_value": "REAL",
    "commercial_assets_value": "REAL",
    "luxury_assets_value": "REAL",
    "bank_asset_value": "REAL",
    "review_notes": "TEXT",
    "reviewed_by": "TEXT",
    "reviewed_at": "TIMESTAMP",
    "ai_summary": "TEXT",
}

DOCUMENT_COLUMNS = {
    "extracted_json": "TEXT",
    "confidence_score": "REAL",
    "classification_confidence": "REAL",
    "file_size": "INTEGER",
}


def get_connection():
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_columns(connection, table_name, columns):
    existing = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_type in columns.items():
        if column_name not in existing:
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )


def create_tables():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id TEXT UNIQUE NOT NULL,
            loan_id INTEGER,
            applicant_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            annual_income REAL,
            loan_amount REAL,
            cibil_score REAL,
            loan_term INTEGER,
            education TEXT,
            self_employed TEXT,
            no_of_dependents INTEGER,
            residential_assets_value REAL,
            commercial_assets_value REAL,
            luxury_assets_value REAL,
            bank_asset_value REAL,
            status TEXT DEFAULT 'Document Pending',
            review_notes TEXT,
            reviewed_by TEXT,
            reviewed_at TIMESTAMP,
            ai_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT UNIQUE NOT NULL,
            application_id TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            saved_filename TEXT NOT NULL,
            document_type TEXT DEFAULT 'Unknown',
            extracted_text TEXT,
            extracted_json TEXT,
            confidence_score REAL,
            classification_confidence REAL,
            file_size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id)
                REFERENCES applications(application_id)
        )
    """)

    _ensure_columns(connection, "applications", APPLICATION_COLUMNS)
    _ensure_columns(connection, "documents", DOCUMENT_COLUMNS)

    connection.commit()
    connection.close()


def insert_application(application):
    connection = get_connection()

    connection.execute("""
        INSERT INTO applications (
            application_id,
            loan_id,
            applicant_name,
            email,
            phone,
            annual_income,
            loan_amount,
            cibil_score,
            loan_term,
            education,
            self_employed,
            no_of_dependents,
            residential_assets_value,
            commercial_assets_value,
            luxury_assets_value,
            bank_asset_value,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        application["application_id"],
        application.get("loan_id"),
        application["applicant_name"],
        application["email"],
        application["phone"],
        application["annual_income"],
        application["loan_amount"],
        application.get("cibil_score"),
        application.get("loan_term"),
        application.get("education"),
        application.get("self_employed"),
        application.get("no_of_dependents"),
        application.get("residential_assets_value"),
        application.get("commercial_assets_value"),
        application.get("luxury_assets_value"),
        application.get("bank_asset_value"),
        application["status"],
    ))

    connection.commit()
    connection.close()


def get_all_applications(status=None):
    connection = get_connection()

    if status:
        rows = connection.execute("""
            SELECT *
            FROM applications
            WHERE status = ?
            ORDER BY id DESC
        """, (status,)).fetchall()
    else:
        rows = connection.execute("""
            SELECT *
            FROM applications
            ORDER BY id DESC
        """).fetchall()

    connection.close()
    return [dict(row) for row in rows]


def get_application_by_id(application_id):
    connection = get_connection()
    row = connection.execute("""
        SELECT *
        FROM applications
        WHERE application_id = ?
    """, (application_id,)).fetchone()
    connection.close()
    return dict(row) if row else None


def application_exists(application_id):
    return get_application_by_id(application_id) is not None


def insert_document(document):
    connection = get_connection()

    extracted_json = document.get("extracted_json")
    if isinstance(extracted_json, (dict, list)):
        extracted_json = json.dumps(extracted_json)

    connection.execute("""
        INSERT INTO documents (
            document_id,
            application_id,
            original_filename,
            saved_filename,
            document_type,
            extracted_text,
            extracted_json,
            confidence_score,
            classification_confidence,
            file_size
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        document["document_id"],
        document["application_id"],
        document["original_filename"],
        document["saved_filename"],
        document.get("document_type", "Unknown"),
        document.get("extracted_text", ""),
        extracted_json,
        document.get("confidence_score"),
        document.get("classification_confidence"),
        document.get("file_size"),
    ))

    connection.commit()
    connection.close()


def update_document(document_id, updates):
    connection = get_connection()

    allowed = {
        "document_type",
        "extracted_text",
        "extracted_json",
        "confidence_score",
        "classification_confidence",
        "file_size",
    }

    fields = []
    values = []
    for key, value in updates.items():
        if key not in allowed:
            continue
        if key == "extracted_json" and isinstance(value, (dict, list)):
            value = json.dumps(value)
        fields.append(f"{key} = ?")
        values.append(value)

    if not fields:
        connection.close()
        return

    values.append(document_id)
    connection.execute(
        f"UPDATE documents SET {', '.join(fields)} WHERE document_id = ?",
        values,
    )
    connection.commit()
    connection.close()


def get_documents_by_application(application_id):
    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM documents
        WHERE application_id = ?
        ORDER BY id DESC
    """, (application_id,)).fetchall()

    connection.close()

    documents = []
    for row in rows:
        item = dict(row)
        if item.get("extracted_json"):
            try:
                item["extracted_json"] = json.loads(item["extracted_json"])
            except (TypeError, json.JSONDecodeError):
                pass
        documents.append(item)

    return documents


def get_document_by_id(document_id):
    connection = get_connection()
    row = connection.execute("""
        SELECT *
        FROM documents
        WHERE document_id = ?
    """, (document_id,)).fetchone()
    connection.close()

    if row is None:
        return None

    item = dict(row)
    if item.get("extracted_json"):
        try:
            item["extracted_json"] = json.loads(item["extracted_json"])
        except (TypeError, json.JSONDecodeError):
            pass
    return item


def update_application_status(application_id, status):
    connection = get_connection()
    connection.execute("""
        UPDATE applications
        SET status = ?
        WHERE application_id = ?
    """, (status, application_id))
    connection.commit()
    connection.close()


def update_application_fields(application_id, updates):
    connection = get_connection()

    allowed = {
        "status",
        "review_notes",
        "reviewed_by",
        "reviewed_at",
        "ai_summary",
        "cibil_score",
        "loan_term",
        "education",
        "self_employed",
        "no_of_dependents",
        "residential_assets_value",
        "commercial_assets_value",
        "luxury_assets_value",
        "bank_asset_value",
        "annual_income",
        "loan_amount",
        "applicant_name",
    }

    fields = []
    values = []
    for key, value in updates.items():
        if key not in allowed:
            continue
        fields.append(f"{key} = ?")
        values.append(value)

    if not fields:
        connection.close()
        return

    values.append(application_id)
    connection.execute(
        f"UPDATE applications SET {', '.join(fields)} WHERE application_id = ?",
        values,
    )
    connection.commit()
    connection.close()


def get_application_summary(application_id):
    application = get_application_by_id(application_id)
    if application is None:
        return None

    documents = get_documents_by_application(application_id)
    summary = dict(application)
    if summary.get("ai_summary"):
        try:
            summary["ai_summary"] = json.loads(summary["ai_summary"])
        except (TypeError, json.JSONDecodeError):
            pass
    summary["documents"] = documents
    return summary
