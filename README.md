# 全球大事日报 · 免费版

一个每天自动更新的新闻日报，**不用买服务器，不花一分钱**。

思路就是之前说的那句：**内容不在 App 里，在服务器上**——这里的“服务器”
是 GitHub 免费提供的两样东西：GitHub Pages（放网页）和 GitHub Actions
（每天定时跑脚本、写新内容）。手机打开网页就能看，每天 8 点自动出新的一期。

> 注意：这个版本现在还**没有真正上线**。文件都在你电脑上，
> 按下面“10 分钟上线”做完，它才会在网上每天自动更新。

---

## 一、它是怎么每天更新的

```
每天 08:00（北京时间）
      │
      ▼
GitHub Actions 定时运行 scripts/fetch_daily.py
      │  抓公开 RSS（TechCrunch、MIT Tech Review、BBC 等）
      ▼
写出 data/editions/2026-10-29.json，并更新 data/latest.json
      │  提交回仓库
      ▼
GitHub Pages 重新发布
      │
      ▼
你打开网页 → 前端读 data/latest.json → 显示今天的 10 条
```

关键点：前端（`index.html`）里**没有任何新闻内容**，它每次打开都去读
`data/latest.json`。内容变了，页面就变了，App 本身不用重新打包。

---

## 二、每个文件是干什么的

| 文件 / 文件夹 | 作用 |
|---|---|
| `index.html` | 页面骨架：标题、分类筛选、列表、详情页 |
| `style.css` | 排版样式（手机优先） |
| `app.js` | 读 `data/latest.json`，渲染列表和详情，上一条 / 下一条 / 返回 |
| `data/latest.json` | **今天那期**，前端只读这一个文件 |
| `data/editions/2026-10-28.json` | 每一期的存档，按日期命名，示例版只有 3 条 |
| `scripts/fetch_daily.py` | 每天跑的脚本：抓 RSS → 去重 → AI 优先排前 10 → 写 JSON。只用 Python 标准库，不用装任何包 |
| `.github/workflows/daily.yml` | 定时任务配置：每天 00:00 UTC（= 北京时间 08:00）运行一次，也可手动触发 |
| `.nojekyll` | 告诉 GitHub Pages 不要用 Jekyll 处理，直接原样发布 |
| `README.md` | 就是这份说明 |

### 一条新闻的数据长什么样

每条新闻在 JSON 里是一个对象，格式沿用现在 Muse 版“人物思考”的格式：

```json
{
  "rank": 1,
  "category": "AI科技",
  "title": "黄仁勋：AI 的问题不是需求，是钱",
  "summary": "一句话摘要",
  "person_name": "黄仁勋",
  "person_role": "英伟达创始人兼 CEO",
  "thinking_question": "他面临的问题",
  "core_judgment": "他认为：……",
  "reasoning": ["推理链第 1 步", "推理链第 2 步"],
  "key_quote": "可核实的原话",
  "background": "背景",
  "watch_next": "接下来看他做什么",
  "sources": [{"title": "来源标题", "url": "https://…"}],
  "images": []
}
```

---

## 三、10 分钟上线（全免费）

### 第 1 步：新建一个 GitHub 仓库

1. 打开 GitHub，点右上角 `+` → `New repository`。
2. 名字随便起，比如 `global-news-daily`，选 **Public**（公开仓库才能用免费 Pages）。
3. 不要勾选“Add a README”，建一个空仓库。

### 第 2 步：把这些文件传上去

在电脑上打开这个文件夹，用下面两种办法任选一种：

- **网页上传**：在仓库页面点 `Add file` → `Upload files`，把本文件夹里的
  全部文件（包括 `.github` 这个隐藏文件夹）拖进去，点 `Commit changes`。
- **命令行**（以后会学到，现在不用会也可以）：
  ```bash
  git init
  git add .
  git commit -m "全球大事日报免费版 v1"
  git branch -M main
  git remote add origin https://github.com/你的用户名/global-news-daily.git
  git push -u origin main
  ```

### 第 3 步：打开 GitHub Pages

1. 进仓库 → `Settings` → 左边找到 `Pages`。
2. `Build and deployment` → `Source` 选 **Deploy from a branch**，
   `Branch` 选 `main`，文件夹选 `/ (root)`，点 `Save`。
3. 等 1–2 分钟，页面顶部会出现你的网址，形如
   `https://你的用户名.github.io/global-news-daily/`。
   手机浏览器打开这个网址，就能看到今天这期（现在是 3 条示例数据）。

### 第 4 步：确认定时任务开了

1. 进仓库 → 顶部 `Actions` 标签页。
2. 左边应该能看到 `每日生成日报` 这个 workflow。
3. 点它 → 点 `Run workflow` → `Run workflow`，手动跑一次。
   跑完（约 1 分钟），`data/editions/` 里会多出今天那期，
   网页刷新后就变成真实抓取的 10 条。
4. 以后每天北京时间 08:00 它会自动跑，不用你管。
   想检查有没有跑成，就来看 `Actions` 里的运行记录：绿色 ✅ 就是成功。

### 第 5 步（可选）：在手机上像 App 一样用

手机浏览器打开网址 → 菜单 → **添加到主屏幕**。桌面会出现一个图标，
点开就是全屏的日报，和装了 App 差不多。

---

## 四、v1 做不到的事（先说清楚）

- **没有 AI 生成的人物思考**：自动抓到的 10 条只有标题、摘要、来源链接，
  人物思考字段是空的，页面上会显示“待补充人物思考”。
  原因是 v1 没有接任何 AI 接口，**绝不从标题推断某个人说了什么**，
  那样就是编造原话。
- **没有推送通知**：GitHub Pages 是静态网页，不会主动给你发消息。
  每天 8 点你自己打开看，或者以后再加。
- **没有登录 / 收藏 / 评论**：静态网页 + JSON 存数据，做不了账号系统。
  要这些功能，得再接一个免费数据库（比如 Supabase），那是下一步。
- **图片是空的**：RSS 里一般不带可用图片，v1 的 `images` 是空数组，
  页面只显示文字。

---

## 五、以后怎么加 AI 生成（C 考完再做）

等你有了 LLM 的 API key（比如 OpenAI / DeepSeek / 通义等，哪个便宜用哪个），
再做这一步，现在不用：

1. 在仓库 `Settings` → `Secrets and variables` → `Actions` 里加一个
   Secret，名字叫 `LLM_API_KEY`，值就是你的 key（不要写进代码里）。
2. 在 `.github/workflows/daily.yml` 里把 key 传给脚本：
   ```yaml
   env:
     LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
   ```
3. 写一个新脚本 `scripts/generate_thinking.py`：读当天抓到的 10 条，
   对每条去找原始采访 / 演讲 / 财报电话会等一手来源，
   只从一手来源里提炼人物的核心判断和原话，找不到就留空、不要这条。
   绝不允许模型凭空编一句“他认为”。
4. 让 `daily.yml` 先跑 `fetch_daily.py`，再跑 `generate_thinking.py`，
   最后一起提交。

这一步是整个项目最难也最值钱的部分，放到 C 考试之后，
Python 学到能写脚本了再动手，正好当练手项目。

---

## 六、本地测试（改代码时用）

```bash
# 检查 JSON 格式
python3 -m json.tool data/latest.json > /dev/null && echo OK

# 手动跑一次抓取（写到 /tmp，不动仓库里的数据）
python3 scripts/fetch_daily.py --date 2026-10-28 --out-dir /tmp/news-test

# 本地看页面
python3 -m http.server 8000
# 浏览器打开 http://localhost:8000/
```
