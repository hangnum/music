# 构建可执行文件

本文档介绍如何将音乐播放器项目打包成可执行文件。项目使用 PyInstaller 进行打包，并提供自动化脚本简化构建过程。

## 快速开始

所有的构建脚本现在都位于 `scripts/` 目录下。

### Windows

```batch
# 进入项目根目录执行
.\scripts\build.bat
```

### macOS 和 Linux

```bash
# 给脚本添加执行权限（仅需执行一次）
chmod +x scripts/build.sh

# 运行构建脚本
./scripts/build.sh
```

## 构建选项

构建系统支持多种模式，可以通过命令行参数或修改 `scripts/build_config.yaml` 来配置。

### 常用命令

| 平台 | 命令 | 说明 |
|------|------|------|
| Windows | `.\scripts\build.bat` | 构建发布版本（单文件） |
| Windows | `.\scripts\build.bat --dev` | 构建开发版本（带控制台，启动快） |
| Linux/macOS | `./scripts/build.sh` | 构建发布版本 |
| Linux/macOS | `./scripts/build.sh --dev` | 构建开发版本 |

### 构建模式说明

- **发布模式 (Release)**:
  - 生成单一可执行文件。
  - 启用 UPX 压缩。
  - 隐藏控制台窗口。
- **开发模式 (Dev)**:
  - 生成包含所有依赖的目录。
  - 禁用压缩以提高构建速度。
  - 显示控制台窗口，方便调试。

## 详细配置

所有的构建行为都由 `scripts/build_config.yaml` 控制。您可以根据需要修改以下内容：

- **应用信息**: 名称、版本、描述。
- **图标**: 位于 `assets/` 目录下的图标文件。
- **数据文件**: 需要打包进程序的资源（如 QSS 样式、图标）。
- **隐藏导入**: PyInstaller 无法自动检测的模块。

## 故障排除

1. **ModuleNotFoundError**: 检查 `build_config.yaml` 中的 `hidden_imports` 是否包含了报错的模块。
2. **权限错误**: 在 macOS/Linux 上确保执行了 `chmod +x scripts/build.sh`。
3. **构建失败**: 使用 `--dev` 模式运行以查看控制台中的详细错误日志。

更多详细信息，请参阅 PyInstaller [官方文档](https://pyinstaller.readthedocs.io/)。
