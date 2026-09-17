import requests
from enum import Enum
from qrlib.QREnv import QREnv
from qrlib.queue.queue_exceptions import BaseUrlNotSetException, IdentifierNotSetException, PatchRequestFailedException

class QueueItemStatus(Enum):
        COMPLETED = "Completed"
        ERROR = "Error"
        PROCESSING = "Processing"
        NEW = "New"

        @property
        def choices(cls):
            return [i.value for i in cls]

         
class QRQueueItem():
    def __init__(self,status:QueueItemStatus,input:dict,queue:int,output:dict={},id:int=None,**kwargs) -> None:
       self.id = id
       self.status = status
       self.input = input
       self.output = output
       self.queue = queue

    def dict(self):
        dict_data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                dict_data[key] = value.value
            else:
                dict_data[key] = value
        #
        return dict_data

    def set_error(self) -> None:
        self.status = QueueItemStatus.ERROR

    def set_success(self) -> None:
        self.status =  QueueItemStatus.COMPLETED

    def set_retry(self)->None:
        self.status =  QueueItemStatus.NEW

    def gen_uri(self):
        if hasattr(QREnv,'BASE_URL'):
            base_url = QREnv.BASE_URL
        else:
            raise BaseUrlNotSetException()

        path = f"/bot/queue/{self.queue}/data/{self.id}/"
        uri = uri = f"{base_url}{path}"
        return uri

    @staticmethod
    def gen_headers():
        identifier = QREnv.IDENTIFIER
        if not identifier:
            raise IdentifierNotSetException

        return {
            "Accept":"application/json",
            "Authorization":f"identifier {identifier}"
        }

    def post(self):
        json_data = self.dict()
        
        response = QREnv.session().patch(
            url=self.gen_uri(),
            json=json_data,
            headers=self.gen_headers()
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise PatchRequestFailedException(response.text)
