"""Check local Markdown file targets in current documentation, excluding snapshots."""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = [*ROOT.glob("*.md"), *ROOT.glob("reports/*.md"), *ROOT.glob("docs/*.md"), ROOT / "docs/audits/README.md"]
    errors = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            target = target.strip("<>").split("#")[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / unquote(target)).exists():
                errors.append(f"{path.relative_to(ROOT)} -> {target}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Local links verified in {len(paths)} current Markdown documents")


if __name__ == "__main__":
    main()
