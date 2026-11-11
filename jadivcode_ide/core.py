"""Finds the JadivCode interpreter and exposes the parts the IDE needs."""

import os
import sys


def candidate_dirs():
    data = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return [os.environ.get("JADIVCODE_HOME", ""), os.path.join(data, "jadivcode"),
            os.path.join(os.path.dirname(here), "jadivcode")]


def locate():
    """Import the jadivcode package; return the folder to put on PYTHONPATH."""
    try:
        import jadivcode  # noqa: F401
        return None
    except ImportError:
        pass
    for folder in candidate_dirs():
        if folder and os.path.isfile(os.path.join(folder, "jadivcode", "__init__.py")):
            sys.path.insert(0, folder)
            return folder
    raise ImportError(
        "JadivCode is not installed. Install it with:\n"
        "curl -fsSL https://raw.githubusercontent.com/JadivCode/jadivcode/main/install.sh | bash")


CORE_PATH = locate()

from jadivcode import FILE_EXTENSION, __version__ as CORE_VERSION  # noqa: E402
from jadivcode.checker import apply_fixes, check_source  # noqa: E402
from jadivcode.libs import LIBRARIES  # noqa: E402
from jadivcode.parser import KEYWORDS  # noqa: E402

__all__ = ["CORE_PATH", "CORE_VERSION", "FILE_EXTENSION", "KEYWORDS", "LIBRARIES",
           "apply_fixes", "check_source", "run_environment"]


def run_environment(simulate=False):
    """Environment variables for running a program from the IDE."""
    env = dict(os.environ)
    if CORE_PATH:
        env["PYTHONPATH"] = CORE_PATH + (os.pathsep + env["PYTHONPATH"]
                                         if env.get("PYTHONPATH") else "")
    env["PYTHONUNBUFFERED"] = "1"
    if simulate:
        env["JADIVCODE_GPIO"] = "sim"
        env["JADIVCODE_GUI"] = "headless"
    return env
