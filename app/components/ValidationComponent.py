from datetime import date
import re

from Constants import REQUIRED_FIELDS
from models.document import DocumentStatus
from qrlib.QRComponent import QRComponent


class ValidationComponent(QRComponent):

    def validate(self, extracted_data: dict) -> dict:
        validation_errors = []
        required_missing = []
        optional_missing = []
        for required_field in REQUIRED_FIELDS:
            if not extracted_data.get(required_field):
                required_missing.append(required_field)
                validation_errors.append(f"{required_field} is missing or empty")
        for field_name in ("nationality", "expiry_date"):
            if not extracted_data.get(field_name):
                optional_missing.append(field_name)

        parsed_dates = {}
        for field_name in ("date_of_birth", "expiry_date"):
            value = extracted_data.get(field_name)
            if value is None or value == "":
                continue
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError
                parsed_dates[field_name] = date.fromisoformat(value)
            except (TypeError, ValueError):
                validation_errors.append(
                    f"{field_name} must be a valid YYYY-MM-DD date"
                )

        date_of_birth = parsed_dates.get("date_of_birth")
        if date_of_birth is not None:
            if date_of_birth.year <= 1900:
                validation_errors.append("date_of_birth must be after 1900")
            if date_of_birth >= date.today():
                validation_errors.append("date_of_birth must be in the past")

        id_number = extracted_data.get("id_number")
        expiry_date = parsed_dates.get("expiry_date")
        extracted_data["is_expired"] = (
            expiry_date is not None and expiry_date < date.today()
        )
        field_completeness = (
            len(REQUIRED_FIELDS) - len(required_missing)
        ) / len(REQUIRED_FIELDS) * 100
        ocr_confidence = float(extracted_data.get("ocr_confidence") or 0.0)
        combined_score = (ocr_confidence * 0.6) + (field_completeness * 0.4)

        if required_missing or combined_score < 50:
            status = DocumentStatus.FAILED
        elif combined_score < 80 or optional_missing or extracted_data["is_expired"]:
            status = DocumentStatus.FLAGGED
        else:
            status = DocumentStatus.PROCESSED

        extracted_data["field_completeness"] = field_completeness
        extracted_data["combined_score"] = combined_score
        extracted_data["status"] = status.value
        extracted_data["validation_errors"] = validation_errors
        return extracted_data
