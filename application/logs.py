import logging
import os
import sys
from logging.handlers import RotatingFileHandler


formatter = logging.Formatter("%(levelname)s:\t%(asctime)s - %(name)s - %(message)s")
fileHandler = RotatingFileHandler("heating_v3.log", maxBytes=200000, backupCount=3)
streamHandler = logging.StreamHandler(stream=sys.stdout)
streamHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)


def get_logger(name=__name__):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO if not os.getenv("DEBUG_HEATING") else logging.DEBUG)
    logger.addHandler(fileHandler)
    logger.addHandler(streamHandler)
    return logger


def log_exceptions(f):
    logger = get_logger(__name__)

    def logged_f(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {e}")

    return logged_f
