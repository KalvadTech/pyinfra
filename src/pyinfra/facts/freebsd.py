from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase
from pyinfra.api.command import QuoteString, StringCommand, make_formatted_string_command

from .util.packages import PackageFactBase

# Greedy package name (matches PkgPackages.regex) followed by a version that
# starts with a digit, e.g. ``vim-addon-manager-1.2`` -> ``vim-addon-manager``.
PKG_NAME_VERSION_REGEX = r"([a-zA-Z0-9_\-\+]+)-[0-9][0-9a-zA-Z\.,_]*"


class ServiceScript(FactBase):
    @override
    def command(self, srvname: str, jail: str | None = None) -> StringCommand:
        if jail is None:
            jail = ""

        return make_formatted_string_command(
            (
                "for service in `service -j {0} -l`; do "
                'if [ {1} = \\"$service\\" ]; '
                'then echo \\"$service\\"; '
                "fi; "
                "done"
            ),
            QuoteString(jail),
            QuoteString(srvname),
        )


class ServiceStatus(FactBase):
    @override
    def command(self, srvname: str, jail: str | None = None) -> StringCommand:
        if jail is None:
            jail = ""

        return make_formatted_string_command(
            ("service -j {0} {1} status > /dev/null 2>&1; if [ $? -eq 0 ]; then echo running; fi"),
            QuoteString(jail),
            QuoteString(srvname),
        )


class Sysrc(FactBase):
    @override
    def command(self, parameter: str, jail: str | None = None) -> StringCommand:
        if jail is None:
            command = make_formatted_string_command(
                ("sysrc -in -- {0} || true"), QuoteString(parameter)
            )
        else:
            command = make_formatted_string_command(
                ("sysrc -j {0} -in -- {1} || true"), QuoteString(jail), QuoteString(parameter)
            )

        return command


class PkgPackage(FactBase):
    @override
    def command(self, package: str, jail: str | None = None) -> StringCommand:
        if jail is None:
            command = make_formatted_string_command(
                ("pkg info -E -- {0} 2> /dev/null || true"), QuoteString(package)
            )
        else:
            command = make_formatted_string_command(
                ("pkg -j {0} info -E -- {1} 2> /dev/null || true"),
                QuoteString(jail),
                QuoteString(package),
            )

        return command


class PkgUpgradeablePackages(FactBase):
    """
    Returns a dict of FreeBSD pkg packages with an available upgrade
    (name to available version):

    .. code:: python

        {
            "package_name": "available_version",
        }
    """

    # ``pkg version -v -R`` lists every package with a status column; only the
    # ``<`` (older than remote) lines carry a "remote has <version>" suffix, so
    # the regex below both selects upgradeable packages and extracts the target.
    regex = re.compile(PKG_NAME_VERSION_REGEX + r"\s+<\s+.*has\s+([^)]+)\)")
    default = dict

    @override
    def command(self, jail: str | None = None) -> str | StringCommand:
        if jail is None:
            return "pkg version -v -R || true"
        return make_formatted_string_command(
            ("pkg -j {0} version -v -R || true"), QuoteString(jail)
        )

    @override
    def process(self, output: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in output:
            match = self.regex.match(line)
            if match:
                result[match.group(1)] = match.group(2).strip()
        return result


class PkgLockedPackages(FactBase):
    """
    Returns a set of locked FreeBSD pkg package names:

    .. code:: python

        {"package_name", ...}
    """

    regex = re.compile("^" + PKG_NAME_VERSION_REGEX)
    default = set

    @override
    def command(self, jail: str | None = None) -> str | StringCommand:
        if jail is None:
            return "pkg lock -lq || true"
        return make_formatted_string_command(("pkg -j {0} lock -lq || true"), QuoteString(jail))

    @override
    def process(self, output: list[str]) -> set[str]:
        result: set[str] = set()
        for line in output:
            match = self.regex.match(line)
            if match:
                result.add(match.group(1))
        return result


class PkgPackages(PackageFactBase):
    """
    Returns a list of installed FreeBSD pkg packages as :class:`PackageInfo`,
    enriched with upgradeable and locked status:

    .. code:: python

        [
            PackageInfo(
                name="package_name",
                installed_versions=("1.0",),
                available_version="1.1",
                status=PackageStatus.UPGRADEABLE,
            ),
        ]
    """

    regex = r"^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.]+)"
    upgradeable_fact = PkgUpgradeablePackages
    locked_fact = PkgLockedPackages

    @override
    def command(self, jail: str | None = None) -> str | StringCommand:
        self.gather(jail=jail)
        if jail is None:
            return "pkg info 2> /dev/null || true"
        return make_formatted_string_command(
            ("pkg -j {0} info 2> /dev/null || true"), QuoteString(jail)
        )
