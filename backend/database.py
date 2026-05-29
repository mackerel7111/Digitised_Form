import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
DB_PATH = STORAGE_DIR / "app.db"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ensure_storage():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():
    ensure_storage()

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def init_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS forms (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                status TEXT NOT NULL,
                fields_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                form_id TEXT NOT NULL,
                values_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (form_id) REFERENCES forms(id)
            )
            """
        )


def row_to_form(row):
    return {
        "id": row["id"],
        "name": row["filename"],
        "filename": row["filename"],
        "status": row["status"],
        "fields": json.loads(row["fields_json"]),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def row_to_submission(row):
    return {
        "id": row["id"],
        "formId": row["form_id"],
        "values": json.loads(row["values_json"]),
        "createdAt": row["created_at"],
    }


def create_form(form_id, filename, fields):
    timestamp = now_iso()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO forms (
                id,
                filename,
                status,
                fields_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                form_id,
                filename,
                "Draft",
                json.dumps(fields),
                timestamp,
                timestamp,
            ),
        )

    return get_form(form_id)


def get_form(form_id):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM forms
            WHERE id = ?
            """,
            (form_id,),
        ).fetchone()

    if row is None:
        return None

    return row_to_form(row)


def list_forms():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM forms
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [row_to_form(row) for row in rows]


def update_form(form_id, fields, status):
    timestamp = now_iso()

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE forms
            SET fields_json = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                json.dumps(fields),
                status,
                timestamp,
                form_id,
            ),
        )

    return get_form(form_id)


def create_submission(form_id, values):
    submission_id = uuid4().hex
    timestamp = now_iso()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO submissions (
                id,
                form_id,
                values_json,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                submission_id,
                form_id,
                json.dumps(values),
                timestamp,
            ),
        )

    return get_submission(submission_id)


def get_submission(submission_id):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM submissions
            WHERE id = ?
            """,
            (submission_id,),
        ).fetchone()

    if row is None:
        return None

    return row_to_submission(row)


def list_submissions(form_id):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM submissions
            WHERE form_id = ?
            ORDER BY created_at DESC
            """,
            (form_id,),
        ).fetchall()

    return [row_to_submission(row) for row in rows]