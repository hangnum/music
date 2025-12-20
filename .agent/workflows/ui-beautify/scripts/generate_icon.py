#!/usr/bin/env python3
"""
SVG 图标生成器
为 PyQt6 音乐播放器生成符合品牌规范的 SVG 图标。

用法:
    python generate_icon.py --name "settings" --type "cog"
    python generate_icon.py --name "play" --type "play" --size 32
    python generate_icon.py --list
"""

import argparse
from pathlib import Path

# 品牌色
BRAND_COLOR = "#3FB7A6"
DEFAULT_COLOR = "currentColor"

# 图标模板
ICONS = {
    "play": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="{color}" stroke="none"><path d="M8 5v14l11-7z"/></svg>''',
    
    "pause": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="{color}" stroke="none"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg>''',
    
    "stop": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="{color}" stroke="none"><rect x="6" y="6" width="12" height="12"/></svg>''',
    
    "next": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="{color}" stroke="none"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg>''',
    
    "previous": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="{color}" stroke="none"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>''',
    
    "volume-high": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>''',
    
    "volume-mute": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>''',
    
    "shuffle": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>''',
    
    "repeat": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>''',
    
    "cog": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>''',
    
    "heart": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>''',
    
    "plus": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>''',
    
    "search": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>''',
    
    "music": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>''',
    
    "list": '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>''',
}


def list_icons():
    """列出所有可用图标类型"""
    print("可用图标类型:")
    for name in sorted(ICONS.keys()):
        print(f"  - {name}")


def generate_icon(name: str, icon_type: str, size: int = 24, 
                  use_brand_color: bool = False) -> str:
    """生成 SVG 图标"""
    if icon_type not in ICONS:
        raise ValueError(f"未知图标类型: {icon_type}")
    
    color = BRAND_COLOR if use_brand_color else DEFAULT_COLOR
    return ICONS[icon_type].format(size=size, color=color)


def save_icon(name: str, content: str, output_dir: Path):
    """保存图标到文件"""
    output_path = output_dir / f"{name}.svg"
    output_path.write_text(content, encoding="utf-8")
    print(f"已生成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="生成 SVG 图标")
    parser.add_argument("--name", help="输出文件名 (不含 .svg)")
    parser.add_argument("--type", dest="icon_type", help="图标类型")
    parser.add_argument("--size", type=int, default=24, help="图标尺寸 (默认 24)")
    parser.add_argument("--brand", action="store_true", help="使用品牌色")
    parser.add_argument("--output", default="src/ui/resources/icons", 
                        help="输出目录")
    parser.add_argument("--list", action="store_true", help="列出可用图标")
    
    args = parser.parse_args()
    
    if args.list:
        list_icons()
        return
    
    if not args.name or not args.icon_type:
        parser.error("需要 --name 和 --type 参数")
    
    content = generate_icon(args.name, args.icon_type, args.size, args.brand)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    save_icon(args.name, content, output_dir)


if __name__ == "__main__":
    main()
