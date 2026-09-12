# iconlibutils

`iconlibutils` 提供 **iconlib** 命令行工具，用于搜索与管理已安装的图标库
（tabler-icons、streamline-vectors、heroicons 等）。

## 仓库结构

- `src/iconlib/` — Python 包（`cmd/`、索引相关模块等）
- `iconlib.in` — meson 替换的 bash 启动器 → `src/iconlib_main.py`
- `findicon.sh` — `iconlib search` 的 bindir 快捷命令
- `tests/` — 单元测试（`unittest`；三个 meson 测试目标）
- `debian/` — Debian 打包
- `po/` — gettext 翻译
- `docs/` — AsciiDoc man 页
- `meson.build` — 安装与测试规则

## 命令：`iconlib`

```bash
iconlib [OPTIONS] COMMAND [ARGS...]
```

### 全局选项

| 选项 | 含义 |
|------|------|
| `-l LIBRARY` | 选择图标库（可重复；无歧义前缀即可） |
| `-d DIR` / `--local-dir DIR` | pull 目标目录（相对 project-dir，默认 `icons`） |
| `-s SCHEMA` / `--schema SCHEMA` | 路径配方（默认 `n`）：`l/f/n`、`l/v/n` 等 |
| `-m NAME=DIR` / `--map NAME=DIR` | 库名映射到本地目录名 |
| `-v` / `-q` / `-h` / `--version` | 详细、安静、帮助、版本 |

### 子命令

- `search [-l/--long | -1/--names] [pattern]` — 列出匹配图标（按 score
  降序；`--long` 含 score）。普通英文词会做单复数与 WordNet 同义词联想
 （依赖 `python3-inflect` + `wordnet-base`，例如 `cat` → `kitty`）。
  `findicon` 是该命令的快捷方式。
- `libraries` / `ls` `[-l|--long | -1|--names]` — 列出已发现的图库
- `which [-a] <name>` — 打印首选路径（`-a` 打印全部）
- `info <name>` — 格式、尺寸、变体与路径
- `pull [-F FORMAT]... [-S SIZE]... [pattern]` — 复制到项目
- `push [pattern]` — 尚未实现
- `browse [pattern]` — 对含 `.themestyles` 的库启动 `themestylebrowser`
- `index [-w|--web] [-F|--faiss] [-f|--force] [-u|--upscale SIZE] [-s|--shard-size SIZE] [-o DIR]` —
  生成网页预览和/或 CLIP FAISS 索引（`faiss` / 分片时 `faiss.N`）。
  默认不分片；大包可用 `-s 10M` 或在 `library.iconlib` 写
  `faiss_shard_size=10M`。
- `delete <name>...` — 删除本地图标文件（含各 variant/size/format）
- `rename <old> <new>` — 本地改名
- `copy <from> <to>` — 本地复制
- `ln [-sf] <target> <name>` — 本地硬链接或符号链接
- `make [-s SIZE]... [-F FMT]... <name>...` — 生成本地尺寸/格式变体

### 匹配模式

- 空 — 全部
- `name` — 精确名
- `glob` — 通配符
- `/regex` — 正则

### 配置

通过扫描 drop-in **文件** 发现图库：

- `<install-prefix /usr>/share/iconlibutils/library/<name>`
- `~/.config/iconlibutils/library/<name>`

每个 `icons-<name>` 包安装名为 `<name>` 的文件（`key=value`：
`name`、`type`、`path`、`title`、`license`、`homepage`、`description`）。
若省略 `path`，默认 `/usr/share/icons-<name>`。

可选的旧版 path 文件（按名称覆盖）：

- `/etc/iconlibutils/path`
- `~/.config/iconlibutils/path`

项目文件 `.iconlibrc`（从 cwd 向上查找）：选项与全局相同；所在目录为
project-dir。命令行覆盖 rc。

### Schema 记号

`o`/`orig`、`l`/`lib`、`f`/`fmt`、`n`/`name`（stem.ext）、`m`/`stem`、
`e`/`extension`、`s`/`size`、`v`/`variant`，用 `/` 组合。默认：`n`。

示例：`-d assets -S medium=64 -s s/l/f/n` →
`assets/medium/tabler-icons/png/foo.png`。

示例：`-s l/v/n` → `tabler-icons/outline/foo.svg`。

## 构建与测试

### 构建依赖（Debian 示例）

```bash
sudo apt install meson ninja-build python3 gettext asciidoctor
```

### 配置与构建

```bash
meson setup /build
ninja -C /build
```

### 运行测试

```bash
meson test -C /build
```

## 国际化（gettext）

```bash
ninja -C /build posync
```

## 安装

```bash
meson install -C /build
```

调试符号链接：`ninja -C /build install-symlinks`。

## Debian 包

```bash
dpkg-buildpackage -us -uc
```

postinst 会确保 `/usr/share/iconlibutils/library` 存在。各 `icons-*`
包通过安装 `/usr/share/iconlibutils/library/<name>`（文件）自注册。

## 许可证

Copyright (C) 2026 Lenik <iconlibutils@bodz.net>

以 **AGPL-3.0-or-later** 许可。  
本项目明确反对 AI 剥削与 AI 霸权，并拒绝无脑的 MIT 式许可与政治上幼稚的
BSD 式许可。详见 `LICENSE`。
