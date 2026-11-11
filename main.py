"""Start the JadivCode IDE from a checkout: python3 main.py [file.jdv]"""

import sys

from jadivcode_ide.launch import launch

if __name__ == "__main__":
    sys.exit(launch())
