from __future__ import annotations

import re
from typing import Iterable

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages

# Source: https://superuser.com/a/1472405
# Modified to return version and release inside a single group and removed extra capturing groups
APK_REGEX = r"(.+)-([^-]+-r[^-]+) \S+ \{\S+\} \(.+?\)"

# Regex for parsing upgradable packages from 'apk list -u'
# Captures: package_name, new_version, old_version
APK_UPGRADABLE_REGEX = r"(.+)-([^-]+-r[^-]+) \S+ \{\S+\} \(.+?\) \[upgradable from: \1-([^-]+-r[^-]+)\]"


class ApkPackages(FactBase):
    """
    Returns a dict of installed apk packages with upgrade information:

    .. code:: python

        {
            "package_name": {
                "status": "installed/upgradable/orphaned",
                "version_installed": "version_number",
                "version_available": "version_number" or None
            }
        }
    """

    @override
    def command(self) -> str:
        return "apk list --installed && echo '---SEPARATOR---' && apk list -u"

    @override
    def requires_command(self) -> str:
        return "apk"

    default = dict

    @override
    def process(self, output):
        packages: dict[str, dict[str, str | None]] = {}
        separator = "---SEPARATOR---"
        current_section = "installed"

        for line in output:
            if separator in line:
                current_section = "upgradable"
                continue

            if current_section == "installed":
                matches = re.match(APK_REGEX, line)
                if matches:
                    name = matches.group(1)
                    version = matches.group(2)
                    packages[name] = {
                        "status": "installed",
                        "version_installed": version,
                        "version_available": None,
                    }
            else:  # upgradable section
                matches = re.match(APK_UPGRADABLE_REGEX, line)
                if matches:
                    name = matches.group(1)
                    new_version = matches.group(2)
                    old_version = matches.group(3)

                    if name in packages:
                        # Update existing package to mark as upgradable
                        packages[name]["status"] = "upgradable"
                        packages[name]["version_available"] = new_version
        return packages
