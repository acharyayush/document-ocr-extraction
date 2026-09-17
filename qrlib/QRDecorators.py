from qrlib.QRRunItem import QRRunItem

def run_item(is_ticket=True, post_success=True, post_error=True, logger_name='quickrpa_default_logger'):
    def decorator(function):
        def wrapper(self, *args, **kwargs):
            queue_item = None
            if "queue_item" in kwargs:
                queue_item = kwargs["queue_item"]

            run_item = QRRunItem(
                logger_name=logger_name, is_ticket=is_ticket, queue_item=queue_item)

            kwargs["run_item"] = run_item

            try:
                value = function(self, *args, **kwargs)
                run_item.set_success()
            except Exception as e:
                run_item.set_error()
                if (post_error):
                    run_item.post()
                raise e

            if (post_success):
                run_item.post()

            run_item.bot_logger.close_logger()
            return value
        return wrapper
    return decorator
