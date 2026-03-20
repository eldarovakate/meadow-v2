// Meadow Shore — main.js

// === Scroll Reveal ===
const revealElements = document.querySelectorAll('.reveal');

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('is-visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, {
  threshold: 0.1,
  rootMargin: '0px 0px -60px 0px'
});

revealElements.forEach(el => revealObserver.observe(el));

// === Header Scroll Effect ===
const header = document.getElementById('site-header');
let lastScrollY = window.scrollY;

window.addEventListener('scroll', () => {
  const currentScrollY = window.scrollY;

  if (currentScrollY > 60) {
    header.classList.add('is-scrolled');
  } else {
    header.classList.remove('is-scrolled');
  }

  if (currentScrollY > lastScrollY && currentScrollY > 120) {
    header.classList.add('is-hidden');
  } else {
    header.classList.remove('is-hidden');
  }

  lastScrollY = currentScrollY;
}, { passive: true });

// === Mobile Menu ===
const burgerBtn = document.getElementById('burger-btn');
const mobileMenu = document.getElementById('mobile-menu');

if (burgerBtn && mobileMenu) {
  burgerBtn.addEventListener('click', () => {
    const isOpen = burgerBtn.getAttribute('aria-expanded') === 'true';
    burgerBtn.setAttribute('aria-expanded', String(!isOpen));
    mobileMenu.setAttribute('aria-hidden', String(isOpen));
    burgerBtn.classList.toggle('is-active');
    mobileMenu.classList.toggle('is-open');
    document.body.classList.toggle('menu-open');
  });

  // Close on link click
  mobileMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      burgerBtn.setAttribute('aria-expanded', 'false');
      mobileMenu.setAttribute('aria-hidden', 'true');
      burgerBtn.classList.remove('is-active');
      mobileMenu.classList.remove('is-open');
      document.body.classList.remove('menu-open');
    });
  });
}

// === Marquee Auto-Clone ===
function initMarquee() {
  document.querySelectorAll('.marquee__track').forEach(track => {
    const originalChildren = Array.from(track.children);
    const oneSetWidth = track.scrollWidth;

    // Клонируем пока трек не покрывает минимум 2× ширину экрана
    while (track.scrollWidth < window.innerWidth * 2) {
      originalChildren.forEach(child => track.appendChild(child.cloneNode(true)));
    }

    // Точная пиксельная анимация = ровно одна "копия" контента
    track.style.setProperty('--marquee-move', `-${oneSetWidth}px`);
  });
}

initMarquee();

// === Close mobile menu on resize ===
window.addEventListener('resize', () => {
  if (window.innerWidth >= 1024 && mobileMenu) {
    burgerBtn.setAttribute('aria-expanded', 'false');
    mobileMenu.setAttribute('aria-hidden', 'true');
    burgerBtn.classList.remove('is-active');
    mobileMenu.classList.remove('is-open');
    document.body.classList.remove('menu-open');
  }
}, { passive: true });
