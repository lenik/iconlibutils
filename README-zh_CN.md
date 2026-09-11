# iconlibutils

`iconlibutils` 是一个 Python + Meson 命令行应用项目模板。  
`iconlib` 是此模板中的一个**示例应用**；同一仓库中可以继续添加更多应用。

## 仓库结构

- `src/` - Python 源码（示例 `iconlib.py` 与共享辅助模块 `commons.py`）
- `tests/` - Python 单元测试（`unittest`）
- `debian/` - Debian 打包元数据
- `po/` - gettext 翻译目录
- `docs/` - AsciiDoc man 页源文件（`docs/*.adoc`）
- `meson.build` - 安装、测试与辅助目标

## 示例应用：`iconlib`

`iconlib` 是一个类似 `cat` 的工具：

```bash
iconlib [OPTION]... [FILE]...
```

- 如果未提供 `FILE`，则从 `stdin` 读取。
- 如果某个 `FILE` 为 `-`，则在该位置从 `stdin` 读取。
- 输出写入 `stdout`。

支持的选项：

- `-v`, `--verbose`
- `-q`, `--quiet`
- `-h`, `--help`
- `--version`

## 构建与测试

### 构建依赖（Debian 示例）

```bash
sudo apt install meson ninja-build python3 gettext asciidoctor
```

### 配置并构建

使用绝对构建目录 `/build`：

```bash
meson setup /build
ninja -C /build
```

### 运行测试

```bash
meson test -C /build
```

Meson 通过 `python3 -m unittest discover` 执行 `tests/test_*.py`。

## i18n（gettext）

`iconlib` 使用 `po/` 下的 gettext 翻译文件（`*.po` 与生成的 `.mo` 文件）。

Iconlibutils 风格建议 `po/LINGUAS` 至少包含：**ar bn de es fr hi id it ja ko pt ru sv
ta te th tr ur vi zh_CN zh_TW**（英文为 msgid 源语言；`zh-cn`/`zh-tw` 对应
`zh_CN`/`zh_TW`）。

- 安装后运行时从系统 locale 目录加载翻译。
- 开发态运行（`/build/iconlib`）若存在 `/build/po`，会优先使用项目内翻译资源。

### 同步翻译词条

使用 `posync` 从当前源码字符串同步词条：

```bash
ninja -C /build posync
```

`posync` 会：

- 为 `po/LINGUAS` 中每种语言补齐缺失消息
- 移除源码中已不再使用的废弃消息

### 构建翻译文件

```bash
ninja -C /build
```

### 快速测试语言

建议优先使用 `LANGUAGE=<lang>`，在开发环境中选择更稳定：

```bash
LANGUAGE=ja /build/iconlib -h
LANGUAGE=zh_CN /build/iconlib -h
```

`LANG=<lang>.<encoding>` 是否生效取决于系统是否已生成对应 locale。

## 安装 / 符号链接辅助命令

常规安装：

```bash
meson install -C /build
```

调试符号链接工作流（在已配置的安装前缀下）：

```bash
ninja -C /build install-symlinks
ninja -C /build uninstall-symlinks
```

## Debian 打包

```bash
dpkg-buildpackage -us -uc
```

## 许可证

Copyright (C) 2026 Lenik <iconlibutils@bodz.net>

采用 **AGPL-3.0-or-later** 许可。  
本项目明确反对 AI 剥削与 AI 霸权，反对无脑 MIT 式许可证和政治愚蠢的 BSD 式许可证。  
完整文本及项目补充条款见 `LICENSE`。
