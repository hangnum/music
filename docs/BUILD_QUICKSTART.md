# 构建快速指南

## 概述

Music Player v2.0 使用了全新的模块化构建系统，支持跨平台打包，具有高度可配置性。

## 快速开始

### 1. 环境准备

确保已安装 Python 3.8+：
```bash
python --version
```

构建脚本会自动安装必要的依赖（PyInstaller、PyYAML等）。

### 2. 构建命令

#### Windows
```cmd
# 构建发布版本（单文件）
build.bat

# 构建开发版本（带控制台，便于调试）
build.bat --dev

# 仅清理构建文件
build.bat --clean

# 构建并创建安装包
build.bat --package
```

#### Linux/macOS
```bash
# 确保脚本可执行
chmod +x build.sh

# 构建发布版本
./build.sh

# 构建开发版本
./build.sh --dev

# 仅清理构建文件
./build.sh --clean
```

#### 直接使用 Python
```bash
# 基本构建
python build.py

# 调试构建
python build.py --debug --console

# 使用目录模式（启动更快）
python build.py --dir

# 自定义配置文件
python build.py --config my_config.yaml
```

## 构建配置

### 配置文件结构

`build_config.yaml` 是主要的配置文件，包含：

- **应用信息**：名称、版本、描述等
- **构建设置**：单文件/目录模式、压缩选项等
- **数据文件**：需要打包的资源文件
- **依赖项**：隐藏导入和排除的模块
- **平台特定设置**：各平台的特殊配置

### 自定义配置

创建自定义配置文件：
```yaml
build:
  app_name: "MyMusicPlayer"
  app_version: "2.0.0"
  single_file: false  # 使用目录模式
  upx_compression: false  # 禁用压缩

  # 添加额外的数据文件
  data_files:
    - source: "extra/themes"
      destination: "themes"
```

然后使用：
```bash
python build.py --config my_config.yaml
```

## 构建模式

### 发布模式 (默认)
- 单文件可执行程序
- 启用 UPX 压缩
- 无调试信息
- 无控制台窗口

### 开发模式 (`--dev`)
- 目录模式（启动更快）
- 禁用压缩
- 保留调试信息
- 显示控制台（便于查看错误）

### 调试模式 (`--debug`)
- 保留所有调试信息
- 显示控制台
- 可以使用调试器附加

## 故障排除

### 常见问题

1. **模块未找到错误**
   - 在 `hidden_imports` 中添加缺失的模块
   - 检查 `data_files` 是否包含必要的资源

2. **启动缓慢**
   - 使用 `--dir` 模式而非单文件模式
   - 禁用 UPX 压缩：`--no-upx`

3. **文件过大**
   - 检查 `excludes` 列表
   - 启用 UPX 压缩
   - 移除不必要的数据文件

4. **权限错误**
   - Linux/macOS：确保脚本有执行权限
   - Windows：以管理员身份运行

### 调试技巧

1. 使用 `--console` 查看详细错误信息
2. 检查生成的 `build.log` 文件
3. 使用 PyInstaller 的 `--debug` 选项

## 输出文件

构建完成后，可执行文件位于：
- Windows: `dist/MusicPlayer.exe`
- Linux: `dist/MusicPlayer`
- macOS: `dist/MusicPlayer.app` (如果打包为应用)

## 高级用法

### 创建桌面文件 (Linux)

```ini
# musicplayer.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=Music Player
Comment=A modern music player with AI queue management
Exec=/path/to/MusicPlayer
Icon=/path/to/icon.png
Categories=AudioVideo;Audio;Player;
```

### 代码签名 (Windows)

需要配置 `build_config.yaml`：
```yaml
platforms:
  windows:
    codesign_identity: "Your Certificate"
```

### 自定义图标

将图标文件放置在：
- Windows: `assets/icon.ico`
- macOS: `assets/icon.icns`
- Linux: `assets/icon.png`

## 性能优化建议

1. **使用虚拟环境**：避免打包不必要的包
2. **精确配置依赖**：只包含必要的模块
3. **使用 UPX**：显著减小文件大小
4. **测试不同模式**：单文件 vs 目录模式

## 更多信息

- PyInstaller 官方文档：https://pyinstaller.readthedocs.io/
- 项目配置文件：`build_config.yaml`
- 构建日志：`build.log`