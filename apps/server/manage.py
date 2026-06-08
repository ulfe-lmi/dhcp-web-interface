#!/usr/bin/env python
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    root_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(root_dir / "src"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "managed_dhcp_server.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
