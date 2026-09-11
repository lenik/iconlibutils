# iconlibutils

`iconlibutils` is a Python + Meson project template for small command-line apps.
`iconlib` is one **example app** in this template; more apps can be added in the same repository.

## Repository layout

- `src/` - Python sources (`iconlib.py` example app and `commons.py` shared helpers)
- `tests/` - Python unit tests (`unittest`)
- `debian/` - Debian packaging metadata
- `po/` - gettext message catalogs
- `docs/` - AsciiDoc man page sources (`docs/*.adoc`)
- `meson.build` - install rules, tests, and helper targets

## Example app: `iconlib`

`iconlib` is a cat-like utility:

```bash
iconlib [OPTION]... [FILE]...
```

- If no `FILE` is provided, it reads from `stdin`.
- If a `FILE` is `-`, it reads from `stdin` at that position.
- Output is written to `stdout`.

Supported options:

- `-v`, `--verbose`
- `-q`, `--quiet`
- `-h`, `--help`
- `--version`

## Build and test

### Build dependencies (Debian example)

```bash
sudo apt install meson ninja-build python3 gettext asciidoctor
```

### Configure and build

Use the absolute build directory `/build`:

```bash
meson setup /build
ninja -C /build
```

### Run tests

```bash
meson test -C /build
```

Meson runs `python3 -m unittest discover` against `tests/test_*.py`.

## i18n (gettext)

`iconlib` uses gettext translations under `po/` (`*.po` + generated `.mo` files).

Iconlibutils style recommends `po/LINGUAS` cover at least: **ar bn de es fr hi id it
ja ko pt ru sv ta te th tr ur vi zh_CN zh_TW** (English is the msgid source;
`zh-cn`/`zh-tw` map to `zh_CN`/`zh_TW`).

- Installed runtime loads translations from system locale dir.
- Dev runtime (`/build/iconlib`) prefers project-local translations from `/build/po` if present.

### Sync translation catalogs

Use `posync` to update catalogs from current source strings:

```bash
ninja -C /build posync
```

`posync` will:

- add missing messages into each language from `po/LINGUAS`
- remove obsolete messages no longer used in source

### Build translation files

```bash
ninja -C /build
```

### Quick locale testing

Prefer `LANGUAGE=<lang>` for predictable gettext selection in dev shells:

```bash
LANGUAGE=ja /build/iconlib -h
LANGUAGE=zh_CN /build/iconlib -h
```

`LANG=<lang>.<encoding>` may depend on whether that locale is generated on your system.

## Install / symlink helpers

Normal install:

```bash
meson install -C /build
```

Debug symlink workflow (under configured prefix):

```bash
ninja -C /build install-symlinks
ninja -C /build uninstall-symlinks
```

## Debian package

```bash
dpkg-buildpackage -us -uc
```

## License

Copyright (C) 2026 Lenik <iconlibutils@bodz.net>

Licensed under **AGPL-3.0-or-later**.  
This project explicitly opposes AI exploitation and AI hegemony, and rejects
mindless MIT-style licensing and politically naive BSD-style licensing.  
See `LICENSE` for the full text and supplemental project terms.
