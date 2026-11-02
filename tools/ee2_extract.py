"""Extract EE2 reference files from the upstream NCO standards.rst.

Structural pass first (code blocks, csv-tables), inline-markup pass applied
only to prose parts so that emitted fences and vendored example code are
never rewritten. The SECTIONS table pins the 1-based line ranges of the
pinned upstream revision; run with --write to emit every reference file.
"""
from __future__ import annotations

import re

SMART = {"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'", "\u2013": "-", "\u2014": "--"}


def clean_prose(text: str) -> str:
    for k, v in SMART.items():
        text = text.replace(k, v)
    text = re.sub(r"^\.\. _[\w-]+:\s*$", "", text, flags=re.M)        # link targets
    text = re.sub(r"\.\. \[#(\w+)\] (.*)", r"[^\1]: \2", text)        # footnote defs
    text = re.sub(r"\[#(\w+)\]_", r"[^\1]", text)                      # footnote refs
    text = re.sub(r".. note::[ \t]*", "**Note:** ", text)
    text = re.sub(r"`([^`]+) <(https?://[^>]+)>`_", r"[\1](\2)", text)  # named hyperlinks
    text = re.sub(r"`([^`]+)`_", r"\1", text)                           # implicit refs
    text = re.sub(r":ref:`([^`]+) <[^`]+>`", r"\1", text)               # sphinx ref roles
    text = re.sub(r"\*\*\*+", "**", text)                               # bold+italic residue
    text = re.sub(r"``([^`]+)``", r"`\1`", text)                       # inline literals
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _csv_rows(block: list[str]) -> list[list[str]]:
    rows = []
    for line in block:
        s = line.strip()
        if not s or s.startswith(":"):
            continue
        cells = re.findall(r'"((?:[^"]|"")*)"', s)
        if cells:
            rows.append([c.replace('""', '"') for c in cells])
    return rows


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip()) if line.strip() else 0


HEADING_LEVELS = {"=": "##", "-": "###", "~": "####", "^": "####"}


def demote_headings(text: str) -> str:
    """Convert RST setext headings to ATX, shifted so the `=` level becomes `##`.

    Fence-aware: lines inside a code block are copied through untouched, so a
    table rule or divider in vendored example code is never read as a heading.
    """
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        underline = lines[i + 1] if i + 1 < len(lines) else ""
        marker = underline.strip()
        if (
            not in_fence
            and line.strip()
            and not line.startswith((" ", "\t"))
            and re.fullmatch(r"([=\-~^])\1{2,}", marker)
        ):
            out.append(f"{HEADING_LEVELS[marker[0]]} {line.strip()}")
            i += 2
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def _relevel(text: str) -> str:
    """Shift heading levels so the shallowest *real* heading in the excerpt is `##`.

    Fence-aware: `#` comment lines inside code blocks are not headings and must
    not be counted when choosing the shift.
    """
    levels = []
    inf = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inf = not inf
            continue
        if not inf:
            m = re.match(r"^(#+) ", line)
            if m:
                levels.append(len(m.group(1)))
    if not levels:
        return text
    shift = 2 - min(levels)
    if shift == 0:
        return text
    out = []
    inf = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inf = not inf
            out.append(line)
            continue
        if inf:
            out.append(line)
            continue
        m = re.match(r"^(#+) ", line)
        if m:
            out.append("#" * max(2, min(6, len(m.group(1)) + shift)) + line[len(m.group(1)):])
        else:
            out.append(line)
    return "\n".join(out)


def convert(text: str) -> str:
    lines = text.split("\n")
    parts: list[tuple[str, str, int]] = []   # (kind, content, indent)
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\s*)\.\. (code-block|csv-table)::[ \t]*(\S*)[ \t]*$", line)
        if m:
            indent, kind, lang = len(m.group(1)), m.group(2), m.group(3)
            i += 1
            body = []
            while i < len(lines):
                if not lines[i].strip():
                    body.append("")
                    i += 1
                    continue
                if _indent_of(lines[i]) <= indent:
                    break
                body.append(lines[i])
                i += 1
            while body and not body[-1].strip():
                body.pop()
            if kind == "code-block":
                strip = min((_indent_of(b) for b in body if b.strip()), default=0)
                code = "\n".join(b[strip:] if b.strip() else "" for b in body)
                parts.append(("code", code, indent))
                parts.append(("lang", lang, indent))
            else:
                parts.append(("table", "\n".join(body), indent))
            continue
        parts.append(("prose", line, -1))
        i += 1

    out: list[str] = []
    buf: list[str] = []
    idx = 0
    while idx < len(parts):
        kind, content, indent = parts[idx]
        if kind == "prose":
            buf.append(content)
            idx += 1
            continue
        if buf:
            out.append(clean_prose("\n".join(buf)))
            buf = []
        if kind == "code":
            code = parts[idx][1]
            lang = parts[idx + 1][1] if parts[idx + 1][0] == "lang" else ""
            fence = " " * indent + "```" + lang
            body = "\n".join(((" " * indent) + c).rstrip() if c else "" for c in code.split("\n"))
            out.append(f"{fence}\n{body}\n" + " " * indent + "```")
            idx += 3 if parts[idx + 2][0] == "lang" else 2
            continue
        if kind == "lang":
            idx += 1
            continue
        rows = _csv_rows(content.split("\n"))
        if len(rows) >= 2:
            header, data = rows[0], rows[1:]
            width = len(header)

            def cell(c: str) -> str:
                return clean_prose(c).replace("|", "\\|").strip()

            table = [" " * indent + "| " + " | ".join(cell(c) for c in header) + " |",
                     " " * indent + "| " + " | ".join("---" for _ in header) + " |"]
            for r in data:
                r = (r + [""] * width)[:width]
                table.append(" " * indent + "| " + " | ".join(cell(c) for c in r[:width]) + " |")
            out.append("\n".join(table))
        idx += 1
    if buf:
        out.append(clean_prose("\n".join(buf)))
    text = "\n".join(out)
    text = demote_headings(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = _relevel(text)
    return "\n".join(line.rstrip() for line in text.split("\n")).strip() + "\n"


def section(path: str, start: int, end: int) -> str:
    lines = open(path, encoding="utf-8").read().split("\n")
    return convert("\n".join(lines[start - 1:end]))


# 1-based inclusive line ranges into the pinned standards.rst (md5
# 699ca1c4ecb6e6ef6c4fbc4cd3112592, ee-docs 11.0.0). Keys are the output
# file names under references/. The title becomes the emitted H1 so each file
# satisfies markdownlint MD041.
SECTIONS = {
    "workflow.md": (38, 66, "Workflow"),
    "environment-variables.md": (72, 135, "Standard Environment Variables"),
    "file-naming.md": (136, 185, "File Name Conventions"),
    "production-utilities.md": (186, 297, "Production Utilities"),
    "date-and-grib-utilities.md": (298, 450, "Date and GRIB Utilities"),
    "standards.md": (451, 654, "Standards"),
    "dataflow.md": (655, 684, "Dataflow"),
    "code-delivery.md": (685, 893, "Code Delivery and Vertical Structure"),
    "examples.md": (894, 1319, "Workflow Examples and Tables"),
}

UPSTREAM_MD5 = "699ca1c4ecb6e6ef6c4fbc4cd3112592"


def extract_all(rst_path: str) -> dict[str, str]:
    """Return {filename: markdown} for every pinned section, H1 included."""
    result = {}
    for name, (start, end, title) in SECTIONS.items():
        body = section(rst_path, start, end)
        result[name] = f"# {title}\n\n{body}"
    return result


def _verify_md5(rst_path: str) -> bool:
    import hashlib
    digest = hashlib.md5(open(rst_path, "rb").read()).hexdigest()
    if digest != UPSTREAM_MD5:
        print(f"WARNING: {rst_path} md5 {digest} != pinned {UPSTREAM_MD5}")
        return False
    return True


if __name__ == "__main__":
    import argparse
    import pathlib

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rst", help="path to the fetched standards.rst")
    ap.add_argument("--write", metavar="DIR", help="directory to write reference files into")
    ap.add_argument("--only", metavar="NAME", help="emit a single section file to stdout")
    args = ap.parse_args()

    _verify_md5(args.rst)
    files = extract_all(args.rst)
    if args.only:
        print(files[args.only], end="")
    elif args.write:
        out = pathlib.Path(args.write)
        out.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (out / name).write_text(text, encoding="utf-8")
            print(f"wrote {out / name} ({len(text.splitlines())} lines)")
    else:
        for name, text in files.items():
            print(f"=== {name} ({len(text.splitlines())} lines) ===")
