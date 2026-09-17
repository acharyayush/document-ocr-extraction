from qrlib.QRProcess import QRProcess
from qrlib.QRDecorators import run_item
from qrlib.QRRunItem import QRRunItem
from app.components.DatabaseComponent import DatabaseComponent
from app.components.DriveComponent import DriveComponent
from app.components.ExtractionComponent import ExtractionComponent
from app.components.ValidationComponent import ValidationComponent
from app.models.document import DocumentData
from Constants import DOWNLOADS_DESTINATION
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from models.document import DocumentStatus
from typing import Any
from robot.libraries.BuiltIn import BuiltIn

class OCRProcess(QRProcess):
    """Main process orchestration."""

    def __init__(self) -> None:
        super().__init__()
        self.database_component = DatabaseComponent()
        self.drive_component = DriveComponent()
        self.extraction_component = ExtractionComponent()
        self.validation_component = ValidationComponent()
        self.register(self.database_component)
        self.register(self.drive_component)
        self.register(self.extraction_component)
        self.register(self.validation_component)
        self.all_files_metadata = []
        self.run_results = []
        self.run_started_at = None
        self.run_log_path = None

    def _write_result(self, file_metadata: dict, result: dict) -> None:
        status = result["status"].lower()
        status_dir = Path("output") / status
        status_dir.mkdir(parents=True, exist_ok=True)
        csv_path = status_dir / "documents.csv"
        row = {
            "drive_file_id": file_metadata.get("id"),
            "file_name": file_metadata.get("name"),
            "doc_type": result.get("doc_type"),
            "full_name": result.get("full_name"),
            "date_of_birth": result.get("date_of_birth"),
            "id_number": result.get("id_number"),
            "nationality": result.get("nationality"),
            "expiry_date": result.get("expiry_date"),
            "status": status,
            "ocr_confidence": result.get("ocr_confidence", 0.0),
            "field_completeness": result.get("field_completeness", 0.0),
            "combined_score": result.get("combined_score", 0.0),
            "is_expired": result.get("is_expired", False),
            "validation_errors": json.dumps(result.get("validation_errors", [])),
        }
        fieldnames = list(row)
        write_header = not csv_path.exists()
        with csv_path.open("a", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
        self.run_results.append(row)

    def _write_run_log(self, message: str) -> None:
        if self.run_log_path:
            with self.run_log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"{datetime.now().isoformat()} {message}\n")

    @run_item(is_ticket=False, post_success=False)
    def before_run(self, *args, **kwargs):
        # Get run item created by decorator. Then notify to all components about new run item.
        run_item: QRRunItem = kwargs["run_item"]
        self.run_started_at = datetime.now()
        self.run_results = []
        output_root = Path("output")
        for status in ("processed", "flagged", "failed"):
            (output_root / status).mkdir(parents=True, exist_ok=True)
        Path("summary").mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(parents=True, exist_ok=True)
        timestamp = self.run_started_at.strftime("%Y%m%d_%H%M%S")
        self.run_log_path = Path("logs") / f"run_{timestamp}.log"
        self._write_run_log("Run started")

        self.notify(run_item)

        self.database_component.setup()
        self.drive_component.setup()
        self.extraction_component.setup()
        self.all_files_metadata = self.drive_component.fetch_all_drive_files_metadata()
        self.temp_output = {}
        with open("temp_output.json", "w", encoding="utf-8") as temp_file:
            json.dump(self.temp_output, temp_file, indent=2)
        run_item.set_success()

    @run_item(is_ticket=False)
    def before_run_item(self, file_metadata: dict, *args, **kwargs):
        # Get run item created by decorator. Then notify to all components about new run item.
        run_item: QRRunItem = kwargs["run_item"]
        self.notify(run_item)

        #Fetch file from drive with given drive_file_id
        destination = os.path.join(DOWNLOADS_DESTINATION, file_metadata['name'])
        self.drive_component.download_file(file_metadata['id'], destination)

        run_item.set_success()

    @run_item(is_ticket=True, post_success=True, post_error=True)
    def execute_run_item(self, file_metadata: dict, *args: Any, **kwargs: Any) -> None:
        # Get run item created by decorator. Then notify to all components about new run item.
        run_item: QRRunItem = kwargs["run_item"]
        self.notify(run_item)
        self.logger = run_item.logger
        try:
            extracted_data = self.extraction_component.extract_document_data(os.path.join(DOWNLOADS_DESTINATION, file_metadata['name']))
            extracted_data = self.validation_component.validate(extracted_data)
            document = DocumentData(
                **extracted_data,
                drive_file_id=file_metadata['id'],
                file_hash=file_metadata.get('md5Checksum'),
            )
            self.database_component.insert_document(document)
            self.drive_component.move_file_to_status(
                file_metadata["id"], extracted_data["status"]
            )
            self._write_result(file_metadata, extracted_data)
            self._write_run_log(
                f"{file_metadata['name']} status={extracted_data['status']} "
                f"score={extracted_data['combined_score']:.2f}"
            )
        except Exception as exc:
            failure_result = {
                "status": DocumentStatus.FAILED.value,
                "ocr_confidence": 0.0,
                "field_completeness": 0.0,
                "combined_score": 0.0,
                "is_expired": False,
                "validation_errors": [str(exc)],
            }
            self._write_result(file_metadata, failure_result)
            self._write_run_log(f"{file_metadata['name']} status=failed error={exc}")
            try:
                self.drive_component.move_file_to_status(
                    file_metadata["id"], DocumentStatus.FAILED.value
                )
            except Exception as move_error:
                self._write_run_log(f"Drive routing failed: {move_error}")
            run_item.notification.data = {
                "reason": str(exc),
                "step": "step",
            }
            self.logger.exception(
                "step=execute_run_item status=failed file_name=%s", file_metadata['name'], 
            )
            run_item.set_error()
            return
        if args:
            run_item.report_data["test"] = args[0]
        run_item.set_success()

    @run_item(is_ticket=False)
    def after_run_item(self, file_metadata:dict, *args: Any, **kwargs: Any) -> None:
        # Get run item created by decorator. Then notify to all components about new run item.
        run_item: QRRunItem = kwargs["run_item"]
        self.notify(run_item)
        self.drive_component.cleanup(os.path.join(DOWNLOADS_DESTINATION, file_metadata['name']))
        run_item.set_success()

    @run_item(is_ticket=False, post_success=False)
    def after_run(self, *args: Any, **kwargs: Any) -> None:
        # Get run item created by decorator. Then notify to all components about new run item.
        run_item: QRRunItem = kwargs["run_item"]
        self.notify(run_item)

        self.drive_component.cleanup()
        timestamp = self.run_started_at.strftime("%Y%m%d_%H%M%S")
        summary = {
            "started_at": self.run_started_at.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "total": len(self.run_results),
            "processed": sum(item["status"] == "processed" for item in self.run_results),
            "flagged": sum(item["status"] == "flagged" for item in self.run_results),
            "failed": sum(item["status"] == "failed" for item in self.run_results),
            "results": self.run_results,
        }
        summary_path = Path("summary") / f"summary_{timestamp}.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        self._write_run_log(f"Run completed: {json.dumps(summary)}")
        BuiltIn().log(
            f"OCR summary: total={summary['total']} processed={summary['processed']} "
            f"flagged={summary['flagged']} failed={summary['failed']}",
            console=True,
        )
        run_item.set_success()

    def execute_run(self, **kwargs: Any) -> None:
        for file_metadata in self.all_files_metadata:
            #Skip for duplicate files
            if self.database_component.is_duplicate(file_metadata['id'], file_metadata['md5Checksum']):
                continue
            self.before_run_item(file_metadata)
            self.execute_run_item(file_metadata)
            self.after_run_item(file_metadata)
