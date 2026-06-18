"""Render reports/report.md -> reports/report.pdf (weasyprint), embedding figures."""
from pathlib import Path

import markdown
from weasyprint import HTML

HERE = Path(__file__).resolve().parent
CSS = """
@page { size: A4; margin: 2cm 1.8cm; @bottom-center { content: counter(page); color:#888; font-size:9pt; } }
body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; font-size:10.5pt;
       line-height:1.5; color:#1a1a1a; }
h1 { font-size:20pt; color:#0b3d2e; border-bottom:3px solid #2a9d6f; padding-bottom:6px; }
h2 { font-size:14pt; color:#0b3d2e; margin-top:1.4em; border-bottom:1px solid #ddd; }
h3 { font-size:11.5pt; color:#2a6; }
code { background:#f4f4f4; padding:1px 4px; border-radius:3px; font-size:9pt; }
pre { background:#f7f7f7; padding:10px; border-radius:6px; font-size:8.5pt; overflow:hidden;
      border:1px solid #eee; white-space:pre-wrap; }
table { border-collapse:collapse; width:100%; font-size:9.5pt; margin:0.6em 0; }
th,td { border:1px solid #ccc; padding:5px 8px; text-align:left; }
th { background:#eaf6f0; }
blockquote { background:#f3faf6; border-left:4px solid #2a9d6f; margin:0.8em 0; padding:8px 14px;
             color:#244; }
img { max-width:48%; border:1px solid #eee; border-radius:4px; margin:4px; }
.figs { text-align:center; }
"""


def main():
    md = (HERE / "report.md").read_text()
    # strip YAML front-matter for the HTML render
    if md.startswith("---"):
        md = md.split("---", 2)[-1]
    html_body = markdown.markdown(
        md, extensions=["tables", "fenced_code", "toc", "sane_lists"])

    figs = sorted((HERE / "figures").glob("*.png"))
    fig_html = ""
    if figs:
        imgs = "".join(f'<img src="figures/{p.name}"/>' for p in figs)
        fig_html = f'<h2>Appendix — Figures</h2><div class="figs">{imgs}</div>'

    html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html_body}{fig_html}</body></html>"
    HTML(string=html, base_url=str(HERE)).write_pdf(HERE / "report.pdf")
    print("Wrote", HERE / "report.pdf")


if __name__ == "__main__":
    main()
