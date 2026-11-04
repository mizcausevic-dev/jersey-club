# Renderer metadata correction

The original release's preview description omitted the renderer's sample clamp
and its patch recipe described an approximate role target that was not measured.
The current recipe records the actual role multipliers and velocity scaling;
the preview manifest records the clamp, PCM conversion and MP3 encoding.
The ZIP includes the corrected recipe. The MIDI and preview audio were not
changed. The original `v1.0.0` tag was not moved and retains its original
contents; this correction is on `main` after that tag.

Build-metadata source hashes describe the generator at the original build, not
the documentation-only edited generator currently on `main`. The validation
report and checksums describe the corrected files.
