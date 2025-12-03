````markdown
# 📰 wx-article-downloader  
**一个支持下载微信公众号文章的工具，保留原始排版、图片与样式，并可选下载评论。**

本工具旨在简化微信公众号文章保存过程，提供本地 HTML 保存方式，最大程度保留文章原貌，可用于备份、归档、内容收集、素材整理等场景。

---

## ✨ 功能特点

- **🖨 完整下载微信公众号文章**
  - 标题、作者、发布时间
  - 正文排版、图片、视频封面
  - 文章样式尽可能保持原样

- **💬（可选）下载评论列表**
  - 一级评论
  - 评论点赞数、昵称、时间
  - 下载为 JSON / HTML

- **🌐 支持多种页面结构**
  - 自动处理 WeChat 防盗链
  - 自动修复图片链接（wximg）

- **🖥 提供 GUI / Web 页面**
  - 输入文章 URL → 一键下载
  - 适合普通用户无需命令行

- **👍 轻量、跨平台、无侵入**
  - 支持 Windows / macOS / Linux

---

## 📦 安装与依赖

确保你的电脑已安装：

- **Python 3.10+**
- `pip`

然后安装依赖：

```bash
pip install -r requirements.txt
````

> 如果你使用 Playwright（爬取动态评论），需要额外执行：

```bash
playwright install
```

---

## 🚀 使用方法

### **方式 1：使用 GUI（推荐）**

运行：

```bash
python app.py
```

打开界面后：

1. 粘贴微信公众号文章链接
2. 点击 **下载**
3. 自动生成本地 HTML 文件

---

### **方式 2：命令行用法**

```bash
python main.py "https://mp.weixin.qq.com/s/XXXXXX"
```

输出目录（示例）：

```
output/
 └── 文章标题/
      ├── index.html
      ├── images/
      └── comments.json  （如果开启了评论下载）
```

---

## 📁 项目结构

```
wx-article-downloader/
├── wechat_article_downloader/
│   ├── downloader.py          # 核心下载逻辑
│   ├── html_renderer.py       # 保存排版
│   ├── comment_fetcher.py     # 评论下载
│   ├── utils.py
│   ├── static/                # CSS/样式/模板
│   └── templates/             
├── app.py                     # GUI / Web 入口
├── main.py                    # CLI 入口
├── requirements.txt
└── README.md
```

> 注：根据你项目的实际结构可自行调整。

---

## 📸 使用界面截图（占位）

> 你可以将实际截图替换下图。

```
[ GUI Screenshot Here ]
```

---

## 🛠 部署到 Web（可选）

你可以将 Web 版本部署到：

### **🚀 方案 A：Vercel（最快）**

适合公开访问，无需服务器。

1. 创建项目（Python → Serverless Functions）
2. 上传代码
3. 绑定域名（可用 Cloudflare DNS）

### **☁ 方案 B：阿里云 / 腾讯云 服务器**

如果需要中国大陆用户更低延迟：

* 使用 Nginx 反向代理
* 运行 Flask/FastAPI Web 服务
* 根据要求备案（如大陆服务器）

---

## ⚖️ 合规性说明（请务必阅读）

本工具仅供 **学习交流与个人备份用途**。
请勿用于：

* 大规模爬取公众号文章
* 商用转载或分发
* 绕过微信安全策略

如用于公开服务，请提前评估：

* 是否涉及内容抓取合规性
* 是否需提示用户仅用于备份

---

## 🤝 贡献

欢迎提交：

* 代码优化
* Bug 修复
* 新功能 PR
* 新模板的样式改进

---

## 📄 License

**MIT License**

你可以自由使用、修改、分发此工具。

---

## ⭐ Star 支持一下！

如果这个工具对你有帮助，请给一个 **Star⭐**
你的支持是我持续优化的动力！

