// 每天一位权威人物 · 前端：只负责读 JSON 并展示，不写任何内容。
// 每天的新内容由 GitHub Actions 生成，写入 data/latest.json；
// 往期档案在 data/archive.json，点开某期读 data/editions/<日期>.json。

let currentDate = null;

const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));

async function loadEdition(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

function renderFeature(edition) {
  const s = (edition.stories || [])[0];
  currentDate = edition.date || null;
  if (!s) {
    $("feature").innerHTML = "<p>今天的内容还没有生成，请稍后再来。</p>";
    $("edition-meta").textContent = edition.date || "";
    return;
  }
  const d = new Date(edition.date + "T08:00:00+08:00");
  const week = "日一二三四五六"[d.getDay()];
  $("edition-meta").textContent =
    `${edition.date} 星期${week} · ${s.person_name || "今日人物"} · ${s.category || ""}`;

  const reasoning = (s.reasoning && s.reasoning.length)
    ? `<h3>他的推理链</h3><ol class="reasoning">${s.reasoning.map((r) => `<li>${esc(r)}</li>`).join("")}</ol>`
    : "";
  const quote = s.key_quote
    ? `<h3>原话</h3><blockquote>“${esc(s.key_quote)}”</blockquote>`
    : "";
  const figures = (s.images && s.images.length)
    ? `<div class="detail-images">${s.images.map((im) => {
        const cap = [im.caption, im.credit].filter(Boolean).join(" · ");
        return `<figure class="detail-img"><img src="${esc(im.url)}" alt="${esc(im.caption || "")}" loading="lazy" referrerpolicy="no-referrer" onerror="this.closest('figure').style.display='none'">${cap ? `<figcaption>${esc(cap)}</figcaption>` : ""}</figure>`;
      }).join("")}</div>`
    : "";
  const sources = (s.sources && s.sources.length)
    ? `<h3>来源</h3><ul class="sources">${s.sources.map((x) =>
        `<li><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title || x.url)}</a></li>`).join("")}</ul>`
    : "";
  const firstPerson = (s.first_person || "").trim()
    ? `<h3>以他自己的话说</h3>${s.first_person.split(/\n\s*\n/).map((p) => `<p>${esc(p.trim())}</p>`).join("")}`
    : "";
  const thinking = s.person_name ? `
    <h3>他面临的问题</h3><p>${esc(s.thinking_question || "")}</p>
    <h3>他的核心判断</h3><p>${esc(s.core_judgment || "")}</p>
    ${firstPerson}
    ${reasoning}${quote}
    <h3>背景</h3><p>${esc(s.background || "")}</p>
    <h3>接下来看他做什么</h3><p>${esc(s.watch_next || "")}</p>
  ` : `
    <h3>人物思考</h3>
    <p>${esc(s.thinking_status || "本条由自动抓取生成，只有标题与摘要，未生成人物思考。")}</p>
  `;

  $("feature").innerHTML = `
    <p class="feature-kicker">${esc(s.category || "")}</p>
    <h2>${esc(s.title)}</h2>
    <p class="feature-summary">${esc(s.summary)}</p>
    ${figures}
    ${s.person_name ? `<div class="person-card">
      <p class="person-name">${esc(s.person_name)}</p>
      <p class="person-role">${esc(s.person_role || "")}</p>
    </div>` : ""}
    ${thinking}${sources}`;
  $("edition-note").textContent = edition.note || "";
}

async function loadArchive() {
  try {
    const res = await fetch("data/archive.json", { cache: "no-store" });
    if (!res.ok) return;
    const archive = await res.json();
    const past = archive.filter((e) => e.date !== currentDate);
    if (!past.length) {
      $("archive-note").textContent = "从明天起，这里会列出往期人物。";
      return;
    }
    $("archive-list").innerHTML = past.map((e) => `
      <li data-date="${esc(e.date)}">
        <span class="archive-date">${esc(e.date)}</span>
        <strong>${esc(e.person_name || "（未记录人物）")}</strong>
        <span class="archive-title">${esc(e.title || "")}</span>
      </li>`).join("");
    document.querySelectorAll("#archive-list li").forEach((li) => {
      li.addEventListener("click", async () => {
        try {
          const edition = await loadEdition(`data/editions/${li.dataset.date}.json`);
          renderFeature(edition);
          $("today-btn").hidden = false;
          window.scrollTo(0, 0);
        } catch (e) {
          $("archive-note").textContent = "这期内容加载失败，请检查网络后重试。";
        }
      });
    });
  } catch (e) {
    // 档案加载失败就不显示，不影响今天的内容
  }
}

async function load() {
  try {
    const edition = await loadEdition("data/latest.json");
    renderFeature(edition);
    loadArchive();
  } catch (e) {
    $("edition-meta").textContent = "今日内容加载失败，请检查网络后刷新（" + e.message + "）。";
  }
}

$("today-btn").addEventListener("click", async () => {
  try {
    const edition = await loadEdition("data/latest.json");
    renderFeature(edition);
    $("today-btn").hidden = true;
    window.scrollTo(0, 0);
  } catch (e) {
    $("edition-meta").textContent = "今日内容加载失败，请检查网络后刷新（" + e.message + "）。";
  }
});

load();
