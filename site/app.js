(function () {
  const grid = document.getElementById("card-grid");
  const countEl = document.getElementById("entry-count");
  const entries = window.ENTRIES || [];

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

  countEl.textContent = `全${entries.length}件`;
  renderCards(entries);
})();
