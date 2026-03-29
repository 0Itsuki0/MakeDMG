# MakeDMG
A Python script for creating dmg with custom background, icon, windows, and etc.

## Run
- python3 make_dmg.py — builds the DMG in the same directory as the script


## Usage & Customization

### Content
- SOURCE_FILES — list of files/folders to include; folders are walked
recursively, .app/.framework/.plugin/.kext/.bundle are treated as single units
- SYMLINKS — symlinks to create (e.g. {"Applications": "/Applications"} for
the drag-to-install arrow)
- ICON_POSITIONS — {filename: (x, y)} pixel positions of each item in the
window
- HIDE_EXTENSIONS — list of filenames whose extensions are hidden in Finder

### Window
- VOLUME_NAME — title shown in the Finder window and sidebar
- WINDOW_POSITION — (left, top) position of the window on screen when opened
- WINDOW_SIZE — (width, height) of the Finder window in points
- ICON_SIZE / TEXT_SIZE — icon and label sizes in points

### Background
- BACKGROUND_FILE_DARK / BACKGROUND_FILE_LIGHT — background image selected
automatically based on system Dark/Light Mode at build time
- BACKGROUND_FILL_COLOR — hex color filling the canvas outside the image
(prevents white showing when window is resized)
- BACKGROUND_CANVAS_SIZE — canvas size in pixels; make this larger than any
expected window resize

### Volume icon
- VOLUME_ICON_FILE — image shown on the DMG file itself (JPEG/PNG,
auto-converted to ICNS); set to None to use default

### Output
- OUTPUT_DMG_NAME — filename of the generated DMG; existing file is
overwritten automatically
