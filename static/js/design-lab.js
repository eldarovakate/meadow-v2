// Design Lab — reveals the forest-trail S-curve once, on scroll into view.
// Loaded only on /design-lab/home-blocks/. Respects prefers-reduced-motion.
document.querySelectorAll('[data-trail]').forEach((el) => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) {
    el.classList.add('is-revealed');
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        el.classList.add('is-revealed');
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.2 });

  observer.observe(el);
});
