import base64
import mimetypes


class QRRunItemNotification:

    def __init__(self):
        self.attachments = []
        self.subject = None
        self.data = {}

    def add_attachment(self, path: str) -> None:
        data = open(path, "rb").read()
        encoded_image = base64.b64encode(data)
        type = mimetypes.guess_type(path)[0]
        decoded_image = f"data:{type};base64," + encoded_image.decode("UTF-8")
        self.attachments.append(decoded_image)

    def set_subject(self, subject: str) -> None:
        self.subject = subject

    def set_data_item(self, key, value) -> dict:
        self.data[key] = value
        return self.data

    def update_data(self, data: dict) -> None:
        self.data.update(data)
        return self.data

    def set(self, subject=None, data=None, path=None) -> None:
        if subject:
            self.subject = subject
        if data:
            self.data = data
        if path:
            self.attachments = []
            self.add_attachment(path)

    def get_notification_dict(self) -> dict:
        notification = {}
        if self.subject:
            notification["subject"] = self.subject
        if self.attachments:
            notification["attachments"] = self.attachments
        if self.data:
            notification["data"] = self.data

        return notification
