# iconlibutils

`iconlibutils` provides the **iconlib** CLI for searching and managing icons
from installed icon libraries (tabler-icons, streamline-vectors, heroicons, …).

## Repository layout

- `src/iconlib/` — Python package (`cmd/`, index helpers, …)
- `iconlib.in` — meson-substituted bash launcher → `src/iconlib_main.py`
- `findicon.sh` — bindir shortcut to `iconlib search`
- `tests/` — Python unit tests (`unittest`; three meson test targets)
- `debian/` — Debian packaging
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
  singular/plural and WordNet synonyms via `python3-inflect` + `wordnet-base`
  (e.g. `cat` → `kitty`). When a selected library has a FAISS index
  (`faiss.index` next to the library / preview dir), CLIP text query results
  are merged in. `findicon` is a shortcut for this command.
- `libraries` / `ls` `[-l|--long | -1|--names]` — list discovered libraries
- `which [-a] <name>` — print preferred path (or all with `-a`)
- `info <name>` — formats, sizes, variants, paths
- `pull [-F FORMAT]... [-S SIZE]... [pattern]` — copy into the project
- `push [pattern]` — not implemented yet
- `browse [pattern]` — run `themestylebrowser` on libraries with `.themestyles`
- `index [-w|--web] [-F|--faiss] [-f|--force] [-s|--upscale SIZE] [-o DIR]` —
  web preview (default) and/or CLIP FAISS index (`faiss.index` /
  `faiss.map` / `faiss.json`). FAISS needs CLIP weights in the Hugging Face
  hub cache (`hf download openai/clip-vit-base-patch32`; optional
  `HF_ENDPOINT=https://hf-mirror.com`), or `ICONLIB_CLIP_MODEL` pointing at
  an existing local checkout.
- `delete <name>...` — remove local icon files (all variants/sizes/formats)
- `rename <old> <new>` — rename local icon files
- `copy <from> <to>` — copy local icon files
- `ln [-sf] <target> <name>` — hard-link or symlink local icon files
- `make [-s SIZE]... [-F FMT]... <name>...` — derive local size/format variants

### Patterns

- empty — all
- `name` — exact
- `glob` — wildcards
- `/regex` — regular expression

### Configuration

Libraries are discovered by scanning drop-in metadata **files**:

- `<install-prefix /usr>/share/iconlibutils/library/<name>`
- `~/.config/iconlibutils/library/<name>`

Each `icons-<name>` package installs a file named `<name>` there (key=value:
`name`, `type`, `path`, `title`, `license`, `homepage`, `description`).
If `path` is omitted, `/usr/share/icons-<name>` is assumed.

Optional legacy path files (`TYPE NAME PATH`) still override by name:

- `/etc/iconlibutils/path`
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

Postinst ensures `/usr/share/iconlibutils/library` exists. Individual
`icons-*` packages register themselves by installing
`/usr/share/iconlibutils/library/<name>` (a file).

## License

Copyright (C) 2026 Lenik <iconlibutils@bodz.net>

Licensed under **AGPL-3.0-or-later**.  
This project explicitly opposes AI exploitation and AI hegemony, and rejects
mindless MIT-style licensing and politically naive BSD-style licensing.  
See `LICENSE` for the full text and supplemental project terms.
