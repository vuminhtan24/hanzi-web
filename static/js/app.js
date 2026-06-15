// ── ChineseNois Shared JS ─────────────────────────────────────

// Toast notifications
function toast(msg, type = 'info', duration = 3000) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  el.innerHTML = `<span>${icons[type] || '•'}</span><span>${msg}</span>`;
  container.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// Cart management
const Cart = {
  get() { return JSON.parse(localStorage.getItem('cn_cart') || '[]'); },
  save(items) { localStorage.setItem('cn_cart', JSON.stringify(items)); Cart.updateBadge(); },
  add(product, qty = 1) {
    const items = Cart.get();
    const idx = items.findIndex(i => i.id === product.id);
    if (idx >= 0) { items[idx].quantity += qty; }
    else { items.push({ id: product.id, name: product.name, price: product.price, image: product.image, quantity: qty }); }
    Cart.save(items);
    toast(`Đã thêm "${product.name}" vào giỏ hàng`, 'success');
  },
  remove(id) {
    const items = Cart.get().filter(i => i.id !== id);
    Cart.save(items);
  },
  updateQty(id, qty) {
    const items = Cart.get();
    const idx = items.findIndex(i => i.id === id);
    if (idx >= 0) { if (qty <= 0) items.splice(idx, 1); else items[idx].quantity = qty; }
    Cart.save(items);
  },
  total() { return Cart.get().reduce((s, i) => s + i.price * i.quantity, 0); },
  count() { return Cart.get().reduce((s, i) => s + i.quantity, 0); },
  clear() { localStorage.removeItem('cn_cart'); Cart.updateBadge(); },
  updateBadge() {
    const badge = document.querySelector('.cart-badge');
    if (badge) { const c = Cart.count(); badge.textContent = c; badge.style.display = c > 0 ? 'flex' : 'none'; }
  }
};

// Auth state
const Auth = {
  async getUser() {
    const res = await fetch('/api/auth/me');
    const d = await res.json();
    return d.user;
  },
  async logout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/';
  }
};

// Format price
function fmtPrice(n) {
  return new Intl.NumberFormat('vi-VN').format(n) + '₫';
}

// Format date
function fmtDate(iso) {
  return new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

// Status labels
const STATUS_LABELS = {
  pending: 'Chờ xác nhận', confirmed: 'Đã xác nhận',
  shipping: 'Đang giao', completed: 'Hoàn thành', cancelled: 'Đã hủy'
};

// Stars
function renderStars(rating) {
  return '★'.repeat(rating) + '☆'.repeat(5 - rating);
}

// API helper
async function api(method, url, data) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (data) opts.body = JSON.stringify(data);
  const res = await fetch(url, opts);
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || 'Có lỗi xảy ra');
  return json;
}

async function apiForm(method, url, formData) {
  const res = await fetch(url, { method, body: formData });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || 'Có lỗi xảy ra');
  return json;
}

// Mobile nav toggle
document.addEventListener('DOMContentLoaded', () => {
  Cart.updateBadge();

  const ham = document.querySelector('.hamburger');
  const navLinks = document.querySelector('.navbar__links');
  if (ham && navLinks) {
    ham.addEventListener('click', () => navLinks.classList.toggle('open'));
    navLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', () => navLinks.classList.remove('open')));
  }

  // Active nav link
  const path = window.location.pathname;
  document.querySelectorAll('.navbar__links a').forEach(a => {
    if (a.getAttribute('href') === path) a.classList.add('active');
    else if (path.startsWith('/products') && a.getAttribute('href') === '/products') a.classList.add('active');
    else if (path.startsWith('/blog') && a.getAttribute('href') === '/blog') a.classList.add('active');
  });
});

// Auth-aware navbar
async function initNavAuth() {
  const user = await Auth.getUser();
  const actionsEl = document.getElementById('nav-actions');
  if (!actionsEl) return;
  if (user) {
    actionsEl.innerHTML = `
      <span style="color:var(--gray-200);font-size:.88rem">Xin chào, <b style="color:var(--gold)">${user.name}</b></span>
      <a href="/account" class="btn btn-ghost btn-sm" style="color:var(--gray-200);border-color:rgba(255,255,255,.2)">Tài khoản</a>
      ${user.is_admin ? `<a href="/admin" class="btn btn-gold btn-sm">Admin</a>` : ''}
      <button onclick="Auth.logout()" class="btn btn-ghost btn-sm" style="color:var(--gray-400)">Đăng xuất</button>
    `;
  } else {
    actionsEl.innerHTML = `
      <button onclick="openLoginModal()" class="btn-login">Đăng nhập</button>
      <button onclick="openRegisterModal()" class="btn btn-primary btn-sm">Đăng ký</button>
    `;
  }
}
