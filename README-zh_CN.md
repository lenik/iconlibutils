# iconlibutils

`iconlibutils` 提供 **iconlib** 命令行工具，用于搜索与管理已安装的图标库
（tabler-icons、streamline-vectors、heroicons 等）。

## 仓库结构

- `src/` — Python 源码（`iconlib.py`、`findicon.py` 与共享模块）
- `tests/` — 单元测试（`unittest`）
- `debian/` — Debian 打包（含 path 文件的 postinst）
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
 （依赖 `python3-pattern`，例如 `cat` → `kitty`）。
- `which [-a] <name>` — 打印首选路径（`-a` 打印全部）
- `info <name>` — 格式、尺寸、变体与路径
- `pull [-F FORMAT]... [-S SIZE]... [pattern]` — 复制到项目
- `push [pattern]` — 尚未实现
- `browse [pattern]` — 对含 `.themestyles` 的库启动 `themestylebrowser`

### 匹配模式

- 空 — 全部
- `name` — 精确名
- `glob` — 通配符
- `/regex` — 正则

### 配置

合并的库注册表（`TYPE NAME PATH`；`auto` 会遍历图片树）：

- `/etc/iconlibutils/path`（打包 postinst 写入）
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

postinst 会在 `/usr/share/…` 存在时，把已知图标库写入
`/etc/iconlibutils/path`。

## 许可证

Copyright (C) 2026 Lenik <iconlibutils@bodz.net>

以 **AGPL-3.0-or-later** 许可。  
本项目明确反对 AI 剥削与 AI 霸权，并拒绝无脑的 MIT 式许可与政治上幼稚的
BSD 式许可。详见 `LICENSE`。
