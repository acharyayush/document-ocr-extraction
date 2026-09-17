import re
import os
import requests
import urllib
import time

from qrlib.QRUtils import get_secret
from qrlib.QREnv import QREnv
from storage_buckets.storage_bucket_exceptions import (
        BaseUrlNotSetException,
        IdentifierNotSetException,
        BucketNameNotSetException,
        BucketIdNotSetException,
        FileDownloadError,
        BucketDoesNotExist,
        PostFileError,
        FileOperationError
    )


class QRStorageBucket:

    STORAGE_LOCAL = 'local'
    STORAGE_S3 = 's3'

    def __init__(self, working_bucket):
        self._working_bucket_type = None
        self._working_bucket_id = None
        self._working_bucket = working_bucket
        self._create_download_location()
        self.get_bucket_info()

    @property
    def working_bucket(self):
        return self._working_bucket

    @property
    def working_bucket_id(self):
        return self._working_bucket_id

    @property
    def working_bucket_type(self):
        return self._working_bucket_type

    def _create_download_location(self):
        location = QREnv.DEFAULT_STORAGE_LOCATION
        os.makedirs(location, exist_ok=True)

    # * URI Generation Methods
    @staticmethod
    def gen_headers():
        identifier = QREnv.IDENTIFIER
        if not identifier:
            raise IdentifierNotSetException

        return {
                "Accept":"application/json",
                "Authorization":f"identifier {identifier}"
            }
    
    @staticmethod
    def _base_url():
        if hasattr(QREnv, 'BASE_URL'):
            base_url = QREnv.BASE_URL
            return base_url
        else:
            raise BaseUrlNotSetException

    def _gen_api_base_uri(self, type: str="bucket"):
        """
        param type: bucket, generate uri for working bucket
        param type: bucket_data, generate uri for working bucket data
        """
        base_url = self._base_url()
        path = f"/bot/storagebuckets/"

        if type == 'bucket_data':
            # * base url for bucket data
            bucket_id = self.working_bucket_id
            if bucket_id is None:
                raise BucketIdNotSetException
            path = f"{path}{bucket_id}/bucket_data/"

        uri = f"{base_url}{path}"
        return uri
        
    def _gen_file_download_link(self, file_url):
        """Implemented for local storage for file downloads"""
        base_url = self._base_url()
        uri = f"{base_url}{file_url}"
        return uri
    
    # * Bucket Processing Methods
    def get_bucket_info(self):
        if(QREnv.NO_PLATFORM):
            return {"id":0,"name":"Test Bucket"}
        
        if self.working_bucket:
            current_working_bucket = self.working_bucket
        else:
            raise BucketNameNotSetException
            
        payload = {"bucket_name": current_working_bucket}
        response = QREnv.session().get(
                    url=self._gen_api_base_uri(),
                    headers=self.gen_headers(),
                    params=payload
                )
        if response.status_code == 200:
            found_bucket = response.json()
        else:
            raise Exception(response.text)

        if found_bucket:
            self._working_bucket_id = found_bucket[0]['id']
            self._working_bucket_type = found_bucket[0]['bucket_type']
        else:
            raise BucketDoesNotExist
        return found_bucket

    def portal_login(self):
        vault_value = get_secret('System')
        email = vault_value['email']
        password = vault_value['password']
        base_url = self._base_url()
        url = base_url+"/token/"

        data = {
            'email': email,
            'password': password
        }

        headers = {
            'Accept': 'application/json',  
        }

        try:
            with QREnv.session().post(url, json=data, headers=headers) as response:
                if response.status_code == 200:
                    json_response = response.json()
                    return json_response['access']
                else:
                    print(f"Error:")
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error: {err}")
        except Exception as e:
            print(f"Error: {e}")

    # * File Processing Methods
    def download_file(self, file_item: dict, save_to_folder=''):
        bucket_type = str(self.working_bucket_type).lower()
        file_url = file_item.get('file')
        filename_str = str(file_item.get('file_display_name'))
        regex_filename = re.findall(r"(([^/]+/)*)([\w._]+)+", string=filename_str)[0]
        filename = str(regex_filename[2]).split(".")

        filename = filename[1] if not filename[0] else filename[0]
        
        if bucket_type == self.STORAGE_LOCAL:
            # download_link = self._gen_file_download_link(file_url=file_url)
            download_link = file_url
            token = self.portal_login()
            headers = {
                "Authorization": f"Bearer {token}"
            }
           
        elif bucket_type == self.STORAGE_S3:
            download_link = file_url
        
        try:
            with QREnv.session().get(download_link, headers=headers) as response:
                response.raise_for_status()
                # content_type = response.headers.get('Content-Type', '')
                # extension = content_type.split('/')[-1]
                extension = file_url.split('.')[-1]

                # Set the correct file name including the extension
                full_file_name = f"{filename}.{extension}"

                # Explicitly set the Content-Disposition header
                response.headers['Content-Disposition'] = f'attachment; filename="{full_file_name}"'

                file_path = os.path.join(QREnv.DEFAULT_STORAGE_LOCATION, full_file_name) if not save_to_folder else os.path.join(save_to_folder, full_file_name)

                with open(file_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
        except Exception as e:
            raise FileDownloadError

        return file_path

    def post_file(self, filename_to_upload, full_file_path):
        base_url = self._gen_api_base_uri(type="bucket_data")

        file = {"file": open(full_file_path, "rb")}
        bucket_data_dictionary = {
            "file_display_name": filename_to_upload
        }

        response = QREnv.session().post(
            url=base_url,
            headers=self.gen_headers(),
            data=bucket_data_dictionary,
            files=file
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise PostFileError(response.text)

    def list_all_files(self):
        base_url = self._gen_api_base_uri(type='bucket_data')
        response = QREnv.session().get(
            url=base_url,
            headers=self.gen_headers()
            )

        if response.status_code == 200:
            files_list = response.json()
        else:
            raise Exception(response.text)

        return files_list

    def search_and_get_file(self, find_filename: str):
        base_url = self._gen_api_base_uri(type="bucket_data")
        file_search_url = urllib.parse.urljoin(base_url, f'?file_name={find_filename}')

        response = QREnv.session().get(
            url=file_search_url,
            headers=self.gen_headers()
            )
        
        if response.status_code == 200:
            files_list = response.json()
        else:
            raise FileNotFoundError(response.text)

        return files_list
    
    def file_operation(self, action: str, file_obj_id: int, new_file_name: str):
        """
        :param action: operation on file i.e. rename, copy, move
        """
        base_url = self._gen_api_base_uri(type="bucket_data")
        full_url = urllib.parse.urljoin(base_url, f'{file_obj_id}/')
        data = {
                "file_display_name": new_file_name,
                "action": action
            }
        response = QREnv.session().patch(url=full_url, headers=self.gen_headers(), data=data)
        if response.status_code == 200:
            file_operation = response.json()
        else:
            raise FileOperationError(response.text)
        return file_operation
