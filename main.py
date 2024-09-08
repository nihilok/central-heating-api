import sys
from datetime import datetime

import uvicorn

from application.logs import LOGGING_CONFIG

from uvicorn.logging import DefaultFormatter


class CustomFormatter(DefaultFormatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
            return s[:-3]  # Truncate microseconds to milliseconds
        else:
            t = ct.strftime(self.default_time_format)
            s = self.default_msec_format % (t, record.msecs)
            return s


if __name__ == "__main__":

    run_args = ["application.app:app"]
    run_kwargs = {"port": 8080}

    if len(cl_args := sys.argv[1:]) > 0:
        if cl_args[0] == "dev":
            run_kwargs["host"] = "0.0.0.0"
            run_kwargs["reload"] = True
            run_kwargs["reload_dirs"] = ["./application", "./data", "./authentication"]

    uvicorn.run(*run_args, **run_kwargs, log_config=LOGGING_CONFIG)
