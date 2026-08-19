// Meadow Shore — main.js

// === Force scroll-to-top on fresh loads (incl. bfcache restores), unless deep-linking to an anchor ===
window.addEventListener('pageshow', () => {
  if (!location.hash) {
    window.scrollTo(0, 0);
  }
});

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

// === Product Carousel ===
document.querySelectorAll('[data-carousel]').forEach((carousel) => {
  const viewport = carousel.querySelector('[data-carousel-viewport]');
  const track = carousel.querySelector('[data-carousel-track]');
  const prevBtn = carousel.querySelector('[data-carousel-prev]');
  const nextBtn = carousel.querySelector('[data-carousel-next]');

  if (!viewport || !track || !prevBtn || !nextBtn) return;

  const updateArrows = () => {
    const maxScroll = track.scrollWidth - viewport.clientWidth;
    prevBtn.disabled = viewport.scrollLeft <= 4;
    nextBtn.disabled = maxScroll <= 4 || viewport.scrollLeft >= maxScroll - 4;
  };

  const scrollByCard = (direction) => {
    const card = track.querySelector('.product-carousel__item');
    if (!card) return;
    const gap = parseFloat(getComputedStyle(track).columnGap) || 0;
    const distance = card.getBoundingClientRect().width + gap;
    viewport.scrollBy({ left: direction * distance, behavior: 'smooth' });
  };

  prevBtn.addEventListener('click', () => scrollByCard(-1));
  nextBtn.addEventListener('click', () => scrollByCard(1));
  viewport.addEventListener('scroll', updateArrows, { passive: true });
  window.addEventListener('resize', updateArrows);
  updateArrows();
});

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

// === Header Icon Badges (cart / favorites count) ===
function updateHeaderBadge(linkSelector, badgeAttr, count) {
  const link = document.querySelector(linkSelector);
  if (!link) return;
  let badge = link.querySelector(`[${badgeAttr}]`);
  if (count > 0) {
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'header__badge';
      badge.setAttribute(badgeAttr, '');
      link.appendChild(badge);
    }
    badge.textContent = count;
  } else if (badge) {
    badge.remove();
  }
}

// === Favorite Toggle ===
document.querySelectorAll('[data-favorite-form]').forEach(form => {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const button = form.querySelector('.favorite-toggle');
    const formData = new FormData(form);

    let data;
    try {
      const response = await fetch(form.getAttribute('action'), {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData,
      });
      if (!response.ok) throw new Error('Request failed');
      data = await response.json();
    } catch (err) {
      form.submit();
      return;
    }

    button.classList.toggle('is-active', data.is_favorite);
    button.setAttribute('aria-pressed', String(data.is_favorite));
    button.setAttribute('aria-label', data.is_favorite ? 'Убрать из избранного' : 'Добавить в избранное');

    updateHeaderBadge('.header__icon-link--favorites', 'data-favorite-badge', data.favorite_count);

    const label = form.parentElement.querySelector('.product-detail__favorite-label');
    if (label) {
      label.textContent = data.is_favorite ? 'В избранном' : 'Добавить в избранное';
    }

    if (!data.is_favorite && document.body.classList.contains('favorites-page')) {
      form.closest('.product-card')?.remove();
    }
  });
});

// === Product Info Accordion (Состав / Уход / Доставка / Оплата / Описание) ===
document.querySelectorAll('.accordion__header').forEach((header) => {
  header.addEventListener('click', () => {
    const panel = header.nextElementSibling;
    const isOpen = header.getAttribute('aria-expanded') === 'true';
    header.setAttribute('aria-expanded', String(!isOpen));
    panel.classList.toggle('is-open', !isOpen);
  });
});

// === Product Image Gallery (dots + hover scrub on cards, thumbnail carousel on detail page) ===
document.querySelectorAll('[data-gallery]').forEach((gallery) => {
  const slides = gallery.querySelectorAll('.gallery-slide');
  const dots = gallery.querySelectorAll('.gallery-dot');
  const thumbs = gallery.querySelectorAll('.gallery-thumb');
  if (slides.length < 2) return;

  let current = 0;

  const setActive = (index) => {
    current = index;
    slides.forEach((slide, i) => slide.classList.toggle('is-active', i === index));
    dots.forEach((dot, i) => dot.classList.toggle('is-active', i === index));
    thumbs.forEach((thumb, i) => thumb.classList.toggle('is-active', i === index));
  };

  dots.forEach((dot) => {
    dot.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      setActive(Number(dot.dataset.index));
    });
  });

  if (thumbs.length) {
    const viewport = gallery.querySelector('[data-thumb-viewport]');
    const prevBtn = gallery.querySelector('[data-thumb-prev]');
    const nextBtn = gallery.querySelector('[data-thumb-next]');

    const goTo = (index) => {
      setActive((index + thumbs.length) % thumbs.length);
      thumbs[current].scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
    };

    thumbs.forEach((thumb) => {
      thumb.addEventListener('click', () => goTo(Number(thumb.dataset.index)));
    });

    prevBtn?.addEventListener('click', () => goTo(current - 1));
    nextBtn?.addEventListener('click', () => goTo(current + 1));

    if (viewport) {
      const updateThumbArrows = () => {
        const maxScroll = viewport.scrollWidth - viewport.clientWidth;
        if (prevBtn) prevBtn.disabled = viewport.scrollLeft <= 4;
        if (nextBtn) nextBtn.disabled = maxScroll <= 4 || viewport.scrollLeft >= maxScroll - 4;
      };
      viewport.addEventListener('scroll', updateThumbArrows, { passive: true });
      window.addEventListener('resize', updateThumbArrows);
      updateThumbArrows();
    }
  } else {
    gallery.addEventListener('mousemove', (e) => {
      const rect = gallery.getBoundingClientRect();
      const ratio = (e.clientX - rect.left) / rect.width;
      const index = Math.min(slides.length - 1, Math.max(0, Math.floor(ratio * slides.length)));
      setActive(index);
    });

    gallery.addEventListener('mouseleave', () => setActive(0));
  }
});

// === Product Card Click-through ===
document.querySelectorAll('[data-card-link]').forEach((card) => {
  card.addEventListener('click', (e) => {
    if (e.target.closest('a, button')) return;
    window.location.href = card.dataset.cardLink;
  });
});

// === Add to Cart ===
document.querySelectorAll('[data-cart-form]').forEach((form) => {
  const sizeSelect = form.querySelector('select[name="size"]');
  const sizeWrap = form.querySelector('.size-select-wrap');
  const sizeError = form.querySelector('[data-size-error]');

  if (sizeSelect) {
    sizeSelect.addEventListener('change', () => {
      sizeWrap?.classList.remove('has-error');
      sizeError?.setAttribute('hidden', '');
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (sizeSelect && !sizeSelect.value) {
      sizeWrap?.classList.add('has-error');
      sizeError?.removeAttribute('hidden');
      sizeSelect.focus();
      return;
    }

    const submitBtn = form.querySelector('.add-to-cart-form__submit');
    const formData = new FormData(form);

    let data;
    try {
      const response = await fetch(form.getAttribute('action'), {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData,
      });
      data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Request failed');
    } catch (err) {
      form.submit();
      return;
    }

    updateHeaderBadge('.header__icon-link--cart', 'data-cart-badge', data.cart_count);

    if (submitBtn) {
      const originalText = submitBtn.textContent;
      submitBtn.textContent = 'Добавлено ✓';
      submitBtn.disabled = true;
      setTimeout(() => {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
      }, 1800);
    }
  });
});

// === Cart Quantity Stepper ===
document.querySelectorAll('[data-cart-qty-form]').forEach((form) => {
  const input = form.querySelector('.cart-line__qty-input');
  const decBtn = form.querySelector('[data-qty-decrease]');
  const incBtn = form.querySelector('[data-qty-increase]');
  if (!input) return;

  decBtn?.addEventListener('click', () => {
    input.value = Math.max(1, Number(input.value) - 1);
  });
  incBtn?.addEventListener('click', () => {
    input.value = Number(input.value) + 1;
  });
});

// === Password Visibility Toggle ===
document.querySelectorAll('[data-password-toggle]').forEach(button => {
  button.addEventListener('click', () => {
    const input = button.parentElement.querySelector('input');
    input.type = input.type === 'password' ? 'text' : 'password';
  });
});

// === Auth Forms Validation (login / register) ===
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/;

function getAuthFieldWrapper(input) {
  return input.closest('.form-group');
}

function showAuthFieldError(input, message) {
  const wrapper = getAuthFieldWrapper(input);
  if (!wrapper) return;
  wrapper.classList.add('has-error');
  input.setAttribute('aria-invalid', 'true');
  let error = wrapper.querySelector('.form-error');
  if (!error) {
    error = document.createElement('div');
    error.className = 'form-error';
    wrapper.appendChild(error);
  }
  error.textContent = message;
}

function clearAuthFieldError(input) {
  const wrapper = getAuthFieldWrapper(input);
  if (!wrapper) return;
  wrapper.classList.remove('has-error');
  input.removeAttribute('aria-invalid');
  const error = wrapper.querySelector('.form-error');
  if (error) error.remove();
}

function validateAuthField(input) {
  if (input.type === 'checkbox') {
    if (input.required && !input.checked) {
      showAuthFieldError(input, 'Необходимо согласие для продолжения');
      return false;
    }
    clearAuthFieldError(input);
    return true;
  }

  const value = input.value.trim();

  if (input.required && !value) {
    showAuthFieldError(input, 'Это поле обязательно для заполнения');
    return false;
  }

  if (input.type === 'email' && value && !EMAIL_RE.test(value)) {
    showAuthFieldError(input, 'Введите корректный email, например name@example.com');
    return false;
  }

  clearAuthFieldError(input);
  return true;
}

document.querySelectorAll('.auth-form').forEach(form => {
  const fields = form.querySelectorAll('input[required], input[type="email"]');

  fields.forEach(input => {
    input.addEventListener('blur', () => validateAuthField(input));
    input.addEventListener('change', () => {
      if (input.type === 'checkbox') validateAuthField(input);
    });
    input.addEventListener('input', () => {
      if (getAuthFieldWrapper(input)?.classList.contains('has-error')) {
        validateAuthField(input);
      }
    });
  });

  form.addEventListener('submit', (e) => {
    let isValid = true;
    let firstInvalid = null;

    fields.forEach(input => {
      if (!validateAuthField(input)) {
        isValid = false;
        if (!firstInvalid) firstInvalid = input;
      }
    });

    if (!isValid) {
      e.preventDefault();
      firstInvalid.focus();
    }
  });
});

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
