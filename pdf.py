# -*- coding: utf-8 -*-
"""PDF 匯出 — WeasyPrint。"""
import sys

def pdf_bytes(html: str) -> bytes:
    # 延遲載入：缺少原生 PDF 套件時仍可正常閱報。
    from weasyprint import HTML
    return HTML(string=html).write_pdf()


def html_to_pdf(html: str, out_path: str) -> str:
    with open(out_path, "wb") as output:
        output.write(pdf_bytes(html))
    return out_path


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        html_to_pdf(f.read(), dst)
    print(dst)
