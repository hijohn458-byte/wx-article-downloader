# ✅ 使用和 Playwright 1.56 匹配的官方镜像
FROM mcr.microsoft.com/playwright/python:v1.56.0-jammy

# 在容器里工作目录
WORKDIR /app

# 先拷贝依赖文件
COPY requirements.txt .

# 安装 Python 依赖（注意这里不要再安装别的 Playwright 版本）
RUN pip install --no-cache-dir -r requirements.txt

# 再拷贝项目代码
COPY . .

# Render 的 free 实例固定监听 10000 端口，日志里之前也是 10000，就继续用它
EXPOSE 10000

# 启动 Flask 应用（通过 gunicorn）
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]
