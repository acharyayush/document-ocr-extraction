from qrlib.QRComponent import QRComponent
from qrlib.QREnv import QREnv
from google import genai
from google.genai import types
from google.genai.errors import APIError
from models.document import ExtractedData
from robot.libraries.BuiltIn import BuiltIn
import os
class ExtractionComponent(QRComponent):
    
    def __init__(self):
        super().__init__()
        self.client = None

    def setup(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        self.client = genai.Client(api_key=api_key)

    def extract_document_data(self, file_path: str) -> dict:
        """
        Uploads local file to Gemini Files API, performs structured extraction,
         and returns a Python dictionary.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Local file not found at path: {file_path}")

        remote_file = None
        try:
            remote_file = self.client.files.upload(file=file_path)

            # Define System Prompt and Extraction Rules
            prompt = """
                    You are an expert document extraction engine. Extract key-value text pairs from the document.

                    EXTRACTION & NORMALIZATION RULES:
                    1. DATE NORMALIZATION: Convert all dates (date_of_birth, expiry_date) to strictly YYYY-MM-DD format (e.g., '15 JAN 1990' -> '1990-01-15').
                    2. WHITESPACE CLEANUP: Strip leading/trailing extra whitespace and newlines from all extracted values.
                    3. ABSOLUTE OMISSION RULE:
                       - For optional fields (nationality, expiry_date), return null if they do NOT exist in the document.
                          4. OCR CONFIDENCE: Return ocr_confidence as a number from 0 to 100 representing your confidence in the extracted values.
                    """

            # Call Gemini enforcing Pydantic response schema
            self.logger.info("Calling Gemini API with structured response schema...")
            response = self.client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=[remote_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractedData,
                    temperature=0.0 # Deterministic OCR
                )
            )
            
            # Convert response to native Python dictionary
            # response.parsed contains the instantiated Document Pydantic object
            extracted_data: ExtractedData = response.parsed
            result_dict = extracted_data.model_dump()

            # Clean up dictionary & strip whitespace across all values
            clean_dict = {}
            for key, val in result_dict.items():
                if isinstance(val, str):
                    val = val.strip()
                if val is not None:
                    clean_dict[key] = val

            return clean_dict

        except APIError as api_err:
            self.logger.error(f"Gemini API Error during extraction: {api_err}")
            raise

        except Exception as err:
            self.logger.critical(f"Unexpected failure in ExtractionComponent: {err}")
            raise

        finally:
            # 7. Remote file cleanup on Gemini server
            if remote_file:
                try:
                    self.client.files.delete(name=remote_file.name)
                    self.logger.info(f"Cleaned up remote Gemini file: {remote_file.name}")
                except Exception as cleanup_err:
                    self.logger.warning(f"Failed to delete remote file: {cleanup_err}")
    