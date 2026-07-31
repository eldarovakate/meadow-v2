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

    const label = form.parentElement.querySelector('.product-detail__favorite-label');
    if (label) {
      label.textContent = data.is_favorite ? 'В избранном' : 'Добавить в избранное';
    }

    if (!data.is_favorite && document.body.classList.contains('favorites-page')) {
      form.closest('.product-card')?.remove();
    }
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
