// Meadow Shore — main.js

// === Force scroll-to-top on fresh loads (incl. bfcache restores), unless deep-linking to an anchor ===
// The delayed re-assertion guards against the browser's own password-manager
// autofill (e.g. Chrome scrolling to/highlighting a saved-password field)
// jumping the page after our initial scroll-to-top has already run. Both
// calls use behavior: 'instant' to bypass the site-wide smooth-scroll CSS —
// otherwise this correction itself becomes a visible glide up the page.
const scrollToTopInstant = () => window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
window.addEventListener('pageshow', (e) => {
  // Страница восстановлена из кэша «Назад/Вперёд»: счётчики корзины/избранного,
  // сердечки и состав корзины могли устареть — берём свежую версию с сервера.
  if (e.persisted) {
    window.location.reload();
    return;
  }
  if (!location.hash) {
    scrollToTopInstant();
    [50, 150, 300].forEach((delay) => setTimeout(scrollToTopInstant, delay));
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

function closeMobileMenu() {
  if (!burgerBtn || !mobileMenu) return;
  burgerBtn.setAttribute('aria-expanded', 'false');
  mobileMenu.setAttribute('aria-hidden', 'true');
  burgerBtn.classList.remove('is-active');
  mobileMenu.classList.remove('is-open');
  document.body.classList.remove('menu-open');
}

if (burgerBtn && mobileMenu) {
  burgerBtn.addEventListener('click', () => {
    const isOpen = burgerBtn.getAttribute('aria-expanded') === 'true';
    if (isOpen) {
      closeMobileMenu();
      return;
    }
    burgerBtn.setAttribute('aria-expanded', 'true');
    mobileMenu.setAttribute('aria-hidden', 'false');
    burgerBtn.classList.add('is-active');
    mobileMenu.classList.add('is-open');
    document.body.classList.add('menu-open');
  });

  // Close on link click
  mobileMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', closeMobileMenu);
  });

  // Close whenever the viewport crosses into the desktop layout (1024px).
  // Two independent listeners on purpose: matchMedia's 'change' event is the
  // correct signal for a breakpoint crossing, and a plain 'resize' fallback
  // covers browsers/situations where that event doesn't fire as expected.
  // A CSS failsafe (@media min-width:1024px { display: none }) also hides the
  // drawer outright regardless of this JS state — see style.css section 29.
  const desktopNavQuery = window.matchMedia('(min-width: 1024px)');
  desktopNavQuery.addEventListener('change', (e) => {
    if (e.matches) closeMobileMenu();
  });
  window.addEventListener('resize', () => {
    if (desktopNavQuery.matches) closeMobileMenu();
  }, { passive: true });
  if (desktopNavQuery.matches) closeMobileMenu();
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
    const changed = badge.textContent !== String(count);
    badge.textContent = count;
    if (changed) {
      // Короткий «вздох» счётчика — единственная анимация обратной связи
      badge.classList.remove('is-bumped');
      void badge.offsetWidth;
      badge.classList.add('is-bumped');
    }
  } else if (badge) {
    badge.remove();
  }
}

// === AJAX helper: POST формы, JSON-ответ. Бросает Error с понятным текстом. ===
async function postForm(url, formData) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    body: formData,
    credentials: 'same-origin',
  });
  let data = null;
  try { data = await response.json(); } catch (err) { /* не JSON — ошибка ниже */ }
  if (!response.ok || !data || data.ok === false) {
    throw new Error((data && data.error) || '');
  }
  return data;
}

// Блокировка кнопки на время запроса: нельзя нажать 10 раз подряд
function setBusy(el, busy) {
  if (!el) return;
  el.disabled = busy;
  el.classList.toggle('is-busy', busy);
  if (busy) el.setAttribute('aria-busy', 'true');
  else el.removeAttribute('aria-busy');
}

// === Toast: тихие уведомления (избранное, удаление, ошибки) ===
const toastRegion = document.querySelector('[data-toast-region]');

function showToast(message, { href = '', linkText = '', tone = 'default', timeout = 4000 } = {}) {
  if (!toastRegion) return;
  const toast = document.createElement('div');
  toast.className = `toast${tone === 'error' ? ' toast--error' : ''}`;
  if (tone === 'error') toast.setAttribute('role', 'alert');

  const text = document.createElement('p');
  text.className = 'toast__text';
  text.textContent = message;
  if (href && linkText) {
    const link = document.createElement('a');
    link.href = href;
    link.className = 'toast__link';
    link.textContent = linkText;
    text.append(' ', link);
  }

  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'toast__close';
  close.setAttribute('aria-label', 'Закрыть уведомление');
  close.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>';

  toast.append(text, close);
  // Одновременно показываем не больше двух — не устраиваем ленту уведомлений
  while (toastRegion.children.length >= 2) toastRegion.firstElementChild.remove();
  toastRegion.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('is-visible'));

  let timer;
  const dismiss = () => {
    clearTimeout(timer);
    toast.classList.remove('is-visible');
    setTimeout(() => toast.remove(), 250);
  };
  const schedule = () => { timer = setTimeout(dismiss, timeout); };
  close.addEventListener('click', dismiss);
  // Пока пользователь наводит или читает с клавиатуры — не прячем
  toast.addEventListener('mouseenter', () => clearTimeout(timer));
  toast.addEventListener('mouseleave', schedule);
  toast.addEventListener('focusin', () => clearTimeout(timer));
  toast.addEventListener('focusout', schedule);
  schedule();
}

// === Мини-корзина: одинаково после добавления из любого места сайта ===
const miniCart = document.querySelector('[data-mini-cart]');

function openMiniCart(data) {
  const item = data.item;
  if (!miniCart || !item) return;
  const q = (sel) => miniCart.querySelector(sel);

  q('[data-mc-heading]').textContent = data.capped ? 'Уже в корзине' : 'Добавлено в корзину';
  miniCart.querySelectorAll('[data-mc-link]').forEach((a) => { a.href = item.url; });
  q('[data-mc-title]').textContent = item.title;
  const img = q('[data-mc-img]');
  img.src = item.image || '';
  img.hidden = !item.image;

  const meta = [];
  if (item.size) meta.push(`Размер: ${item.size}`);
  if (item.technique) meta.push(item.technique);
  q('[data-mc-meta]').textContent = meta.join(' · ');

  const qty = q('[data-mc-qty]');
  qty.textContent = `Количество: ${item.quantity}`;
  qty.hidden = item.quantity < 2;

  q('[data-mc-price]').textContent = item.price_display;
  const old = q('[data-mc-old]');
  old.textContent = item.old_price_display;
  old.hidden = !item.old_price_display;

  const note = q('[data-mc-note]');
  note.textContent = data.capped ? 'Больше этого размера нет в наличии — в корзине уже все доступные вещи.' : '';
  note.hidden = !data.capped;

  q('[data-mc-count]').textContent = data.summary.count_label;
  q('[data-mc-sum]').textContent = data.summary.total_display;

  if (!miniCart.open) miniCart.showModal();
  q('.mini-cart__go').focus();
}

// === Favorite Toggle: сердце, счётчик и тост синхронно на всей странице ===
function renderFavorite(productId, isFavorite) {
  document.querySelectorAll(`[data-favorite-form][data-product-id="${productId}"]`).forEach((form) => {
    const button = form.querySelector('.favorite-toggle');
    button.classList.toggle('is-active', isFavorite);
    button.setAttribute('aria-pressed', String(isFavorite));
    button.setAttribute('aria-label', isFavorite ? 'Убрать из избранного' : 'Добавить в избранное');
    const inlineLabel = form.querySelector('[data-favorite-label]');
    if (inlineLabel) inlineLabel.textContent = isFavorite ? 'В избранном' : 'В избранное';
    const pageLabel = form.parentElement.querySelector('.product-detail__favorite-label');
    if (pageLabel) pageLabel.textContent = isFavorite ? 'В избранном' : 'Добавить в избранное';
  });
}

document.querySelectorAll('[data-favorite-form]').forEach((form) => {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const button = form.querySelector('.favorite-toggle');
    if (button.disabled) return;
    setBusy(button, true);

    let data;
    try {
      data = await postForm(form.getAttribute('action'), new FormData(form));
    } catch (err) {
      showToast('Не удалось обновить избранное. Попробуйте ещё раз.', { tone: 'error' });
      return;
    } finally {
      setBusy(button, false);
    }

    renderFavorite(form.dataset.productId, data.is_favorite);
    updateHeaderBadge('.header__icon-link--favorites', 'data-favorite-badge', data.favorite_count);

    if (data.is_favorite) {
      showToast('Добавлено в избранное.', { href: '/favorites/', linkText: 'Смотреть избранное →' });
    } else {
      showToast('Удалено из избранного.');
    }

    if (!data.is_favorite && document.body.classList.contains('favorites-page')) {
      const card = form.closest('.products__grid .product-card');
      const grid = card?.parentElement;
      card?.remove();
      // Последняя вещь убрана — показываем пустое состояние
      if (grid && !grid.querySelector('.product-card')) window.location.reload();
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

  const counter = gallery.querySelector('[data-gallery-current]');

  const setActive = (index) => {
    current = index;
    gallery.dataset.current = String(index);
    slides.forEach((slide, i) => slide.classList.toggle('is-active', i === index));
    dots.forEach((dot, i) => dot.classList.toggle('is-active', i === index));
    thumbs.forEach((thumb, i) => {
      thumb.classList.toggle('is-active', i === index);
      if (i === index) thumb.setAttribute('aria-current', 'true');
      else thumb.removeAttribute('aria-current');
    });
    if (counter) counter.textContent = String(index + 1);
  };

  dots.forEach((dot) => {
    dot.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      setActive(Number(dot.dataset.index));
    });
  });

  if (thumbs.length) {
    const goTo = (index) => {
      setActive((index + slides.length) % slides.length);
      thumbs[current].scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
    };

    thumbs.forEach((thumb) => {
      thumb.addEventListener('click', () => goTo(Number(thumb.dataset.index)));
    });

    gallery.querySelector('[data-gallery-prev]')?.addEventListener('click', () => goTo(current - 1));
    gallery.querySelector('[data-gallery-next]')?.addEventListener('click', () => goTo(current + 1));

    // Стрелки клавиатуры, когда фокус внутри галереи
    gallery.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') { e.preventDefault(); goTo(current - 1); }
      if (e.key === 'ArrowRight') { e.preventDefault(); goTo(current + 1); }
    });

    // Swipe on the main photo (phones)
    const mainImage = gallery.querySelector('.product-detail__main-image');
    let touchStartX = null;
    mainImage?.addEventListener('touchstart', (e) => { touchStartX = e.touches[0].clientX; }, { passive: true });
    mainImage?.addEventListener('touchend', (e) => {
      if (touchStartX === null) return;
      const dx = e.changedTouches[0].clientX - touchStartX;
      touchStartX = null;
      if (Math.abs(dx) > 40) goTo(current + (dx < 0 ? 1 : -1));
    });
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

// === Product page: dialogs (таблица размеров, просмотр фото) ===
document.querySelectorAll('[data-dialog-open]').forEach((trigger) => {
  trigger.addEventListener('click', () => {
    document.getElementById(trigger.dataset.dialogOpen)?.showModal();
  });
});

document.querySelectorAll('dialog').forEach((dialog) => {
  dialog.querySelectorAll('[data-dialog-close]').forEach((btn) => {
    btn.addEventListener('click', () => dialog.close());
  });
  // Клик по затемнённому фону закрывает окно (Escape закрывает нативно).
  // Проверяем координаты: клик по пустому месту внутри самой панели её не закрывает.
  dialog.addEventListener('click', (e) => {
    if (e.target.classList.contains('lightbox__stage')) { dialog.close(); return; }
    if (e.target !== dialog) return;
    const r = dialog.getBoundingClientRect();
    const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
    if (!inside || dialog.classList.contains('lightbox')) dialog.close();
  });
});

document.querySelectorAll('[data-lightbox]').forEach((lightbox) => {
  const slides = lightbox.querySelectorAll('[data-lightbox-slide]');
  const counter = lightbox.querySelector('[data-lightbox-current]');
  const gallery = document.querySelector('[data-product-gallery]');
  let current = 0;

  const show = (index) => {
    current = (index + slides.length) % slides.length;
    slides.forEach((slide, i) => { slide.hidden = i !== current; });
    if (counter) counter.textContent = String(current + 1);
  };

  const open = (index) => {
    show(index);
    lightbox.showModal();
  };

  document.querySelectorAll('[data-lightbox-open]').forEach((img) => {
    img.addEventListener('click', () => open(Number(img.dataset.lightboxOpen)));
  });
  document.querySelector('[data-lightbox-open-current]')?.addEventListener('click', () => {
    open(Number(gallery?.dataset.current || 0));
  });

  lightbox.querySelector('[data-lightbox-prev]')?.addEventListener('click', () => show(current - 1));
  lightbox.querySelector('[data-lightbox-next]')?.addEventListener('click', () => show(current + 1));
  lightbox.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') show(current - 1);
    if (e.key === 'ArrowRight') show(current + 1);
  });

  let touchStartX = null;
  lightbox.addEventListener('touchstart', (e) => { touchStartX = e.touches[0].clientX; }, { passive: true });
  lightbox.addEventListener('touchend', (e) => {
    if (touchStartX === null) return;
    const dx = e.changedTouches[0].clientX - touchStartX;
    touchStartX = null;
    if (Math.abs(dx) > 40) show(current + (dx < 0 ? 1 : -1));
  });
});

// === Product page: мобильная панель покупки (появляется, когда основная кнопка ушла вверх) ===
document.querySelectorAll('[data-buybar]').forEach((bar) => {
  const form = document.querySelector('[data-cart-form]');
  const submit = form?.querySelector('[data-cart-submit]');
  if (!form || !submit) return;

  const barBtn = bar.querySelector('[data-buybar-btn]');
  const barLabelAdd = barBtn.textContent;
  let added = false;

  // Проверяем позицию на каждом кадре прокрутки: IntersectionObserver не срабатывает,
  // если быстрый свайп перескочил кнопку целиком.
  let ticking = false;
  const update = () => {
    ticking = false;
    const scrolledPast = submit.getBoundingClientRect().bottom < 0;
    bar.classList.toggle('is-visible', scrolledPast);
    document.body.classList.toggle('has-bottom-bar', scrolledPast);
    bar.setAttribute('aria-hidden', String(!scrolledPast));
    barBtn.tabIndex = scrolledPast ? 0 : -1;
  };
  window.addEventListener('scroll', () => {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }, { passive: true });
  update();

  document.addEventListener('cart-toggle:change', (e) => {
    added = e.detail.added;
    barBtn.textContent = added ? submit.dataset.labelInCart : barLabelAdd;
  });

  barBtn.addEventListener('click', () => {
    if (added) {
      window.location.href = '/cart/';
      return;
    }
    if (form.querySelector('input[name="size"]') && !form.querySelector('input[name="size"]:checked')) {
      form.querySelector('[data-size-group]')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    form.requestSubmit();
  });
});

// === Product Card Click-through ===
document.querySelectorAll('[data-card-link]').forEach((card) => {
  card.addEventListener('click', (e) => {
    if (e.target.closest('a, button')) return;
    window.location.href = card.dataset.cardLink;
  });
});

// === Catalog Filters (color / print type) ===
document.querySelectorAll('.catalog-filters').forEach((filters) => {
  const grid = document.querySelector('[data-products-grid]');
  const noResults = document.querySelector('[data-no-results]');
  if (!grid) return;

  const cards = Array.from(grid.querySelectorAll('.product-card'));
  const selects = filters.querySelectorAll('[data-filter]');

  const applyFilters = () => {
    const active = {};
    selects.forEach((select) => {
      if (select.value) active[select.dataset.filter] = select.value;
    });

    let visibleCount = 0;
    cards.forEach((card) => {
      const matches = Object.entries(active).every(([key, value]) => card.dataset[key] === value);
      card.hidden = !matches;
      if (matches) visibleCount += 1;
    });

    if (noResults) noResults.hidden = visibleCount !== 0;
  };

  selects.forEach((select) => select.addEventListener('change', applyFilters));
});

// === Add to Cart ===
document.querySelectorAll('[data-cart-form]').forEach((form) => {
  const sizeInputs = form.querySelectorAll('input[name="size"]');
  const sizeOptions = form.querySelector('.size-options');
  const sizeError = form.querySelector('[data-size-error]');

  const submitBtn = form.querySelector('.add-to-cart-form__submit');

  // Страница товара: кнопка — переключатель. Выбранный размер уже в корзине →
  // «В корзине ✓», повторное нажатие убирает его (счётчик в шапке уменьшается).
  const isToggle = form.hasAttribute('data-cart-toggle');
  const inCartNote = form.querySelector('[data-in-cart-note]');
  const inCart = new Set(JSON.parse(document.getElementById('in-cart-sizes')?.textContent || '[]'));
  const selectedSize = () => (sizeInputs.length
    ? form.querySelector('input[name="size"]:checked')?.value || null
    : '-');

  const renderToggle = () => {
    if (!isToggle || !submitBtn) return;
    const size = selectedSize();
    const added = size !== null && inCart.has(size);
    submitBtn.textContent = added ? submitBtn.dataset.labelInCart : submitBtn.dataset.labelAdd;
    submitBtn.classList.toggle('is-in-cart', added);
    submitBtn.setAttribute('aria-pressed', String(added));
    if (inCartNote) inCartNote.hidden = !added;
    document.dispatchEvent(new CustomEvent('cart-toggle:change', { detail: { added } }));
  };

  sizeInputs.forEach((input) => {
    input.addEventListener('change', () => {
      sizeOptions?.classList.remove('has-error');
      sizeError?.setAttribute('hidden', '');
      renderToggle();
    });
  });
  renderToggle();

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (sizeInputs.length && !form.querySelector('input[name="size"]:checked')) {
      sizeOptions?.classList.add('has-error');
      sizeError?.removeAttribute('hidden');
      form.querySelector('input[name="size"]:not(:disabled)')?.focus({ preventScroll: true });
      return;
    }

    const size = selectedSize();
    const removing = isToggle && inCart.has(size);
    const url = removing
      ? form.dataset.removeUrl.replace('__size__', encodeURIComponent(size))
      : form.getAttribute('action');
    if (submitBtn?.disabled) return;
    setBusy(submitBtn, true);

    let data;
    try {
      data = await postForm(url, new FormData(form));
    } catch (err) {
      setBusy(submitBtn, false);
      showToast(err.message || (removing
        ? 'Не удалось убрать товар из корзины. Попробуйте ещё раз.'
        : 'Не удалось добавить товар в корзину. Попробуйте ещё раз.'), { tone: 'error' });
      return;
    }
    setBusy(submitBtn, false);

    updateHeaderBadge('.header__icon-link--cart', 'data-cart-badge', data.cart_count);

    if (isToggle) {
      if (removing) inCart.delete(size);
      else inCart.add(size);
      renderToggle();
    }

    if (removing) {
      showToast('Товар убран из корзины.');
    } else {
      openMiniCart(data);
    }
  });
});

// === Checkout: block double submit ===
document.querySelectorAll('[data-checkout-form]').forEach((form) => {
  form.addEventListener('submit', () => {
    const btn = form.querySelector('[data-checkout-submit]');
    if (!btn || btn.disabled) return;
    btn.dataset.originalText = btn.textContent;
    btn.textContent = 'Оформляем…';
    btn.disabled = true;
  });
});

// === Cart page: количество без кнопки «Обновить», удаление, пересчёт итогов ===
function renderCartSummary(summary) {
  document.querySelectorAll('[data-summary-count]').forEach((el) => { el.textContent = summary.count_label; });
  document.querySelectorAll('[data-summary-full]').forEach((el) => { el.textContent = summary.full_total_display; });
  document.querySelectorAll('[data-summary-total]').forEach((el) => { el.textContent = summary.total_display; });
  document.querySelectorAll('[data-summary-discount]').forEach((el) => { el.textContent = summary.discount_display; });
  document.querySelectorAll('[data-summary-discount-row]').forEach((el) => { el.hidden = !summary.discount; });
}

document.querySelectorAll('[data-cart-item]').forEach((row) => {
  const qtyForm = row.querySelector('[data-cart-qty]');
  const value = row.querySelector('[data-qty-value]');
  const dec = row.querySelector('[data-qty-dec]');
  const inc = row.querySelector('[data-qty-inc]');
  const subtotal = row.querySelector('[data-subtotal]');
  const limit = row.querySelector('[data-qty-limit]');
  const removeForm = row.querySelector('[data-cart-remove]');

  const renderQty = (item) => {
    value.textContent = item.quantity;
    subtotal.textContent = item.subtotal_display;
    dec.value = item.quantity - 1;
    inc.value = item.quantity + 1;
    // «−» на единице выключен: удаление — только явной кнопкой «Удалить»
    dec.disabled = item.quantity <= 1;
    const atMax = item.max_quantity !== null && item.quantity >= item.max_quantity;
    inc.disabled = atMax;
    if (limit) limit.hidden = !atMax;
  };

  qtyForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const button = e.submitter;
    if (!button || button.disabled) return;
    const formData = new FormData(qtyForm);
    formData.set('quantity', button.value);

    row.classList.add('is-updating');
    setBusy(dec, true);
    setBusy(inc, true);
    let data;
    try {
      data = await postForm(qtyForm.getAttribute('action'), formData);
    } catch (err) {
      setBusy(dec, false);
      setBusy(inc, false);
      row.classList.remove('is-updating');
      showToast('Не удалось обновить корзину. Попробуйте ещё раз.', { tone: 'error' });
      return;
    }
    setBusy(dec, false);
    setBusy(inc, false);
    row.classList.remove('is-updating');
    if (data.item) renderQty(data.item);
    renderCartSummary(data.summary);
    updateHeaderBadge('.header__icon-link--cart', 'data-cart-badge', data.cart_count);
  });

  removeForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const button = removeForm.querySelector('button');
    if (button.disabled) return;
    setBusy(button, true);
    row.classList.add('is-updating');
    let data;
    try {
      data = await postForm(removeForm.getAttribute('action'), new FormData(removeForm));
    } catch (err) {
      setBusy(button, false);
      row.classList.remove('is-updating');
      showToast('Не удалось удалить товар. Попробуйте ещё раз.', { tone: 'error' });
      return;
    }
    updateHeaderBadge('.header__icon-link--cart', 'data-cart-badge', data.cart_count);
    if (!data.summary.count) {
      // Корзина опустела — сервер нарисует пустое состояние
      window.location.reload();
      return;
    }
    renderCartSummary(data.summary);
    row.classList.add('is-removing');
    setTimeout(() => row.remove(), 250);
    showToast('Товар удалён из корзины.');
  });
});

// Мобильная панель «Итого / Оформить»: не прячет контент — внизу страницы место под неё
if (document.querySelector('[data-cart-bar]')) {
  document.body.classList.add('has-bottom-bar');
}

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

