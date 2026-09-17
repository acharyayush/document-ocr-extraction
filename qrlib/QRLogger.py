import logging
import io


class QRLogger(object):
    def __init__(self, logger_name: str = "quickrpa_default_logger") -> None:
        self.logger_name = logger_name
        self.logger = logging.getLogger(self.logger_name)
        self.logger.setLevel(logging.DEBUG)
        
        self.logger.handlers.clear()

        self.log_capture_string = io.StringIO()
        self.ch = logging.StreamHandler(self.log_capture_string)
        self.ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.ch.setFormatter(formatter)
        self.logger.addHandler(self.ch)

    def get_log_contents(self) -> str:
        return self.log_capture_string.getvalue()

    def clear_logs(self) -> None:
        self.log_capture_string.truncate(0)
        self.log_capture_string.seek(0)

    def close_logger(self) -> None:
        self.log_capture_string.close()
        self.logger.removeHandler(self.ch)
