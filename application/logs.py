import logging
import os
import sys
from logging.handlers import RotatingFileHandler

UVI_FORMAT = "%(levelprefix)s %(asctime)s - %(message)s"
APP_FORMAT = "%(levelname)s %(asctime)s - %(message)s"


class CustomFormatter(logging.Formatter):
    levelname_to_prefix = {
        "DEBUG": "DEBUG:   ",
        "INFO": "INFO:    ",
        "WARNING": "WARNING: ",
        "ERROR": "ERROR:   ",
        "CRITICAL": "CRITICAL:",
    }

    def format(self, record):
        # Store the original levelname
        original_levelname = record.levelname
        # Replace it with the prefixed version
        record.levelname = self.levelname_to_prefix.get(
            record.levelname, record.levelname
        )
        # Create the formatted message
        formatted_message = super().format(record)
        # Restore the original levelname
        record.levelname = original_levelname
        return formatted_message


formatter = CustomFormatter(APP_FORMAT)
fileHandler = RotatingFileHandler("heating_v3.log", maxBytes=2000000, backupCount=3)
fileHandler.setFormatter(formatter)
streamHandler = logging.StreamHandler(stream=sys.stdout)
streamHandler.setFormatter(formatter)


def get_logger(name=__name__):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO if not os.getenv("DEBUG_HEATING") else logging.DEBUG)
    logger.addHandler(fileHandler)
    logger.addHandler(streamHandler)
    return logger


def log_exceptions(name=None):
    if callable(name):
        # No argument provided, arg is the function to be decorated
        fn = name
        logger = get_logger(fn.__name__)

        def logged_f(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                import traceback

                logger.error(f"{e.__class__.__name__}: {e}\n{traceback.format_exc()}")

        return logged_f
    else:
        # Logger name provided
        def real_decorator(f):
            _logger = get_logger(name)

            def logged_f(*args, **kwargs):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    import traceback

                    _logger.error(
                        f"{e.__class__.__name__}: {e}\n{traceback.format_exc()}"
                    )

            return logged_f

        return real_decorator
