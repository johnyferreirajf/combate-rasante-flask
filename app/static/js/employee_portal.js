(function () {
  const search = document.getElementById("spSearch");
  const sort = document.getElementById("spSort");
  const rowsWrap = document.getElementById("spRows");
  const empty = document.getElementById("spEmpty");

  function getRows() {
    return rowsWrap ? Array.from(rowsWrap.querySelectorAll(".sp-row-item")) : [];
  }

  function applyFilter() {
    const q = (search?.value || "").trim().toLowerCase();
    let visible = 0;

    getRows().forEach((r) => {
      const name = r.dataset.name || "";
      const type = r.dataset.type || "";
      const ok = !q || name.includes(q) || type.includes(q);
      r.style.display = ok ? "" : "none";
      if (ok) visible++;
    });

    if (empty) empty.style.display = visible === 0 ? "" : "none";
  }

  function applySort() {
    const key = sort?.value || "name";
    const rows = getRows();

    const val = (r) => {
      if (key === "name") return (r.dataset.name || "");
      if (key === "type") return (r.dataset.type || "");
      if (key === "size") return Number(r.dataset.size || 0);
      if (key === "modified") return Number(r.dataset.modified || 0);
      return (r.dataset.name || "");
    };

    // Pastas sempre antes (SharePoint-like)
    rows.sort((a, b) => {
      const af = Number(a.dataset.folder || 0);
      const bf = Number(b.dataset.folder || 0);
      if (af !== bf) return bf - af; // 1 primeiro
      const A = val(a);
      const B = val(b);
      if (typeof A === "number" && typeof B === "number") return B - A;
      return String(A).localeCompare(String(B), "pt-BR");
    });

    rows.forEach((r) => rowsWrap.appendChild(r));
  }

  // Modals
  function openModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.setAttribute("aria-hidden", "false");
  }
  function closeModal(el) {
    if (!el) return;
    el.setAttribute("aria-hidden", "true");
  }

  document.querySelectorAll("[data-modal-open]").forEach((btn) => {
    btn.addEventListener("click", () => openModal(btn.getAttribute("data-modal-open")));
  });

  document.querySelectorAll("[data-modal-close]").forEach((el) => {
    el.addEventListener("click", () => closeModal(el.closest(".sp-modal")));
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".sp-modal[aria-hidden='false']").forEach(closeModal);
    }
  });

  // Rename prompt
  document.querySelectorAll("[data-rename-btn]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const form = btn.closest("form[data-rename-form]");
      if (!form) return;
      const current = btn.getAttribute("data-current") || "";
      const nv = window.prompt("Novo nome exibido:", current);
      if (!nv) return;
      form.querySelector("input[name='new_title']").value = nv.trim();
      form.submit();
    });
  });

  // Delete confirm
  document.querySelectorAll("[data-delete-btn]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const form = btn.closest("form[data-delete-form]");
      if (!form) return;
      const ok = window.confirm("Excluir este arquivo? Essa ação não pode ser desfeita.");
      if (!ok) return;
      form.submit();
    });
  });

  search?.addEventListener("input", () => { applyFilter(); });
  sort?.addEventListener("change", () => { applySort(); applyFilter(); });

  applySort();
  applyFilter();
})();