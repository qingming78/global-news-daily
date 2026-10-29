# 每天一位权威人物 · 免费版

一个每天自动更新的“人物思考”页面，**不用买服务器，不花一分钱**。

思路就是之前说的那句：**内容不在 App 里，在服务器上**——这里的“服务器”
是 GitHub 免费提供的两样东西：GitHub Pages（放网页）和 GitHub Actions
（每天定时跑脚本、写新内容）。手机打开网页就能看，每天 8 点自动出新的一期。

每天只推一个人：从当天新闻里选出一位权威人物，读他对一件事的深度思考——
他面临的问题、核心判断、推理链、原话、背景，以及接下来看他做什么。
往期人物会留在页面下方的“往期人物”里，可以点开回看。

> 这个版本已经上线，每天 08:00 自动更新，网址是
> https://qingming78.github.io/global-news-daily/

---

## 一、它是怎么每天更新的

```
每天 08:00（北京时间）
      │
      ▼
GitHub Actions 定时运行 scripts/fetch_daily.py
      │  抓公开 RSS（TechCrunch、MIT Tech Review、BBC 等），取 10 条候选
      ▼
scripts/generate_thinking.py（需要 DEEPSEEK_API_KEY）
      │  对每条打开原文，用 DeepSeek 提炼人物思考，原话逐字校验；
      │  正文主体用第一人称写一段较长的自述，尽量展现他本人的原观点
      ▼
scripts/pick_feature.py
      │  按评分选出当天一位人物，把当期改写为 1 条特写，
      │  并把他追加到 data/archive.json（往期档案）
      ▼
写出 data/editions/2026-10-29.json，并更新 data/latest.json
      │  提交回仓库
      ▼
GitHub Pages 重新发布
      │
      ▼
你打开网页 → 前端读 data/latest.json → 显示今天的一位人物
```

关键点：前端（`index.html`）里**没有任何新闻内容**，它每次打开都去读
`data/latest.json`。内容变了，页面就变了，App 本身不用重新打包。

---

## 二、每个文件是干什么的

| 文件 / 文件夹 | 作用 |
|---|---|
| `index.html` | 页面骨架：今日人物特写 + 往期人物档案 |
| `style.css` | 排版样式（手机优先） |
| `app.js` | 读 `data/latest.json`，渲染今日人物；读 `data/archive.json`，点开往期 |
| `data/latest.json` | **今天那期**（只有 1 条特写），前端只读这一个文件 |
| `data/editions/2026-10-28.json` | 每一期的存档，按日期命名；首期是马斯克专访特写 |
| `data/archive.json` | 往期档案：日期、人物、标题、核心判断，按新到旧排列 |
| `scripts/fetch_daily.py` | 每天跑的脚本：抓 RSS → 去重 → AI 优先排前 10 → 写 JSON。只用 Python 标准库，不用装任何包。同时从 RSS 里取配图（media:content / enclosure / 正文里的第一张图） |
| `scripts/generate_thinking.py` | 抓取后跑：对每条打开原文链接，用 DeepSeek 从原文里提炼人物思考。文风：正文主体是第一人称长文（`first_person`，600–1200 字，3–5 段），尽量展现他本人的原观点和思考过程，篇幅长一点也没关系；核心判断和推理链也用第一人称；第三人称只出现在开头的概括（`summary`）里。原话逐字校验，找不到就留空。需要 `DEEPSEEK_API_KEY`，没有时自动跳过。RSS 没给图时，用原文的 og:image 封面图兜底 |
| `scripts/pick_feature.py` | 选人脚本：从补好思考的 10 条里选出当天一位（评分规则见下），把当期改写为 1 条特写，并更新 `data/archive.json`。当天没有任何一条有人物思考时，取 rank 1 的那条兜底（页面显示“待补充人物思考”，日报不断更） |
| `.github/workflows/daily.yml` | 定时任务配置：每天 00:00 UTC（= 北京时间 08:00）运行一次，也可手动触发；00:15、00:30 UTC 各有一次兜底运行（GitHub 定时任务偶尔会晚到或跳过，兜底时如果今天的特写已生成会自动跳过，不重复出两期） |
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
  "core_judgment": "我认为：……",
  "first_person": "用第一人称写的一段较长自述，600–1200 字，分段……",
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
   手机浏览器打开这个网址，就能看到今天的一位人物。

### 第 4 步：确认定时任务开了

1. 进仓库 → 顶部 `Actions` 标签页。
2. 左边应该能看到 `每日生成日报` 这个 workflow。
3. 点它 → 点 `Run workflow` → `Run workflow`，手动跑一次。
   跑完（约 1 分钟），`data/editions/` 里会多出今天那期，
   网页刷新后就变成今天选出的那位人物。
4. 以后每天北京时间 08:00 它会自动跑，不用你管。
   想检查有没有跑成，就来看 `Actions` 里的运行记录：绿色 ✅ 就是成功。

### 第 5 步（可选）：在手机上像 App 一样用

手机浏览器打开网址 → 菜单 → **添加到主屏幕**。桌面会出现一个图标，
点开就是全屏的日报，和装了 App 差不多。

---

## 四、v1 做不到的事（先说清楚）

- **每天只有一位人物**：10 条候选里按评分选出一位（有原话 +3、AI科技 +2、
  推理链每条 +1、背景 +1，同分取 rank 更靠前的）。当天没有任何一条有
  人物思考时，取 rank 1 的那条兜底，页面显示“待补充人物思考”，日报不断更。
- **人物思考需要一个 DeepSeek key 才能开**：自动抓到的 10 条默认只有标题、
  摘要、来源链接，人物思考字段是空的，页面上会显示“待补充人物思考”。
  不是技术上做不到，是 v1 没有接任何 AI 接口，**绝不从标题推断某个人说了什么**，
  那样就是编造原话。接 key 的方法见第五节，脚本已经写好了。
- **没有推送通知**：GitHub Pages 是静态网页，不会主动给你发消息。
  每天 8 点你自己打开看，或者以后再加。
- **没有登录 / 收藏 / 评论**：静态网页 + JSON 存数据，做不了账号系统。
  要这些功能，得再接一个免费数据库（比如 Supabase），那是下一步。
- **图片来自原文，不是现找的**：每条优先用 RSS 自带的配图，没有时用原文页的
  og:image 封面图兜底；两个都没有就留空不显示。图片只做展示、标明来源
  （如“图片来源：TechCrunch”），不下载到仓库里。极少数来源防盗链打不开的
  图片，页面会自动隐藏，不会留一个裂开的图。

---

## 五、人物思考怎么加上（脚本已写好，只差你的 key）

原理很简单，`daily.yml` 现在是三步：先跑 `fetch_daily.py` 抓 10 条候选，
再跑 `generate_thinking.py`，对每条打开原文链接、读正文，
调 DeepSeek 从**原文**里提炼那个人物的核心判断、推理链和原话，
最后跑 `pick_feature.py`，按评分选出当天一位，写回 JSON。
前端不用改，字段一填上，页面就自动显示今天的那个人。

文风是这样定的：正文主体是目标人物**自己的话**——用第一人称写一段
较长的自述（600–1200 字），尽量展现他本人的原观点和思考过程，篇幅
长一点也没关系；核心判断和推理链也用第一人称。第三人称只出现在开头
的一句话概括（`summary`）里，概括整件事就行。背景和“接下来看他做
什么”仍是第三人称的补充信息。

防编造有三道关，都是写在脚本里的：

1. **只从原文提炼**：原文打不开、原文里找不到明确表达观点的人物，
   就留空，不编。
2. **原话逐字校验**：模型给出的原话，必须在原文里一字不差地出现，
   否则删掉这句原话（只保留提炼出的判断）。
3. **人名校验**：人名也必须在原文里出现，否则整条思考作废，
   防止把 A 的话安到 B 头上。

你需要做的只有两步：

### 第 1 步：弄一个 DeepSeek 的 key

1. 打开 platform.deepseek.com，注册 / 登录（手机号就行）。
2. 左边进 `API keys` → `Create new API key`，起个名字比如 `global-news`，
   点创建，**把 key 复制下来，只显示这一次**。
3. 费用：DeepSeek 很便宜，每天 10 条按官方价目表大约几分钱，
   充 10 块钱能用很久。具体以 DeepSeek 账单为准。

### 第 2 步：把 key 存到仓库的 Secret 里

1. 进仓库 → `Settings` → 左边 `Secrets and variables` → `Actions`。
2. 点 `New repository secret`，名字填 `DEEPSEEK_API_KEY`，
   值粘贴你的 key，点 `Add secret`。
3. key 只存在 GitHub 的 Secret 里，不会写进代码、不会出现在网页上。

### 第 3 步：把更新过的文件传上去

这次改版改了 9 个文件（我重新打的包里都有）：

| 文件 | 变化 |
|---|---|
| `scripts/pick_feature.py` | 新增，每天选出一位人物的脚本 |
| `scripts/generate_thinking.py` | 改了，提炼改成第一人称长文（新增 `first_person` 字段，推理链上限提到 6 条） |
| `.github/workflows/daily.yml` | 改了，加了“选出今天的一位人物”这一步 |
| `index.html` / `app.js` / `style.css` | 改了，改成单人特写 + 往期档案 |
| `data/latest.json` / `data/editions/2026-10-28.json` | 改了，今天这期改成马斯克专访特写 |
| `data/archive.json` | 新增，往期人物档案 |
| `README.md` | 改了，就是这份说明 |

传上去后，不用手动跑 workflow——今天这期已经是马斯克特写；
从明天 08:00 起，每天自动选出新的一位。

没加 key 之前也不用担心：脚本会自己跳过（日志里写 `[skip]`），
日报照常出 10 条，只是不带人物思考。

---

## 六、本地测试（改代码时用）

```bash
# 检查 JSON 格式
python3 -m json.tool data/latest.json > /dev/null && echo OK

# 手动跑一次抓取（写到 /tmp，不动仓库里的数据）
python3 scripts/fetch_daily.py --date 2026-10-28 --out-dir /tmp/news-test

# 人物思考脚本（没 key 时自动跳过；有 key 时对 /tmp 里那期补思考）
DEEPSEEK_API_KEY=sk-... python3 scripts/generate_thinking.py --edition /tmp/news-test/2026-10-28.json

# 本地看页面
python3 -m http.server 8000
# 浏览器打开 http://localhost:8000/
```
