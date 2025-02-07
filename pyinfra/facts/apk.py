from __future__ import annotations

from pyinfra.api import FactBase

from .util.packaging import parse_packages

APK_REGEX = r"^([a-zA-Z0-9\-_]+)-([0-9\.]+\-?[a-z0-9]*)\s"


class ApkPackages(FactBase):
    """
    Returns a dict of installed apk packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    def command(self) -> str:
        return "apk list --installed"

    def requires_command(self) -> str:
        return "apk"

    default = dict

    def process(self, output):
        return parse_packages(APK_REGEX, output)
