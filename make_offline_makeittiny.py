#!/usr/bin/env python3
"""Build a self-contained, offline copy of Make It Tiny.

Make It Tiny normally ships as make-it-tiny.html plus sibling files: the codec
bundle (mit-codecs.min.js) and four WebAssembly binaries. Because those load over
the network, the app must be served over http(s) -- browsers block Worker/module
fetches from file:// URLs.

This script folds all of that into one file. It:

  1. reads mit-codecs.min.js and rewrites every reference to a .wasm binary into an
     inline `data:` URL (so the codec never fetches a sibling file), then
  2. drops that rewritten source into the #embeddedCodec placeholder in
     make-it-tiny.html (between the MIT-OFFLINE:codec-source START/END markers).

The result, make-it-tiny-offline.html, is a single ~5 MB file that runs by
double-clicking it -- no web server, fully offline. The original make-it-tiny.html
is left untouched.

Usage:
    python3 make_offline_makeittiny.py

Run it from the repo directory (or anywhere -- paths are resolved relative to this
script's location).
"""

import base64
import pathlib
import re
import sys

# All inputs/outputs live beside this script.
HERE = pathlib.Path(__file__).resolve().parent

SOURCE_HTML = HERE / "make-it-tiny.html"
CODEC_JS = HERE / "mit-codecs.min.js"
OUTPUT_HTML = HERE / "make-it-tiny-offline.html"

# The .wasm binaries the codec bundle loads by (quoted) filename. Each is inlined
# as a data: URL so the offline build never has to fetch a sibling file.
WASM_FILES = [
    "webp_enc.wasm",
    "mozjpeg_enc.wasm",
    "avif_enc.wasm",
    "squoosh_oxipng_bg.wasm",
]

# The codec bundle fetches wasm only through this map: qn={webp:"webp_enc.wasm",...}.
# (The filenames also appear in each Emscripten module's dead wasmBinaryFile, which is
# never read because the bundle supplies its own instantiateWasm.) We rewrite ONLY the
# map, so every binary is inlined exactly once instead of once per textual occurrence.
QN_MAP_RE = re.compile(r"qn=\{[^}]*\}")

# Three Emscripten modules (webp/jpeg/avif) eagerly evaluate, during init,
#   dr = new URL("<name>.wasm", import.meta.url).href
# to locate their sibling .wasm. That path is dead in this bundle (each module is given
# its own instantiateWasm, so dr is never fetched), but the expression still runs -- and
# inside the offline build's Blob module Worker, import.meta.url is not a usable base, so
# `new URL(...)` throws "<name>.wasm is not a valid URL" before any encoding happens. We
# strip these external-file lookups, leaving dr as a harmless (never-fetched) string, so
# the offline build never even constructs a URL to an external .wasm. (The oxipng module
# has a similar reference but behind a `typeof $ > "u"` guard that is never true here.)
DEAD_WASM_URL_RE = re.compile(r'new URL\("([a-z_]+\.wasm)",import\.meta\.url\)\.href')

# The build flag in make-it-tiny.html. False in the source; the offline build flips it to
# true so the app runs the embedded codec (and never fetches the sibling files).
FLAG_FALSE = "const EMBEDDED_OFFLINE = false; /* MIT-OFFLINE:flag */"
FLAG_TRUE = "const EMBEDDED_OFFLINE = true; /* MIT-OFFLINE:flag */"

# The placeholder <script> element the codec source is injected into. Matched
# non-greedily so an (expected) empty element is replaced, and re-running on an
# already-built file would just replace it again.
PLACEHOLDER_RE = re.compile(
    r'(<script type="text/plain" id="embeddedCodec">)(.*?)(</script>)',
    re.DOTALL,
)


def die(message):
    sys.exit("error: " + message)


def wasm_data_url(path):
    """Return a data: URL holding the base64-encoded contents of a .wasm file."""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return "data:application/wasm;base64," + encoded


def build_embedded_codec():
    """Read the codec bundle and inline each .wasm reference as a data: URL."""
    if not CODEC_JS.exists():
        die(f"{CODEC_JS.name} not found next to this script")

    source = CODEC_JS.read_text(encoding="utf-8")

    match = QN_MAP_RE.search(source)
    if not match:
        die(f"could not find the wasm map (qn={{...}}) in {CODEC_JS.name}; bundle changed?")

    qn_map = match.group(0)
    for name in WASM_FILES:
        path = HERE / name
        if not path.exists():
            die(f"{name} not found next to this script")

        quoted = f'"{name}"'
        if quoted not in qn_map:
            die(f"expected {quoted} in the wasm map of {CODEC_JS.name}; bundle changed?")

        qn_map = qn_map.replace(quoted, f'"{wasm_data_url(path)}"')
        print(f"  inlined {name} ({path.stat().st_size:,} bytes)")

    # Substitute the rewritten map back in (function replacement so the base64 payload
    # isn't scanned for regex backreferences).
    source = source[: match.start()] + qn_map + source[match.end() :]

    # Strip the dead external-.wasm URL lookups that throw in a Blob module Worker.
    source, dead_count = DEAD_WASM_URL_RE.subn(lambda m: f'"{m.group(1)}"', source)
    if dead_count == 0:
        die(f"expected external-wasm URL lookups in {CODEC_JS.name}; bundle changed?")
    print(f"  neutralized {dead_count} external-wasm URL lookup(s)")

    return source


def main():
    if not SOURCE_HTML.exists():
        die(f"{SOURCE_HTML.name} not found next to this script")

    html = SOURCE_HTML.read_text(encoding="utf-8")

    if not PLACEHOLDER_RE.search(html):
        die(
            'could not find the <script type="text/plain" id="embeddedCodec"> '
            "injection point in " + SOURCE_HTML.name
        )

    if FLAG_FALSE not in html:
        die(f"could not find the EMBEDDED_OFFLINE build flag in {SOURCE_HTML.name}")
    html = html.replace(FLAG_FALSE, FLAG_TRUE, 1)

    print("Inlining codec + wasm...")
    embedded = build_embedded_codec()

    # A raw-text <script> element ends at the first "</script"; the codec source and
    # base64 data URLs contain none, but assert it so a future codec change can't
    # silently produce a truncated, broken file.
    if "</script" in embedded.lower():
        die("codec source contains '</script'; cannot safely inline it")

    # Replacement text is passed as a function so backslashes/`\g` in the codec
    # source aren't interpreted as regex group references.
    result = PLACEHOLDER_RE.sub(lambda m: m.group(1) + embedded + m.group(3), html, count=1)

    OUTPUT_HTML.write_text(result, encoding="utf-8")
    print(f"\nWrote {OUTPUT_HTML.name} ({OUTPUT_HTML.stat().st_size:,} bytes)")
    print("Open it directly (file://) -- no web server needed.")


if __name__ == "__main__":
    main()
