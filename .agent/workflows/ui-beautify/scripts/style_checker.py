#!/usr/bin/env python3
"""
UI 样式检查器
检查 PyQt6 代码中的硬编码样式值和未使用 DesignTokens 的情况。

用法:
    python style_checker.py src/ui/
    python style_checker.py src/ui/widgets/player_controls.py
"""

import argparse
import re
from pathlib import Path
from typing import NamedTuple

# 检测模式
HEX_COLOR_PATTERN = re.compile(r'["\']#[0-9A-Fa-f]{3,8}["\']')
RGB_PATTERN = re.compile(r'rgb\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)')
RGBA_PATTERN = re.compile(r'rgba\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,')

# 允许的模式 (在 DesignTokens 和 ThemeManager 中)
ALLOWED_FILES = {"design_tokens.py", "theme_manager.py", "dark_theme.qss"}


class Issue(NamedTuple):
    file: Path
    line: int
    message: str
    severity: str  # "warning" or "error"


def check_file(filepath: Path) -> list[Issue]:
    """检查单个文件"""
    issues = []
    
    if filepath.name in ALLOWED_FILES:
        return issues
    
    if not filepath.suffix == ".py":
        return issues
    
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return issues
    
    lines = content.splitlines()
    
    for i, line in enumerate(lines, 1):
        # 跳过注释
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        
        # 检查硬编码 Hex 颜色
        if HEX_COLOR_PATTERN.search(line):
            # 排除导入 DesignTokens 的行
            if "tokens." not in line and "DesignTokens" not in line:
                issues.append(Issue(
                    file=filepath,
                    line=i,
                    message=f"硬编码颜色值: {HEX_COLOR_PATTERN.search(line).group()}",
                    severity="warning"
                ))
        
        # 检查 RGB/RGBA
        if RGB_PATTERN.search(line) or RGBA_PATTERN.search(line):
            if "tokens." not in line:
                issues.append(Issue(
                    file=filepath,
                    line=i,
                    message="硬编码 RGB/RGBA 颜色值",
                    severity="warning"
                ))
        
        # 检查直接设置字体大小
        if "font-size:" in line.lower() and "tokens" not in line.lower():
            if "setStyleSheet" in line or '"""' in content[max(0,i-5):i]:
                issues.append(Issue(
                    file=filepath,
                    line=i,
                    message="硬编码字体大小",
                    severity="info"
                ))
    
    return issues


def check_directory(dirpath: Path) -> list[Issue]:
    """递归检查目录"""
    all_issues = []
    
    for filepath in dirpath.rglob("*.py"):
        if "__pycache__" in str(filepath):
            continue
        issues = check_file(filepath)
        all_issues.extend(issues)
    
    return all_issues


def print_report(issues: list[Issue]):
    """打印检查报告"""
    if not issues:
        print("✅ 未发现样式问题")
        return
    
    print(f"发现 {len(issues)} 个问题:\n")
    
    # 按文件分组
    by_file: dict[Path, list[Issue]] = {}
    for issue in issues:
        by_file.setdefault(issue.file, []).append(issue)
    
    for filepath, file_issues in sorted(by_file.items()):
        print(f"📄 {filepath}")
        for issue in file_issues:
            icon = "⚠️" if issue.severity == "warning" else "ℹ️"
            print(f"  {icon} L{issue.line}: {issue.message}")
        print()


def main():
    parser = argparse.ArgumentParser(description="检查 UI 样式一致性")
    parser.add_argument("path", help="要检查的文件或目录")
    
    args = parser.parse_args()
    target = Path(args.path)
    
    if not target.exists():
        print(f"错误: 路径不存在 {target}")
        return 1
    
    if target.is_file():
        issues = check_file(target)
    else:
        issues = check_directory(target)
    
    print_report(issues)
    return 1 if issues else 0


if __name__ == "__main__":
    exit(main())
