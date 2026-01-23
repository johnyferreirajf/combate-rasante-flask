(function () {
  const modal = document.getElementById("imgModal");
  const modalImg = document.getElementById("imgModalPhoto");
  const closeBtn = document.querySelector(".img-modal-close");
  const backdrop = document.querySelector(".img-modal-backdrop");

  function openModal(src, alt) {
    modalImg.src = src;
    modalImg.alt = alt || "";
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    modalImg.src = "";
    document.body.style.overflow = "";
  }

  document.addEventListener("click", function (e) {
    const target = e.target;

    // abrir
    if (target && target.classList.contains("js-open-image")) {
      const full = target.getAttribute("data-full") || target.src;
      openModal(full, target.alt);
      return;
    }

    // fechar clicando fora
    if (target === backdrop) {
      closeModal();
      return;
    }
  });

  // fechar no X
  if (closeBtn) closeBtn.addEventListener("click", closeModal);

  // fechar no ESC
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && modal.classList.contains("is-open")) {
      closeModal();
    }
  });
})();
