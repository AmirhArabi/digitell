/**
 * سایدبار پنل مدیریت زیترو — پوسته ریلی آیکونی، بخش‌های تاشو و کشوی موبایل.
 *
 * وضعیت روی <body> نگه داشته می‌شود و CSS بر اساس همان داده‌ها انیمیشن را اجرا می‌کند:
 *   data-sidebar = "full" | "collapsed"   → دسکتاپ
 *   data-drawer  = "open" | "closed"      → موبایل
 *
 * منطق در دو نسخه منو (دسکتاپ و کشو) مشترک است چون هر نسخه مستقل مقدار‌دهی می‌شود.
 */
(function () {
    'use strict';

    var body = document.body;
    var STORAGE_KEY = 'zitro_dash_sidebar';
    var DESKTOP_QUERY = '(min-width: 1024px)';
    var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

    var sidebar = document.getElementById('dash-sidebar');
    var trigger = document.getElementById('dash-trigger');
    var rail = document.getElementById('dash-rail');
    var drawer = document.getElementById('dash-drawer');
    var backdrop = document.getElementById('dash-backdrop');
    var drawerClose = document.getElementById('drawer-close');
    var main = document.getElementById('dash-main');

    if (!sidebar || !trigger || !drawer) return;

    function isDesktop() {
        return window.matchMedia(DESKTOP_QUERY).matches;
    }

    /* ------------------------------------------------------------- پنل دسکتاپ */

    function panelState() {
        return body.getAttribute('data-sidebar') === 'collapsed' ? 'collapsed' : 'full';
    }

    /**
     * زیرمنوی بسته (یا زیرمنویی که با جمع‌شدن پنل پنهان شده) نباید در دسترس
     * صفحه‌خوان و ترتیب Tab باشد. کامپوننت مرجع آیتم‌های بسته را unmount می‌کند؛
     * معادل آن در اینجا attribute اینرسی است.
     */
    function syncSubmenus() {
        var panelCollapsed = panelState() === 'collapsed';
        Array.prototype.forEach.call(document.querySelectorAll('.side-sub'), function (list) {
            var hiddenByPanel = panelCollapsed && sidebar.contains(list);
            var blocked = hiddenByPanel || list.getAttribute('data-open') !== 'true';
            if (blocked) {
                list.setAttribute('inert', '');
            } else {
                list.removeAttribute('inert');
            }
        });
    }

    // عنوان راهنما فقط در حالت ریل آیکونی لازم است (متن برچسب پنهان می‌شود)؛
    // در پنل باز، tooltip اضافی و آزاردهنده است.
    var titledItems = Array.prototype.slice
        .call(document.querySelectorAll('#dash-sidebar [title]'))
        .filter(function (item) { return sidebar.contains(item); });

    function syncTitles(collapsed) {
        titledItems.forEach(function (item) {
            if (collapsed) {
                item.setAttribute('title', item.getAttribute('data-title') || '');
            } else {
                item.removeAttribute('title');
            }
        });
    }

    titledItems.forEach(function (item) {
        if (!item.hasAttribute('data-title')) {
            item.setAttribute('data-title', item.getAttribute('title') || '');
        }
    });

    function setPanel(state, persist) {
        body.setAttribute('data-sidebar', state);
        trigger.setAttribute('aria-expanded', state === 'full' ? 'true' : 'false');
        trigger.setAttribute('aria-label', state === 'full' ? 'جمع‌کردن منو' : 'بازکردن منو');
        if (persist) {
            try { localStorage.setItem(STORAGE_KEY, state); } catch (e) { }
        }
        syncTitles(state === 'collapsed');
        syncSubmenus();
    }

    function togglePanel() {
        setPanel(panelState() === 'full' ? 'collapsed' : 'full', true);
    }

    // مقدار اولیه از localStorage در همان ابتدای <body> خوانده شده است؛ اینجا فقط
    // وضعیت کنترل‌ها با آن هم‌تراز می‌شود.
    setPanel(panelState(), false);

    trigger.addEventListener('click', function (event) {
        event.stopPropagation();
        if (isDesktop()) {
            togglePanel();
        } else {
            openDrawer();
        }
    });

    if (rail) {
        rail.addEventListener('click', function () {
            if (isDesktop()) togglePanel();
        });
    }

    /* --------------------------------------------------------- بخش‌های تاشو */

    function sectionListFor(button) {
        var section = button.closest('.side-section');
        return section ? section.querySelector('.side-sub') : null;
    }

    function setSection(button, open) {
        var list = sectionListFor(button);
        if (!list) return;
        list.setAttribute('data-open', open ? 'true' : 'false');
        button.setAttribute('aria-expanded', open ? 'true' : 'false');
        syncSubmenus();
    }

    // هر نسخه منو جداگانه مدیریت می‌شود تا باز/بسته شدن یک نسخه روی نسخه دیگر اثر نگذارد.
    Array.prototype.forEach.call(document.querySelectorAll('.side-nav'), function (nav) {
        var buttons = Array.prototype.slice.call(nav.querySelectorAll('.side-parent'));

        buttons.forEach(function (button) {
            button.addEventListener('click', function () {
                var list = sectionListFor(button);
                if (!list) return;

                var willOpen = list.getAttribute('data-open') !== 'true';

                // در ریل آیکونی جای زیرمنو نیست؛ ابتدا پنل باز می‌شود (مثل رفتار
                // کامپوننت مرجع که با انتخاب یک گروه، سایدبار را باز می‌کند).
                if (isDesktop() && panelState() === 'collapsed') {
                    setPanel('full', true);
                }

                // آکاردئونی: هم‌زمان فقط یک بخش باز می‌ماند
                buttons.forEach(function (other) {
                    if (other !== button) setSection(other, false);
                });
                setSection(button, willOpen);
            });
        });
    });

    /* ---------------------------------------------------------- کشوی موبایل */

    var drawerOpen = false;
    var lastFocused = null;

    function focusableInDrawer() {
        // در حالت «inert» فقط المان‌های قابل‌مشاهده قابل فوکوس هستند
        return Array.prototype.filter.call(
            drawer.querySelectorAll(FOCUSABLE),
            function (element) { return element.offsetParent !== null; }
        );
    }

    function openDrawer() {
        if (drawerOpen) return;
        drawerOpen = true;
        lastFocused = document.activeElement;

        body.setAttribute('data-drawer', 'open');
        drawer.removeAttribute('inert');
        drawer.setAttribute('aria-hidden', 'false');
        trigger.setAttribute('aria-expanded', 'true');
        if (main) main.setAttribute('inert', '');

        window.requestAnimationFrame(function () {
            (drawerClose || drawer).focus({ preventScroll: true });
        });
    }

    function closeDrawer() {
        if (!drawerOpen) return;
        drawerOpen = false;

        body.setAttribute('data-drawer', 'closed');
        drawer.setAttribute('inert', '');
        drawer.setAttribute('aria-hidden', 'true');
        trigger.setAttribute('aria-expanded', 'false');
        if (main) main.removeAttribute('inert');

        if (lastFocused && typeof lastFocused.focus === 'function') {
            lastFocused.focus({ preventScroll: true });
        }
    }

    if (backdrop) backdrop.addEventListener('click', closeDrawer);
    if (drawerClose) drawerClose.addEventListener('click', closeDrawer);

    // انتخاب یک لینک در کشو، کشو را می‌بندد (رفتار closeOnSelect کامپوننت مرجع)
    drawer.addEventListener('click', function (event) {
        var link = event.target.closest ? event.target.closest('a[href]') : null;
        if (link) closeDrawer();
    });

    drawer.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            event.preventDefault();
            closeDrawer();
            return;
        }
        if (event.key !== 'Tab') return;

        var items = focusableInDrawer();
        if (!items.length) return;

        var first = items[0];
        var last = items[items.length - 1];

        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    });

    /* ---------------------------------------------------------- میان‌بُرها */

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && drawerOpen) {
            closeDrawer();
            return;
        }

        // Ctrl+B / ⌘B — همان میان‌بُر کامپوننت مرجع
        if (event.key && event.key.toLowerCase() === 'b' && (event.ctrlKey || event.metaKey) && !event.altKey) {
            event.preventDefault();
            if (isDesktop()) {
                togglePanel();
            } else if (drawerOpen) {
                closeDrawer();
            } else {
                openDrawer();
            }
        }
    });

    // با بزرگ‌تر شدن پنجره، کشوی موبایل معنا ندارد
    window.addEventListener('resize', function () {
        if (drawerOpen && isDesktop()) closeDrawer();
        syncSubmenus();
    });

    syncSubmenus();

    // پس از هر جابه‌جایی HTMX، کشو بسته شود (رفتار قبلی پنل حفظ می‌شود)
    document.addEventListener('htmx:afterSwap', function (event) {
        if (drawerOpen && event.target && event.target.id !== 'dash-sidebar') closeDrawer();
    });
})();
