"""Checks for and installs updates of JadivCode and the JadivCode IDE.

An update is available when the version number on the main branch of the
project's repository is higher than the installed one.  Updating runs the
project's own installer, the same one used for the first installation.

Nothing here touches the window toolkit, so the logic is easy to test.
"""

import os
import re
import urllib.error
import urllib.request

RAW = "https://raw.githubusercontent.com/JadivCode"
TIMEOUT = 6

#: name -> (version file, installer, folder name under ~/.local/share)
PRODUCTS = {
    "JadivCode": (f"{RAW}/jadivcode/main/jadivcode/__init__.py",
                  f"{RAW}/jadivcode/main/install.sh", "jadivcode"),
    "JadivCode IDE": (f"{RAW}/jadivcode-ide/main/jadivcode_ide/__init__.py",
                      f"{RAW}/jadivcode-ide/main/install.sh", "jadivcode-ide"),
}
VERSION_RE = re.compile(r"""__version__\s*=\s*["']([0-9][0-9A-Za-z.\-+]*)["']""")
MAX_DOWNLOAD = 1024 * 1024


class UpdateError(Exception):
    """An update could not be checked or prepared."""


def parse_version(text):
    """'0.10.2' -> (0, 10, 2). Anything after the numbers is ignored."""
    numbers = []
    for part in str(text).split("."):
        match = re.match(r"\d+", part)
        if not match:
            break
        numbers.append(int(match.group()))
    return tuple(numbers)


def is_newer(remote, local):
    remote_parts, local_parts = parse_version(remote), parse_version(local)
    if not remote_parts or not local_parts:
        return False
    width = max(len(remote_parts), len(local_parts))
    pad = lambda parts: parts + (0,) * (width - len(parts))  # noqa: E731
    return pad(remote_parts) > pad(local_parts)


def download(url):
    """Download a small text file over HTTPS."""
    if not url.startswith("https://"):
        raise UpdateError("Updates are only downloaded over https")
    request = urllib.request.Request(url, headers={"User-Agent": "JadivCode-IDE"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = response.read(MAX_DOWNLOAD + 1)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise UpdateError(f"Cannot reach the update server: {getattr(exc, 'reason', exc)}")
    if len(data) > MAX_DOWNLOAD:
        raise UpdateError("The update server sent an unexpectedly large file")
    return data.decode("utf-8", "replace")


def remote_version(name, fetch=download):
    match = VERSION_RE.search(fetch(PRODUCTS[name][0]))
    if not match:
        raise UpdateError(f"Cannot read the newest version of {name}")
    return match.group(1)


def install_dir(name):
    data = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(data, PRODUCTS[name][2])


def managed(name, running_from):
    """True when this copy was put in place by the installer.

    A copy that runs from somewhere else (a git checkout, Code Master, pip)
    is updated by whatever installed it, so the IDE leaves it alone.
    """
    if not running_from:
        return False
    try:
        return os.path.samefile(running_from, install_dir(name))
    except OSError:
        return False


def check(installed, fetch=download):
    """Compare installed versions with the newest ones.

    ``installed`` maps a product name to (version, folder it runs from).
    Returns a list of dicts: name, installed, latest, newer, managed.
    """
    results = []
    for name, (version, running_from) in installed.items():
        latest = remote_version(name, fetch)
        results.append({"name": name, "installed": version, "latest": latest,
                        "newer": is_newer(latest, version),
                        "managed": managed(name, running_from)})
    return results


def summary(results):
    """One sentence describing the result of a check."""
    newer = [r for r in results if r["newer"]]
    if not newer:
        return "JadivCode and the IDE are up to date."
    parts = [f"{r['name']} {r['latest']} (you have {r['installed']})" for r in newer]
    return "Update available: " + " and ".join(parts) + "."


def installer_script(name, fetch=download):
    """Download the installer of a product and return its text."""
    text = fetch(PRODUCTS[name][1])
    if not text.startswith("#!") or "JadivCode" not in text:
        raise UpdateError(f"The installer of {name} does not look right; nothing was changed")
    return text
