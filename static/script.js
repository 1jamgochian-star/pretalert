// GDPR consent banner
(function () {
    if (!localStorage.getItem('gdpr_accepted')) {
        var banner = document.getElementById('gdpr-banner');
        if (banner) banner.style.display = 'flex';
    }
})();

function acceptGDPR() {
    localStorage.setItem('gdpr_accepted', '1');
    var banner = document.getElementById('gdpr-banner');
    if (banner) banner.style.display = 'none';
}

function toggleAlerta() {
    const form = document.getElementById('forma-alerta');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

/* ═══════════════════════════════════════════════════════════
   PretAlert Animations
═══════════════════════════════════════════════════════════ */

/* ── 1. Typing placeholder effect ───────────────────────── */
(function initTyping() {
    var input = document.querySelector('.search-input');
    if (!input || input.value.trim()) return;
    var items = [
        'iPhone 16 Pro Max', 'Samsung Galaxy S25', 'MacBook Air M3',
        'PlayStation 5', 'LG OLED 55"', 'Dyson V15 Detect',
        'AirPods Pro 2', 'Samsung TV 65"', 'Xiaomi 14T Pro', 'RTX 4080 Super'
    ];
    var idx = 0, ch = 0, deleting = false, paused = false, tid;
    input.addEventListener('focus', function () {
        paused = true; clearTimeout(tid);
        input.placeholder = 'Caută un produs...';
    });
    input.addEventListener('blur', function () {
        if (!input.value.trim()) { paused = false; tid = setTimeout(tick, 400); }
    });
    function tick() {
        if (paused || input === document.activeElement) return;
        var word = items[idx];
        if (deleting) {
            ch--;
            input.placeholder = ch > 0 ? word.substring(0, ch) : 'Caută un produs...';
        } else {
            ch++;
            input.placeholder = word.substring(0, ch);
        }
        var delay = deleting ? 52 : 92;
        if (!deleting && ch === word.length) { delay = 1900; deleting = true; }
        else if (deleting && ch === 0)       { deleting = false; idx = (idx + 1) % items.length; delay = 330; }
        tid = setTimeout(tick, delay);
    }
    tid = setTimeout(tick, 2200);
})();

/* ── 2. 3D card tilt — event delegation ─────────────────── */
(function initTilt() {
    document.addEventListener('mousemove', function (e) {
        var card = e.target.closest && e.target.closest('.card-produs');
        if (!card) return;
        var r = card.getBoundingClientRect();
        var x = (e.clientX - r.left) / r.width  - .5;
        var y = (e.clientY - r.top)  / r.height - .5;
        card.style.transition = 'border-color .2s, box-shadow .2s';
        card.style.transform  = 'perspective(700px) rotateX(' + (-y * 10) + 'deg) rotateY(' + (x * 10) + 'deg) translateY(-5px) scale(1.018)';
    }, { passive: true });
    document.addEventListener('mouseout', function (e) {
        var card = e.target.closest && e.target.closest('.card-produs');
        if (!card || card.contains(e.relatedTarget)) return;
        card.style.transition = '';
        card.style.transform  = '';
    });
})();

/* ── 3. Staggered fade-in on grid cards ─────────────────── */
(function initCardStagger() {
    var grid = document.getElementById('produse-grid');
    if (!grid) return;
    var seen = typeof WeakSet !== 'undefined' ? new WeakSet() : null;
    new MutationObserver(function () {
        grid.querySelectorAll('.card-produs').forEach(function (card, i) {
            if (seen) { if (seen.has(card)) return; seen.add(card); }
            card.style.animationDelay = (Math.min(i, 14) * 36) + 'ms';
        });
    }).observe(grid, { childList: true });
})();

/* ── 4. Price counter animation (.pret-curent) ──────────── */
(function initPriceCounter() {
    var el = document.querySelector('.pret-curent');
    if (!el) return;
    var m = el.textContent.trim().match(/([\d.,\s]+)\s*Lei/i);
    if (!m) return;
    var target = parseFloat(m[1].replace(/[\s]/g, '').replace(',', '.'));
    if (!target || isNaN(target)) return;
    var start = target * 1.28, dur = 950, t0 = null;
    el.textContent = start.toFixed(2) + ' Lei'; /* set before first paint */
    requestAnimationFrame(function step(ts) {
        if (!t0) t0 = ts;
        var p    = Math.min((ts - t0) / dur, 1);
        var ease = 1 - Math.pow(1 - p, 3);
        el.textContent = (start - (start - target) * ease).toFixed(2) + ' Lei';
        if (p < 1) requestAnimationFrame(step);
        else el.textContent = target.toFixed(2) + ' Lei';
    });
})();

/* ── 5. Ripple effect on .search-btn ────────────────────── */
(function initRipple() {
    document.addEventListener('click', function (e) {
        var btn = e.target.closest && e.target.closest('.search-btn');
        if (!btn) return;
        var r   = btn.getBoundingClientRect();
        var rip = document.createElement('span');
        rip.className        = 'ripple-wave';
        rip.style.top        = (e.clientY - r.top)  + 'px';
        rip.style.left       = (e.clientX - r.left) + 'px';
        btn.appendChild(rip);
        setTimeout(function () { if (rip.parentNode) rip.parentNode.removeChild(rip); }, 620);
    });
})();

/* ── 6. Scroll reveal on feature cards ──────────────────── */
(function initReveal() {
    var els = document.querySelectorAll('.feature-card, .feature');
    if (!els.length) return;
    if (!window.IntersectionObserver) {
        els.forEach(function (el) { el.classList.add('reveal-visible'); });
        return;
    }
    var obs = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
            if (en.isIntersecting) {
                en.target.classList.add('reveal-visible');
                obs.unobserve(en.target);
            }
        });
    }, { threshold: 0.12 });
    els.forEach(function (el) { el.classList.add('reveal-ready'); obs.observe(el); });
})();

/* ── 7. CSS particles ────────────────────────────────────── */
(function initParticles() {
    var container = document.getElementById('particles');
    if (!container) return;
    for (var i = 0; i < 22; i++) {
        var p = document.createElement('div');
        p.className = 'particle';
        p.style.left = (Math.random() * 100) + 'vw';
        p.style.bottom = (Math.random() * 30) + 'vh';
        p.style.setProperty('--dx', ((Math.random() - .5) * 80) + 'px');
        p.style.animationDelay = (Math.random() * 8) + 's';
        p.style.animationDuration = (4 + Math.random() * 6) + 's';
        var sz = (Math.random() * 2 + 2) + 'px';
        p.style.width = p.style.height = sz;
        container.appendChild(p);
    }
})();

/* ══════════════════════════════════════════════════════════ */

async function salveazaAlerta(produsId) {
    const email = document.getElementById('email').value;
    const pretDorit = document.getElementById('pret-dorit').value;
    const msg = document.getElementById('alerta-msg');

    const gdprCheck = document.getElementById('gdpr-alerta');
    if (!email || !pretDorit) {
        msg.textContent = '⚠️ Completează email și prețul dorit!';
        msg.style.color = 'red';
        return;
    }
    if (!gdprCheck.checked) {
        msg.textContent = '⚠️ Trebuie să accepți Politica de Confidențialitate pentru a seta alerta.';
        msg.style.color = 'red';
        return;
    }

    const formData = new FormData();
    formData.append('produs_id', produsId);
    formData.append('email', email);
    formData.append('pret_dorit', pretDorit);

    try {
        const r = await fetch('/alerta', { method: 'POST', body: formData });
        const data = await r.json();
        msg.textContent = data.mesaj;
        msg.style.color = data.status === 'ok' ? 'green' : 'red';
    } catch (e) {
        msg.textContent = '❌ Eroare la salvare!';
        msg.style.color = 'red';
    }
}
