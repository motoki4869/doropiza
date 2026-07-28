(function () {
  const grid = document.getElementById("card-grid");
  const emptyState = document.getElementById("empty-state");
  const countEl = document.getElementById("entry-count");
  const searchInput = document.getElementById("search");
  const tagFilters = document.getElementById("tag-filters");
  const tagToggle = document.getElementById("tag-toggle");
  const tagClear = document.getElementById("tag-clear");
  const entries = window.ENTRIES || [];

  const modal = document.getElementById("modal");
  const modalBackdrop = modal.querySelector(".modal-backdrop");
  const modalBodyEl = modal.querySelector(".modal-body");
  const modalClose = document.getElementById("modal-close");
  const modalNumber = document.getElementById("modal-number");
  const modalTitle = document.getElementById("modal-title");
  const modalTags = document.getElementById("modal-tags");
  const modalSource = document.getElementById("modal-source");
  const modalContent = document.getElementById("modal-content");

  // カードに表示するタグの上限。超過分は「+N」にまとめてカードの高さを揃える。
  const MAX_CARD_TAGS = 3;
  const EXCERPT_LENGTH = 96;

  const state = { query: "", activeTags: new Set() };
  let lastFocused = null;

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function stripTags(html) {
    return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
  }

  // 概要の第1文はほぼ全件が「本動画は、人気漫画『ONE PIECE』の〜」という
  // 同じ枕詞で始まる。カードの抜粋は2行しかないため、この定型部分を落として
  // 動画ごとに異なる内容から始まるようにする。
  const LEAD_IN = /^(?:本|この)動画(?:では|には|で|は)[、,]?\s*/;
  // 作品名は直後が「の」のときだけ落とす。「『ONE PIECE』が〜」「〜における」まで
  // 削ると助詞から始まる読めない文になるため。
  const TITLE_PREFIX = /^(?:(?:大)?人気)?(?:漫画|マンガ)?\s*(?:『ONE PIECE』|「ONE PIECE」)の\s*/;

  function trimBoilerplate(text) {
    let trimmed = text.replace(LEAD_IN, "");
    trimmed = trimmed.replace(TITLE_PREFIX, "");
    // 削りすぎて意味が取れなくなる場合は元の文を使う
    return trimmed.length >= 20 ? trimmed : text;
  }

  // 検索対象テキストと抜粋は初回に一度だけ作る（入力のたびに作り直さない）
  const searchText = new Map();
  const excerpts = new Map();
  entries.forEach((e) => {
    searchText.set(e.id, `${e.title} ${stripTags(e.html)}`);
    const firstPara = e.html.match(/<p[^>]*>([\s\S]*?)<\/p>/);
    const text = trimBoilerplate(stripTags(firstPara ? firstPara[1] : e.html));
    excerpts.set(e.id, text.length > EXCERPT_LENGTH ? `${text.slice(0, EXCERPT_LENGTH)}…` : text);
  });

  function allTags() {
    const set = new Set();
    entries.forEach((e) => e.tags.forEach((t) => set.add(t)));
    return Array.from(set).sort((a, b) => a.localeCompare(b, "ja"));
  }

  function filteredEntries() {
    return entries.filter((e) => {
      const matchesQuery = !state.query || searchText.get(e.id).includes(state.query);
      const matchesTags =
        state.activeTags.size === 0 || Array.from(state.activeTags).every((t) => e.tags.includes(t));
      return matchesQuery && matchesTags;
    });
  }

  function renderTagList(tags) {
    const shown = tags.slice(0, MAX_CARD_TAGS);
    const rest = tags.length - shown.length;
    const chips = shown.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("");
    return chips + (rest > 0 ? `<span class="tag-more">+${rest}</span>` : "");
  }

  function renderCards(list) {
    grid.innerHTML = list
      .map(
        (e) => `
      <div class="entry-card${e.number ? "" : " no-badge"}" tabindex="0" role="button" data-id="${escapeHtml(e.id)}">
        ${e.number ? `<div class="badge">${escapeHtml(e.number)}</div>` : ""}
        <h2>${escapeHtml(e.title)}</h2>
        <p class="excerpt">${escapeHtml(excerpts.get(e.id))}</p>
        <div class="tags">${renderTagList(e.tags)}</div>
        <div class="source">${escapeHtml(e.sourceFile)}</div>
      </div>`
      )
      .join("");
    emptyState.hidden = list.length > 0;
  }

  function renderTagFilters() {
    tagFilters.innerHTML = allTags()
      .map(
        (t) => `<button type="button" class="tag-filter-chip${state.activeTags.has(t) ? " active" : ""}" data-tag="${escapeHtml(t)}">${escapeHtml(t)}</button>`
      )
      .join("");
    tagClear.hidden = state.activeTags.size === 0;
  }

  function update() {
    const list = filteredEntries();
    countEl.textContent = `全${entries.length}件中 ${list.length}件表示`;
    renderCards(list);
  }

  function openModal(id) {
    const entry = entries.find((e) => e.id === id);
    if (!entry) return;
    lastFocused = document.activeElement;
    modalNumber.textContent = entry.number ? `No.${entry.number}` : "";
    modalNumber.style.display = entry.number ? "inline-block" : "none";
    modalTitle.textContent = entry.title;
    modalTags.innerHTML = entry.tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("");
    modalSource.textContent = entry.sourceFile;
    modalContent.innerHTML = entry.html;
    modal.removeAttribute("hidden");
    document.body.style.overflow = "hidden";
    modalBodyEl.scrollTop = 0;
    modalBodyEl.focus();
  }

  function closeModal() {
    modal.setAttribute("hidden", "");
    document.body.style.overflow = "";
    if (lastFocused && document.contains(lastFocused)) lastFocused.focus();
    lastFocused = null;
  }

  searchInput.addEventListener("input", (e) => {
    state.query = e.target.value.trim();
    update();
  });

  tagFilters.addEventListener("click", (e) => {
    const chip = e.target.closest(".tag-filter-chip");
    if (!chip) return;
    const tag = chip.dataset.tag;
    if (state.activeTags.has(tag)) {
      state.activeTags.delete(tag);
    } else {
      state.activeTags.add(tag);
    }
    renderTagFilters();
    update();
  });

  tagToggle.addEventListener("click", () => {
    const expanded = tagFilters.classList.toggle("expanded");
    tagToggle.setAttribute("aria-expanded", String(expanded));
    tagToggle.textContent = expanded ? "タグを折りたたむ" : "タグをすべて表示";
  });

  tagClear.addEventListener("click", () => {
    state.activeTags.clear();
    renderTagFilters();
    update();
  });

  grid.addEventListener("click", (e) => {
    const card = e.target.closest(".entry-card");
    if (card) openModal(card.dataset.id);
  });
  grid.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const card = e.target.closest(".entry-card");
    if (card) {
      e.preventDefault();
      openModal(card.dataset.id);
    }
  });

  modalClose.addEventListener("click", closeModal);
  modalBackdrop.addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.hasAttribute("hidden")) closeModal();
  });

  renderTagFilters();
  update();
})();
