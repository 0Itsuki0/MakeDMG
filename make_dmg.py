#!/usr/bin/env python3
"""
make_dmg.py - DMG builder using dmgbuild (macOS Tahoe compatible)

Usage:
    python3 make_dmg.py

Dependencies are auto-installed on first run (dmgbuild, Pillow).

All paths in the Configuration section are relative to this script's directory
unless they start with / (absolute path), e.g.:
    "background.jpg"        → same folder as this script
    "assets/background.jpg" → subfolder
    "/Users/me/bg.jpg"      → absolute path
"""
import os, sys, subprocess, tempfile

def auto_install(package_name):
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", package_name,
        "--quiet", "--break-system-packages",
    ])

try:
    import dmgbuild
except ImportError:
    auto_install("dmgbuild")
    import dmgbuild

try:
    from PIL import Image
except ImportError:
    auto_install("Pillow")
    from PIL import Image

# ── Configuration ────────────────────────────────────────────────────────────
# Full settings reference: https://dmgbuild.readthedocs.io/en/latest/settings.html

# Output filename (saved next to this script)
OUTPUT_DMG_NAME       = "Pikachu-Installer.dmg"

# Volume name shown in the Finder window title and sidebar
VOLUME_NAME           = "Pikachu Installer"

# Files/folders to include in the DMG.
# - Paths are relative to this script (or absolute)
# - Plain folders are walked recursively
# - Bundles (.app, .framework, .plugin, .kext, .bundle) are copied as-is
SOURCE_FILES          = ["source"]

# Symlinks to create inside the DMG.
# The key is the name shown in Finder; the value is the target path.
# {"Applications": "/Applications"} creates the standard drag-to-install arrow.
SYMLINKS              = {"Applications": "/Applications"}

# Background image for the Finder window.
# - Selected automatically based on the system's Dark/Light Mode at build time
# - Supports JPEG and PNG (PNG is lossless)
# - Set to None to use BACKGROUND_FILL_COLOR only
BACKGROUND_FILE_DARK  = "background.jpg"   # used when system is in Dark Mode
BACKGROUND_FILE_LIGHT = "background.jpg"   # used when system is in Light Mode

# Solid color shown outside the background image when the window is resized.
# Accepts any hex color string, e.g. "#1a1a2e". Set to None for white.
BACKGROUND_FILL_COLOR = "#000000"

# Icon shown on the DMG file itself in Finder (not inside the installer).
# JPEG and PNG are accepted and auto-converted to ICNS.
# Set to None to use the macOS default disk image icon.
VOLUME_ICON_FILE      = "icon.jpeg"

# Position of the Finder window on screen when the DMG is opened, in points.
# (left, top) from the top-left corner of the screen.
WINDOW_POSITION       = (200, 120)

# Size of the Finder window in points. (width, height)
WINDOW_SIZE           = (500, 300)

# Size of icons inside the window, in points (e.g. 64, 80, 100, 128)
ICON_SIZE             = 80

# Size of icon label text, in points (e.g. 11, 12, 13)
TEXT_SIZE             = 12

# Icon positions inside the Finder window, in points from the top-left.
# Keys must match the exact filename (or symlink name) as it appears in the DMG.
ICON_POSITIONS = {
    "pikachu.png":  (150, 150),
    "Applications": (350, 150),
}

# Filenames whose extensions are hidden in Finder (e.g. shows "pikachu" not "pikachu.png")
HIDE_EXTENSIONS = ["pikachu.png"]

# Canvas size in pixels for the background image.
# The background image is pasted at the top-left; the rest is filled with
# BACKGROUND_FILL_COLOR. Make this large enough to cover any window resize.
BACKGROUND_CANVAS_SIZE = (6000, 4000)
# ────────────────────────────────────────────────────────────────────────────


def convert_image_to_icns(source_path: str, output_directory: str) -> str:
    """Convert any image to .icns using sips + iconutil."""
    iconset_directory = os.path.join(output_directory, "vol.iconset")
    icns_path         = os.path.join(output_directory, "vol.icns")
    os.makedirs(iconset_directory)
    for base_size in [16, 32, 128, 256, 512]:
        for scale_factor, filename_suffix in [(1, ""), (2, "@2x")]:
            pixel_size  = base_size * scale_factor
            output_icon = os.path.join(iconset_directory, f"icon_{base_size}x{base_size}{filename_suffix}.png")
            subprocess.run(
                ["sips", "-z", str(pixel_size), str(pixel_size), source_path,
                 "--setProperty", "format", "png", "--out", output_icon],
                check=True, capture_output=True,
            )
    subprocess.run(["iconutil", "-c", "icns", iconset_directory, "-o", icns_path], check=True)
    return icns_path


def prepare_background(source_path: str, fill_color: str,
                        canvas_size: tuple, output_directory: str) -> str:
    """
    Paste the background image onto a large solid-color canvas so resizing
    the window shows the fill color instead of white.
    PNG sources are saved losslessly; JPEG sources at quality 95.
    """
    file_extension   = os.path.splitext(source_path)[1].lower()
    use_png          = file_extension == ".png"
    output_filename  = f"background.{'png' if use_png else 'jpg'}"
    output_path      = os.path.join(output_directory, output_filename)

    background_image = Image.open(source_path).convert("RGBA" if use_png else "RGB")

    canvas = Image.new("RGBA" if use_png else "RGB", canvas_size, fill_color)
    canvas.paste(background_image, (0, 0))

    if use_png:
        canvas.save(output_path, "PNG")
    else:
        canvas.save(output_path, "JPEG", quality=95)
    return output_path


def is_dark_mode() -> bool:
    """Return True if the system is currently in Dark Mode."""
    result = subprocess.run(
        ["defaults", "read", "-g", "AppleInterfaceStyle"],
        capture_output=True, text=True,
    )
    return result.stdout.strip().lower() == "dark"


def main():
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # Bundles are treated as single units and not recursed into
    bundle_extensions = {".app", ".framework", ".plugin", ".kext", ".bundle"}

    def collect_files(entry_path: str) -> list:
        if not os.path.isdir(entry_path):
            return [entry_path]
        if os.path.splitext(entry_path)[1].lower() in bundle_extensions:
            return [entry_path]
        collected = []
        for child_name in os.listdir(entry_path):
            child_path = os.path.join(entry_path, child_name)
            collected.extend(collect_files(child_path))
        return collected

    # Resolve all source paths (relative paths are resolved from the script directory)
    absolute_source_files = []
    for source_entry in SOURCE_FILES:
        absolute_entry = os.path.join(script_directory, source_entry) if not os.path.isabs(source_entry) else source_entry
        absolute_source_files.extend(collect_files(absolute_entry))

    selected_background_file = BACKGROUND_FILE_DARK if is_dark_mode() else BACKGROUND_FILE_LIGHT
    absolute_background_src  = (
        os.path.join(script_directory, selected_background_file)
        if selected_background_file and not os.path.isabs(selected_background_file)
        else selected_background_file
    )
    absolute_volume_icon_src = (
        os.path.join(script_directory, VOLUME_ICON_FILE)
        if VOLUME_ICON_FILE and not os.path.isabs(VOLUME_ICON_FILE)
        else VOLUME_ICON_FILE
    )

    output_path = os.path.join(script_directory, OUTPUT_DMG_NAME)
    if os.path.exists(output_path):
        os.remove(output_path)

    with tempfile.TemporaryDirectory() as temp_directory:
        prepared_background = None
        if absolute_background_src:
            prepared_background = prepare_background(
                absolute_background_src,
                BACKGROUND_FILL_COLOR or "#ffffff",
                BACKGROUND_CANVAS_SIZE,
                temp_directory,
            )
        elif BACKGROUND_FILL_COLOR:
            prepared_background = BACKGROUND_FILL_COLOR

        converted_volume_icon = None
        if absolute_volume_icon_src:
            converted_volume_icon = convert_image_to_icns(absolute_volume_icon_src, temp_directory)

        settings = {
            "files":             absolute_source_files,
            "symlinks":          SYMLINKS,
            "icon_locations":    ICON_POSITIONS,
            "hide_extensions":   HIDE_EXTENSIONS,
            "background":        prepared_background,
            "window_rect":       (WINDOW_POSITION, WINDOW_SIZE),
            "default_view":      "icon-view",
            "show_status_bar":   False,
            "show_tab_view":     False,
            "show_toolbar":      False,
            "show_pathbar":      False,
            "show_sidebar":      False,
            "icon_size":         ICON_SIZE,
            "show_icon_preview": True,
            "text_size":         TEXT_SIZE,
            "format":            "UDZO",
            "filesystem":        "HFS+",
        }
        if converted_volume_icon:
            settings["icon"] = converted_volume_icon

        dmgbuild.build_dmg(
            filename=output_path,
            volume_name=VOLUME_NAME,
            settings=settings,
        )

    print(f"Done: {output_path}")


if __name__ == "__main__":
    main()
