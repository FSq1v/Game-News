"""Obsidian のニュースまとめを、公開用の Markdown に変換して取り込む。"""
import argparse
import re
import sys
from pathlib import Path

DEFAULT_SRC = Path(r"<保管庫>\30_ニュース")
DEFAULT_DEST = Path("src/content/digest")

IMPACT = "自分への影響"
NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_ニュースまとめ(?:_(\d+))?\.md$")
SOURCE_RE = re.compile(r"^(\s*- 出典：)(.+?)\s+(https?://\S+)$")
WIKI_RE = re.compile(r"\[\[([^\]|]*)(?:\|([^\]]*))?\]\]")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _is_impact(line: str) -> bool:
    s = line.strip()
    if s.startswith("- "):
        s = s[2:]
    s = s.lstrip("*").lstrip()
    return s.startswith(IMPACT)


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", text, re.S)
    if not m:
        raise ValueError("プロパティ（frontmatter）が読めない")
    props: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            props[k.strip()] = v.strip()
    return props, m.group(2)


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _parse_tags(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [t.strip().strip("\"'") for t in raw.split(",") if t.strip()]


def convert(text: str) -> tuple[str, int]:
    """公開用の Markdown と、取り除いた行の数を返す。"""
    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    props, body = _split_frontmatter(text)
    date = props.get("created", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("created が読めない")

    lines = body.split("\n")
    title = None
    out: list[str] = []
    removed = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if title is None and line.startswith("# "):
            title = line[2:].strip()  # タイトルはレイアウトが出すので本文からは消す
            i += 1
            continue
        if _is_impact(line):
            base = _indent(line)
            removed += 1
            i += 1
            while i < len(lines) and lines[i].strip() and _indent(lines[i]) > base:
                removed += 1
                i += 1
            continue
        line = SOURCE_RE.sub(r"\1[\2](\3)", line)
        line = WIKI_RE.sub(lambda m: m.group(2) or m.group(1), line)
        out.append(line)
        i += 1
    if not title:
        raise ValueError("タイトル（# の行）が読めない")

    fm = ["---", f"title: {_q(title)}", f"date: {date}"]
    if props.get("period"):
        fm.append(f"period: {_q(props['period'])}")
    tags = _parse_tags(props.get("tags", ""))
    fm.append("tags: [" + ", ".join(_q(t) for t in tags) + "]")
    fm.append("---")
    return "\n".join(fm) + "\n" + "\n".join(out).lstrip("\n"), removed


def output_name(source_name: str) -> str:
    m = NAME_RE.match(source_name)
    if not m:
        raise ValueError("ファイル名が YYYY-MM-DD_ニュースまとめ[_N].md の形ではない")
    return f"{m.group(1)}-{m.group(2)}.md" if m.group(2) else f"{m.group(1)}.md"


def sync(src: Path, dest: Path) -> list[str]:
    """src のノートを変換して dest に書き、報告の行を返す。"""
    report: list[str] = []
    dest.mkdir(parents=True, exist_ok=True)
    for path in sorted(src.glob("*.md")):
        try:
            new, removed = convert(path.read_text(encoding="utf-8"))
            name = output_name(path.name)
        except ValueError as e:
            report.append(f"スキップ: {path.name}（{e}）")
            continue
        target = dest / name
        if target.exists():
            old = target.read_text(encoding="utf-8")
            status = "変更なし" if old == new else "上書き"
        else:
            status = "新規"
        if status != "変更なし":
            target.write_text(new, encoding="utf-8", newline="\n")
        report.append(f"{status}: {name}（取り除いた行: {removed}）")
    return report


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    args = ap.parse_args()
    for line in sync(args.src, args.dest):
        print(line)


if __name__ == "__main__":
    main()
