"""
Unified package data model for all package managers.

Provides a common :class:`PackageInfo` dataclass and :class:`PackageStatus`
enum so that package facts can return rich, structured data instead of plain
``dict[str, set[str]]``, plus :class:`PackageFactBase` to build that data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar

from typing_extensions import override

from pyinfra.api import FactBase

from .packaging import parse_packages


class PackageStatus(Enum):
    """Status of an installed package."""

    INSTALLED = "installed"
    UPGRADEABLE = "upgradeable"
    HELD = "held"


_VERSION_PART_RE = re.compile(r"\d+|\D+")


def _version_sort_key(version: str) -> tuple[tuple[int, int | str], ...]:
    """Natural-order sort key for package version strings.

    Splits into runs of digits and non-digits; digit runs compare as integers
    so ``5.10`` sorts after ``5.2`` and ``9.0-1`` after ``9.0``. Good enough
    for rpm, dpkg and portage version strings as a cross-distro default; it
    is not a substitute for distro-specific vercmp.
    """
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in _VERSION_PART_RE.findall(version)
    )


@dataclass(frozen=True)
class PackageInfo:
    """Unified package information returned by enriched package facts.

    ``installed_versions`` holds every installed version, sorted ascending so
    the highest is last. Most package managers only ever install one version
    of a package, but rpm-family installonly packages (kernels), portage
    SLOTs and dpkg multi-arch can produce more than one. The
    :pyattr:`installed_version` property returns the highest installed
    version (or ``None`` when none are reported).
    """

    name: str
    installed_versions: tuple[str, ...] = ()
    available_version: str | None = None
    status: PackageStatus = PackageStatus.INSTALLED

    @property
    def installed_version(self) -> str | None:
        return self.installed_versions[-1] if self.installed_versions else None

    def to_json(self) -> dict[str, Any]:
        """JSON-friendly form (used by fact caching/debug output and tests)."""
        return {
            "name": self.name,
            "installed_versions": list(self.installed_versions),
            "available_version": self.available_version,
            "status": self.status.value,
        }


def build_package_map(
    installed: dict[str, set[str]],
    upgradeable: dict[str, str] | None = None,
    held: set[str] | None = None,
) -> list[PackageInfo]:
    """Build a list of :class:`PackageInfo` by combining sub-fact data.

    + installed: installed packages from a fact (name to set of versions).
    + upgradeable: packages with available upgrades (name to available version).
    + held: names of held/locked/pinned packages.

    The result is a flat ``list[PackageInfo]`` (the name lives on each
    :class:`PackageInfo`, so a name-keyed dict would just duplicate it), sorted
    by name for determinism. Versions within each entry are sorted with a
    natural-order key (digit runs as integers) so the highest version is last.
    """

    result: list[PackageInfo] = []
    _upgradeable = upgradeable or {}
    _held = held or set()

    for name in sorted(installed):
        sorted_versions = tuple(sorted(installed[name], key=_version_sort_key))

        if name in _held:
            status = PackageStatus.HELD
        elif name in _upgradeable:
            status = PackageStatus.UPGRADEABLE
        else:
            status = PackageStatus.INSTALLED

        result.append(
            PackageInfo(
                name=name,
                installed_versions=sorted_versions,
                available_version=_upgradeable.get(name),
                status=status,
            )
        )

    return result


class PackageFactBase(FactBase["list[PackageInfo]"]):
    """Base for "installed packages" facts that return a ``list[PackageInfo]``
    instead of the legacy ``dict[str, set[str]]``.

    Subclasses set ``regex`` (an installed ``name``/``version`` regex parsed by
    :func:`parse_packages`) and may set ``upgradeable_fact`` / ``locked_fact``.
    Their ``command()`` calls :meth:`gather` to resolve those sub-facts for the
    current host, and :meth:`process` combines everything via
    :func:`build_package_map`.

    ``command()`` is intentionally left to the subclass: the fact test harness
    introspects its argument names, so per-manager arguments such as ``jail``
    must appear in the real signature rather than be hidden behind ``**kwargs``.
    """

    upgradeable_fact: ClassVar[type[FactBase] | None] = None
    locked_fact: ClassVar[type[FactBase] | None] = None
    regex: ClassVar[str]
    default = list

    def gather(self, **kwargs: Any) -> None:
        """Resolve the upgradeable/locked sub-facts for the current host.

        Call this from the subclass ``command()`` so the results are available
        to :meth:`process`. Extra kwargs (e.g. ``jail``) are forwarded to the
        sub-facts unchanged.
        """
        from pyinfra import host

        self._upgradeable = (
            host.get_fact(self.upgradeable_fact, **kwargs) if self.upgradeable_fact else {}
        )
        self._held = host.get_fact(self.locked_fact, **kwargs) if self.locked_fact else set()

    @override
    def process(self, output: list[str]) -> list[PackageInfo]:
        return build_package_map(
            parse_packages(self.regex, output),
            getattr(self, "_upgradeable", None),
            getattr(self, "_held", None),
        )
