"""Build the native desktop app with PyInstaller.

Usage::

    pip install -e ".[build]"
    python build.py              # one-folder app in dist/ (recommended)
    python build.py --onefile    # single executable (slower start, more AV flags)
    python build.py --archive    # also zip/tar the result for distribution

The default is ``--onedir``: it starts instantly (nothing is unpacked at
launch), triggers far fewer antivirus false positives than a self-extracting
single file, and produces a proper ``.app`` bundle on macOS.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
ASSETS_DIR = SRC_DIR / "passgen" / "gui" / "assets"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
APP_NAME = "SecurePasswordGenerator"
BUNDLE_ID = "io.github.alvaroaramayochain.securepasswordgenerator"
ENTRY_SCRIPT = ROOT / "main.py"
PLATFORM_NAMES = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}
# Qt pieces pulled in by plugins that a QPainter/widgets app never uses
# (software OpenGL, Qt Quick/QML, PDF, virtual keyboard). Removing them saves
# roughly 40 MB. Only applied to one-folder builds on Windows and Linux; macOS
# ships Qt as frameworks and is left untouched.
PRUNE_PATTERNS = (
    "*opengl32sw*",
    "*Qt6Quick*",
    "*Qt6Qml*",
    "*Qt6Pdf*",
    "*Qt6VirtualKeyboard*",
    "*qtvirtualkeyboard*",
    "*qpdf*",
)
SELF_TEST_TIMEOUT_SECONDS = 60


def platform_name() -> str:
    """Return the short name of the current operating system.

    Returns:
        ``"windows"``, ``"macos"`` or ``"linux"``.
    """
    return PLATFORM_NAMES.get(platform.system(), platform.system().lower())


def icon_path() -> Path:
    """Return the icon file PyInstaller should use on this platform.

    Windows needs ``.ico``; on macOS PyInstaller converts the PNG to
    ``.icns`` with Pillow; Linux ignores the option but the PNG is harmless.

    Returns:
        The icon file path.
    """
    return ASSETS_DIR / ("icon.ico" if platform_name() == "windows" else "icon.png")


def pyinstaller_args(onefile: bool) -> list[str]:
    """Build the PyInstaller command-line arguments.

    Args:
        onefile: Produce a single executable instead of a folder.

    Returns:
        The argument list.
    """
    args = [
        str(ENTRY_SCRIPT),
        "--name", APP_NAME,
        "--windowed",
        "--onefile" if onefile else "--onedir",
        "--noconfirm",
        "--clean",
        "--paths", str(SRC_DIR),
        "--hidden-import", "passgen.gui.app",
        "--add-data", f"{ASSETS_DIR}{os.pathsep}passgen/gui/assets",
        "--icon", str(icon_path()),
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR),
    ]
    if platform_name() == "macos":
        args += ["--osx-bundle-identifier", BUNDLE_ID]
    return args


def built_artifact(onefile: bool) -> Path:
    """Return the path of the main build output.

    Args:
        onefile: Whether a single executable was built.

    Returns:
        The ``.app`` bundle on macOS, otherwise the folder or executable.
    """
    if platform_name() == "macos":
        return DIST_DIR / f"{APP_NAME}.app"
    if onefile:
        suffix = ".exe" if platform_name() == "windows" else ""
        return DIST_DIR / f"{APP_NAME}{suffix}"
    return DIST_DIR / APP_NAME


def prune(folder: Path) -> int:
    """Delete unused Qt libraries and plugins from a one-folder build.

    Args:
        folder: The build output folder.

    Returns:
        The number of bytes freed.
    """
    freed = 0
    for pattern in PRUNE_PATTERNS:
        for path in folder.rglob(pattern):
            if path.is_file():
                freed += path.stat().st_size
                path.unlink()
    return freed


def executable_path(artifact: Path, onefile: bool) -> Path:
    """Return the runnable executable inside the build output.

    Args:
        artifact: The build output (folder, executable or ``.app``).
        onefile: Whether a single executable was built.

    Returns:
        The executable path.
    """
    if platform_name() == "macos":
        return artifact / "Contents" / "MacOS" / APP_NAME
    if onefile:
        return artifact
    suffix = ".exe" if platform_name() == "windows" else ""
    return artifact / f"{APP_NAME}{suffix}"


def verify(executable: Path) -> bool:
    """Run the packaged app's offscreen self-test.

    Args:
        executable: The built executable.

    Returns:
        ``True`` if the self-test exited successfully.
    """
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    result = subprocess.run([str(executable), "--self-test"], env=env,
                            timeout=SELF_TEST_TIMEOUT_SECONDS, check=False)
    return result.returncode == 0


def archive(artifact: Path) -> Path:
    """Package the build output as ``SecurePasswordGenerator-<os>.zip|.tar.gz``.

    macOS uses ``ditto`` and Linux uses tar so the symlinks inside the Qt
    frameworks survive; Windows uses a plain zip.

    Args:
        artifact: The build output to package.

    Returns:
        The archive path.
    """
    base = DIST_DIR / f"{APP_NAME}-{platform_name()}"
    if platform_name() == "macos":
        target = base.with_suffix(".zip")
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                        str(artifact), str(target)], check=True)
        return target
    if platform_name() == "linux":
        target = base.with_name(base.name + ".tar.gz")
        with tarfile.open(target, "w:gz") as tar:
            tar.add(artifact, arcname=artifact.name)
        return target
    root_dir, base_dir = (artifact.parent, artifact.name)
    return Path(shutil.make_archive(str(base), "zip", root_dir=root_dir, base_dir=base_dir))


def main() -> int:
    """Parse arguments, run PyInstaller and optionally archive the result.

    Returns:
        The process exit code.
    """
    parser = argparse.ArgumentParser(description="Build the desktop app with PyInstaller.")
    parser.add_argument("--onefile", action="store_true",
                        help="build a single executable instead of a folder")
    parser.add_argument("--archive", action="store_true",
                        help="zip/tar the result as SecurePasswordGenerator-<os>")
    parser.add_argument("--verify", action="store_true",
                        help="run the packaged app's offscreen self-test")
    args = parser.parse_args()
    try:
        import PyInstaller.__main__ as pyinstaller
    except ImportError:
        print('PyInstaller is missing. Install it with: pip install -e ".[build]"',
              file=sys.stderr)
        return 1
    pyinstaller.run(pyinstaller_args(args.onefile))
    artifact = built_artifact(args.onefile)
    if not args.onefile and platform_name() != "macos":
        print(f"Pruned {prune(artifact) / 2**20:.1f} MB of unused Qt files")
    print(f"Built: {artifact}")
    if args.verify and not verify(executable_path(artifact, args.onefile)):
        print("Self-test of the packaged app failed.", file=sys.stderr)
        return 1
    if args.archive:
        print(f"Archive: {archive(artifact)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
