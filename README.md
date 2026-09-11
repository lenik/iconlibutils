# iconlibutils

`iconlibutils` provides the **iconlib** CLI for searching and managing icons
from installed icon libraries (tabler-icons, streamline-vectors, heroicons, …).

## Repository layout

- `src/` — Python sources (`iconlib.py`, `findicon.py`, shared modules)
- `tests/` — Python unit tests (`unittest`)
- `debian/` — Debian packaging (including path-file postinst)
- `po/` — gettext catalogs
- `docs/` — AsciiDoc man page sources
- `meson.build` — install rules and tests

## Command: `iconlib`

```bash
iconlib [OPTIONS] COMMAND [ARGS...]
```

### Global options

| Option | Meaning |
|--------|---------|
| `-l LIBRARY` | Select library (repeatable; unambiguous prefix OK) |
| `-d DIR` / `--local-dir DIR` | Pull destination under project-dir (default `icons`) |
| `-s SCHEMA` / `--schema SCHEMA` | Path recipe (default `n`): `l/f/n`, `v/m.e`, … |
| `-m NAME=DIR` / `--map NAME=DIR` | Map library → local dirname |
| `-v` / `-q` / `-h` / `--version` | Verbose, quiet, help, version |

### Commands

- `search [-l/--long | -1/--names] [pattern]` — list matching icons (score
  descending; `--long` includes score). Plain English queries expand
  singular/plural and WordNet synonyms via `python3-pattern` (e.g. `cat` →
  `kitty`).
- `which [-a] <name>` — print preferred path (or all with `-a`)
- `info <name>` — formats, sizes, variants, paths
- `pull [-F FORMAT]... [-S SIZE]... [pattern]` — copy into the project
- `push [pattern]` — not implemented yet
- `browse [pattern]` — run `themestylebrowser` on libraries with `.themestyles`

### Patterns

- empty — all
- `name` — exact
- `glob` — wildcards
- `/regex` — regular expression

### Configuration

Merged library registry (`TYPE NAME PATH`; `auto` walks image trees):

- `/etc/iconlibutils/path` (seeded by package postinst)
- `~/.config/iconlibutils/path`

Project file `.iconlibrc` (walk cwd → root): same flags as globals; its
directory is the project-dir. CLI overrides rc.

### Schema tokens

`o`/`orig`, `l`/`lib`, `f`/`fmt`, `n`/`name` (stem.ext), `m`/`stem`,
`e`/`extension`, `s`/`size`, `v`/`variant` — combined with `/`.
Default: `n` (flat `name.ext` under the local dir).

Example: `-d assets -S medium=64 -s s/l/f/n` →
`assets/medium/tabler-icons/png/foo.png`.

Example: `-s l/v/n` → `tabler-icons/outline/foo.svg`.
## Build and test

### Build dependencies (Debian example)

```bash
sudo apt install meson ninja-build python3 gettext asciidoctor
```

### Configure and build

```bash
meson setup /build
ninja -C /build
```

### Run tests

```bash
meson test -C /build
```

## i18n (gettext)

`iconlib` uses gettext under `po/`. Sync catalogs:

```bash
ninja -C /build posync
```

## Install

```bash
meson install -C /build
```

Debug symlinks: `ninja -C /build install-symlinks`.

## Debian package

```bash
dpkg-buildpackage -us -uc
```

Postinst writes managed entries into `/etc/iconlibutils/path` for known
libraries present under `/usr/share/…`.

## License

Copyright (C) 2026 Lenik <iconlibutils@bodz.net>

Licensed under **AGPL-3.0-or-later**.  
This project explicitly opposes AI exploitation and AI hegemony, and rejects
mindless MIT-style licensing and politically naive BSD-style licensing.  
See `LICENSE` for the full text and supplemental project terms.
