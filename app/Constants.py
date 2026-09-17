"""Non-secret configuration constants for the bot.

All secret credentials are fetched in QREnv vaults .
Update these values before deployment.
"""
SHARED_FOLDER_ID = "10SWsd_7RN-5FisEZ45vsWxi15dXcWmvi"
SERVICE_ACCOUNT_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/drive'] # This specifies editor permission
ACCEPTED_MIME_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
DOWNLOADS_DESTINATION = "/Users/aacs/Desktop/OCR project/input"
REQUIRED_FIELDS = ["doc_type", "full_name", "date_of_birth", "id_number"]