project(
    'iconlibutils',
    version: run_command(
        'sh',
        '-c', '''
        v=$(
            command -v zfr >/dev/null 2>&1 && zfr version 2>/dev/null || true
        )
        if [ -z "$v" ] && [ -f VERSION ]; then
            v=$(head -n1 VERSION | tr -d '\r')
            v=${v#v}
        fi
        if [ -z "$v" ]; then
            v="0.0.0" # FIXED TO 0.0.0, DO NOT MODIFY
        fi
        printf '%s' "$v"
        ''',
        check: false,
    ).stdout().strip(),
    license: 'AGPL-3.0-or-later',
)

project_author = 'Lenik'
project_email = 'iconlibutils@bodz.net'
project_year = 2026

py = import('python').find_installation('python3')
fs = import('fs')
asciidoctor = find_program('asciidoctor', required: true)

prefix = get_option('prefix')
bindir = prefix / get_option('bindir')
datadir = prefix / get_option('datadir')
localedir = prefix / get_option('localedir')
mandir = prefix / get_option('mandir')
pkgdocdir = datadir / 'doc' / meson.project_name()

subdir('po')

iconlib_exe = custom_target(
    'iconlib',
    input: 'src/iconlib.py',
    output: 'iconlib',
    command: [
        py,
        '-c',
        'import os, shutil, sys; shutil.copyfile(sys.argv[1], sys.argv[2]); os.chmod(sys.argv[2], 0o755)',
        '@INPUT@',
        '@OUTPUT@',
    ],
    build_by_default: true,
    install: true,
    install_dir: bindir,
)

# Alias used by per-library launcher shortcuts (e.g. /usr/bin/heroicons)
install_symlink(
    'iconlibutils',
    pointing_to: 'iconlib',
    install_dir: bindir,
)

findicon_exe = custom_target(
    'findicon',
    input: 'src/findicon.py',
    output: 'findicon',
    command: [
        py,
        '-c',
        'import os, shutil, sys; shutil.copyfile(sys.argv[1], sys.argv[2]); os.chmod(sys.argv[2], 0o755)',
        '@INPUT@',
        '@OUTPUT@',
    ],
    build_by_default: true,
    install: true,
    install_dir: bindir,
)

foreach mod : ['ilcommon', 'paths', 'rc', 'autoindex', 'schema', 'semantic']
  custom_target(
      mod,
      input: 'src' / (mod + '.py'),
      output: mod + '.py',
      command: ['cp', '@INPUT@', '@OUTPUT@'],
      build_by_default: true,
      install: true,
      install_dir: bindir,
  )
endforeach

install_data(
    'iconlib.bash',
    install_dir: datadir / 'bash-completion' / 'completions',
    rename: 'iconlib',
)

install_data(
    'findicon.bash',
    install_dir: datadir / 'bash-completion' / 'completions',
    rename: 'findicon',
)

install_data(
    [
        'LICENSE',
        'README.md',
        'README-zh_CN.md',
    ],
    install_dir: pkgdocdir,
)

custom_target(
    'iconlib-man',
    input: 'docs/iconlib.adoc',
    output: 'iconlib.1',
    command: [
        asciidoctor,
        '-b', 'manpage',
        '-a', 'project-version=' + meson.project_version(),
        '-a', 'project-year=@0@'.format(project_year),
        '-a', 'project-author=' + project_author,
        '-a', 'project-email=' + project_email,
        '-o', '@OUTPUT@',
        '@INPUT@',
    ],
    build_by_default: true,
    install: true,
    install_dir: mandir / 'man1',
)

custom_target(
    'findicon-man',
    input: 'docs/findicon.adoc',
    output: 'findicon.1',
    command: [
        asciidoctor,
        '-b', 'manpage',
        '-a', 'project-version=' + meson.project_version(),
        '-a', 'project-year=@0@'.format(project_year),
        '-a', 'project-author=' + project_author,
        '-a', 'project-email=' + project_email,
        '-o', '@OUTPUT@',
        '@INPUT@',
    ],
    build_by_default: true,
    install: true,
    install_dir: mandir / 'man1',
)

manpage_langs = ['ar', 'de', 'es', 'fr', 'it', 'ja', 'ko', 'zh_CN']
manpage_cmds = ['iconlib', 'findicon']
foreach lang : manpage_langs
  foreach cmd : manpage_cmds
    custom_target(
        cmd + '-man-' + lang,
        input: 'docs' / lang / (cmd + '.adoc'),
        output: cmd + '.1.' + lang,
        command: [
            asciidoctor,
            '-b', 'manpage',
            '-a', 'project-version=' + meson.project_version(),
            '-a', 'project-year=@0@'.format(project_year),
            '-a', 'project-author=' + project_author,
            '-a', 'project-email=' + project_email,
            '-o', '@OUTPUT@',
            '@INPUT@',
        ],
        build_by_default: true,
    )
  endforeach
endforeach

meson.add_install_script(
    'sh',
    '-euc',
    '''
        build="@0@"
        mandir="@1@"
        for lang in ar de es fr it ja ko zh_CN; do
            dest="${DESTDIR}${mandir}/${lang}/man1"
            mkdir -p "$dest"
            install -m644 "$build/iconlib.1.$lang" "$dest/iconlib.1"
            install -m644 "$build/findicon.1.$lang" "$dest/findicon.1"
        done
    '''.format(meson.project_build_root(), mandir),
)

test(
    'python-unit',
    py,
    args: ['-m', 'unittest', 'discover', '-s', (meson.project_source_root() / 'tests'), '-p', 'test_*.py'],
    env: [
        'PYTHONPATH=' + (meson.project_source_root() / 'src'),
        'ICONLIBUTILS_LOCALEDIR=' + (meson.project_build_root() / 'po'),
    ],
    timeout: 180,
)

run_target(
    'posync',
    command: [
        'bash',
        '-euc', '''
            cd "@SOURCE_ROOT@/po"
            xgettext --from-code=UTF-8 --keyword=_ --language=Python --directory=.. --output=iconlib.pot --files-from=POTFILES
            while IFS= read -r lang; do
                [ -n "$lang" ] || continue
                case "$lang" in
                    '#'* ) continue ;;
                esac
                po_file="$lang.po"
                if [ ! -f "$po_file" ]; then
                    msginit --no-translator --input=iconlib.pot --locale="$lang" --output-file="$po_file"
                fi
                msgmerge --update --backup=none "$po_file" iconlib.pot
                msgattrib --no-obsolete --output-file="$po_file" "$po_file"
            done < LINGUAS
        ''',
    ],
)

run_target(
    'look',
    command: [
        'bash',
        '-euc', '''
            tmpdir=$(mktemp -d)
            DESTDIR=$tmpdir meson install -C "@BUILD_ROOT@"
            tree "$tmpdir"
            rm -fr "$tmpdir"
        ''',
    ],
)

run_target(
    'install-symlinks',
    command: [
        'bash',
        '-euc', '''
            prefix="@0@"
            bindir="@1@"
            datadir="@2@"
            mandir="@3@"
            mkdir -p "$bindir" "$datadir/bash-completion/completions" "$mandir/man1"
            sudo ln -sfn "@BUILD_ROOT@/iconlib" "$bindir/iconlib"
            sudo ln -sfn "@BUILD_ROOT@/iconlib.1" "$mandir/man1/iconlib.1"
            sudo ln -sfn "@SOURCE_ROOT@/iconlib.bash" "$datadir/bash-completion/completions/iconlib"
            printf "Symlinks installed under %s\n" "$prefix"
        '''.format(get_option('prefix'), bindir, datadir, mandir),
    ],
)

run_target(
    'uninstall-symlinks',
    command: [
        'bash',
        '-euc', '''
            prefix="@0@"
            bindir="@1@"
            datadir="@2@"
            mandir="@3@"
            for p in "$bindir/iconlib" "$mandir/man1/iconlib.1" "$datadir/bash-completion/completions/iconlib"
            do
                if [ -L "$p" ]; then
                    sudo rm -f "$p"
                    printf "Removed %s\n" "$p"
                else
                    printf "Skipped (not a symlink): %s\n" "$p"
                fi
            done
        '''.format(get_option('prefix'), bindir, datadir, mandir),
    ],
)
