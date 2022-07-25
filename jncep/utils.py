from collections import deque
from datetime import timezone
import inspect
import logging
import os
import re
import sys
import unicodedata

from addict import Dict as Addict
import rich.console
import rich.theme

logger = logging.getLogger(__name__)


def setup_logging(is_debug, package=__package__):
    format = "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
    if not logging.getLogger().handlers:
        # coloredlogs is used
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=format)
    else:
        # Colored_logs has installed its own handler but not configured the way
        # I want
        logging.getLogger().handlers[0].formatter.datefmt = "%Y-%m-%d,%H:%M:%S,%f"
        # coloredlogs changes the level of the handler
        logging.getLogger().handlers[0].setLevel(logging.NOTSET)

    logger = logging.getLogger(package)
    if is_debug:
        logger.setLevel(logging.DEBUG)
        # keep debug console (ie logging)
        # or issues mixing the print and the logs with Rich
    else:
        logger.setLevel(logging.INFO)
        getConsole().console = RichConsole()


def tryint(val):
    try:
        return int(val)
    except Exception:
        return None


def to_yn(b):
    return "yes" if b else "no"


def to_safe_filename(name):
    name = "".join(
        c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn"
    )
    safe = re.sub(r"[^0-9a-zA-Z_]+", "_", name)
    safe = safe.strip("_")
    return safe


def to_max_len_filepath(original_path):
    max_len = 255
    if len(original_path) > max_len:
        # too long for windows
        # TODO also check dir path => if too long, display useful error message
        path, ext = os.path.splitext(original_path)
        max_path_len = max_len - len(ext)
        short_path = path[:max_path_len]
        original_path = short_path + ext

        counter = 0
        while os.path.exists(original_path):
            # find one that doesn't exist
            counter += 1
            suffix = f" ({counter})"
            max_path_len = max_len - len(ext) - len(suffix)
            short_path = path[:max_path_len]
            original_path = short_path + suffix + ext

    return original_path


def module_info():
    # for main module : its __name__ is __main__
    # so find out its real name
    frm = inspect.stack()[1]
    mod = inspect.getmodule(frm[0])
    return mod.__spec__.name


def isoformat_with_z(d):
    # like the date format used by the JNC API
    if d.tzinfo != timezone.utc:
        # just in case but shouldn't happen : only date in UTC is used in the code
        raise ValueError("Date not in UTC !")
    return d.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def deep_freeze(data):
    if type(data) is Addict:
        data.freeze()
        for value in data.values():
            if type(value) is list:
                for v in value:
                    deep_freeze(v)


rich_theme = rich.theme.Theme(
    {
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "highlight": "magenta",
    }
)


class RichConsole:
    def __init__(self):
        self.console = rich.console.Console(
            highlight=False, theme=rich_theme, soft_wrap=True
        )
        self._status = None

    def info(self, *args, **kwargs):
        self.console.print(*args, **kwargs)

    def warning(self, *args, **kwargs):
        self.console.print(*args, **{"style": "warning", **kwargs})

    def error(self, *args, **kwargs):
        self.console.print(*args, **{"style": "error", **kwargs})

    def status(self, message, **kwargs_spinner_style):
        if not self._status:
            default = {}
            if self.is_advanced():
                default = {"spinner": "dots"}
            else:
                default = {"spinner": "line", "refresh_per_second": 6}
            st_args = {**default, **kwargs_spinner_style}

            self._status = self.console.status(message, **st_args)
            self._status.start()
        else:
            self._status.update(message, **kwargs_spinner_style)

    def stop_status(self):
        if self._status:
            self._status.stop()

    def log(self, *args, **kwargs):
        self.console.log(*args, **kwargs)

    def is_advanced(self):
        return not self.console.legacy_windows


class DebugConsole:
    def __init__(self):
        pass

    def info(self, message, *args, **kwargs):
        logger.info(message)

    def warning(self, message, *args, **kwargs):
        logger.warning(message)

    def error(self, message, *args, **kwargs):
        logger.error(message)

    def status(self, message, **kwargs_spinner_style):
        logger.warning(message)

    def stop_status(self):
        pass

    def log(self, message, *args, **kwargs):
        logger.info(message)

    def is_advanced(self):
        return False


class RootConsole:
    def __init__(self):
        # default
        self.console = DebugConsole()
        self.stack_status = deque()

    def info(self, message, *args, **kwargs):
        self.console.info(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self.console.warning(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self.console.error(message, *args, **kwargs)

    def status(self, message, clear=True, **kwargs_spinner_style):
        if clear:
            self.stack_status.clear()
        self.stack_status.append((message, kwargs_spinner_style))
        self.console.status(message, **kwargs_spinner_style)

    def pop_status(self):
        self.stack_status.pop()
        message, kwargs_spinner_style = self.stack_status[-1]
        self.console.status(message, **kwargs_spinner_style)

    def stop_status(self):
        self.console.stop_status()

    def log(self, message, *args, **kwargs):
        self.console.log(message, *args, **kwargs)

    def is_advanced(self):
        return self.console.is_advanced()


ROOT_CONSOLE = RootConsole()


def getConsole():
    return ROOT_CONSOLE
