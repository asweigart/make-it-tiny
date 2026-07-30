# Make It Tiny

A free, **offline** image optimizer that runs entirely in your web browser. Drag,
drop, or paste images to shrink their file size — **nothing is ever uploaded**. All
encoding happens locally in your browser, so your images never leave your device.

By [Al Sweigart](https://inventwithpython.com).

## Features

- **Formats:** encode to **WebP**, **JPEG**, **PNG**, or **AVIF** — or keep each
  image's **Original** format (pasted images become WebP).
- **Quality control:** a quality slider for lossy formats, and an "Allow lossy
  optimization" option for formats that can be lossless (PNG/WebP/AVIF/Original).
- **Resize:** optionally scale images down to fit, by max pixel dimensions or by
  percentage.
- **Strip metadata:** remove EXIF/GPS and other metadata (or keep it — EXIF is
  re-embedded from the source by default).
- **Batch friendly:** add many images at once; download them all as a `.zip` or as
  separate files, reprocess with new settings, or clear the queue.
- **Add images any way you like:** drag-and-drop, click to choose files, or paste
  (`Ctrl`+`V`).
- **Localized:** the interface is translated into ~39 languages.
- **Private by design:** no servers, no tracking, no network requests for your images.

## How it works

The heavy lifting is done by the [jSquash](https://github.com/jamsinclair/jSquash)
WebAssembly codecs. To keep a page view small (~60 KB), the codec bundle
(`mit-codecs.min.js`) and its `.wasm` binaries are **not** embedded in the page — they
live as sibling files and are loaded lazily, only when you first optimize an image, and
only the codec for the format actually being used.

## Files

| File | Purpose |
| --- | --- |
| `make-it-tiny.html` | The app (unminified, commented). This is the multi-file build. |
| `mit-codecs.min.js` | The jSquash codec bundle. |
| `webp_enc.wasm`, `mozjpeg_enc.wasm`, `avif_enc.wasm`, `squoosh_oxipng_bg.wasm` | The WebAssembly encoders, loaded on demand. |
| `make-it-tiny-og-preview.png` | Social-share preview image (Open Graph / Twitter card). |
| `make_offline_makeittiny.py` | Builds the single-file offline version (see below). |

## Running it

### Multi-file build (default)

Serve the folder over `http(s)` and open `make-it-tiny.html`. A web server is required
because browsers block the Worker/module fetches used to load the codecs from `file://`
URLs. Any static server works, e.g.:

```sh
python3 -m http.server
# then open http://localhost:8000/make-it-tiny.html
```

### Single-file offline build

To get one self-contained `.html` that runs by double-clicking it — no web server, fully
offline — run:

```sh
python3 make_offline_makeittiny.py
```

This reads `make-it-tiny.html`, inlines the codec bundle and its `.wasm` binaries (as
`data:` URLs), flips the app's `EMBEDDED_OFFLINE` build flag, and writes
**`make-it-tiny-offline.html`** (~5.8 MB). Open that file directly from a `file://` URL.

> Note: in the offline build the codecs run on the main thread (module Workers can't load
> from a `file://` page), so a very large batch will feel a little less responsive than
> the served version. The result is identical.

## Privacy

Everything runs in your browser. No image data is uploaded, and there are no analytics or
third-party network calls. The app — and the images you optimize — stay entirely on your
device. Keep the offline build (or the page plus its codec files) and you own a working
copy forever.
