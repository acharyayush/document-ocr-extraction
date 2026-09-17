from qrlib.QRComponent import QRComponent
from qrlib.QREnv import QREnv
from Constants import SERVICE_ACCOUNT_FILE, SCOPES, ACCEPTED_MIME_TYPES, SHARED_FOLDER_ID
import os
import shutil
from pathlib import Path
from Constants import DOWNLOADS_DESTINATION
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials
from robot.libraries.BuiltIn import BuiltIn

class DriveComponent(QRComponent):
    
    def __init__(self):
        super().__init__()
        self.drive_service = None
        self.next_page_token = None
        self.mime_type_query = ""
        self.status_folder_ids = {}

    def setup(self):
        """Setup drive service, mime type for query and create folder for downloads"""
        drive_creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        self.drive_service = build('drive', 'v3', credentials=drive_creds)

        #Create mime type query
        self.mime_type_query = " or ".join(
            f"mimeType = '{mime_type}'" for mime_type in ACCEPTED_MIME_TYPES
        )
        #Create folder for download if it doesn't exist
        folder = Path(DOWNLOADS_DESTINATION)
        folder.mkdir(exist_ok=True)
        

    def fetch_all_drive_files_metadata(self):
        """Fetch every file metadata in the shared folder from drive"""
        all_files = []
        while True:
            response = self.fetch_drive_files_page(self.next_page_token)
            all_files.extend(response)
            if not self.next_page_token:
                return all_files
            
    def fetch_drive_files_page(self, page_token):
        """Fetch list of metadatas of files (max: 2 files for page token)"""
        query = (
            f"'{SHARED_FOLDER_ID}' in parents and "
            f"({self.mime_type_query}) and trashed = false"
        )
        while True:
            try:
                response = self.drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, size, md5Checksum, parents)',
                    pageSize=2,
                    pageToken=page_token
                ).execute()
                self.next_page_token = response.get('nextPageToken', None)
                return response['files']
                

            except HttpError as http_err:
                status_code = http_err.resp.status
                self.logger.error(f"HTTP {status_code} Error: {http_err}")
                raise

            except Exception as unexpected_err:
                self.logger.error(f"Unexpected Error occured: {unexpected_err}")
                raise

    def download_file(self, drive_file_id: str, destination_path:str):
        # Check if local destination file already exists
        if os.path.exists(destination_path):
            raise FileExistsError(
                f"File already exists. in this destination: {destination_path}"
        )
        try:
            request = self.drive_service.files().get_media(fileId=drive_file_id)
            with open(destination_path, 'wb') as local_file:
                downloader = MediaIoBaseDownload(local_file, request, chunksize=1024 * 1024)
                done = False
                while not done:
                    _, done = downloader.next_chunk()

            self.logger.info(f"Successfully downloaded file ID {drive_file_id} to {destination_path}")
            return destination_path

        except Exception:
            # Cleanup incomplete/corrupted file if an exception occurred midway through streaming
            if os.path.exists(destination_path):
                try:
                    os.remove(destination_path)
                except OSError as cleanup_err:
                    self.logger.warning(f"Failed to remove incomplete file '{destination_path}': {cleanup_err}")
            raise

    def cleanup(self, filePath: str):
        #Remove file with given file path
            if os.path.exists(filePath):
                try:
                    os.remove(filePath)
                except OSError as cleanup_err:
                    self.logger.warning(f"Failed to remove incomplete file '{filePath}': {cleanup_err}")

    def cleanup(self) -> None:
        """Remove download destination directory. (This is for after run)"""
        if os.path.isdir(DOWNLOADS_DESTINATION):
            try:
                shutil.rmtree(DOWNLOADS_DESTINATION)
            except OSError as cleanup_err:
                self.logger.warning(
                    f"Failed to remove download directory '{DOWNLOADS_DESTINATION}': {cleanup_err}"
                )

    def move_file_to_status(self, drive_file_id: str, status: str) -> None:
        folder_name = status.lower()
        folder_id = self.status_folder_ids.get(folder_name)
        if not folder_id:
            folder_query = (
                f"'{SHARED_FOLDER_ID}' in parents and "
                f"name = '{folder_name}' and "
                "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            )
            folders = self.drive_service.files().list(
                q=folder_query,
                spaces="drive",
                fields="files(id)",
                pageSize=1,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute().get("files", [])
            if folders:
                folder_id = folders[0]["id"]
            else:
                folder_id = self.drive_service.files().create(
                    body={
                        "name": folder_name,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [SHARED_FOLDER_ID],
                    },
                    fields="id",
                    supportsAllDrives=True,
                ).execute()["id"]
            self.status_folder_ids[folder_name] = folder_id

        file_info = self.drive_service.files().get(
            fileId=drive_file_id,
            fields="parents",
            supportsAllDrives=True,
        ).execute()
        previous_parents = ",".join(file_info.get("parents", []))
        self.drive_service.files().update(
            fileId=drive_file_id,
            addParents=folder_id,
            removeParents=previous_parents or None,
            fields="id, parents",
            supportsAllDrives=True,
        ).execute()