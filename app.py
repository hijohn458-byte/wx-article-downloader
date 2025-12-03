import io
import os
import re
import zipfile
from urllib.parse import urlparse, parse_qs

from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from playwright.sync_api import sync_playwright

app = Flask(__name__)
app.secret_key = "some-random-secret-key"  # 用来支持 flash 消息，随便写个字符串即可


def safe_filename(name: str) -> str:
    """将标题转换为安全的文件名：去掉非法字符、缩短长度"""
    name = name.strip()
    name = re.sub(r'[\/\\\:\*\?\"\<\>\|]', '_', name)
    name = re.sub(r'\s+', ' ', name)
    return name[:80] or "wechat_article"


def get_article_title(page):
    """优先使用 #activity-name，找不到就用 <title>"""
    try:
        locator = page.locator("#activity-name")
        if locator.count() > 0:
            title = locator.first.inner_text().strip()
            if title:
                return title
    except Exception:
        pass

    try:
        title = page.title().strip()
        title = re.sub(r"-\s*微信公众平台.*$", "", title).strip()
        return title or "wechat_article"
    except Exception:
        return "wechat_article"


def get_article_id_from_url(url: str) -> str:
    """从 URL 中提取参数作为备选文件名"""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    parts = []
    for key in ("__biz", "mid", "sn", "idx"):
        if key in qs:
            parts.append(f"{key}_{qs[key][0]}")
    return "_".join(parts) or "wechat_article"


def auto_scroll(page, step=800, delay=300):
    """自动滚动页面，确保图片和评论加载出来"""
    last_height = 0
    same_count = 0

    while True:
        page.evaluate(f"window.scrollBy(0, {step});")
        page.wait_for_timeout(delay)
        height = page.evaluate("() => document.body.scrollHeight")
        if height == last_height:
            same_count += 1
        else:
            same_count = 0
        last_height = height
        if same_count >= 3:
            break


def download_single_article(page, url: str) -> tuple[str, bytes]:
    """
    打开单篇文章并导出为 PDF（二进制）
    返回: (文件名, pdf_bytes)
    """
    page.goto(url, wait_until="networkidle", timeout=60000)

    # 滚动页面，加载图片和评论
    auto_scroll(page, step=800, delay=300)
    page.wait_for_timeout(2000)

    title = get_article_title(page)
    base_name = safe_filename(title)
    if base_name == "wechat_article":
        base_name = get_article_id_from_url(url)

    # 设置适合微信文章的视口宽度
    page.set_viewport_size({"width": 414, "height": 896})
    auto_scroll(page, step=800, delay=300)
    page.wait_for_timeout(1000)

    pdf_bytes = page.pdf(
        print_background=True,
        scale=0.9,
        margin={"top": "0.4in", "bottom": "0.4in", "left": "0.3in", "right": "0.3in"},
    )

    filename = base_name + ".pdf"
    return filename, pdf_bytes


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        urls_text = request.form.get("urls", "").strip()
        if not urls_text:
            flash("请先粘贴至少一条微信公众号文章链接。")
            return redirect(url_for("index"))

        # 允许用户一行一个链接
        urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
        if not urls:
            flash("未检测到有效链接，请检查输入。")
            return redirect(url_for("index"))

        # 用 Playwright 处理所有链接
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ],
                )
                context = browser.new_context()
                page = context.new_page()

                pdf_results = []

                for url in urls:
                    if not url.startswith("http"):
                        # 简单判断，不是 http 开头的就跳过
                        continue
                    try:
                        filename, pdf_bytes = download_single_article(page, url)
                        pdf_results.append((filename, pdf_bytes))
                    except Exception as e:
                        print(f"[ERROR] 下载失败: {url} - {e}")

                browser.close()

        except Exception as e:
            print("[FATAL] Playwright 运行错误：", e)
            flash("下载时发生错误，请检查终端输出或稍后再试。")
            return redirect(url_for("index"))

        if not pdf_results:
            flash("所有链接下载失败，请确认链接是否为有效的公众号文章。")
            return redirect(url_for("index"))

        # 如果只有一个 PDF，就直接把单个 PDF 返回给用户
        if len(pdf_results) == 1:
            filename, pdf_bytes = pdf_results[0]
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )

        # 多个 PDF，打包成一个 ZIP 返回
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename, pdf_bytes in pdf_results:
                zf.writestr(filename, pdf_bytes)
        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="wechat_articles.zip",
        )

    # GET 请求直接渲染页面
    return render_template("index.html")


if __name__ == "__main__":
    # 默认本地启动 http://127.0.0.1:5000
    app.run(debug=True)
