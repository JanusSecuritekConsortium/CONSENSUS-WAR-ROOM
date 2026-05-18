import logging
import json
import time

class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": time.time(),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        return json.dumps(log_entry)
