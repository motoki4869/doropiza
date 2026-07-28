(function () {
  const grid = document.getElementById("card-grid");
  const countEl = document.getElementById("entry-count");
  const searchInput = document.getElementById("search");
  const tagFilters = document.getElementById("tag-filters");
  const entries = window.ENTRIES || [];

  const modal = document.getElementById("modal");
  const modalBackdrop = modal.querySelector(".modal-backdrop");
  const modalClose = document.getElementById("modal-close");
  const modalNumber = document.getElementById("modal-number");
  const modalTitle = document.getElementById("modal-title");
  const modalTags = document.getElementById("modal-tags");
  const modalContent = document.getElementById("modal-content");

  const state = { query: "", activeTags: new Set() };

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  const searchText = new Map(
    entries.map((e) => [e.id, `${e.title} ${e.html.replace(/<[^>]*>/g, " ")}`])
  );

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

  function renderCards(list) {
    grid.innerHTML = list
      .map(
        (e) => `
      <div class="entry-card" tabindex="0" role="button" data-id="${e.id}">
        ${e.number ? `<div class="badge">${escapeHtml(e.number)}</div>` : ""}
        <h2>${escapeHtml(e.title)}</h2>
        <div class="tags">${e.tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}</div>
        <div class="source">${escapeHtml(e.sourceFile)}</div>
      </div>`
      )
      .join("");
  }

  function renderTagFilters() {
    tagFilters.innerHTML = allTags()
      .map(
        (t) => `<button type="button" class="tag-filter-chip${state.activeTags.has(t) ? " active" : ""}" data-tag="${escapeHtml(t)}">${escapeHtml(t)}</button>`
      )
      .join("");
  }

  function update() {
    const list = filteredEntries();
    countEl.textContent = `全${entries.length}件中 ${list.length}件表示`;
    renderCards(list);
  }

  function openModal(id) {
    const entry = entries.find((e) => e.id === id);
    if (!entry) return;
    modalNumber.textContent = entry.number ? `No.${entry.number}` : "";
    modalNumber.style.display = entry.number ? "inline-block" : "none";
    modalTitle.textContent = entry.title;
    modalTags.innerHTML = entry.tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("");
    modalContent.innerHTML = entry.html;
    modal.removeAttribute("hidden");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    modal.setAttribute("hidden", "");
    document.body.style.overflow = "";
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
