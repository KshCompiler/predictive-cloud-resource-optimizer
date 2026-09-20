# -*- coding: utf-8 -*-
"""
Rebuild the three PDFs from their HTML sources.

Run from the project root:
    venv\\Scripts\\python.exe report\\build_report.py

    report/report.html  ->  Phase1_Progress_Report.pdf      (what is done, results)
    report/guide.html   ->  Project_Explained_Simply.pdf    (every decision and why)
    report/summary.html ->  Quick_Summary.pdf               (the short version)

Steps:
  1. make_figs.py regenerates the report-only figures into plots/
     (plots/top_vms.png and plots/cpu_distribution.png come from
      `python -m utils.explore`, plots/270_week.png from utils.load_data,
      plots/verify_pipeline.png from utils.preprocessing - run those first)
  2. {{CSS}}, {{IMG:...}} and {{SVG:...}} tokens are replaced with the shared
     stylesheet, base64-embedded PNGs and the SVG diagrams from diagrams.py
  3. headless Chrome/Edge prints each page to an A4 PDF
"""
import base64
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from diagrams import DIAGRAMS  # noqa: E402

DOCUMENTS = [
    ("report.html", "Phase1_Progress_Report.pdf"),
    ("guide.html", "Project_Explained_Simply.pdf"),
    ("summary.html", "Quick_Summary.pdf"),
]

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser():
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    raise SystemExit("No Chrome or Edge found - install one, or add its path above.")


def embed_image(match):
    """Replace {{IMG:plots/x.png}} with a <figure> holding the base64 image."""
    rel = match.group(1)
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit(f"missing figure {rel} - run the script that makes it first")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f'<figure><img src="data:image/png;base64,{b64}" alt="{rel}">'


def embed_diagram(match):
    """Replace {{SVG:name}} with the inline SVG built by diagrams.py."""
    name = match.group(1)
    if name not in DIAGRAMS:
        raise SystemExit(f"unknown diagram: {name}")
    return DIAGRAMS[name]()


def build_html(source):
    css = open(os.path.join(HERE, "style.css"), encoding="utf-8").read()
    html = open(os.path.join(HERE, source), encoding="utf-8").read()
    html = html.replace("{{CSS}}", css)
    html = re.sub(r"\{\{IMG:([^}]+)\}\}", embed_image, html)
    html = re.sub(r"\{\{SVG:([^}]+)\}\}", embed_diagram, html)

    leftover = re.findall(r"\{\{[^}]+\}\}", html)
    if leftover:
        raise SystemExit(f"{source}: unresolved tokens {leftover}")

    # each {{IMG}} opens a <figure>; close it after the caption that follows
    html = re.sub(r"</figcaption>", "</figcaption></figure>", html)
    if html.count("<figure>") != html.count("</figure>"):
        raise SystemExit(f"{source}: every {{{{IMG}}}} needs a figcaption right after it")
    return html


def print_pdf(html_path, pdf_path):
    subprocess.run([
        find_browser(),
        "--headless", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=12000",
        f"--print-to-pdf={pdf_path}",
        "file:///" + html_path.replace("\\", "/"),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    print("[1/2] regenerating report figures")
    subprocess.run([sys.executable, os.path.join(HERE, "make_figs.py")],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)

    print("[2/2] building PDFs")
    for source, pdf_name in DOCUMENTS:
        built = os.path.join(HERE, source.replace(".html", "_built.html"))
        with open(built, "w", encoding="utf-8") as f:
            f.write(build_html(source))
        pdf = os.path.join(ROOT, pdf_name)
        print_pdf(built, pdf)
        os.remove(built)
        print(f"  wrote {pdf_name}  ({os.path.getsize(pdf) // 1024} KB)")


if __name__ == "__main__":
    main()
