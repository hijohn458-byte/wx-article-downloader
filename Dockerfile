# 1. 使用官方 Playwright Python 镜像
#    自带：Python + Playwright + Chromium（三大浏览器）+ 常用字体
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# 2. 工作目录
WORKDIR /app

# 3. 安装 Python 依赖（requirements.txt 已经包含 Flask、Gunicorn、Playwright）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 安装中文字体（解决 PDF 乱码）
RUN apt-get update && \
    apt-get install -y --no-install-recommends fonts-noto-cjk && \
    rm -rf /var/lib/apt/lists/*

# 5. 拷贝项目代码
COPY . .

# 6. Render 默认用 10000 端口，这里显式绑到 10000
ENV PORT=10000

# 7. 启动命令：用 gunicorn 跑 Flask 应用
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:10000"]
