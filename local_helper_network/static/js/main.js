/**
 * Help R Circle — main.js
 * Handles: mobile nav, flash auto-dismiss, navbar scroll effect,
 *          stat counter animations, form validation hints.
 */

// ── DOM Ready ────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initMobileNav();
  initNavScroll();
  initFlashAutoDismiss();
  initStatCounters();
  initScrollReveal();
  initFormValidation();
  initAuthPages();
  initCheckboxCards();
  initNotifications();
});

function initNotifications() {
  const bell = document.getElementById('notificationBell');
  const panel = document.getElementById('notificationPanel');
  const list = document.getElementById('notificationList');
  const badge = document.getElementById('notificationBadge');
  const markAllReadBtn = document.getElementById('markAllReadBtn');
  if (!bell || !panel || !list || !badge) return;

  async function loadNotifications() {
    try {
      const response = await fetch('/api/notifications');
      const data = await response.json();
      const items = data.notifications || [];
      const unread = (data.unread_count || 0);
      badge.textContent = unread > 0 ? unread : '0';
      badge.classList.toggle('hidden', unread === 0);
      if (!items.length) {
        list.innerHTML = '<div class="notification-empty">No notifications yet.</div>';
        return;
      }
      list.innerHTML = items.map(item => `
        <div class="notification-item ${item.is_read ? '' : 'unread'}" data-id="${item.id}">
          <div class="notification-item-message">${escapeHtml(item.message)}</div>
          <div class="notification-item-meta">
            <span>${formatRelativeTime(item.created_at)}</span>
            <span>${item.is_read ? 'Read' : 'Unread'}</span>
          </div>
        </div>
      `).join('');
      list.querySelectorAll('.notification-item').forEach(el => {
        el.addEventListener('click', async () => {
          const id = Number(el.dataset.id);
          if (!id) return;
          await fetch(`/api/notifications/${id}/read`, { method: 'POST' });
          await loadNotifications();
        });
      });
    } catch (error) {
      console.error('Failed to load notifications', error);
    }
  }

  bell.addEventListener('click', () => {
    const isHidden = panel.classList.toggle('hidden');
    if (!isHidden) {
      loadNotifications();
    }
  });

  markAllReadBtn?.addEventListener('click', async () => {
    await fetch('/api/notifications/read-all', { method: 'POST' });
    await loadNotifications();
  });

  document.addEventListener('click', (event) => {
    if (!panel.contains(event.target) && !bell.contains(event.target)) {
      panel.classList.add('hidden');
    }
  });

  loadNotifications();

  const socket = window.io ? window.io() : null;
  window.helpRCircleSocket = socket;
  if (socket) {
    socket.on('connect', () => {
      socket.emit('join', { userId: document.body.dataset.userId || null });
    });
    socket.on('notification', async (data) => {
      bell.classList.remove('notification-arrive');
      void bell.offsetWidth;
      bell.classList.add('notification-arrive');
      await loadNotifications();
    });
  }
}

function initScrollReveal() {
  const elements = document.querySelectorAll('.reveal-on-scroll');
  if (!elements.length) return;

  document.documentElement.classList.add('js-ready');
  if (!('IntersectionObserver' in window)) {
    elements.forEach(element => element.classList.add('visible'));
    return;
  }

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px' });

  elements.forEach(element => observer.observe(element));
}

function escapeHtml(value) {
  return String(value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function formatRelativeTime(dateText) {
  if (!dateText) return 'Just now';
  const then = new Date(dateText.replace(' ', 'T'));
  const diffMs = Date.now() - then.getTime();
  const mins = Math.max(1, Math.round(diffMs / 60000));
  if (mins < 2) return 'Just now';
  if (mins < 60) return `${mins} minutes ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.round(hours / 24);
  if (days === 1) return 'Yesterday';
  return `${days} days ago`;
}


// ── Auth Page Enhancements ───────────────────────────────────────────────────
function initAuthPages() {
  document.querySelectorAll('.password-toggle').forEach(toggleButton => {
    const wrapper = toggleButton.closest('.password-row');
    const passwordInput = wrapper?.querySelector('input');
    if (!passwordInput) return;

    toggleButton.addEventListener('click', () => {
      const isPassword = passwordInput.type === 'password';
      passwordInput.type = isPassword ? 'text' : 'password';
      toggleButton.innerHTML = isPassword
        ? '<i class="fas fa-eye-slash"></i>'
        : '<i class="fas fa-eye"></i>';
      toggleButton.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
    });
  });

  const roleCards = document.querySelectorAll('.role-card');
  const helperFields = document.querySelectorAll('.helper-fields');

  function updateHelperFields(show) {
    helperFields.forEach(section => section.classList.toggle('hidden', !show));
  }

  roleCards.forEach(card => {
    const input = card.querySelector('input[type="radio"]');
    if (!input) return;
    if (input.checked) card.classList.add('selected');

    card.addEventListener('click', () => {
      roleCards.forEach(item => item.classList.remove('selected'));
      input.checked = true;
      card.classList.add('selected');
      if (input.name === 'role') updateHelperFields(input.value === 'helper');
    });
  });

  const selectedRole = document.querySelector('.role-card input[name="role"]:checked');
  if (selectedRole) {
    updateHelperFields(selectedRole.value === 'helper');
  }

  document.querySelectorAll('.auth-form').forEach(form => {
    form.addEventListener('submit', () => {
      const submitButton = form.querySelector('button[type="submit"]');
      const btnText = submitButton?.querySelector('.btn-text');
      if (!submitButton) return;
      submitButton.disabled = true;
      submitButton.classList.add('loading');
      if (btnText) btnText.textContent = 'Submitting...';
    });
  });
}


// ── Mobile Navigation Toggle ─────────────────────────────────────────────────
function initMobileNav() {
  const hamburger = document.getElementById("hamburger");
  const navLinks  = document.getElementById("navLinks");
  if (!hamburger || !navLinks) return;

  hamburger.addEventListener("click", () => {
    const isOpen = navLinks.classList.toggle("open");
    hamburger.setAttribute("aria-expanded", isOpen);
    // Animate hamburger → X
    const spans = hamburger.querySelectorAll("span");
    if (isOpen) {
      spans[0].style.transform = "translateY(7px) rotate(45deg)";
      spans[1].style.opacity   = "0";
      spans[2].style.transform = "translateY(-7px) rotate(-45deg)";
    } else {
      spans.forEach(s => { s.style.transform = ""; s.style.opacity = ""; });
    }
  });

  // Close nav when a link is tapped
  navLinks.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", () => {
      navLinks.classList.remove("open");
      hamburger.querySelectorAll("span").forEach(s => {
        s.style.transform = ""; s.style.opacity = "";
      });
    });
  });

  // Close when tapping outside
  document.addEventListener("click", e => {
    if (!hamburger.contains(e.target) && !navLinks.contains(e.target)) {
      navLinks.classList.remove("open");
      hamburger.querySelectorAll("span").forEach(s => {
        s.style.transform = ""; s.style.opacity = "";
      });
    }
  });
}


// ── Navbar Shadow on Scroll ──────────────────────────────────────────────────
function initNavScroll() {
  const navbar = document.getElementById("navbar");
  if (!navbar) return;

  window.addEventListener("scroll", () => {
    if (window.scrollY > 10) {
      navbar.style.boxShadow = "0 2px 20px rgba(0,0,0,.10)";
    } else {
      navbar.style.boxShadow = "";
    }
  }, { passive: true });
}


// ── Flash Message Auto-Dismiss ───────────────────────────────────────────────
function initFlashAutoDismiss() {
  const flashes = document.querySelectorAll(".flash");
  flashes.forEach((flash, i) => {
    // Stagger dismiss: first at 5s, then 5.5s, 6s …
    setTimeout(() => {
      flash.style.transition = "opacity .4s, transform .4s";
      flash.style.opacity    = "0";
      flash.style.transform  = "translateX(20px)";
      setTimeout(() => flash.remove(), 400);
    }, 5000 + i * 500);
  });
}


// ── Animated Stat Counters (home page) ──────────────────────────────────────
function initStatCounters() {
  const statNums = document.querySelectorAll(".stat-num[data-target]");
  if (!statNums.length) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el     = entry.target;
      const target = parseInt(el.getAttribute("data-target"), 10);
      animateCount(el, target);
      observer.unobserve(el);
    });
  }, { threshold: 0.5 });

  statNums.forEach(el => observer.observe(el));
}

function animateCount(el, target) {
  const duration = 1200;
  const start    = performance.now();
  const from     = 0;

  function step(now) {
    const progress = Math.min((now - start) / duration, 1);
    const ease     = 1 - Math.pow(1 - progress, 3); // easeOutCubic
    el.textContent = Math.round(from + (target - from) * ease);
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = target;
  }
  requestAnimationFrame(step);
}


// ── Inline Form Validation Hints ─────────────────────────────────────────────
function initFormValidation() {
  const forms = document.querySelectorAll(".lhn-form");
  forms.forEach(form => {
    form.addEventListener("submit", e => {
      let valid = true;
      form.querySelectorAll("[required]").forEach(field => {
        if (!field.value.trim()) {
          markInvalid(field);
          valid = false;
        } else {
          markValid(field);
        }
      });

      // Phone: must be 10 digits
      const phoneField = form.querySelector('input[name="phone"]');
      if (phoneField && phoneField.value.trim()) {
        const digits = phoneField.value.replace(/\D/g, "");
        if (digits.length < 10) {
          markInvalid(phoneField, "Enter a valid 10-digit phone number.");
          valid = false;
        }
      }

      if (!valid) e.preventDefault();
    });

    // Clear error on input
    form.querySelectorAll("input, select, textarea").forEach(field => {
      field.addEventListener("input", () => markValid(field));
      field.addEventListener("change", () => markValid(field));
    });
  });
}

function markInvalid(field, message) {
  field.style.borderColor = "#DC2626";
  field.style.background  = "#FEF2F2";

  // Show message below field
  let errEl = field.parentElement.querySelector(".field-error");
  if (!errEl) {
    errEl = document.createElement("span");
    errEl.className = "field-error";
    errEl.style.cssText = "color:#DC2626;font-size:.78rem;margin-top:2px;display:block;";
    field.parentElement.appendChild(errEl);
  }
  errEl.textContent = message || "This field is required.";
}

function markValid(field) {
  field.style.borderColor = "";
  field.style.background  = "";
  const errEl = field.parentElement.querySelector(".field-error");
  if (errEl) errEl.remove();
}


// ── Checkbox Card Toggle (helper page) ────────────────────────────────────
function initCheckboxCards() {
  document.querySelectorAll(".checkbox-card input[type='checkbox']").forEach(cb => {
    cb.addEventListener("change", () => {
      cb.closest(".checkbox-card").classList.toggle("checked", cb.checked);
    });
  });
}


// ── Smooth scroll for anchor links ───────────────────────────────────────────
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener("click", function(e) {
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
});
