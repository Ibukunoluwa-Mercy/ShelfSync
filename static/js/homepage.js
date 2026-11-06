document.addEventListener("DOMContentLoaded", () => {
  const nav = document.getElementById("site-nav");
  const year = document.getElementById("current-year");
  const mobileMenu = document.getElementById("homepageNav");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (year) year.textContent = new Date().getFullYear();

  document.querySelectorAll('.page-home a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      const target = document.querySelector(link.getAttribute("href"));
      if (!target) return;
      event.preventDefault();
      const offset = (nav ? nav.offsetHeight : 0) + 10;
      window.scrollTo({ top: target.offsetTop - offset, behavior: reduceMotion ? "auto" : "smooth" });
      if (mobileMenu && mobileMenu.classList.contains("show")) {
        bootstrap.Collapse.getOrCreateInstance(mobileMenu).hide();
      }
    });
  });

  const updateNav = () => nav && nav.classList.toggle("scrolled", window.scrollY > 12);
  updateNav();
  window.addEventListener("scroll", updateNav, { passive: true });

  const sections = [...document.querySelectorAll(".page-home section[id]")];
  const navLinks = [...document.querySelectorAll(".homepage-navbar .nav-link")];
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navLinks.forEach((link) => link.classList.toggle("active", link.getAttribute("href") === `#${entry.target.id}`));
      });
    }, { rootMargin: "-30% 0px -60% 0px" });
    sections.forEach((section) => observer.observe(section));

    if (!reduceMotion) {
      const revealObserver = new IntersectionObserver((entries, currentObserver) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            currentObserver.unobserve(entry.target);
          }
        });
      }, { threshold: 0.1 });
      document.querySelectorAll(".reveal").forEach((element) => revealObserver.observe(element));
    } else {
      document.querySelectorAll(".reveal").forEach((element) => element.classList.add("is-visible"));
    }
  }
});
