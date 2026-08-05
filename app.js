const fallbackNotices = [
  {
    id: "demo-zju-cs-2026-pretui",
    school: "浙江大学",
    college: "计算机科学与技术学院",
    type: "预推免",
    title: "示例：2026 年接收推荐免试研究生报名通知",
    deadline: "2026-09-12T17:00:00+08:00",
    sourceUrl: "#",
    applyUrl: "#",
    tags: ["985", "211", "计算机", "预推免"],
    lastCheckedAt: "2026-08-05",
    verified: false,
    demo: true
  },
  {
    id: "demo-ucas-ai-2026-pretui",
    school: "中国科学院大学",
    college: "人工智能学院",
    type: "预推免",
    title: "示例：2026 年优秀大学生推免生报名通知",
    deadline: "2026-09-18T12:00:00+08:00",
    sourceUrl: "#",
    applyUrl: "#",
    tags: ["国科大", "中科院", "人工智能", "预推免"],
    lastCheckedAt: "2026-08-05",
    verified: false,
    demo: true
  },
  {
    id: "demo-buaa-cs-2026-summer",
    school: "北京航空航天大学",
    college: "计算机学院",
    type: "夏令营",
    title: "示例：2026 年全国优秀大学生夏令营活动通知",
    deadline: "2026-06-20T23:59:00+08:00",
    sourceUrl: "#",
    applyUrl: "#",
    tags: ["985", "211", "计算机", "夏令营"],
    lastCheckedAt: "2026-08-01",
    verified: false,
    demo: true
  }
];

const state = {
  notices: [],
  schools: [],
  query: "",
  tag: "all",
  type: "all",
  status: "all",
  sort: "deadlineAsc"
};

const $ = (selector) => document.querySelector(selector);
const formatter = new Intl.DateTimeFormat("zh-CN", {
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false
});

async function readJson(path, fallback) {
  try {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) throw new Error(`Failed to load ${path}`);
    return await response.json();
  } catch {
    return fallback;
  }
}

function getStatus(notice) {
  const now = new Date();
  const deadline = new Date(notice.deadline);
  const diffDays = Math.ceil((deadline - now) / 86400000);
  if (Number.isNaN(deadline.valueOf())) return { key: "open", text: "待核验", days: null };
  if (diffDays < 0) return { key: "closed", text: "已截止", days: diffDays };
  if (diffDays <= 7) return { key: "soon", text: `${diffDays} 天内截止`, days: diffDays };
  return { key: "open", text: `剩 ${diffDays} 天`, days: diffDays };
}

function normalizeText(value) {
  return String(value || "").trim().toLowerCase();
}

function matchesQuery(notice) {
  const text = [
    notice.school,
    notice.college,
    notice.type,
    notice.title,
    ...(notice.tags || [])
  ]
    .join(" ")
    .toLowerCase();
  return !state.query || text.includes(state.query);
}

function matchesFilters(notice) {
  const status = getStatus(notice).key;
  const tags = notice.tags || [];
  return (
    matchesQuery(notice) &&
    (state.tag === "all" || tags.includes(state.tag)) &&
    (state.type === "all" || notice.type === state.type) &&
    (state.status === "all" || status === state.status)
  );
}

function sortNotices(items) {
  return [...items].sort((a, b) => {
    if (state.sort === "schoolAsc") {
      return a.school.localeCompare(b.school, "zh-CN");
    }
    if (state.sort === "updatedDesc") {
      return new Date(b.lastCheckedAt || 0) - new Date(a.lastCheckedAt || 0);
    }
    return new Date(a.deadline || 0) - new Date(b.deadline || 0);
  });
}

function renderMetrics() {
  const statuses = state.notices.map(getStatus);
  const active = statuses.filter((item) => item.key === "open" || item.key === "soon").length;
  const urgent = statuses.filter((item) => item.key === "soon").length;
  const dates = state.notices
    .map((item) => item.lastCheckedAt)
    .filter(Boolean)
    .sort()
    .reverse();

  $("#activeCount").textContent = active;
  $("#urgentCount").textContent = urgent;
  $("#targetCount").textContent = state.schools.length || "待录入";
  $("#lastChecked").textContent = dates[0] || "-";
}

function renderRows() {
  const rows = sortNotices(state.notices.filter(matchesFilters));
  const body = $("#noticeBody");
  body.innerHTML = "";

  rows.forEach((notice) => {
    const status = getStatus(notice);
    const deadline = new Date(notice.deadline);
    const displayDeadline = Number.isNaN(deadline.valueOf())
      ? "待补充"
      : formatter.format(deadline);
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>
        <div class="school">
          <strong>${escapeHtml(notice.school)}</strong>
          <span>${escapeHtml(notice.college)}</span>
          <span>${escapeHtml(notice.title)}${notice.demo ? "（演示数据）" : ""}</span>
          <div class="tags">${(notice.tags || [])
            .map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`)
            .join("")}</div>
        </div>
      </td>
      <td>${escapeHtml(notice.type)}</td>
      <td><strong>${displayDeadline}</strong><div class="meta">${escapeHtml(notice.deadline || "")}</div></td>
      <td><span class="status ${status.key}">${escapeHtml(status.text)}</span></td>
      <td>
        <strong>${notice.verified ? "已核验" : "待核验"}</strong>
        <div class="meta">${escapeHtml(notice.lastCheckedAt || "-")}</div>
      </td>
      <td>
        <a class="link" href="${escapeAttribute(notice.sourceUrl || "#")}" target="_blank" rel="noreferrer">官方通知</a>
      </td>
    `;
    body.appendChild(tr);
  });

  $("#resultCount").textContent = `${rows.length} 条`;
  $("#emptyState").hidden = rows.length !== 0;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  const safe = String(value || "#");
  if (safe === "#" || safe.startsWith("http://") || safe.startsWith("https://")) {
    return escapeHtml(safe);
  }
  return "#";
}

function bindFilters() {
  $("#searchInput").addEventListener("input", (event) => {
    state.query = normalizeText(event.target.value);
    renderRows();
  });
  $("#tagFilter").addEventListener("change", (event) => {
    state.tag = event.target.value;
    renderRows();
  });
  $("#typeFilter").addEventListener("change", (event) => {
    state.type = event.target.value;
    renderRows();
  });
  $("#statusFilter").addEventListener("change", (event) => {
    state.status = event.target.value;
    renderRows();
  });
  $("#sortSelect").addEventListener("change", (event) => {
    state.sort = event.target.value;
    renderRows();
  });
  $("#resetButton").addEventListener("click", () => {
    state.query = "";
    state.tag = "all";
    state.type = "all";
    state.status = "all";
    state.sort = "deadlineAsc";
    $("#searchInput").value = "";
    $("#tagFilter").value = "all";
    $("#typeFilter").value = "all";
    $("#statusFilter").value = "all";
    $("#sortSelect").value = "deadlineAsc";
    renderRows();
  });
}

function bindEditor() {
  const form = $("#noticeForm");
  const preview = $("#jsonPreview");
  const today = new Date().toISOString().slice(0, 10);
  form.elements.lastCheckedAt.value = today;

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const school = data.get("school").trim();
    const college = data.get("college").trim();
    const type = data.get("type").trim();
    const deadline = `${data.get("deadline")}:00+08:00`;
    const tags = data
      .get("tags")
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
    const record = {
      id: `${slugify(school)}-${slugify(college)}-${Date.now()}`,
      school,
      college,
      type,
      title: data.get("title").trim(),
      deadline,
      sourceUrl: data.get("sourceUrl").trim(),
      applyUrl: data.get("sourceUrl").trim(),
      tags: tags.length ? tags : [type],
      lastCheckedAt: data.get("lastCheckedAt") || today,
      verified: true
    };
    preview.textContent = JSON.stringify(record, null, 2);
  });

  $("#copyJson").addEventListener("click", async () => {
    await navigator.clipboard.writeText(preview.textContent);
    $("#copyJson").textContent = "已复制";
    window.setTimeout(() => {
      $("#copyJson").textContent = "复制";
    }, 1200);
  });
}

function slugify(value) {
  return String(value)
    .toLowerCase()
    .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
}

async function init() {
  const [notices, schools] = await Promise.all([
    readJson("./data/notices.json", fallbackNotices),
    readJson("./data/schools.json", [])
  ]);
  state.notices = Array.isArray(notices) && notices.length ? notices : fallbackNotices;
  state.schools = Array.isArray(schools) ? schools : [];
  bindFilters();
  bindEditor();
  renderMetrics();
  renderRows();
}

init();
