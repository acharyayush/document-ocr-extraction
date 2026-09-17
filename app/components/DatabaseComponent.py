import json
import sqlite3
from pathlib import Path
from typing import Optional, Tuple
from models.document import DocumentStatus
from qrlib.QRComponent import QRComponent
from app.models.document import DocumentData


class DatabaseComponent(QRComponent):

    TABLE = "processed_documents"

    def __init__(self, db_path: Optional[str] = None) -> None:
        super().__init__()
        project_root = Path(__file__).resolve().parents[2]
        self._db_path = db_path or str(project_root / "processed_documents.db")

    def _connect(self) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        """Establish connection, configure Row factory, and enable PRAGMAs."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row  # Enables dict-style column access
        cur = conn.cursor()

        # Enforce foreign keys and turn on WAL mode for concurrent access
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute("PRAGMA journal_mode = WAL;")
        return conn, cur

    def setup(self) -> None:
        """Create table if absent, then migrate any missing columns. Called once in before_run."""
        con = None
        cur = None
        try:
            con, cur = self._connect()
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE} (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    drive_file_id TEXT UNIQUE NOT NULL,
                    file_hash     TEXT,
                    status        TEXT,
                    doc_type      TEXT,
                    full_name     TEXT,
                    date_of_birth TEXT,
                    id_number     TEXT,
                    nationality   TEXT,
                    expiry_date   TEXT,
                    is_expired    INTEGER NOT NULL DEFAULT 0,
                    validation_errors TEXT NOT NULL DEFAULT '[]',
                    ocr_confidence REAL,
                    field_completeness REAL,
                    combined_score REAL
                )
            """)  
            con.commit()
            self.logger.info("step=db_setup status=ok table=%s path=%s", self.TABLE, self._db_path)
        except Exception as e:
            if self.logger:
                self.logger.error("step=db_setup status=failed error=%s", e)
            raise
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def insert_document(self, document: DocumentData) -> int:
        """Insert a document and return its database id."""
        con = None
        cur = None
        try:
            con, cur = self._connect()
            cur.execute(
                f"""
                INSERT INTO {self.TABLE} (
                    drive_file_id,
                    file_hash,
                    status,
                    doc_type,
                    full_name,
                    date_of_birth,
                    id_number,
                    nationality,
                    expiry_date,
                    is_expired,
                    validation_errors,
                    ocr_confidence,
                    field_completeness,
                    combined_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document.drive_file_id,
                    document.file_hash,
                    document.status,
                    document.doc_type,
                    document.full_name,
                    document.date_of_birth,
                    document.id_number,
                    document.nationality,
                    document.expiry_date,
                    int(document.is_expired),
                    json.dumps(document.validation_errors),
                    document.ocr_confidence,
                    document.field_completeness,
                    document.combined_score,
                ),
            )
            con.commit()
            return cur.lastrowid
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def update_status(self, drive_file_id:str, status:DocumentStatus) -> bool:
        """Update an existing document identified by its drive file id."""
        con = None
        cur = None
        try:
            con, cur = self._connect()
            cur.execute(
                f"""
                UPDATE {self.TABLE}
                SET status = ?
                WHERE drive_file_id = ?
                """,
                (
                    status,
                    drive_file_id,
                ),
            )
            con.commit()
            return cur.rowcount > 0
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def is_duplicate(self, drive_file_id: str, file_hash: str) -> bool:
        """Return whether the file ID or content hash is already stored."""
        con = None
        cur = None
        try:
            con, cur = self._connect()
            cur.execute(
                f"""
                SELECT 1
                FROM {self.TABLE}
                WHERE drive_file_id = ?
                   OR (file_hash = ?)
                LIMIT 1
                """,
                (drive_file_id, file_hash),
            )
            return cur.fetchone() is not None
        finally:
            if cur:
                cur.close()
            if con:
                con.close()