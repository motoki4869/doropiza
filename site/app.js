(function () {
  const grid = document.getElementById("card-grid");
  const countEl = document.getElementById("entry-count");
  const entries = window.ENTRIES || [];

  const modal = document.getElementById("modal");
  const modalBackdrop = modal.querySelector(".modal-backdrop");
  const modalClose = document.getElementById("modal-close");
  const modalNumber = document.getElementById("modal-number");
  const modalTitle = document.getElementById("modal-title");
  const modalTags = document.getElementById("modal-tags");
  const modalContent = document.getElementById("modal-content");

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
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

  countEl.textContent = `全${entries.length}件`;
  renderCards(entries);
})();
