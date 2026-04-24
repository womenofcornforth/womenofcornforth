#!/usr/bin/env python3
"""Convert RTF/DOCX source files into Jekyll collection markdown entries.

Pipeline:
  source .rtf/.docx
    -> LibreOffice headless (soffice --convert-to txt)
    -> cleaned paragraphs
    -> markdown file with YAML front matter in _stories/ or _tales/

Re-runnable: always overwrites its own output so edits to the sources flow
through on a re-run. Hand-edits to front matter (e.g. curated excerpts) will
be clobbered — curate by editing the sources or this script's overrides.
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = ROOT.parent / "Women of Cornforth Website Information"
STORIES_OUT = ROOT / "_stories"
TALES_OUT = ROOT / "_tales"

# Files that are drafts / duplicates / too big / not text-first. Skipped.
SKIP_PATTERNS = [
    "Doggie's Tales Draft 1",
    "Doggie's Tales Draft 2 JES.rtf",  # 60MB with images
    "Doggie's Tales Draft 3",
    "Durham Map 1898",
    "Doggie's Tales Draft 2 JES Minus photographs",  # we use as "doggies-tales" below
    "Doggie's Tales Introduction Draft 2",
    "Doggie Tales Draft 4",
    "James Scott Gunn Another View",
    "Women of Cornforth Bits and Bobs",
    "My Mother Said.rtf",          # older duplicate of "My Mother Said 1.rtf"
    "Pat Pennick 1.rtf",           # shorter early draft; keep "Pat Pennick.rtf"
    "~$",                          # Office lock files
]

# Hand-curated title overrides where filename-derived titles read badly.
# Key: source filename (exact basename).
TITLE_OVERRIDES = {
    "GLADYS THIRLAWAY  nee  ROSSITER   MY MAM (Autosaved).docx": "Gladys Thirlaway (née Rossiter)",
    "G(Pina) Mitton.docx": "Pina Mitton",
    "Peggy Sweeting - Biography.docx": "Peggy Sweeting",
}

# Explicit picks for the "tales" and "stories" collections, drawn from the
# essay layer (top-level and Doggie's Tales/). Everything in Women of
# Cornforth/ is classified as a story automatically further down.
#   source path (relative to SOURCE_ROOT) -> (kind, slug, title, subtitle)
ESSAY_PICKS = {
    "Introduction.rtf":                             ("tale",  "introduction", "Introduction", "Julie's welcome to the archive"),
    "Hearth and Home without illustrations.rtf":    ("tale",  "hearth-and-home", "Hearth and Home", None),
    "Down The Street 2.rtf":                        ("tale",  "down-the-street", "Down The Street", None),
    "High Street Smells.rtf":                       ("tale",  "high-street-smells", "High Street Smells", None),
    "Housewife.rtf":                                ("tale",  "housewife", "Housewife", None),
    "Love and Marriage.rtf":                        ("tale",  "love-and-marriage", "Love and Marriage", None),
    "Monday was washing day.rtf":                   ("tale",  "monday-was-washing-day", "Monday was washing day", None),
    # "My Mother Said 1.rtf" is the fuller/later version; the un-numbered file
    # is an earlier draft and is skipped via SKIP_PATTERNS.
    "My Mother Said 1.rtf":                         ("tale",  "my-mother-said", "My Mother Said", "A collection of sayings"),
    "Take care of the pennies.rtf":                 ("tale",  "take-care-of-the-pennies", "Take care of the pennies", None),
    "Voices of Cornforth  JESL January 22 2020.rtf":("tale",  "voices-of-cornforth", "Voices of Cornforth", "January 2020"),
    "Requests for Contributions.rtf":               ("tale",  "requests-for-contributions", "Requests for Contributions", None),
    # Individual biographies that happen to sit at the essay layer.
    "Beryl Walker Biog 1.rtf":                      ("story", "beryl-walker", "Beryl Walker", None),
    "Shirley (Cadman) Frisby 1.rtf":                ("story", "shirley-frisby", "Shirley (Cadman) Frisby", None),
    # Doggie's Tales book.
    "Doggie's Tales/Doggie's Tales Draft 2 JES Minus photographs.rtf":
                                                    ("tale",  "doggies-tales", "Doggie's Tales", "Village history, collected"),
    "Doggie's Tales/Doggie's Tales Introduction.rtf":
                                                    ("tale",  "doggies-tales-introduction", "Doggie's Tales — Introduction", None),
    "Doggie's Tales/Cornforth Memories.rtf":        ("tale",  "cornforth-memories", "Cornforth Memories", None),
    "Doggie's Tales/James Scott Gunn Abriged.docx": ("story", "james-scott-gunn", "James Scott Gunn", "An abridged life"),
}

# Everything in Women of Cornforth/ becomes a story (biography). The slug
# comes from the filename; the title from the filename minus suffixes.
STORIES_SUBDIR = "Women of Cornforth"

STOPWORDS_IN_TITLE = {"(Autosaved)", "nee", "Biog"}


@dataclass
class Entry:
    kind: str          # "story" | "tale"
    slug: str
    title: str
    subtitle: str | None
    source: Path


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def should_skip(name: str) -> bool:
    return any(p in name for p in SKIP_PATTERNS)


_P_SPLIT = re.compile(r"<p\b[^>]*>", re.IGNORECASE)
_TAG_STRIP = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_BOLD = re.compile(r"<b\b[^>]*>(.*?)</b>", re.IGNORECASE | re.DOTALL)
_ITAL = re.compile(r"<i\b[^>]*>(.*?)</i>", re.IGNORECASE | re.DOTALL)
_BODY = re.compile(r"<body\b[^>]*>(.*?)</body>", re.IGNORECASE | re.DOTALL)
_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)


def _strip_inline_tags(segment: str) -> str:
    """Turn a snippet of soffice HTML into plain text, preserving only **bold**
    and *italic* markdown emphasis."""
    segment = _BR.sub("\n", segment)
    # Convert bold / italic before stripping everything else. Nested font tags
    # inside a <b>...</b> need their inner contents preserved.
    def bold_sub(m):
        inner = _TAG_STRIP.sub("", m.group(1))
        inner = html.unescape(inner).strip()
        return f"**{inner}**" if inner else ""
    def ital_sub(m):
        inner = _TAG_STRIP.sub("", m.group(1))
        inner = html.unescape(inner).strip()
        return f"*{inner}*" if inner else ""
    segment = _BOLD.sub(bold_sub, segment)
    segment = _ITAL.sub(ital_sub, segment)
    segment = _TAG_STRIP.sub("", segment)
    segment = html.unescape(segment)
    return segment


def html_to_markdown(raw_html: str) -> str:
    """Parse LibreOffice-exported HTML into a tidy markdown string.

    Each `<p>` becomes a markdown paragraph; a paragraph whose text content
    is entirely wrapped in bold is treated as an h2 heading.
    """
    body_match = _BODY.search(raw_html)
    body = body_match.group(1) if body_match else raw_html

    # Split on opening <p> so each chunk starts with paragraph content, then
    # ends at either the next <p> or </p>. We just keep everything up to the
    # first </p>.
    chunks = _P_SPLIT.split(body)
    out: list[str] = []
    for chunk in chunks:
        end = chunk.lower().find("</p>")
        if end != -1:
            chunk = chunk[:end]
        raw_bold_check = re.sub(r"<(?!/?b\b)[^>]+>", "", chunk).strip()
        is_heading = (
            raw_bold_check.startswith("<b>") or raw_bold_check.startswith("<B>")
        ) and (raw_bold_check.endswith("</b>") or raw_bold_check.endswith("</B>"))

        # Decide heading vs. paragraph up front so we can skip the bold/italic
        # markdown pass on headings (which otherwise end up sprinkled with
        # asterisks from tightly-packed font+b+i spans).
        if is_heading:
            text = _TAG_STRIP.sub("", chunk)
            text = html.unescape(text)
            text = _WS.sub(" ", text).strip()
            if text and len(text) < 140:
                out.append(f"## {text}")
                continue
            # fall through as a normal paragraph if the heading ended up long

        text = _strip_inline_tags(chunk)
        text = _WS.sub(" ", text).strip()
        if text:
            out.append(text)
    return "\n\n".join(out) + "\n"


def make_excerpt(markdown: str, limit: int = 220) -> str:
    for block in markdown.split("\n\n"):
        block = block.strip()
        if not block or block.startswith("#"):
            continue
        if len(block) <= limit:
            return block
        return block[: limit - 1].rstrip() + "…"
    return ""


def convert_one(src: Path, tmpdir: Path) -> str:
    """Return the HTML content of `src` by shelling to LibreOffice."""
    result = subprocess.run(
        [
            "soffice", "--headless", "--convert-to", "html",
            "--outdir", str(tmpdir), str(src),
        ],
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode != 0:
        print(f"  [warn] soffice failed for {src.name}: {result.stderr.strip()}", file=sys.stderr)
        return ""
    out = tmpdir / (src.stem + ".html")
    if not out.exists():
        print(f"  [warn] no output for {src.name}", file=sys.stderr)
        return ""
    return out.read_text(encoding="utf-8", errors="replace")


def biography_title(filename: str) -> str:
    stem = Path(filename).stem
    # Drop parenthetical "(Autosaved)" style tags.
    stem = re.sub(r"\s*\(.*?\)\s*", " ", stem)
    # Drop trailing " 1", " 2" duplicate markers.
    stem = re.sub(r"\s+\d+$", "", stem)
    # Tidy up ALLCAPS NAMES → Title Case.
    if stem.isupper():
        stem = stem.title()
    return " ".join(stem.split())


def collect_entries() -> list[Entry]:
    entries: list[Entry] = []

    for rel, (kind, slug, title, subtitle) in ESSAY_PICKS.items():
        src = SOURCE_ROOT / rel
        if not src.exists():
            print(f"  [warn] missing: {rel}", file=sys.stderr)
            continue
        entries.append(Entry(kind, slug, title, subtitle, src))

    bios_dir = SOURCE_ROOT / STORIES_SUBDIR
    for src in sorted(bios_dir.iterdir()):
        if not src.is_file():
            continue
        if src.suffix.lower() not in {".rtf", ".docx"}:
            continue
        if should_skip(src.name):
            continue
        if src.stat().st_size < 500:
            # Stub placeholder files like "Elizabeth Jane Sweeting.rtf" (7 bytes).
            print(f"  [skip] empty stub: {src.name}")
            continue
        title = TITLE_OVERRIDES.get(src.name) or biography_title(src.name)
        slug = slugify(title)
        entries.append(Entry("story", slug, title, None, src))

    return entries


def write_entry(entry: Entry, markdown: str) -> Path:
    out_dir = STORIES_OUT if entry.kind == "story" else TALES_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{entry.slug}.md"
    excerpt = make_excerpt(markdown)
    fm = [
        "---",
        f'title: "{entry.title.replace(chr(34), chr(39))}"',
    ]
    if entry.subtitle:
        fm.append(f'subtitle: "{entry.subtitle.replace(chr(34), chr(39))}"')
    if excerpt:
        fm.append(f'excerpt: "{excerpt.replace(chr(34), chr(39))}"')
    fm.append(f"slug: {entry.slug}")
    fm.append("---")
    path.write_text("\n".join(fm) + "\n\n" + markdown, encoding="utf-8")
    return path


def main() -> int:
    if not SOURCE_ROOT.exists():
        print(f"Source root not found: {SOURCE_ROOT}", file=sys.stderr)
        return 2

    # Clean output directories so removed sources don't linger.
    for d in (STORIES_OUT, TALES_OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    entries = collect_entries()
    print(f"Found {len(entries)} source entries.")

    with tempfile.TemporaryDirectory(prefix="woc-convert-") as tmp:
        tmpdir = Path(tmp)
        for entry in entries:
            raw = convert_one(entry.source, tmpdir)
            if not raw.strip():
                print(f"  [skip] empty after conversion: {entry.source.name}")
                continue
            md = html_to_markdown(raw)
            out = write_entry(entry, md)
            print(f"  [{entry.kind:5}] {entry.slug:38} <- {entry.source.name}  ({len(md)} chars)")
            _ = out

    return 0


if __name__ == "__main__":
    sys.exit(main())
