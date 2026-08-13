import datetime as dt
import json
import logging
import random
from typing import override
from pathlib import Path

logger = logging.getLogger("SR_city_converter")

class MyJSONFormatter(logging.Formatter):
    def __init__(self, *, fmt_keys: dict[str, str] | None = None):
        super().__init__()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}

    @override
    def format(self, record: logging.LogRecord) -> str:
        message = self._prepare_log_dict(record)
        return json.dumps(message, default=str)

    def _prepare_log_dict(self, record: logging.LogRecord):
        always_fields = {
            "message": record.getMessage(),
            "timestamp": dt.datetime.fromtimestamp(
                record.created, tz=dt.timezone.utc).isoformat(),
        }
        if record.exc_info is not None:
            always_fields["exc_info"] = self.formatException(record.exc_info)
        else:
            always_fields["exc_info"] = None
        if record.stack_info is not None:
            always_fields["stack_info"] = self.formatStack(record.stack_info)
        else:
            always_fields["stack_info"] = None

        message = {
            key: msg_val
            if (msg_val := always_fields.pop(val, None)) is not None
else getattr(record, val)
            for key, val in self.fmt_keys.items()
        }
        message.update(always_fields)
        return message


def setup_logging():
    config_file = Path("config/logger.json")
    with open(config_file) as f_in:
        config = json.load(f_in)
        config["handlers"]["file"]["filename"] += str(random.randrange(10000))
    logging.config.dictConfig(config)

def log(severity: str, message: str):
    # __debug__ is enabled if we do not run with 'python3 -O'
    if __debug__:
        match severity:
            case "debug":
                logger.debug(message)
            case "info":
                logger.info(message)
            case "warning":
                logger.warning(message)
            case "error":
                logger.error(message)
            case "critical":
                logger.critical(message)
    else:
        # in prod. No traces
        return


