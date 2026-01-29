/* ============================================
   今天吃什么？页面逻辑
   - 左滑/左键：跳过
   - 右滑/右键：加入购物清单（x1）
   ============================================ */

(function () {
    const SEEN_KEY = 'whatToEat_seenIds_v1';
    const ORDER_KEY = 'whatToEat_order_v1';

    let allRecipes = [];
    let order = [];
    let seen = new Set();
    let currentRecipeId = null;

    function $(id) { return document.getElementById(id); }

    function getStoredThemePreference() {
        try {
            const pref = localStorage.getItem('themePreference');
            if (pref === 'light' || pref === 'dark' || pref === 'auto') return pref;
        } catch (e) {}
        return 'auto';
    }

    function isNightByLocalTime(date = new Date()) {
        const h = date.getHours();
        return (h >= 18 || h < 6);
    }

    function resolveThemeFromPreference(pref) {
        if (pref === 'light' || pref === 'dark') return pref;
        return isNightByLocalTime() ? 'dark' : 'light';
    }

    function applyTheme(theme, withTransition = true) {
        const html = document.documentElement;
        if (!html) return;
        if (withTransition) {
            html.classList.add('theme-transition');
            window.setTimeout(() => html.classList.remove('theme-transition'), 280);
        }
        html.setAttribute('data-theme', theme);
    }

    function updateThemeToggleUI(pref) {
        const btns = [ $('theme-toggle'), $('theme-toggle-menubar') ].filter(Boolean);
        const theme = resolveThemeFromPreference(pref);
        const icon = pref === 'auto' ? '🌓' : (theme === 'dark' ? '🌙' : '☀️');
        const label = pref === 'auto' ? '自动' : (theme === 'dark' ? '暗色' : '亮色');
        btns.forEach((b) => {
            const iconEl = b.querySelector('.theme-icon');
            const labelEl = b.querySelector('.theme-label');
            if (iconEl) iconEl.textContent = icon;
            if (labelEl) labelEl.textContent = label;
        });
    }

    function cycleThemePreference() {
        const current = getStoredThemePreference();
        const next = current === 'auto' ? 'light' : (current === 'light' ? 'dark' : 'auto');
        try { localStorage.setItem('themePreference', next); } catch (e) {}
        applyTheme(resolveThemeFromPreference(next), true);
        updateThemeToggleUI(next);
    }

    function initThemeUI() {
        const pref = getStoredThemePreference();
        applyTheme(resolveThemeFromPreference(pref), false);
        updateThemeToggleUI(pref);
        const bind = (id) => {
            const btn = $(id);
            if (!btn) return;
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                if (navigator.vibrate) navigator.vibrate(8);
                cycleThemePreference();
            });
        };
        bind('theme-toggle');
        bind('theme-toggle-menubar');
    }

    function showToast(message, type = 'success') {
        const t = document.createElement('div');
        t.className = `what-to-eat-toast ${type}`;
        t.textContent = message;
        document.body.appendChild(t);
        window.setTimeout(() => t.classList.add('show'), 20);
        window.setTimeout(() => {
            t.classList.remove('show');
            window.setTimeout(() => t.remove(), 260);
        }, 1200);
    }

    function loadSessionState() {
        try {
            const seenArr = JSON.parse(sessionStorage.getItem(SEEN_KEY) || '[]');
            if (Array.isArray(seenArr)) seen = new Set(seenArr.map(Number));
        } catch (e) {}

        try {
            const ord = JSON.parse(sessionStorage.getItem(ORDER_KEY) || '[]');
            if (Array.isArray(ord) && ord.length) order = ord.map(Number);
        } catch (e) {}
    }

    function updateProgressUI() {
        const el = $('wte-progress');
        if (!el) return;
        const total = Array.isArray(allRecipes) ? allRecipes.length : 0;
        const seenCount = seen ? seen.size : 0;
        const remaining = Math.max(total - seenCount, 0);
        el.textContent = total
            ? `已浏览 ${seenCount}/${total} · 剩余 ${remaining}`
            : '加载中…';
    }

    function saveSessionState() {
        try { sessionStorage.setItem(SEEN_KEY, JSON.stringify(Array.from(seen))); } catch (e) {}
        try { sessionStorage.setItem(ORDER_KEY, JSON.stringify(order)); } catch (e) {}
    }

    function resetSession() {
        seen = new Set();
        order = [];
        currentRecipeId = null;
        try { sessionStorage.removeItem(SEEN_KEY); } catch (e) {}
        try { sessionStorage.removeItem(ORDER_KEY); } catch (e) {}
    }

    function shuffle(arr) {
        const a = arr.slice();
        for (let i = a.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [a[i], a[j]] = [a[j], a[i]];
        }
        return a;
    }

    function ensureOrder() {
        if (order.length) return;
        order = shuffle(allRecipes.map(r => r.id));
        saveSessionState();
    }

    function getNextRecipeId() {
        ensureOrder();
        for (const id of order) {
            if (!seen.has(id)) return id;
        }
        return null;
    }

    function renderEmptyState() {
        const stage = $('swipe-stage');
        if (!stage) return;
        stage.innerHTML = `
          <div class="swipe-empty">
            <div class="swipe-empty-title">这一轮都看完啦</div>
            <div class="swipe-empty-sub">你可以点击“重新开始”再来一轮，或者去购物清单看看。</div>
          </div>
        `;
        updateProgressUI();
    }

    function createCard(recipe) {
        const card = document.createElement('div');
        card.className = 'swipe-card';
        card.setAttribute('role', 'group');
        card.setAttribute('aria-label', `食谱：${recipe.title}`);
        card.innerHTML = `
          <div class="swipe-card-media">
            <img src="${recipe.imageUrl || 'images/recipe_1.png'}" alt="${recipe.title}">
          </div>
          <div class="swipe-card-body">
            <div class="swipe-card-title">${escapeHtml(recipe.title || '')}</div>
            <div class="swipe-card-meta">
              <span class="meta-pill">默认分量：x1.00</span>
              ${(recipe.category && recipe.category.length) ? `<span class="meta-pill meta-pill-soft">${escapeHtml(recipe.category[0])}</span>` : ''}
            </div>
            <div class="swipe-card-desc">${escapeHtml(recipe.description || '—')}</div>
          </div>
          <div class="swipe-card-badges">
            <div class="badge badge-nope">不吃</div>
            <div class="badge badge-like">想吃</div>
          </div>
        `;
        return card;
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function animateOut(card, direction /* -1 left, +1 right */) {
        const x = direction > 0 ? window.innerWidth * 1.1 : -window.innerWidth * 1.1;
        card.classList.add('leaving');
        card.style.transform = `translateX(${x}px) rotate(${direction * 12}deg)`;
        card.style.opacity = '0';
    }

    function resetCard(card) {
        card.classList.remove('dragging', 'leaving');
        card.style.transform = '';
        card.style.opacity = '';
        card.style.setProperty('--swipe-progress', '0');
    }

    function mountCard(recipe) {
        const stage = $('swipe-stage');
        if (!stage) return;
        stage.innerHTML = '';
        const card = createCard(recipe);
        stage.appendChild(card);
        // 进场动画
        card.classList.add('entering');
        window.setTimeout(() => card.classList.remove('entering'), 280);
        initSwipe(card);
        currentRecipeId = recipe.id;
        updateProgressUI();
    }

    function goNext() {
        const nextId = getNextRecipeId();
        if (!nextId) {
            renderEmptyState();
            currentRecipeId = null;
            return;
        }
        const recipe = allRecipes.find(r => r.id === nextId);
        if (!recipe) {
            seen.add(nextId);
            saveSessionState();
            return goNext();
        }
        mountCard(recipe);
    }

    function markSeen(id) {
        seen.add(Number(id));
        saveSessionState();
        updateProgressUI();
    }

    function addToShoppingList(recipeId) {
        if (typeof addRecipeToShoppingList !== 'function') {
            showToast('购物清单模块未加载', 'error');
            return;
        }
        try {
            addRecipeToShoppingList(recipeId, allRecipes, 1);
            showToast('已添加至购物清单（x1.00）', 'success');
        } catch (e) {
            showToast('添加失败，请重试', 'error');
        }
    }

    function handleChoice(direction /* -1 skip, +1 eat */) {
        const stage = $('swipe-stage');
        const card = stage ? stage.querySelector('.swipe-card') : null;
        if (!currentRecipeId || !card) return;

        const id = currentRecipeId;
        markSeen(id);

        if (navigator.vibrate) navigator.vibrate(direction > 0 ? 16 : 10);

        if (direction > 0) addToShoppingList(id);

        animateOut(card, direction);
        window.setTimeout(() => goNext(), 220);
    }

    function initKeyboard() {
        document.addEventListener('keydown', (e) => {
            // 避免影响输入框等
            const t = e.target;
            const tag = t && t.tagName ? t.tagName.toLowerCase() : '';
            if (tag === 'input' || tag === 'textarea' || tag === 'select' || (t && t.isContentEditable)) return;

            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                handleChoice(-1);
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                handleChoice(1);
            }
        });
    }

    function initButtons() {
        const skip = $('btn-skip');
        const eat = $('btn-eat');
        const reset = $('btn-reset');
        if (skip) skip.addEventListener('click', () => handleChoice(-1));
        if (eat) eat.addEventListener('click', () => handleChoice(1));
        if (reset) reset.addEventListener('click', () => {
            resetSession();
            showToast('已重置，重新开始', 'success');
            loadSessionState();
            goNext();
        });
    }

    function initSwipe(card) {
        let startX = 0;
        let startY = 0;
        let dx = 0;
        let dy = 0;
        let dragging = false;

        const threshold = 90;

        const onDown = (e) => {
            dragging = true;
            card.classList.add('dragging');
            const p = getPoint(e);
            startX = p.x;
            startY = p.y;
            dx = 0;
            dy = 0;
            card.setPointerCapture && e.pointerId && card.setPointerCapture(e.pointerId);
        };

        const onMove = (e) => {
            if (!dragging) return;
            const p = getPoint(e);
            dx = p.x - startX;
            dy = p.y - startY;

            // 若主要是水平滑动，阻止页面垂直滚动抖动
            if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 6) {
                e.preventDefault();
            }

            const rot = Math.max(-12, Math.min(12, dx / 18));
            const progress = Math.max(-1, Math.min(1, dx / 140));
            card.style.transform = `translateX(${dx}px) rotate(${rot}deg)`;
            card.style.setProperty('--swipe-progress', String(progress));
        };

        const onUp = () => {
            if (!dragging) return;
            dragging = false;
            card.classList.remove('dragging');

            if (dx > threshold) {
                handleChoice(1);
            } else if (dx < -threshold) {
                handleChoice(-1);
            } else {
                resetCard(card);
            }
        };

        // Pointer Events 优先（iOS Safari 也支持）
        card.addEventListener('pointerdown', onDown, { passive: true });
        card.addEventListener('pointermove', onMove, { passive: false });
        card.addEventListener('pointerup', onUp);
        card.addEventListener('pointercancel', onUp);
    }

    function getPoint(e) {
        if (e.touches && e.touches[0]) return { x: e.touches[0].clientX, y: e.touches[0].clientY };
        return { x: e.clientX, y: e.clientY };
    }

    async function loadRecipes() {
        const res = await fetch('recipes.json', { cache: 'no-store' });
        const data = await res.json();
        if (!Array.isArray(data)) return [];
        return data;
    }

    async function init() {
        initThemeUI();
        initKeyboard();
        initButtons();
        initHeaderScroll();

        loadSessionState();
        try {
            allRecipes = await loadRecipes();
        } catch (e) {
            showToast('加载食谱失败', 'error');
            return;
        }
        if (!allRecipes.length) {
            showToast('食谱为空', 'error');
            return;
        }
        updateProgressUI();
        goNext();
    }

    document.addEventListener('DOMContentLoaded', init);
})();

/* ============================================
   Header 滚动收缩为 Menu Bar（今天吃什么页）
   简化版：复用全站样式，只控制 header/menu-bar 类名
   ============================================ */

let wteHeaderScrollState = {
    lastScrollTop: 0,
    scrollThreshold: 0,
    hysteresis: 0,
    topThreshold: 5,
    isHeaderVisible: true,
    ticking: false,
    lastStateChange: 0,
    minStateChangeInterval: 150
};

function updateWteHeaderScrollThresholds() {
    const isMobile = window.innerWidth <= 768;
    wteHeaderScrollState.scrollThreshold = isMobile ? 80 : 120;
    wteHeaderScrollState.hysteresis = isMobile ? 20 : 28;
}

function initHeaderScroll() {
    const header = document.getElementById('main-header');
    const menuBar = document.getElementById('menu-bar');
    if (!header || !menuBar) return;

    updateWteHeaderScrollThresholds();

    header.classList.remove('header-compact');
    menuBar.classList.remove('menu-bar-visible');
    wteHeaderScrollState.isHeaderVisible = true;
    wteHeaderScrollState.lastScrollTop = window.pageYOffset || document.documentElement.scrollTop;
    wteHeaderScrollState.lastStateChange = 0;

    window.addEventListener('scroll', handleWteHeaderScroll, { passive: true });
    window.addEventListener('resize', updateWteHeaderScrollThresholds);
    window.addEventListener('orientationchange', updateWteHeaderScrollThresholds);
}

function handleWteHeaderScroll() {
    if (wteHeaderScrollState.ticking) return;
    window.requestAnimationFrame(function () {
        processWteHeaderScroll();
        wteHeaderScrollState.ticking = false;
    });
    wteHeaderScrollState.ticking = true;
}

let wteScrollEndTimeout = null;
function handleWteScrollEnd() {
    clearTimeout(wteScrollEndTimeout);
    wteScrollEndTimeout = setTimeout(function () {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        if (scrollTop < wteHeaderScrollState.topThreshold) {
            expandWteHeader();
        }
    }, 200);
}

function processWteHeaderScroll() {
    const header = document.getElementById('main-header');
    const menuBar = document.getElementById('menu-bar');
    if (!header || !menuBar) return;

    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const currentTime = Date.now();

    if (scrollTop < wteHeaderScrollState.topThreshold) {
        if (!wteHeaderScrollState.isHeaderVisible) {
            expandWteHeader();
        }
        wteHeaderScrollState.lastScrollTop = scrollTop;
        handleWteScrollEnd();
        return;
    }

    const timeSinceLastChange = currentTime - wteHeaderScrollState.lastStateChange;
    if (timeSinceLastChange < wteHeaderScrollState.minStateChangeInterval) {
        wteHeaderScrollState.lastScrollTop = scrollTop;
        handleWteScrollEnd();
        return;
    }

    const collapseThreshold = wteHeaderScrollState.scrollThreshold + wteHeaderScrollState.hysteresis;
    const expandThreshold = Math.max(
        wteHeaderScrollState.topThreshold + 1,
        wteHeaderScrollState.scrollThreshold - wteHeaderScrollState.hysteresis
    );

    if (scrollTop > collapseThreshold && wteHeaderScrollState.isHeaderVisible) {
        compactWteHeader();
        wteHeaderScrollState.lastStateChange = currentTime;
    } else if (scrollTop <= expandThreshold && !wteHeaderScrollState.isHeaderVisible) {
        expandWteHeader();
        wteHeaderScrollState.lastStateChange = currentTime;
    }

    wteHeaderScrollState.lastScrollTop = scrollTop;
    handleWteScrollEnd();
}

function compactWteHeader() {
    const header = document.getElementById('main-header');
    const menuBar = document.getElementById('menu-bar');
    if (!header || !menuBar) return;
    if (!wteHeaderScrollState.isHeaderVisible) return;
    header.classList.add('header-compact');
    menuBar.classList.add('menu-bar-visible');
    wteHeaderScrollState.isHeaderVisible = false;
}

function expandWteHeader() {
    const header = document.getElementById('main-header');
    const menuBar = document.getElementById('menu-bar');
    if (!header || !menuBar) return;
    if (wteHeaderScrollState.isHeaderVisible) return;
    header.classList.remove('header-compact');
    menuBar.classList.remove('menu-bar-visible');
    wteHeaderScrollState.isHeaderVisible = true;
}



