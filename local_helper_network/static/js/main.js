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
  initFormValidation();
  initAuthPages();
  initCheckboxCards();
});


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
  const volunteerFields = document.querySelectorAll('.volunteer-fields');

  function updateVolunteerFields(show) {
    volunteerFields.forEach(section => section.classList.toggle('hidden', !show));
  }

  roleCards.forEach(card => {
    const input = card.querySelector('input[type="radio"]');
    if (!input) return;
    if (input.checked) card.classList.add('selected');

    card.addEventListener('click', () => {
      roleCards.forEach(item => item.classList.remove('selected'));
      input.checked = true;
      card.classList.add('selected');
      if (input.name === 'role') updateVolunteerFields(input.value === 'volunteer');
    });
  });

  const selectedRole = document.querySelector('.role-card input[name="role"]:checked');
  if (selectedRole) {
    updateVolunteerFields(selectedRole.value === 'volunteer');
  }

  const passwordInput = document.querySelector('#signupForm #password');
  const strengthFill = document.getElementById('passwordStrengthFill');
  const strengthText = document.getElementById('passwordStrengthText');

  if (passwordInput && strengthFill && strengthText) {
    const updatePasswordStrength = value => {
      let score = 0;
      if (value.length >= 6) score += 1;
      if (value.length >= 10) score += 1;
      if (/[A-Z]/.test(value)) score += 1;
      if (/[0-9]/.test(value)) score += 1;
      if (/[^A-Za-z0-9]/.test(value)) score += 1;

      const width = (score / 5) * 100;
      strengthFill.style.width = `${width}%`;
      if (score <= 1) {
        strengthFill.style.background = '#DC2626';
        strengthText.textContent = 'Very weak';
      } else if (score <= 3) {
        strengthFill.style.background = '#F59E0B';
        strengthText.textContent = 'Fair strength';
      } else {
        strengthFill.style.background = '#047857';
        strengthText.textContent = 'Strong password';
      }
    };

    passwordInput.addEventListener('input', event => {
      updatePasswordStrength(event.target.value);
    });

    updatePasswordStrength(passwordInput.value);
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


// ── Checkbox Card Toggle (volunteer page) ────────────────────────────────────
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
