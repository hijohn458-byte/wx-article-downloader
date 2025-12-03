import os
import io
import re
import zipfile
import traceback
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    send_file,
    flash,
)

from playwright.sync_api import sync_playwright

# -------------------------------------------------
# Flask 基础配置
# -------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")


# -------------------------------------------------
# 工具函数
# -------------------------------------------------
WECHAT_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/16.0 Mobile/15E148 Safari/604.1 "
    "MicroMessenger/8.0.47(0x18002F2C) NetType/WIFI Language/zh_CN"
)


def sanitize_filename(name: str, default: str = "wechat-article") -> str:
    """把网页标题变成安全的文件名."""
    if not name:
        name = default

    # 去掉前后空格
    name = name.strip()

    # Windows / Linux / macOS 中不允许的字符
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)

    # 避免空文件名
    if not name:
        name = default

    # 长度限制，防止路径过长
    if len(name) > 80:
        name = name[:80]

    return name


def generate_pdfs_for_urls(urls):
    """
    使用 Playwright 把多个微信文章链接转成 PDF。
    返回值：
        - files: 生成的 PDF 本地路径列表
    """
    files = []

    # 用临时目录存放 PDF
    tmp_dir = "/tmp/wx_article_pdfs"
    os.makedirs(tmp_dir, exist_ok=True)

    with sync_playwright() as p:
        # Render 上必须加上这些 sandbox 相关参数
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        # 用接近微信内置浏览器的 UA，附带 Referer，避免被拦截
        context = browser.new_context(
            user_agent=WECHAT_MOBILE_UA,
            viewport={"width": 1280, "height": 720},
            device_scale_factor=2,
            locale="zh-CN",
            extra_http_headers={
                "Referer": "https://mp.weixin.qq.com/",
                "Accept-Language": "zh-CN,zh;q=0.9",
            },
        )

        page = context.new_page()

        for idx, url in enumerate(urls, start=1):
            print(f"[INFO] 开始处理第 {idx} 条链接：{url}", flush=True)

            try:
                # 打开链接，等待网络空闲
                page.goto(url, wait_until="networkidle", timeout=60_000)
                # 再额外等一会儿，保证懒加载图片加载出来
                page.wait_for_timeout(2_000)

                # 读取标题
                try:
                    title = page.title()
                except Exception:
                    title = f"article-{idx}"

                safe_title = sanitize_filename(title, f"article-{idx}")
                pdf_path = os.path.join(tmp_dir, f"{safe_title}.pdf")

                print(f"[INFO] 生成 PDF: {pdf_path}", flush=True)

                page.pdf(
                    path=pdf_path,
                    format="A4",
                    print_background=True,
                    margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"},
                )

                files.append(pdf_path)

            except Exception as e:
                # 某一条失败了，记录日志，继续处理后面的
                print(f"[ERROR] 处理链接失败：{url}", flush=True)
                traceback.print_exc()
                continue

        context.close()
        browser.close()

    return files


# -------------------------------------------------
# Flask 路由
# -------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        raw_text = request.form.get("urls", "").strip()

        if not raw_text:
            flash("请粘贴至少一条微信公众号文章链接。")
            return render_template("index.html")

        # 支持多行，一行一条链接
        urls = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if not urls:
            flash("未检测到有效链接，请检查后重试。")
            return render_template("index.html")

        try:
            pdf_files = generate_pdfs_for_urls(urls)

            if not pdf_files:
                flash("所有链接都下载失败，请稍后重试。")
                return render_template("index.html")

            # 只有一篇文章：直接返回 PDF
            if len(pdf_files) == 1:
                pdf_path = pdf_files[0]
                filename = os.path.basename(pdf_path)
                return send_file(
                    pdf_path,
                    mimetype="application/pdf",
                    as_attachment=True,
                    download_name=filename,
                )

            # 多篇文章：打包成 ZIP 返回
            mem = io.BytesIO()
            with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in pdf_files:
                    arcname = os.path.basename(path)
                    zf.write(path, arcname=arcname)

            mem.seek(0)
            zip_name = f"wechat_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

            return send_file(
                mem,
                mimetype="application/zip",
                as_attachment=True,
                download_name=zip_name,
            )

        except Exception as e:
            print("[FATAL] 下载流程出错：", e, flush=True)
            traceback.print_exc()
            flash("下载时发生错误，请检查服务端日志或稍后再试。")
            return render_template("index.html")

    # GET 请求：只渲染页面
    return render_template("index.html")


# -------------------------------------------------
# 本地调试入口
# -------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
