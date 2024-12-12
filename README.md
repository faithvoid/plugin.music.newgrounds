# plugin.music.newgrounds
Basic Newgrounds Audio Portal client for XBMC.

[](release/default.tbn)

Requires the latest version of XBMC (3.6-DEV-r33046 or later) from Xbins (as it has crucial TLS/SSL updates that allow this script to work). Sources are NOT provided (outside of one public domain movie source) and must be input manually!


## How To Use:
- Download latest release file, or "release" folder from the repository (delete update.zip if you do!).
- Extract the .zip file.
- Copy the "Newgrounds" folder to Q:/plugins/music
- Run the add-on and enjoy!

## Issues:
- Thumbnails are currently broken as Newgrounds uses .webp, which XBMC doesn't support.
- HTML sometimes shows up in search strings. Need to sanitize artist names and titles a bit better.
- You tell me.

## TODO:
- Implement pagination.
- Get rid of dialog box that appears before every track.
- Implement better filename sanitization
- Incorporate update script.
