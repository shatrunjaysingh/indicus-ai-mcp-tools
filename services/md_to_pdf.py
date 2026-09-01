"""Render a Markdown file to PDF.

    backend/.venv/bin/python demo/md_to_pdf.py FILE.md [FILE.md ...]

Uses the Chromium that Playwright already installs for the end-to-end tests,
rather than adding a PDF engine. Chromium's print pipeline handles the two
things that matter here — page breaks that do not cut a table row in half, and
text that stays selectable — which an image-based renderer does not.

Styling is deliberately plain and print-first: black on white, a serif face for
body text at a size that survives being printed and read on paper, and tables
that keep their header row when they span a page. These documents go to
auditors and finance, not to a browser.
"""

from __future__ import annotations

import asyncio
import pathlib
import sys

import markdown

CSS = """
@page { size: A4; margin: 20mm 18mm; }

body {
  font-family: Georgia, "Times New Roman", serif;
  font-size: 10.5pt;
  line-height: 1.55;
  color: #111;
  max-width: none;
}

h1 { font-size: 20pt; margin: 0 0 4pt; letter-spacing: -0.01em; }
h2 {
  font-size: 13pt;
  margin: 22pt 0 6pt;
  padding-bottom: 3pt;
  border-bottom: 1px solid #ccc;
  /* A heading alone at the foot of a page reads as a mistake. */
  page-break-after: avoid;
}
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; page-break-after: avoid; }

p, li { orphans: 3; widows: 3; }
ul, ol { padding-left: 18pt; }
li { margin-bottom: 3pt; }

table {
  border-collapse: collapse;
  width: 100%;
  margin: 10pt 0;
  font-size: 9pt;
  /* Rows are read across; splitting one across a page break loses the row. */
  page-break-inside: auto;
}
thead { display: table-header-group; }  /* repeat the header on every page */
tr { page-break-inside: avoid; }
th, td {
  border: 1px solid #bbb;
  padding: 4pt 6pt;
  text-align: left;
  vertical-align: top;
}
th { background: #f2f2f2; font-weight: 600; }

code, pre {
  font-family: "SF Mono", Menlo, Consolas, monospace;
  font-size: 8.5pt;
}
pre {
  background: #f6f6f6;
  border: 1px solid #ddd;
  padding: 8pt;
  white-space: pre-wrap;
  word-wrap: break-word;
  page-break-inside: avoid;
}
code { background: #f2f2f2; padding: 1pt 3pt; }
pre code { background: none; padding: 0; }

blockquote {
  margin: 10pt 0;
  padding: 2pt 0 2pt 12pt;
  border-left: 3px solid #999;
  color: #333;
  font-style: italic;
}

hr { border: none; border-top: 1px solid #ddd; margin: 16pt 0; }
strong { font-weight: 700; }
a { color: #111; text-decoration: none; }
"""


def to_html(path: pathlib.Path) -> str:
    body = markdown.markdown(
        path.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{path.stem}</title><style>{CSS}</style></head>"
        f"<body>{body}</body></html>"
    )


async def render(paths: list[pathlib.Path]) -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        for path in paths:
            html = to_html(path)
            # Loaded as a data URL rather than written to a temp file, so a
            # failed run leaves nothing behind to clean up.
            await page.set_content(html, wait_until="load")
            out = path.with_suffix(".pdf")
            await page.pdf(
                path=str(out),
                format="A4",
                print_background=True,
                margin={"top": "20mm", "bottom": "20mm", "left": "18mm", "right": "18mm"},
                display_header_footer=True,
                header_template="<div></div>",
                footer_template=(
                    "<div style='font-size:8pt;color:#666;width:100%;"
                    "padding:0 18mm;text-align:right;font-family:Georgia,serif'>"
                    "<span class='pageNumber'></span> / <span class='totalPages'></span>"
                    "</div>"
                ),
            )
            print(f"  {out.name:38} {out.stat().st_size // 1024:>4} KB")
        await browser.close()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    paths = [pathlib.Path(a).resolve() for a in sys.argv[1:]]
    missing = [p for p in paths if not p.exists()]
    if missing:
        raise SystemExit(f"Not found: {', '.join(str(p) for p in missing)}")
    asyncio.run(render(paths))


if __name__ == "__main__":
    main()
