// Translation review: one question per screen; answers kept in this browser and sent as a GitHub issue or copied.
"use strict";

const $ = (id) => document.getElementById(id);
const STORE = "pa-translation-review-v1";
const SPEC = /%(?:\d+\$)?(lld|ld|d|@|f)/g;
// A GitHub "new issue" link longer than this may be cut off; past it, the issue asks for the copied answers instead.
const MAX_URL = 7500;

let data = null;
let lang = null;          // the language being reviewed
let index = 0;            // current item
let saved = load();       // { reviewer, answers: { [lang]: { [id]: {status, suggestion, comment} } }, other: { [lang]: text }, at: { [lang]: index } }

function load() {
  try { return JSON.parse(localStorage.getItem(STORE)) || {}; } catch { return {}; }
}
function persist() {
  try { localStorage.setItem(STORE, JSON.stringify(saved)); } catch { /* private mode: answers last until the tab closes */ }
}
const answers = () => ((saved.answers ??= {})[lang.code] ??= {});

function show(id) {
  for (const s of document.querySelectorAll(".screen")) s.hidden = s.id !== id;
  window.scrollTo(0, 0);
}
function progress(fraction) { $("progress-fill").style.width = `${Math.round(fraction * 100)}%`; }
function specs(text) { return [...text.matchAll(SPEC)].map((m) => m[1]).sort().join(","); }

// MARK: Start

function renderStart() {
  $("reviewer").value = saved.reviewer || "";
  $("langs").replaceChildren(...data.languages.map((l) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "lang-btn";
    const done = Object.keys(saved.answers?.[l.code] || {}).length;
    b.innerHTML = `<span class="native"></span><small></small>${done ? `<span class="resume">${done} of ${l.items.length} answered</span>` : ""}`;
    b.querySelector(".native").textContent = l.native;
    b.querySelector(".native").lang = l.code;
    b.querySelector("small").textContent = l.name;
    b.addEventListener("click", () => start(l));
    return b;
  }));
  progress(0);
  show("screen-start");
}

function start(l) {
  saved.reviewer = $("reviewer").value.trim();
  lang = l;
  persist();
  const resumeAt = saved.at?.[l.code] ?? 0;
  index = Math.min(resumeAt, l.items.length - 1);
  renderItem();
}

// MARK: Items

function renderItem() {
  const item = lang.items[index];
  const answer = answers()[item.id];
  const terms = lang.items.filter((i) => i.group === "term").length;
  const isTerm = item.group === "term";
  $("item-group").textContent = isTerm ? "Key term" : "Please check";
  $("item-count").textContent = isTerm ? `${index + 1} of ${terms}` : `${index - terms + 1} of ${lang.items.length - terms}`;
  $("item-where").textContent = item.where;
  $("item-english").textContent = item.english;
  const current = $("item-current");
  current.textContent = item.current;
  current.lang = lang.code; current.dir = lang.dir;
  $("item-note").textContent = item.note || (isTerm ? "Used on many screens of the app. Is this the word you'd expect?" : "");

  const suggestion = $("suggestion");
  suggestion.value = answer?.suggestion ?? item.current;
  suggestion.lang = lang.code; suggestion.dir = lang.dir;
  suggestion.rows = item.plural ? Math.max(3, item.current.split("\n").length + 1) : 3;
  $("comment").value = answer?.comment ?? "";
  select(answer?.status ?? null, false);
  $("back").disabled = false;
  progress(index / (lang.items.length + 1));
  (saved.at ??= {})[lang.code] = index; persist();
  show("screen-item");
  document.querySelector(".choice")?.focus({ preventScroll: true });
}

function select(status, focus = true) {
  for (const c of document.querySelectorAll(".choice")) c.setAttribute("aria-pressed", String(c.dataset.status === status));
  $("item-edit").hidden = status !== "change";
  $("item-comment").hidden = status === null || status === "ok";
  $("next").disabled = status === null;
  checkPlaceholders();
  if (!focus) return;
  if (status === "change") { $("suggestion").focus(); $("suggestion").select(); }
  else if (status === "unsure") $("comment").focus();
  else $("next").focus();
}

function currentStatus() {
  return document.querySelector('.choice[aria-pressed="true"]')?.dataset.status ?? null;
}

function checkPlaceholders() {
  const item = lang?.items[index];
  const warn = $("placeholder-warn");
  if (!item || currentStatus() !== "change") { warn.hidden = true; return; }
  const ok = specs($("suggestion").value) === specs(item.current);
  warn.hidden = ok;
  if (!ok) warn.textContent = `Keep the placeholders exactly as in the current text (${[...item.current.matchAll(SPEC)].map((m) => m[0]).join(" ") || "none"}): the app fills in names, amounts and dates there.`;
}

function saveItem() {
  const item = lang.items[index];
  const status = currentStatus();
  if (!status) return false;
  const entry = { status };
  if (status === "change") entry.suggestion = $("suggestion").value.trim();
  if (status !== "ok" && $("comment").value.trim()) entry.comment = $("comment").value.trim();
  if (status === "change" && entry.suggestion === item.current && !entry.comment) entry.status = "ok";
  answers()[item.id] = entry;
  persist();
  return true;
}

function next() {
  if (!saveItem()) return;
  if (index < lang.items.length - 1) { index += 1; renderItem(); }
  else renderOther();
}

function back() {
  if (currentStatus()) saveItem();
  if (index > 0) { index -= 1; renderItem(); } else renderStart();
}

// MARK: Anything else, then send

function renderOther() {
  $("site-link").href = lang.site;
  $("other").value = saved.other?.[lang.code] ?? "";
  progress(lang.items.length / (lang.items.length + 1));
  show("screen-other");
  $("other").focus({ preventScroll: true });
}

function saveOther() { (saved.other ??= {})[lang.code] = $("other").value.trim(); persist(); }

function counts() {
  const all = answers();
  const c = { ok: 0, change: 0, unsure: 0, open: 0 };
  for (const item of lang.items) c[all[item.id]?.status ?? "open"] += 1;
  return c;
}

function report() {
  const all = answers();
  const c = counts();
  const who = saved.reviewer || "(no name given)";
  const lines = [`## Translation review: ${lang.name} (${lang.code})`, "",
    `Reviewer: ${who}  `, `${lang.items.length} items: ${c.ok} look right, ${c.change} ${c.change === 1 ? "change" : "changes"}, ${c.unsure} not sure` +
    (c.open ? `, ${c.open} not answered` : ""), ""];
  const block = (title, status) => {
    const items = lang.items.filter((i) => all[i.id]?.status === status);
    if (!items.length) return;
    lines.push(`### ${title}`, "");
    for (const i of items) {
      const a = all[i.id];
      lines.push(`**${i.where}:** \`${i.english.replace(/`/g, "'")}\`  `, `Current: ${i.current.replace(/\n/g, " · ")}  `);
      if (a.suggestion) lines.push(`Suggested: ${a.suggestion.replace(/\n/g, " · ")}  `);
      if (a.comment) lines.push(`Comment: ${a.comment}  `);
      lines.push("");
    }
  };
  block("Changes", "change");
  block("Not sure", "unsure");
  const other = saved.other?.[lang.code];
  if (other) lines.push("### Other feedback", "", other, "");
  const machine = { lang: lang.code, reviewer: saved.reviewer || null,
    answers: lang.items.filter((i) => all[i.id] && all[i.id].status !== "ok")
      .map((i) => ({ where: i.where, key: i.key, ...all[i.id] })), other: other || null };
  lines.push("<details><summary>Answers as data</summary>", "", "```json", JSON.stringify(machine, null, 1), "```", "</details>");
  return lines.join("\n");
}

function renderSend() {
  saveOther();
  const c = counts();
  $("summary").textContent = `You reviewed ${lang.items.length - c.open} of ${lang.items.length} items in ${lang.name}: ` +
    `${c.ok} look right, ${c.change} with a suggested change, ${c.unsure} not sure.` +
    (c.open ? ` ${c.open} are still unanswered; you can go back to them below.` : "");
  const text = report();
  $("answers-text").value = text;
  const title = `Translation review: ${lang.name}${saved.reviewer ? ` (${saved.reviewer})` : ""}`;
  const base = `https://github.com/${data.repo}/issues/new?title=${encodeURIComponent(title)}&body=`;
  const full = base + encodeURIComponent(text);
  const tooLong = full.length > MAX_URL;
  $("send-github").href = tooLong
    ? base + encodeURIComponent("Paste your answers here: they were copied when you pressed the button.")
    : full;
  $("send-github").dataset.copyFirst = String(tooLong);
  $("send-status").textContent = "";

  const all = answers();
  $("review-list").replaceChildren(...lang.items.map((item, i) => {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button";
    const status = all[item.id]?.status;
    b.innerHTML = `<span class="key"></span><span class="pill ${status || ""}"></span>`;
    b.querySelector(".key").textContent = item.english;
    b.querySelector(".pill").textContent = { ok: "Looks right", change: "Change", unsure: "Not sure" }[status] || "Not answered";
    b.addEventListener("click", () => { index = i; renderItem(); });
    li.append(b);
    return li;
  }));
  progress(1);
  show("screen-send");
}

async function copyAnswers(message) {
  const text = $("answers-text").value;
  try {
    await navigator.clipboard.writeText(text);
    $("send-status").textContent = message;
    return true;
  } catch {
    const details = document.querySelector("#screen-send details");
    details.open = true;
    $("answers-text").focus(); $("answers-text").select();
    $("send-status").textContent = "Couldn't copy automatically. The text is selected below: copy it with your keyboard or menu.";
    return false;
  }
}

// MARK: Wiring

function wire() {
  for (const c of document.querySelectorAll(".choice")) c.addEventListener("click", () => select(c.dataset.status));
  $("next").addEventListener("click", next);
  $("back").addEventListener("click", back);
  $("suggestion").addEventListener("input", checkPlaceholders);
  $("reviewer").addEventListener("change", () => { saved.reviewer = $("reviewer").value.trim(); persist(); });
  $("other-back").addEventListener("click", () => { saveOther(); index = lang.items.length - 1; renderItem(); });
  $("other-next").addEventListener("click", renderSend);
  $("send-copy").addEventListener("click", () => copyAnswers("Copied. Paste them into an email or message."));
  $("send-github").addEventListener("click", (event) => {
    if ($("send-github").dataset.copyFirst === "true") {
      copyAnswers("Copied. In the GitHub issue, paste them over the placeholder text, then press Submit new issue.");
    }
    void event;
  });
  $("restart").addEventListener("click", renderStart);

  document.addEventListener("keydown", (event) => {
    if ($("screen-item").hidden || event.metaKey || event.ctrlKey || event.altKey) {
      if (!$("screen-item").hidden && (event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); next(); }
      return;
    }
    const typing = ["TEXTAREA", "INPUT"].includes(document.activeElement?.tagName);
    if (!typing && ["1", "2", "3"].includes(event.key)) {
      event.preventDefault();
      select(["ok", "change", "unsure"][Number(event.key) - 1]);
    } else if (event.key === "Enter" && document.activeElement?.tagName !== "TEXTAREA") {
      if (document.activeElement?.tagName === "BUTTON" && document.activeElement.id !== "next") return; // let the button act
      event.preventDefault();
      next();
    }
  });
}

fetch("data.json")
  .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
  .then((json) => { data = json; wire(); renderStart(); })
  .catch(() => {
    $("app").innerHTML = '<p class="lede">The review couldn’t load. Check your connection and reload the page.</p>';
  });
