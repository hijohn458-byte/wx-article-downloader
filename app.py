import os
import tempfile
import zipfile
import uuid

from flask import Flask, render_template, request, send_file, after_this_request
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# 模拟 iPhone 微信内置浏览器，避免出现“请在微信客户端打开链接”的提示页
WECHAT_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Mobile/15E148 MicroMessenger/8.0.42(0x18002a2b) NetType/WIFI Language/zh_CN"
)


def sanitize_filename(name: str, default: str) -> str:
    if not name:
        return default
    # 去掉文件名非法字符
    bad_chars = '\\/:*?"<>|'
    for ch in bad_chars:
        name = name.replace(ch, "_")
    name = name.strip()
    return name or default


def generate_pdf_for_url(p, url: str, index: int):
    """
    使用 Playwright 打开公众号文章，并导出为 PDF。
    返回：pdf_path, file_name（不带扩展名）
    """
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
    )

    context = browser.new_context(
        user_agent=WECHAT_UA,
        viewport={"width": 1280, "height": 720},
    )
    page = context.new_page()

    page.goto(url, wait_until="networkidle", timeout=60000)

    # 某些号会有“继续访问 / 点击此处打开正文”之类的中间页，这里尝试点掉
    try:
        if page.is_visible("text=继续访问"):
            page.click("text=继续访问")
            page.wait_for_timeout(2000)
        if page.is_visible("text=点击此处打开正文"):
            page.click("text=点击此处打开正文")
            page.wait_for_timeout(2000)
    except Exception:
        pass

    # 等待真正的文章内容加载出来
    page.wait_for_selector("div#js_content", timeout=30000)

    # 优先使用 h1#activity-name 作为标题
    title = page.title()
    try:
        article_title = page.text_content("h1#activity-name")
        if article_title:
            title = article_title.strip()
    except Exception:
        pass

    safe_name = sanitize_filename(title, f"article-{index+1}")
    pdf_path = os.path.join(tempfile.gettempdir(), f"{safe_name}.pdf")

    page.pdf(
        path=pdf_path,
        format="A4",
        print_background=True,
        margin={"top": "15mm", "bottom": "15mm", "left": "10mm", "right": "10mm"},
    )

    context.close()
    browser.close()

    return pdf_path, safe_name


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download():
    raw = request.form.get("urls", "").strip()
    urls = [u.strip() for u in raw.splitlines() if u.strip()]
    if not urls:
        return "请先粘贴至少一个链接", 400

    pdf_files = []

    with sync_playwright() as p:
        for idx, url in enumerate(urls):
            pdf_path, _ = generate_pdf_for_url(p, url, idx)
            pdf_files.append(pdf_path)

    # 下载单个 PDF
    if len(pdf_files) == 1:
        pdf_path = pdf_files[0]
        filename = os.path.basename(pdf_path)

        @after_this_request
        def cleanup(response):
            try:
                os.remove(pdf_path)
            except FileNotFoundError:
                pass
            return response

        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf",
        )

    # 多个 PDF：打包成 ZIP
    zip_path = os.path.join(
        tempfile.gettempdir(), f"wx-articles-{uuid.uuid4().hex}.zip"
    )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for pdf_path in pdf_files:
            zf.write(pdf_path, arcname=os.path.basename(pdf_path))

    @after_this_request
    def cleanup_zip(response):
        for pdf_path in pdf_files:
            try:
                os.remove(pdf_path)
            except FileNotFoundError:
                pass
        try:
            os.remove(zip_path)
        except FileNotFoundError:
            pass
        return response

    return send_file(
        zip_path,
        as_attachment=True,
        download_name="wechat-articles.zip",
        mimetype="application/zip",
    )


if __name__ == "__main__":
    app.run(debug=True)
