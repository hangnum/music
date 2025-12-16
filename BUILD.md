# 构建可执行文件

本文档介绍如何将音乐播放器项目打包成可执行文件，支持 Windows、macOS 和 Linux 平台。

## 快速开始

### Windows

```batch
# 双击运行或在命令行执行
build.bat
```

### macOS 和 Linux

```bash
# 给脚本添加执行权限（仅需执行一次）
chmod +x build.sh

# 运行构建脚本
./build.sh
```

## 详细构建说明

### 环境要求

- Python 3.8 或更高版本
- 操作系统：Windows 10+、macOS 10.15+、Linux
- 内存：至少 2GB 可用内存
- 磁盘空间：至少 1GB 可用空间

### 平台特定依赖

#### Windows
- Windows 10/11（推荐）
- Visual C++ Redistributable（通常已包含）

#### macOS
- Xcode Command Line Tools
  ```bash
  xcode-select --install
  ```

#### Linux
- Ubuntu/Debian:
  ```bash
  sudo apt install python3 python3-pip python3-venv libsdl2-2.0-0
  ```
- Fedora:
  ```bash
  sudo dnf install python3 python3-pip SDL2
  ```
- Arch:
  ```bash
  sudo pacman -S python python-pip sdl2
  ```

### 构建选项

构建脚本支持以下选项：

1. **单文件模式**（默认）：生成一个独立的可执行文件
   - 优点：分发简单，只需一个文件
   - 缺点：启动稍慢，文件较大

2. **目录模式**：生成一个包含所有依赖的目录
   - 优点：启动更快，文件较小
   - 缺点：需要整个目录一起分发

修改 `build_config.yaml` 中的 `single_file` 选项来切换模式。

### 自定义配置

#### 应用图标

将图标文件放在以下位置：
- Windows: `assets/icon.ico`
- macOS: `assets/icon.icns`
- Linux: `assets/icon.png`

支持的图标格式：
- Windows: ICO 格式，包含多种尺寸（16x16 到 256x256）
- macOS: ICNS 格式
- Linux: PNG 格式，推荐 512x512 像素

#### 应用信息

在 `build_config.yaml` 中修改应用信息：
```yaml
build:
  app_name: "YourAppName"
  app_version: "1.0.0"
  app_description: "Your App Description"
```

#### 包含/排除文件

编辑 `build_config.yaml` 中的 `data_files` 和 `excludes` 部分。

## 构建脚本说明

### build.py

主要的 Python 构建脚本，使用 PyInstaller 打包应用。功能包括：
- 依赖检查
- 图标生成
- 规格文件创建
- 多平台构建支持

### build_config.yaml

构建配置文件，包含所有构建选项：
- 应用信息
- 平台特定设置
- 包含/排除的模块
- 数据文件列表
- 压缩设置

### build.bat

Windows 批处理脚本，自动化 Windows 平台的构建过程：
- 虚拟环境创建
- 依赖安装
- 构建执行
- 错误处理

### build.sh

Unix shell 脚本，支持 macOS 和 Linux：
- 平台检测
- 依赖检查
- 系统包管理器集成
- 构建后选项

## 故障排除

### 常见问题

1. **ModuleNotFoundError**
   - 将缺失的模块添加到 `build_config.yaml` 的 `hidden_imports` 列表

2. **DLL/库文件缺失**
   - Windows：安装 Visual C++ Redistributable
   - Linux：安装所需的系统库（如 SDL2）

3. **权限错误**
   - Linux/macOS：使用 `chmod +x build.sh`
   - Windows：以管理员身份运行命令提示符

4. **内存不足**
   - 关闭其他应用程序
   - 或者使用目录模式而不是单文件模式

5. **启动失败**
   - 启用控制台模式进行调试：
     ```yaml
     console: true
     ```

### 调试技巧

1. **查看详细日志**
   ```bash
   # 使用 PyInstaller 的详细输出
   pyinstaller --clean --noconfirm --log-level DEBUG MusicPlayer.spec
   ```

2. **检查包含的模块**
   ```bash
   # 分析生成的可执行文件
   pyi-archive_viewer dist/MusicPlayer
   ```

3. **测试依赖**
   ```python
   # 创建测试脚本 test_imports.py
   import sys
   for module in ['pygame', 'PyQt6', 'mutagen', 'yaml']:
       try:
           __import__(module)
           print(f"✓ {module}")
       except ImportError as e:
           print(f"✗ {module}: {e}")
   ```

## 优化建议

### 减小文件大小

1. **排除不需要的模块**：编辑 `build_config.yaml` 的 `excludes` 列表
2. **使用 UPX 压缩**：确保 `upx_compression: true`
3. **删除调试信息**：设置 `debug: false`

### 提高启动速度

1. **使用目录模式**：设置 `single_file: false`
2. **延迟导入**：将不立即需要的模块改为运行时导入
3. **优化导入**：删除未使用的导入

### 依赖管理最佳实践

1. **使用 requirements.txt**：确保所有依赖都已列出
2. **版本锁定**：使用固定版本号以避免兼容性问题
3. **虚拟环境**：始终在虚拟环境中构建

## 发布准备

### Windows 安装包

如果需要创建 Windows 安装程序，可以使用：
- NSIS（免费）：已生成 installer.nsi 脚本
- Inno Setup（免费）
- WiX Toolset（高级）

### macOS

创建 DMG 镜像：
```bash
# 使用 create-dmg 工具
create-dmg "MusicPlayer.app" dist/MusicPlayer.dmg
```

### Linux

创建 AppImage：
```bash
# 使用 linuxdeploy
wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
chmod +x linuxdeploy-x86_64.AppImage
./linuxdeploy-x86_64.AppImage --appdir AppDir --executable dist/MusicPlayer --create-desktop-file --output appimage
```

## 许可证和合规

确保你有权分发所有包含的依赖：
- 检查每个库的许可证
- 考虑使用许可证检查工具
- 在关于对话框中包含第三方库声明

## 自动化构建

可以集成到 CI/CD 流水线：

### GitHub Actions 示例

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [windows-latest, macos-latest, ubuntu-latest]

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Build
      run: |
        if [ "$RUNNER_OS" == "Windows" ]; then
          ./build.bat
        else
          chmod +x build.sh
          ./build.sh
        fi

    - name: Upload
      uses: actions/upload-artifact@v2
      with:
        name: ${{ runner.os }}-build
        path: dist/
```

## 更多资源

- [PyInstaller 官方文档](https://pyinstaller.readthedocs.io/)
- [PyQt6 部署指南](https://www.riverbankcomputing.com/static/Docs/PyQt6/deployment.html)
- [UPX 压缩工具](https://upx.github.io/)
- [跨平台 GUI 应用打包指南](https://packaging.python.org/guides/packaging-projects/)