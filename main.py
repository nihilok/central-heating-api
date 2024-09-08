import sys

import uvicorn

from application.config.logging import LOGGING_CONFIG

if __name__ == "__main__":

    run_args = ["application.app:app"]
    run_kwargs = {"port": 8080}

    if len(cl_args := sys.argv[1:]) > 0:
        if cl_args[0] == "dev":
            run_kwargs["host"] = "0.0.0.0"
            run_kwargs["reload"] = True
            run_kwargs["reload_dirs"] = ["./application", "./data", "./authentication"]

    uvicorn.run(*run_args, **run_kwargs, log_config=LOGGING_CONFIG)
