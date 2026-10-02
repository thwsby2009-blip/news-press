# -*- coding: utf-8 -*-
"""PDF 匯出 — WeasyPrint。"""
import sys

from weasyprint import HTML


def html_to_pdf(html: str, out_path: str) -> str:
    HTML(string=html, base_url=".").write_pdf(out_path)
    return out_path


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        html_to_pdf(f.read(), dst)
    print(dst)
