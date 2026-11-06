// API_BASE aur api() common.js mein hain
const $ = (id) => document.getElementById(id);
const tip = $("tooltip");

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---- Tooltip ----
function attachTip(el, html) {
  el.addEventListener("mousemove", (e) => {
    tip.innerHTML = html;
    tip.classList.remove("hidden");
    tip.style.left = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8) + "px";
    tip.style.top = e.clientY + 14 + "px";
  });
  el.addEventListener("mouseleave", () => tip.classList.add("hidden"));
}

async function getJSON(path) {
  const res = await api(path);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Server error");
  return data;
}

// ---- Stats + daily chart ----
function renderStats(s) {
  $("tTotal").textContent = s.total;
  $("tFake").textContent = s.fake;
  $("tReal").textContent = s.real;
  $("tConf").textContent = s.total ? s.avg_confidence + "%" : "–";

  // Pichhle 14 din (khaali din bhi dikhao)
  const byDay = Object.fromEntries(s.daily.map((d) => [d.day, d]));
  const days = [];
  for (let i = 13; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    days.push({ key, label: `${d.getDate()}/${d.getMonth() + 1}`, fake: byDay[key]?.fake || 0, real: byDay[key]?.real || 0 });
  }
  const max = Math.max(1, ...days.map((d) => d.fake + d.real));
  const chart = $("dailyChart");
  chart.innerHTML = "";

  if (!s.total) {
    chart.innerHTML = `<div class="empty">Abhi koi check nahi hua. Checker page par news check karo.</div>`;
    return;
  }

  days.forEach((d) => {
    const col = document.createElement("div");
    col.className = "vcol";
    const h = (n) => (n / max) * 170;
    col.innerHTML = `
      <div class="vstack">
        ${d.real ? `<div class="vseg real" style="height:${h(d.real)}px"></div>` : ""}
        ${d.fake ? `<div class="vseg fake" style="height:${h(d.fake)}px"></div>` : ""}
      </div>
      <div class="vlabel">${d.label}</div>`;
    attachTip(col, `<b>${d.label}</b><br>Fake: ${d.fake}<br>Real: ${d.real}<br>Total: ${d.fake + d.real}`);
    chart.appendChild(col);
  });
}

// ---- Model comparison ----
function renderModels(info) {
  $("modelMeta").textContent =
    `Dataset: ${info.dataset.total.toLocaleString()} articles · Test set: ${info.dataset.test_size.toLocaleString()} · ` +
    `Trained: ${info.trained_at} · Live model: ${info.best_model}`;

  const chart = $("modelChart");
  chart.innerHTML = "";
  info.results.forEach((r) => {
    const acc = (r.accuracy * 100).toFixed(2);
    const row = document.createElement("div");
    row.className = "hrow";
    row.innerHTML = `
      <div class="hname">${esc(r.model)}${r.model === info.best_model ? '<span class="best-tag">★ best</span>' : ""}</div>
      <div class="htrack"><div class="hbar" style="width:${acc}%"></div></div>
      <div class="hval">${acc}%</div>`;
    const cm = r.confusion_matrix;
    attachTip(row, `<b>${esc(r.model)}</b><br>Accuracy: ${acc}%<br>F1: ${(r.f1 * 100).toFixed(2)}%<br>` +
      `Galat: ${cm.fake_as_real} fake→real, ${cm.real_as_fake} real→fake`);
    chart.appendChild(row);
  });

  $("modelTable").querySelector("tbody").innerHTML = info.results.map((r) => `
    <tr>
      <td>${esc(r.model)}</td>
      <td>${(r.accuracy * 100).toFixed(2)}%</td>
      <td>${(r.precision * 100).toFixed(2)}%</td>
      <td>${(r.recall * 100).toFixed(2)}%</td>
      <td>${(r.f1 * 100).toFixed(2)}%</td>
      <td>${r.train_seconds}s</td>
    </tr>`).join("");
}

// ---- History ----
function renderHistory(rows) {
  const body = $("historyTable").querySelector("tbody");
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="5" class="empty">Koi history nahi hai</td></tr>`;
    return;
  }
  body.innerHTML = rows.map((r) => {
    const news = r.source === "url"
      ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title || r.url)}</a>`
      : esc(r.snippet);
    const cls = r.prediction === "REAL" ? "real" : "fake";
    const icon = r.prediction === "REAL" ? "✅" : "❌";
    return `
      <tr>
        <td>${esc(r.created_at)}</td>
        <td>${r.source === "url" ? "🔗 URL" : "📝 Text"}</td>
        <td class="news" title="${esc(r.snippet)}">${news}</td>
        <td class="badge ${cls}">${icon} ${r.prediction}</td>
        <td>${r.confidence}%</td>
      </tr>`;
  }).join("");
}

async function load() {
  try {
    const [stats, info, hist] = await Promise.all([
      getJSON("/api/stats"),
      getJSON("/api/model-info").catch(() => null),
      getJSON("/api/history?limit=50"),
    ]);
    renderStats(stats);
    if (info) renderModels(info);
    renderHistory(hist);
    $("status").textContent = "";
  } catch (err) {
    $("status").className = "status error";
    $("status").textContent = err.message === "Failed to fetch"
      ? "Backend se connect nahi ho paya. Kya 'python backend\\app.py' chal raha hai?"
      : err.message;
  }
}

$("clearHistory").addEventListener("click", async () => {
  if (!confirm("Saari history delete karni hai?")) return;
  await api("/api/history", { method: "DELETE" });
  load();
});

load();
