"""
Manage FreeBSD packages.
"""

from __future__ import annotations


from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.facts.freebsd import PkgLockedPackages, PkgPackage, PkgPackages

from pyinfra.operations.util.packaging import ensure_packages


@operation()
def update(jail: str | None = None, force: bool = False, reponame: str | None = None):
    """
    Update the local catalogues of the enabled package repositories.

    + jail: See ``-j`` in ``pkg(8)``.
    + force: See ``-f`` in ``pkg-update(8)``.
    + reponame: See ``-r`` in ``pkg-update(8)``

    **Examples:**

    .. code:: python

        # host
        pkg.update()

        # jail
        pkg.update(
            jail="nginx"
        )
    """

    args: list[str | QuoteString] = []

    args.append("pkg")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["update"])

    if force:
        args.append("-f")

    if reponame is not None:
        args.extend(["-r", QuoteString(reponame)])

    yield StringCommand(*args)


@operation()
def upgrade(jail: str | None = None, force: bool = False, reponame: str | None = None):
    """
    Perform upgrades of package software distributions.

    + jail: See ``-j`` in ``pkg(8)``.
    + force: See ``-f`` in ``pkg-upgrade(8)``.
    + reponame: See ``-r`` in ``pkg-upgrade(8)``.

    **Examples:**

    .. code:: python

        # host
        pkg.upgrade()

        # jail
        pkg.upgrade(
            jail="nginx"
        )
    """

    args: list[str | QuoteString] = []

    args.append("pkg")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["upgrade", "-y"])

    if force:
        args.append("-f")

    if reponame is not None:
        args.extend(["-r", QuoteString(reponame)])

    yield StringCommand(*args)


@operation()
def install(package: str, jail: str | None = None, reponame: str | None = None):
    """
    Install packages from remote packages repositories or local archives.

    + package: Package to install.
    + jail: See ``-j`` in ``pkg(8)``.
    + reponame: See ``-r`` in ``pkg-install(8)``.

    **Example:**

    .. code:: python

        pkg.install("nginx")
    """

    if host.get_fact(PkgPackage, package=package, jail=jail):
        host.noop(f"Package '{package}' already installed")
        return

    args: list[str | QuoteString] = []

    args.append("pkg")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["install", "-y"])

    if reponame is not None:
        args.extend(["-r", QuoteString(reponame)])

    args.extend(["--", QuoteString(package)])

    yield StringCommand(*args)


@operation()
def remove(package: str, jail: str | None = None):
    """
    Deletes packages from the database and the system.

    + package: Package to remove.
    + jail: See ``-j`` in ``pkg(8)``.

    **Example:**

    .. code:: python

        pkg.remove("nginx")
    """

    if not host.get_fact(PkgPackage, package=package, jail=jail):
        host.noop(f"Package '{package}' cannot be found")
        return

    args: list[str | QuoteString] = []

    args.append("pkg")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["remove", "-y"])

    args.extend(["--", QuoteString(package)])

    yield StringCommand(*args)


@operation()
def autoremove(jail: str | None = None):
    """
    Remove orphan packages.

    + jail: See ``-j`` in ``pkg(8)``.

    **Example:**

    .. code:: python

        pkg.autoremove()
    """

    args: list[str | QuoteString] = []

    args.append("pkg")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["autoremove", "-y"])

    yield StringCommand(*args)


@operation()
def clean(all_pkg: bool = False, jail: str | None = None):
    """
    Clean the local cache of fetched remote packages.

    + all_pkg: See ``-a`` in ``pkg-clean(8)``.
    + jail: See ``-j`` in ``pkg(8)``.

    **Example:**

    .. code:: python

        pkg.clean(
            all_pkg=True
        )
    """

    args: list[str | QuoteString] = []

    args.append("pkg")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["clean", "-y"])

    if all_pkg:
        args.append("-a")

    yield StringCommand(*args)


@operation()
def packages(
    packages: str | list[str] | None = None,
    present: bool = True,
    latest: bool = False,
    jail: str | None = None,
    reponame: str | None = None,
):
    """
    Install/remove/upgrade multiple packages, checking installed, upgradeable
    and locked state. Locked packages are never changed, and ``latest`` only
    upgrades packages that actually have an available upgrade.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + jail: See ``-j`` in ``pkg(8)``.
    + reponame: See ``-r`` in ``pkg-install(8)``/``pkg-upgrade(8)``.

    **Example:**

    .. code:: python

        from pyinfra.operations import freebsd

        freebsd.pkg.packages(
            name="Install nginx and vim",
            packages=["nginx", "vim"],
        )
    """

    def _command(*action: str | QuoteString, with_repo: bool = False) -> StringCommand:
        bits: list[str | QuoteString] = ["pkg"]
        if jail is not None:
            bits.extend(["-j", QuoteString(jail)])
        bits.extend(action)
        if with_repo and reponame is not None:
            bits.extend(["-r", QuoteString(reponame)])
        bits.append("--")
        return StringCommand(*bits)

    yield from ensure_packages(
        host,
        packages,
        host.get_fact(PkgPackages, jail=jail),
        present,
        install_command=_command("install", "-y", with_repo=True),
        uninstall_command=_command("delete", "-y"),
        latest=latest,
        upgrade_command=_command("upgrade", "-y", with_repo=True),
    )


@operation()
def lock(package: str, jail: str | None = None):
    """
    Lock a package to prevent it being reinstalled, upgraded or removed.

    + package: Package to lock.
    + jail: See ``-j`` in ``pkg(8)``.

    **Example:**

    .. code:: python

        pkg.lock("nginx")
    """

    if package in host.get_fact(PkgLockedPackages, jail=jail):
        host.noop(f"Package '{package}' is already locked")
        return

    args: list[str | QuoteString] = ["pkg"]

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["lock", "-y", "--", QuoteString(package)])

    yield StringCommand(*args)


@operation()
def unlock(package: str, jail: str | None = None):
    """
    Unlock a package previously locked with ``pkg.lock``.

    + package: Package to unlock.
    + jail: See ``-j`` in ``pkg(8)``.

    **Example:**

    .. code:: python

        pkg.unlock("nginx")
    """

    if package not in host.get_fact(PkgLockedPackages, jail=jail):
        host.noop(f"Package '{package}' is not locked")
        return

    args: list[str | QuoteString] = ["pkg"]

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["unlock", "-y", "--", QuoteString(package)])

    yield StringCommand(*args)
