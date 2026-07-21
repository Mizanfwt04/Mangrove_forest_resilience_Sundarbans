(() => {
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const revealTargets = document.querySelectorAll(
    ".section h2, .section-copy, .about-grid article, .program-list li, .lab-figure, .pub-group, .lead-profile, .timeline li, .lead-stats div, .lead-highlights li, .service-list li, .pathway-grid article, .contact .btn"
  );

  revealTargets.forEach((el) => el.classList.add("reveal"));

  if (prefersReduced || !("IntersectionObserver" in window)) {
    revealTargets.forEach((el) => el.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.15, rootMargin: "0px 0px -8% 0px" }
  );

  revealTargets.forEach((el) => observer.observe(el));

  const coast = document.querySelector(".atmosphere__coast");
  if (!coast) return;

  let ticking = false;
  window.addEventListener(
    "scroll",
    () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(() => {
        const offset = Math.min(window.scrollY * 0.08, 48);
        coast.style.transform = `translateY(${offset}px)`;
        ticking = false;
      });
    },
    { passive: true }
  );
})();
