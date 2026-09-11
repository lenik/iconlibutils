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

pkgdatadir = datadir / 'iconlibutils'

# Meson-substituted package config (version + install paths).
py_conf = configuration_data()
py_conf.set('VERSION', meson.project_version())
py_conf.set('PKGDATADIR', pkgdatadir)
py_conf.set('DATADIR', datadir)
py_conf.set('LOCALEDIR', localedir)
py_conf.set('WORDNET_DIR', '/usr/share/wordnet')
iconlib_config_py = configure_file(
  input: '_config.py.in',
  output: '_config.py',
  configuration: py_conf,
)
install_data(
  iconlib_config_py,
  install_dir: py.get_install_dir() / 'iconlib',
)

# Install the iconlib Python package (not into bindir).
install_subdir(
  'src/iconlib',
  install_dir: py.get_install_dir(),
  exclude_directories: ['__pycache__'],
)

# Python entry invoked by the bash launcher.
install_data(
  'src/iconlib_main.py',
  install_dir: pkgdatadir,
  install_mode: 'rwxr-xr-x',
)

# Build-tree launcher: source paths + PYTHONPATH so ./build/iconlib works.
conf_local = configuration_data()
conf_local.set_quoted('PYTHON', '/usr/bin/python3')
conf_local.set_quoted(
  'ICONLIB_MAIN',
  meson.project_source_root() / 'src' / 'iconlib_main.py',
)
conf_local.set_quoted(
  'PYTHONPATH_EXTRA',
  meson.project_source_root() / 'src',
)
conf_local.set_quoted('LOCALEDIR', meson.project_build_root() / 'po')
iconlib_local_cfg = configure_file(
  input: 'iconlib.in',
  output: 'iconlib.local.in',
  configuration: conf_local,
)
custom_target(
  'iconlib',
  input: iconlib_local_cfg,
  output: 'iconlib',
  command: [
    'sh',
    '-c',
    'cp -f "$1" "$2" && chmod 755 "$2"',
    'sh',
    '@INPUT@',
    '@OUTPUT@',
  ],
  build_by_default: true,
)

# Installed launcher: prefix paths; site-packages already on sys.path.
conf_inst = configuration_data()
conf_inst.set_quoted('PYTHON', '/usr/bin/python3')
conf_inst.set_quoted('ICONLIB_MAIN', pkgdatadir / 'iconlib_main.py')
conf_inst.set_quoted('PYTHONPATH_EXTRA', '')
conf_inst.set_quoted('LOCALEDIR', localedir)
iconlib_installed = configure_file(
  input: 'iconlib.in',
  output: 'iconlib.install',
  configuration: conf_inst,
)
install_data(
  iconlib_installed,
  install_dir: bindir,
  rename: 'iconlib',
  install_mode: 'rwxr-xr-x',
)

# Stage and install findicon as the final bindir name (avoid install rename).
custom_target(
  'findicon',
  input: 'findicon.sh',
  output: 'findicon',
  command: [
    'sh',
    '-c',
    'cp -f "$1" "$2" && chmod 755 "$2"',
    'sh',
    '@INPUT@',
    '@OUTPUT@',
  ],
  build_by_default: true,
  install: true,
  install_dir: bindir,
)

install_subdir(
  'share/index',
  install_dir: datadir / 'iconlibutils',
  strip_directory: false,
)

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

test_env = [
  'PYTHONPATH=' + (meson.project_source_root() / 'src'),
  'ICONLIBUTILS_LOCALEDIR=' + (meson.project_build_root() / 'po'),
]

test(
  'python-unit-iconlib',
  py,
  args: [
    '-m',
    'unittest',
    'tests.test_iconlib',
    '-v',
  ],
  workdir: meson.project_source_root(),
  env: test_env,
  timeout: 120,
)

test(
  'python-unit-findicon',
  py,
  args: [
    '-m',
    'unittest',
    'tests.test_findicon',
    '-v',
  ],
  workdir: meson.project_source_root(),
  env: test_env,
  timeout: 60,
)

test(
  'python-unit-faiss',
  py,
  args: [
    '-m',
    'unittest',
    'tests.test_bytesize_faiss',
    '-v',
  ],
  workdir: meson.project_source_root(),
  env: test_env,
  timeout: 600,
  is_parallel: false,
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
            sudo ln -sfn "@BUILD_ROOT@/findicon" "$bindir/findicon"
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
            for p in "$bindir/iconlib" "$bindir/findicon" "$mandir/man1/iconlib.1" "$datadir/bash-completion/completions/iconlib"
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
