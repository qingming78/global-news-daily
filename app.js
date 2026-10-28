// 全球大事日报 · 前端：只负责读 data/latest.json 并展示，不写任何内容。
// 每天的新内容由 GitHub Actions 跑 scripts/fetch_daily.py 写入 JSON。

let edition = null;
let current = 0; // 当前打开的条目下标

const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));

async function load() {
  try {
    const res = await fetch("data/latest.json", { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    edition = await res.json();
  } catch (e) {
    $("edition-meta").textContent = "今日内容加载失败，请检查网络后刷新（" + e.message + "）。";
    return;
  }
  const d = new Date(edition.date + "T08:00:00+08:00");
  const week = "日一二三四五六"[d.getDay()];
  $("edition-meta").textContent =
    `${edition.date} 星期${week} · ${edition.stories.length} 条` +
    (edition.sample ? " · 示例版" : "");
  $("edition-note").textContent = edition.note || "";
  renderList();
}

function filtered() {
  const f = $("filter").value;
  return edition.stories.filter((s) => !f || s.category === f);
}

function renderList() {
  const list = filtered();
  $("count").textContent = `共 ${list.length} 条`;
  $("story-list").innerHTML = list.map((s) => {
    const idx = edition.stories.indexOf(s);
    const thinker = s.person_name
      ? `<p class="thinker">${esc(s.person_name)}（${esc(s.person_role || "")}）<br><strong>他认为：</strong>${esc(s.core_judgment || "")}</p>`
      : `<p class="thinker"><span class="badge-pending">待补充人物思考</span></p>`;
    const sample = s.title.startsWith("示例") ? ` <span class="badge-sample">示例</span>` : "";
    const cover = (s.images && s.images.length)
      ? `<img class="cover" src="${esc(s.images[0].url)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none'">`
      : "";
    return `<li data-idx="${idx}">
      <span class="rank">${s.rank}</span><span class="cat">${esc(s.category)}</span>${sample}
      <h2>${esc(s.title)}</h2>
      ${cover}
      <p>${esc(s.summary)}</p>
      ${thinker}
    </li>`;
  }).join("");
  document.querySelectorAll("#story-list li").forEach((li) => {
    li.addEventListener("click", () => openDetail(Number(li.dataset.idx)));
  });
}

function openDetail(idx) {
  current = idx;
  const s = edition.stories[idx];
  $("list-view").hidden = true;
  $("detail-view").hidden = false;
  window.scrollTo(0, 0);

  const reasoning = (s.reasoning && s.reasoning.length)
    ? `<h3>他的推理链</h3><ul>${s.reasoning.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>`
    : "";
  const quote = s.key_quote
    ? `<h3>原话</h3><blockquote>“${esc(s.key_quote)}”</blockquote>`
    : "";
  const thinking = s.person_name ? `
    <h3>他面临的问题</h3><p>${esc(s.thinking_question || "")}</p>
    <h3>他的核心判断</h3><p>${esc(s.core_judgment || "")}</p>
    ${reasoning}${quote}
    <h3>背景</h3><p>${esc(s.background || "")}</p>
    <h3>接下来看他做什么</h3><p>${esc(s.watch_next || "")}</p>
  ` : `
    <h3>人物思考</h3><p><span class="badge-pending">待补充人物思考</span></p>
    <p>${esc(s.thinking_status || "本条由自动抓取生成，只有标题与摘要，未生成人物思考。")}</p>
  `;
  const sources = (s.sources && s.sources.length)
    ? `<h3>来源</h3><ul class="sources">${s.sources.map((x) =>
        `<li><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title || x.url)}</a></li>`).join("")}</ul>`
    : "";
  const figures = (s.images && s.images.length)
    ? `<div class="detail-images">${s.images.map((im) => {
        const cap = [im.caption, im.credit].filter(Boolean).join(" · ");
        return `<figure class="detail-img"><img src="${esc(im.url)}" alt="${esc(im.caption || "")}" loading="lazy" referrerpolicy="no-referrer" onerror="this.closest('figure').style.display='none'">${cap ? `<figcaption>${esc(cap)}</figcaption>` : ""}</figure>`;
      }).join("")}</div>`
    : "";

  $("detail").innerHTML = `
    <p><span class="rank">${s.rank}</span><span class="cat">${esc(s.category)}</span></p>
    <h2>${esc(s.title)}</h2>
    <p>${esc(s.summary)}</p>
    ${figures}
    ${s.person_name ? `<p><strong>${esc(s.person_name)}</strong> · ${esc(s.person_role || "")}</p>` : ""}
    ${thinking}${sources}`;
  $("prev-btn").disabled = idx <= 0;
  $("next-btn").disabled = idx >= edition.stories.length - 1;
}

function closeDetail() {
  $("detail-view").hidden = true;
  $("list-view").hidden = false;
}

$("filter").addEventListener("change", renderList);
$("back-btn").addEventListener("click", closeDetail);
$("prev-btn").addEventListener("click", () => { if (current > 0) openDetail(current - 1); });
$("next-btn").addEventListener("click", () => { if (current < edition.stories.length - 1) openDetail(current + 1); });

load();
