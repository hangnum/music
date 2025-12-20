#!/usr/bin/env python3
"""Create or overwrite a plan markdown file in ~/.gemini/plans."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from plan_utils import get_plans_dir, validate_plan_name

DEFAULT_TEMPLATE = """# Plan

<1-3 句话：意图、范围、方法>

## Requirements
- <需求 1>
- <需求 2>

## Scope
- In:
- Out:

## Files and entry points
- <文件/模块 1>
- <文件/模块 2>

## Data model / API changes
- <如适用，描述 schema 或契约变更>

## Action items
[ ] <步骤 1>
[ ] <步骤 2>
[ ] <步骤 3>

## Testing and validation
- <测试命令或验证步骤>

## Risks and edge cases
- <风险 1>
- <风险 2>

## Open questions
- <问题 1>
"""


def read_body(args: argparse.Namespace) -> str | None:
    if args.template:
        return DEFAULT_TEMPLATE
    if args.body_file:
        return Path(args.body_file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a plan file under ~/.gemini/plans."
    )
    parser.add_argument("--name", required=True, help="Plan name (lower-case, hyphen-delimited).")
    parser.add_argument("--description", required=True, help="Short plan description.")
    parser.add_argument(
        "--body-file",
        help="Path to markdown body (without frontmatter). If omitted, read from stdin.",
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="Write a template body instead of reading from stdin or --body-file.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the plan file if it already exists.",
    )
    args = parser.parse_args()

    name = args.name.strip()
    description = args.description.strip()
    validate_plan_name(name)
    if not description or "\n" in description:
        raise SystemExit("Description must be a single line.")

    body = read_body(args)
    if body is None:
        raise SystemExit("Provide --body-file, stdin, or --template to supply plan content.")

    body = body.strip()
    if not body:
        raise SystemExit("Plan body cannot be empty.")
    if body.lstrip().startswith("---"):
        raise SystemExit("Plan body should not include frontmatter.")

    plans_dir = get_plans_dir()
    plans_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plans_dir / f"{name}.md"

    if plan_path.exists() and not args.overwrite:
        raise SystemExit(f"Plan already exists: {plan_path}. Use --overwrite to replace.")

    content = f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n"
    plan_path.write_text(content, encoding="utf-8")
    print(str(plan_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
