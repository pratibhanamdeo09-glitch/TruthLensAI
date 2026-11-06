// API_BASE aur api() common.js mein hain
const $ = (id) => document.getElementById(id);
const textEl = $("newsText");
const urlEl = $("newsUrl");
const checkBtn = $("checkBtn");
const statusEl = $("status");
const resultEl = $("result");

let mode = "text";

function setStatus(msg, isError = false) {
  statusEl.textContent = msg;
  statusEl.className = "status" + (isError ? " error" : "");
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---- Tabs ----
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    mode = tab.dataset.tab;
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    $("panel-text").classList.toggle("hidden", mode !== "text");
    $("panel-url").classList.toggle("hidden", mode !== "url");
    setStatus("");
  });
});

textEl.addEventListener("input", () => {
  const n = textEl.value.trim() ? textEl.value.trim().split(/\s+/).length : 0;
  $("wordCount").textContent = n;
});

// ---- Explanation ----
function renderChips(el, words, cls) {
  el.innerHTML = words.length
    ? words.map((w) => `<span class="chip ${cls}" title="Score: ${w.score}">${escapeHtml(w.word)}</span>`).join("")
    : `<span class="none">Koi khaas shabd nahi mila</span>`;
}

function highlight(text, fakeWords, realWords) {
  // Har shabd (bigram ke dono hisse bhi) ko uske rang se mark karo
  const map = new Map();
  fakeWords.forEach((w) => w.word.split(" ").forEach((p) => p.length > 2 && map.set(p, "fake")));
  realWords.forEach((w) => w.word.split(" ").forEach((p) => p.length > 2 && !map.has(p) && map.set(p, "real")));

  const safe = escapeHtml(text);
  if (!map.size) return safe;
  const pattern = new RegExp(`\\b(${[...map.keys()].join("|")})\\b`, "gi");
  return safe.replace(pattern, (m) => `<mark class="${map.get(m.toLowerCase())}">${m}</mark>`);
}

function showResult(data, originalText) {
  const isReal = data.prediction === "REAL";
  $("verdict").textContent = `${isReal ? "✅" : "❌"} ${data.prediction} (${data.confidence}%)`;
  $("verdict").className = "verdict " + (isReal ? "real" : "fake");
  $("modelName").textContent = `Model: ${data.model} · ${data.word_count} words`;

  $("warning").textContent = data.warning ? "⚠️ " + data.warning : "";
  $("warning").classList.toggle("hidden", !data.warning);

  $("fakePct").textContent = data.fake_probability + "%";
  $("realPct").textContent = data.real_probability + "%";
  $("fakeBar").style.width = "0";
  $("realBar").style.width = "0";

  const { fake_words, real_words } = data.explanation;
  renderChips($("fakeWords"), fake_words, "fake");
  renderChips($("realWords"), real_words, "real");

  const articleText = data.text || originalText;
  $("articleTitle").textContent = data.title || "";
  $("highlighted").innerHTML = highlight(articleText, fake_words, real_words);

  resultEl.classList.remove("hidden");
  requestAnimationFrame(() => requestAnimationFrame(() => {
    $("fakeBar").style.width = data.fake_probability + "%";
    $("realBar").style.width = data.real_probability + "%";
  }));
}

// ---- Check ----
async function checkNews() {
  let body;
  if (mode === "text") {
    const text = textEl.value.trim();
    if (text.length < 20) return setStatus("Kam se kam 20 characters ka text daalo.", true);
    body = { text };
  } else {
    const url = urlEl.value.trim();
    if (!/^https?:\/\//i.test(url)) return setStatus("Sahi URL daalo (https:// se shuru).", true);
    body = { url };
  }

  checkBtn.disabled = true;
  resultEl.classList.add("hidden");
  setStatus(mode === "url" ? "Website se article nikal rahe hain..." : "Checking...");

  try {
    const res = await api("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Server error");
    showResult(data, body.text || "");
    setStatus("");
  } catch (err) {
    setStatus(
      err.message === "Failed to fetch"
        ? "Backend se connect nahi ho paya. Kya 'python backend\\app.py' chal raha hai?"
        : err.message,
      true
    );
  } finally {
    checkBtn.disabled = false;
  }
}

checkBtn.addEventListener("click", checkNews);
$("clearBtn").addEventListener("click", () => {
  textEl.value = "";
  urlEl.value = "";
  $("wordCount").textContent = "0";
  resultEl.classList.add("hidden");
  setStatus("");
});
textEl.addEventListener("keydown", (e) => { if (e.key === "Enter" && e.ctrlKey) checkNews(); });
urlEl.addEventListener("keydown", (e) => { if (e.key === "Enter") checkNews(); });
