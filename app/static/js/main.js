(function () {
  const menu = document.getElementById("navbar-menu");
  const toggle = document.getElementById("navbar-toggle");

  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      menu.classList.toggle("open");
    });
  }

  // Smooth scroll for anchor links
  document.addEventListener("click", function (evt) {
    const target = evt.target;
    if (target instanceof HTMLAnchorElement && target.getAttribute("href")?.startsWith("#")) {
      const id = target.getAttribute("href").slice(1);
      const el = document.getElementById(id);
      if (el) {
        evt.preventDefault();
        const top = el.getBoundingClientRect().top + window.scrollY - 80;
        window.scrollTo({ top, behavior: "smooth" });
      }
    }
  });
})();
