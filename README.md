# 高质量Python音乐播放器

一个采用模块化架构设计的本地音乐播放器应用。

## 技术栈

- **GUI框架**: PyQt6
- **音频引擎**: pygame
- **元数据解析**: mutagen
- **数据库**: SQLite
- **配置管理**: YAML

## 安装

```bash
# 使用conda创建环境
conda create -n music python=3.11
conda activate music

# 安装依赖
pip install -r requirements.txt
```

## 运行

```bash
python src/main.py
```

## 项目结构

```
music/
├── docs/           # 文档
├── src/            # 源代码
│   ├── core/       # 核心模块
│   ├── models/     # 数据模型
│   ├── services/   # 服务层
│   ├── ui/         # 界面层
│   └── utils/      # 工具模块
├── tests/          # 测试
├── config/         # 配置文件
└── resources/      # 资源文件
```

## 功能

- [x] 本地音乐播放
- [x] 播放列表管理
- [x] 媒体库扫描
- [ ] 均衡器
- [ ] 歌词显示

## 开发

详细设计文档请查看 `docs/` 目录。
