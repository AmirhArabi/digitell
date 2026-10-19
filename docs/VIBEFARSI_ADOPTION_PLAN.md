# پلن پذیرش وایب‌فارسی در پروژه دیجی‌تل

> نسخه: ۱.۰ · تاریخ بررسی: ۱۴۰۵/۰۷/۲۷ · منبع: [vibefarsi.ir](https://vibefarsi.ir) و رجیستری عمومی `/r`

## ۱. خلاصه اجرایی

وایب‌فارسی یک **رجیستری کامپوننت React + Tailwind v4** برای رابط‌های راست‌چین فارسی است، نه یک پکیج npm وابسته به زمان اجرا. کد هر آیتم داخل پروژه کپی می‌شود و از همان لحظه مال پروژه است. این کتابخانه ۳۰۰ آیتم دارد: **۷۸ کامپوننت، ۲۳ بلاک، ۱۵ نمودار، ۱۰ تقویم، ۶۳ انیمیشن، ۴۴ پس‌زمینه، ۳۱ قالب، ۶ تم، ۱۱ کتابخانه کمکی و ۱۳ مهارت (SKILL.md)**.

پروژه دیجی‌تل اما **Django SSR + HTMX + Tailwind v4 + جاوااسکریپت خالص** است و هیچ پکیج React یا باندلر JS ندارد. بنابراین:

- `npx vibefarsi init` و `add` در این پروژه **قابل استفاده نیست** (فرض آن‌ها Next.js/Vite است و tsconfig و layout.tsx می‌سازند).
- کد کامپوننت‌های تعاملی با React Hooks نوشته شده‌اند؛ مستقیم داخل قالب Django قابل اجرا نیستند.
- اما **سیستم طراحی، توکن‌ها، قالب‌های صفحه، بلاک‌ها، کتابخانه‌های فارسی و منطق فرم‌ها** ارزش مستقیم و بالایی برای پروژه دارند.

**تصمیم پیشنهادی:** گزینه A — «پورت سیستم طراحی و کامپوننت‌های نمایشی به Django + JS خالص»، با امکان افزودن React island فقط برای تقویم شمسی/نمودارهای پیچیده در آینده. با این روش:

- هیچ runtime جدیدی به سایت اضافه نمی‌شود؛
- ظاهر و کیفیت فارسی/راست‌چین ارتقا می‌یابد؛
- کامپوننت‌ها یک‌بار ساخته می‌شوند و در همه صفحات استفاده می‌شوند؛
- وابستگی به کتابخانه خارجی در زمان اجرا صفر می‌ماند.

---

## ۲. وایب‌فارسی دقیقاً چه چیزی ارائه می‌دهد؟

| بخش | تعداد | نمونه‌های مرتبط با دیجی‌تل |
| --- | ---: | --- |
| کامپوننت | ۷۸ | `price`، `stat`، `amount-input`، `phone-input`، `otp-field`، `date-picker`، `data-table`، `timeline`، `combobox`، `dialog`، `table`، `rating`، `file-upload` |
| بلاک | ۲۳ | `hero`، `product-grid`، `pricing`، `faq`، `testimonials`، `auth-card`، `navbar`، `footer`، `contact` |
| نمودار | ۱۵ | خطی، میله‌ای، دایره‌ای، حلقه‌ی پیشرفت، نقشه‌ی حرارتی، آبشاری، شمعی (SVG و بدون کتابخانه) |
| تقویم | ۱۰ | تقویم شمسی، انتخاب تاریخ، بازه‌ی تاریخ، انتخاب نوبت، گانت، شیفت |
| قالب صفحه | ۳۱ | `checkout`، `receipt`، `auth`، `wallet`، `invoice`، `shop-dashboard`، `store`، `admin-orders` |
| کتابخانه کمکی | ۱۱ | `utils` (اعداد فارسی/تومان)، `number-to-words`، `persian` (اعتبارسنجی)، `jalali`، `iran-divisions`، `iran-holidays`، `chart-utils` |
| تم | ۶ | گرافیت، فیروز‌ه، زعفران، انار، لاجورد، کاغذ |
| مهارت | ۱۳ | `persian-rtl-ui`، `persian-typography`، `persian-ui-copy`، `iran-validation`، `jalali-calendar`، `zarinpal-payment`، `kavenegar-otp` |

نکات فنی مهم:

- مجوز **MIT** و رایگان است؛ آیکون‌ها از `lucide-react` (مجوز ISC) می‌آیند.
- تقریباً همه‌ی کامپوننت‌ها وابستگی npm دیگری جز `lucide-react` ندارند؛ Framer Motion و GSAP در رجیستری نیست.
- کامپوننت‌های تعاملی با `"use client"`، `useState`، `useRef`، `useEffect` و در موارد پیچیده `createContext` نوشته شده‌اند.
- رنگ‌ها از توکن‌های معنایی (`bg-background`، `text-muted-foreground`، `border-border`، `rounded-control`، `shadow-control`، `duration-(--motion)`) می‌آیند. **این توکن‌ها در پروژه ما وجود ندارند** و بدون لایه‌ی سازگاری، کد کپی‌شده ناقص رندر می‌شود.
- رجیستری JSON در مسیرهای جمع (`/r/components/...`، `/r/blocks/...`، `/r/templates/...`، `/r/lib/...`، `/r/themes/...`) در دسترس است و برای اسنپ‌شات گرفتن کد مناسب است.

---

## ۳. وضعیت فعلی پروژه و شکاف‌ها

| موضوع | وضعیت فعلی | ارتباط با وایب‌فارسی |
| --- | --- | --- |
| فریم‌ورک | Django، قالب‌سرور، HTMX 2، JS خالص | React components قابل استفاده مستقیم نیستند |
| Tailwind | v4.3.3 با CLI و `input.css` | هم‌نسخه با وایب‌فارسی؛ خبر خوب |
| RTL | `dir="rtl"` سراسری و کلاس‌های منطقی نسبی | پایه آماده است |
| فونت | YekanBakh محلی با ارقام فارسی | باید حفظ شود؛ Vazirmatn کتابخانه جایگزین نشود |
| واحد پول | پارت `toman_icon.html` و نماد SVG | باید در کامپوننت‌های پورت‌شده هم حفظ شود |
| اعداد | ارقام لاتین در داده، نمایش فارسی با فونت | VibeFarsi هم همین الگو را دارد (`fa`/`en`) |
| توکن معنایی | پالت `primary-*` و کلاس‌های slate، بدون لایه semantic | نیازمند Phase 0 |
| کامپوننت مشترک | مارک‌آپ‌ها در قالب‌ها تکرار شده (کارت محصول، قیمت، دکمه) | بزرگ‌ترین فرصت بازآرایی |
| تقویم شمسی | دیت‌پیکر سفارشی iOS در پروفایل + `jdatetime` | می‌تواند از UX و منطق وایب‌فارسی الگو بگیرد |
| نمودار | Chart.js محلی در داشبورد | بهتر است بماند؛ SVGهای React جایگزین پرهزینه‌اند |
| اعتبارسنجی ایرانی | فیلدهای کارت/شبا/کد ملی در مدل، بدون اعتبارسنجی کامل | `lib/persian` ارزش بالایی دارد |
| تست | ۱۷۸ تست Django | باید با تست‌های جدید برای توکن/کامپوننت/فرم‌ها گسترش یابد |

---

## ۴. گزینه‌های معماری

| معیار | A: پورت سیستم طراحی (پیشنهادی) | B: React island برای بخش‌ها | C: فقط کپی قالب/بلاک |
| --- | --- | --- | --- |
| روش | توکن‌ها + پورت کامپوننت به Django partial + JS خالص | افزودن Vite + چند island React برای تقویم/نمودار | کپی مارک‌آپ و کلاس‌ها بدون ساخت سیستم |
| runtime جدید | ندارد | React + ReactDOM (~۴۵KB gzip) | ندارد |
| سرعت شروع | متوسط | بالا برای ویجت پیچیده | خیلی بالا |
| نگه‌داری | بالا؛ کد مال خودمان | متوسط؛ دو دنیای فنی | پایین؛ تکرار و واگرایی |
| هماهنگی با HTMX | کامل | نیازمند مرزبندی دقیق SSR/CSR | کامل |
| ریسک | پورت تعامل‌ها | پیچیدگی بیلد و hydration | بدهی فنی سریع |
| هزینه تقریبی MVP | ۱۰ تا ۱۴ روز کاری | ۱۵ تا ۲۰ روز کاری | ۳ تا ۵ روز کاری |

**انتخاب: A.** گزینه B فقط به‌عنوان «در پشتی» برای تقویم رویداد/گانت یا نمودارهای خیلی خاص نگه داشته شود؛ نه برای دکمه و فرم.

---

## ۵. تصمیم‌های فنی کلیدی

### ۵.۱. توکن‌های سازگاری، نه تم تیره‌ی کتابخانه

تم پیش‌فرض وایب‌فارسی «گرافیت» و تیره است. سایت ما روشن و برند‌محور است. باید ساختار تم «کاغذ» را بگیریم اما رنگ‌ها را به برند فعلی نگاشت کنیم:

```css
/* static/css/input.css — لایه سازگاری وایب‌فارسی */
@theme {
  --color-background: #f7fafd;
  --color-foreground: #1e293b;
  --color-card: #ffffff;
  --color-card-foreground: #1e293b;
  --color-popover: #ffffff;
  --color-popover-foreground: #1e293b;
  --color-muted: #f1f5f9;
  --color-muted-foreground: #64748b;
  --color-border: #e2e8f0;
  --color-input: #e3eaf3;
  --color-ring: #7db2df;
  --color-primary: #1f5eb2;            /* برند دیجی‌تل */
  --color-primary-foreground: #ffffff;
  --color-secondary: #eef4fb;
  --color-secondary-foreground: #153f78;
  --color-accent: #eff6fd;
  --color-accent-foreground: #153f78;
  --color-success: #059669;
  --color-warning: #f59e0b;
  --color-destructive: #e11d48;
  --color-brand: #1f5eb2;
  --color-brand-foreground: #ffffff;

  --radius-control: 0.75rem;
  --radius-field: 0.75rem;
  --radius-surface: 1rem;
  --radius-overlay: 1.25rem;
  --shadow-control: 0 1px 2px rgba(15, 42, 80, 0.04);
  --shadow-overlay: 0 24px 60px -30px rgba(15, 42, 80, 0.35);
  --motion: 200ms;
  --ease-motion: cubic-bezier(0.32, 0.72, 0, 1);
  --border-width-line: 1px;
  --font-sans: "YekanBakhFaNum", "YekanBakh", system-ui, sans-serif;
}
```

نکته: `--color-primary` جدید با پالت `--color-primary-50..950` فعلی تعارض ندارد و می‌تواند همان `#1F5EB2` باشد.

### ۵.۲. اعداد: داده لاتین، نمایش فارسی

- مقدار فرم‌ها و دیتابیس **لاتین** بماند (سازگاری با اعتبارسنجی، ارسال به درگاه، جست‌وجو).
- نمایش با ارقام فارسی انجام شود؛ در سمت سرور با تمپلیت‌تگ و در سمت کلاینت با فونت فعلی یا تابع `fa()`.
- برای جداکننده هزارگان تصمیم بگیریم: وایب‌فارسی `٬` (U+066C) استفاده می‌کند، پروژه فعلی `,`. پیشنهاد: **در نمایش جدید از `٬` استفاده شود** و یک تمپلیت‌تگ مشترک این کار را انجام دهد تا همه‌جا یکسان باشد. اگر تغییر سراسری ریسک دارد، در فاز اول `,` حفظ و در فاز بعد مهاجرت شود.

### ۵.۳. فونت و واحد پول

- فونت YekanBakh محلی حفظ می‌شود؛ فونت Vazirmatn کتابخانه فقط در کدهای مرجع دیده می‌شود و وارد پروژه نمی‌شود.
- کامپوننت `price` پورت‌شده باید به‌جای متن «تومان» از `{% include 'includes/toman_icon.html' %}` استفاده کند یا پارامتر `unit` با حالت `icon` داشته باشد.

### ۵.۴. آیکون‌ها

- `lucide-react` در Django استفاده نمی‌شود؛ مسیرهای SVG لازم به اسپرایت موجود `templates/includes/svg_sprites.html` اضافه می‌شوند یا پارت `components/icon.html` با کلاس اندازه ساخته می‌شود.
- فقط آیکون‌های استفاده‌شده اضافه شوند؛ کل پکیج کپی نشود.
- مجوز ISC لوکید و MIT وایب‌فارسی در `vendor/vibefarsi/LICENSE` نگه‌داری شود.

### ۵.۵. مرز SSR و تعامل

- وضعیت سرور با Django + HTMX؛ وضعیت محلی UI (باز/بسته، فوکوس، انتخاب) با JS خالص و `data-*`.
- هیچ دوباره‌سازی state در کلاینت نباشد. مثلاً `data-table` با صفحه‌بندی و مرتب‌سازی سمت سرور پیاده شود، نه با `useMemo` و مرتب‌سازی کلاینت.
- همه‌ی ماژول‌های JS باید پس از `DOMContentLoaded` و `htmx:afterSettle` دوباره مقداردهی شوند.

### ۵.۶. منبع کد و نسخه

- کد از رجیستری با اسکریپت `scripts/fetch_vibefarsi.py` در پوشه‌ی `vendor/vibefarsi/` اسنپ‌شات شود؛ این پوشه مرجع است، نه بخشی از build.
- تاریخ/نسخه‌ی اسنپ‌شات در `vendor/vibefarsi/README.md` ثبت شود تا به‌روزرسانی آگاهانه باشد.
- به‌روزرسانی خودکار و مداوم ممنوع؛ ارتقا دستی و همراه با تست.

---

## ۶. نقشه راه فازی

### Phase 0 — پایه و لایه سازگاری (۱ تا ۲ روز)

**خروجی‌ها:**

1. توکن‌های semantic در `input.css` + نگاشت به Tailwind v4.
2. ساختار `templates/components/{ui,forms,layout}/` و `static/js/ui/`.
3. تمپلیت‌تگ‌های فارسی: `fa`، `fa_number`، `toman`، `percent`، `jalali_date` در `utils/templatetags/ui.py`.
4. تابع‌های JS مشترک: `static/js/ui/core.js` (`fa`, `en`, `faNumber`, `formatToman`, `initOnHtmx`).
5. صفحه‌ی گالری داخلی `/dev/ui/` فقط برای `DEBUG` یا `is_staff` با همه‌ی کامپوننت‌ها و حالت‌ها.
6. اسنپ‌شات رجیستری + مجوز + مستند `docs/VIBEFARSI.md`.

**معیار پذیرش:** صفحه‌ی گالری باز می‌شود؛ توکن‌ها در DevTools دیده می‌شوند؛ `bg-background`، `text-muted-foreground`، `rounded-control` و `shadow-control` کار می‌کنند؛ build بدون خطای Tailwind.

### Phase 1 — کامپوننت‌های پایه (۲ تا ۳ روز)

پورت بدون React: `button`, `input`, `textarea`, `select`, `badge`, `alert`, `card`, `separator`, `skeleton`, `spinner`, `progress`, `empty-state`, `table`, `price`, `stat`, `avatar`, `kbd`, `breadcrumb`, `pagination`, `accordion`, `timeline`.

**الگو:** هر کامپوننت یک پارت Django با پارامترهای محدود + یک نقشه‌ی variant در پایتون. مثال:

```django
{# templates/components/ui/button.html #}
<{% if href %}a{% else %}button{% endif %}
   {% if href %}href="{{ href }}"{% else %}type="{{ type|default:'button' }}"{% endif %}
   class="ui-btn ui-btn--{{ variant|default:'primary' }} ui-btn--{{ size|default:'md' }} {{ class }}">
  {% if icon_start %}{% include 'components/icon.html' with name=icon_start %}{% endif %}
  <span>{{ label }}</span>
  {% if icon_end %}{% include 'components/icon.html' with name=icon_end %}{% endif %}
</{% if href %}a{% else %}button{% endif %}>
```

**معیار پذیرش:** کارت محصول، دکمه‌ها و قیمت‌ها با کامپوننت‌های جدید بدون تغییر ظاهر محسوس رندر شوند؛ تعداد تکرار مارک‌آپ قیمت در قالب‌ها کاهش یابد؛ تست رگرسیون قالب‌ها سبز بماند.

### Phase 2 — فرم‌ها و اعتبارسنجی ایرانی (۳ تا ۵ روز)

1. `amount-input`: ارتقای فیلد مبلغ صفحه واریز با quick chips، حداقل/حداکثر، نمایش «به حروف» و نماد تومان.
2. `phone-input` + `lib/persian`: اعتبارسنجی موبایل، تشخیص اپراتور، نرمال‌سازی ارقام فارسی.
3. `otp-field`: صفحه‌ی `verify_otp` با جعبه‌های LTR، چسباندن کد و پشتیبانی کیبورد فارسی.
4. `number-field`: تعداد در سبد خرید و صفحه محصول (جایگزین استپر فعلی).
5. `address-picker` + `iran-divisions`: استان/شهر در تسویه‌حساب؛ اعتبارسنجی کد پستی.
6. `national-id-input`، `iban-input`، `card-number-input` برای پروفایل و کیف پول.
7. پورت منطق اعتبارسنجی به **پایتون** برای اعتبارسنجی سرور (موبایل، کد ملی، شبا mod 97، کارت Luhn) + تست واحد.

**معیار پذیرش:** فرم‌های واریز، ورود با OTP و تسویه‌حساب بدون خطا کار می‌کنند؛ ارقام فارسی و لاتین هر دو پذیرفته می‌شوند؛ خطاها سمت سرور هم enforceable هستند؛ تست‌ها پاس می‌شوند.

### Phase 3 — قالب‌ها و بازآرایی صفحات (۴ تا ۶ روز)

- **Product detail:** `price`, `rating`, `badge`, `tabs`, `accordion`, استپر تعداد.
- **Shop/Category:** `product-grid`, `pagination`, `breadcrumb`, `skeleton`, `empty-state`, `sheet` برای فیلترها.
- **Cart:** `table`, `number-field`, `alert`, `empty-state`.
- **Checkout:** `stepper`, `address-picker`, `radio-group`, `textarea`, خلاصه سفارش با `price`.
- **Deposit:** نسخه‌ی نهایی با `amount-input` و `receipt`/`success-check` صفحه‌ی موفقیت.
- **Auth:** قالب `auth`، `otp-field`, `stepper`, `password-input`.
- **Dashboard:** `stat`, `data-table` سرورمحور، `date-range-picker`، `badge`, `skeleton`.
- **Order tracking:** `timeline` شمسی.
- **Profile:** تاریخ تولد با `date-picker` شمسی، `tabs`، `dialog`.

**معیار پذیرش:** صفحات کلیدی با کامپوننت‌های مشترک بازسازی شده‌اند؛ تفاوت‌های بصری فقط در جهت بهبود است؛ همه‌ی مسیرهای خرید تست دستی/خودکار می‌شوند.

### Phase 4 — تقویم، نمودار و موارد پیچیده (اختیاری، ۴ تا ۶ روز)

- **تقویم:** یا پورت سبک `month-view` به JS خالص و اتصال به دیت‌پیکر فعلی، یا React island برای `calendar-core`/`event-calendar`. پیشنهاد: شروع با پورت سبک؛ island فقط اگر گانت/شیفت لازم شد.
- **نمودار:** Chart.js فعلی بماند. فقط فرمت‌دهی `chart-utils` (تیک‌های فارسی، محور شمسی، اعداد فارسی) به JS پورت شود. کد SVG کامل React پورت نشود.
- **انیمیشن‌ها:** فقط ۳ تا ۴ مورد کم‌هزینه (`reveal`, `success-check`, `counter`, `marquee` در صورت نیاز) و با `prefers-reduced-motion`.

**معیار پذیرش:** هیچ React runtime وارد باندل اصلی نشده؛ اندازه JS جدید کمتر از ۱۵KB gzip؛ CLS و LCP بدتر نشده‌اند.

### Phase 5 — بهینه‌سازی و تثبیت (۱ تا ۲ روز)

- بازبینی دسترس‌پذیری (فوکوس، ARIA، کیبورد، کنتراست).
- حذف CSS/JS استفاده‌نشده، اندازه‌گیری بودجه.
- مستندسازی الگوها و افزودن قواعد به `AGENTS.md`.
- تست دود Playwright برای سه مسیر: واریز، OTP، تسویه‌حساب.

**جمع‌بندی زمان:** MVP با کیفیت (Phase 0 تا 2 + دو صفحه‌ی نمونه) حدود **۸ تا ۱۲ روز کاری**؛ پوشش کامل صفحات ۳ تا ۴ هفته.

---

## ۷. نقشه‌ی کامپوننت به صفحه

| کامپوننت/آیتم وایب‌فارسی | محل استفاده در دیجی‌تل | اولویت | روش پیاده‌سازی |
| --- | --- | --- | --- |
| `price` | کارت محصول، صفحه محصول، سبد، تسویه، داشبورد | بحرانی | پورت ساده + نماد تومان |
| `button`, `badge`, `alert`, `card`, `input` | همه‌جا | بحرانی | پورت مستقیم |
| `amount-input` + `number-to-words` | واریز وجه، کیف پول | بحرانی | پورت JS خالص |
| `phone-input` + `persian` | ورود/ثبت‌نام، تسویه، پروفایل | بحرانی | JS + اعتبارسنجی پایتون |
| `otp-field` | `verify_otp` | بحرانی | JS خالص |
| `stat` | داشبورد، صفحه محصول (فروش) | بالا | پورت مستقیم |
| `timeline` | پیگیری سفارش، تیکت | بالا | پورت مستقیم |
| `stepper` | تسویه‌حساب، ثبت‌نام | بالا | پورت مستقیم |
| `empty-state`, `skeleton`, `pagination` | فروشگاه، داشبورد | بالا | پورت مستقیم |
| `product-grid`, `hero`, `features`, `faq`, `footer` | صفحات عمومی | متوسط | الگوی بصری، نه کپی کامل |
| `data-table` | داشبورد سفارش‌ها/محصولات | متوسط | پورت با صفحه‌بندی سرور |
| `date-picker` + `jalali` | تاریخ تولد، فیلتر گزارش‌ها | متوسط | JS خالص/الگوی دیت‌پیکر فعلی |
| `iban-input`, `card-number-input`, `national-id-input`, `postal-code-input` | پروفایل، کیف پول، آدرس | متوسط | JS + پایتون |
| `address-picker` + `iran-divisions` | تسویه‌حساب | متوسط | پورت با HTMX |
| `receipt`, `checkout`, `auth`, `invoice` | واریز، تسویه، ورود، فاکتور | متوسط | الگوی صفحه + کامپوننت‌ها |
| `chart-utils` + فرمت‌ها | نمودارهای داشبورد | متوسط | پورت کوچک JS/Python |
| `calendar-core`, `event-calendar`, `gantt`, `shift-scheduler` | آینده/نوبت‌دهی | پایین | React island یا مدل جدید |
| نمودارهای SVG ری‌اکتی | داشبورد | پایین | جایگزین Chart.js نشود |
| `animations` (۶۳) | صفحات منتخب | پایین | ۳ تا ۴ مورد CSS |
| `backgrounds` (۴۴) | لندینگ/کمپین | پایین | فقط CSS سبک؛ شیدرها نه |
| `command`, `context-menu`, `carousel`, `video-player` | آینده | پایین | فعلاً لازم نیست |

---

## ۸. الگوی پیاده‌سازی پیشنهادی

### ۸.۱. ساختار پوشه‌ها

```
templates/
  components/
    ui/            # button.html, badge.html, price.html, ...
    forms/         # field.html, error.html, help.html
    layout/        # section.html, card.html
  dev/ui_gallery.html
static/
  js/ui/
    core.js        # fa/en/faNumber + init registry
    otp.js
    amount-input.js
    phone-input.js
    dialog.js
    data-table.js
  css/input.css    # توکن‌ها + لایه components
utils/
  persian.py       # اعتبارسنجی موبایل/شبا/کد ملی/کارت
  templatetags/ui.py
vendor/vibefarsi/  # اسنپ‌شات مرجع + LICENSE + README
```

### ۸.۲. تمپلیت‌تگ فارسی

```python
# utils/templatetags/ui.py
from django import template
register = template.Library()

FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"

@register.filter
def fa_digits(value):
    return str(value).translate(str.maketrans("0123456789", FA_DIGITS))

@register.filter
def fa_number(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return value
    return f"{number:,}".translate(str.maketrans("0123456789", FA_DIGITS)).replace(",", "٬")

@register.simple_tag
def toman(value):
    return fa_number(value)
```

### ۸.۳. ماژول JS و اتصال به HTMX

```js
// static/js/ui/core.js
export const FA = "۰۱۲۳۴۵۶۷۸۹";
export const fa = (v) => String(v).replace(/\d/g, (d) => FA[+d]);
export const en = (v) => String(v).replace(/[۰-۹]/g, (d) => FA.indexOf(d));

const registry = new Map();
export function register(name, init) { registry.set(name, init); }

export function initAll(root = document) {
  root.querySelectorAll("[data-ui]").forEach((el) => {
    if (el.dataset.uiReady) return;
    registry.get(el.dataset.ui) ?. (el);
    el.dataset.uiReady = "1";
  });
}

document.addEventListener("DOMContentLoaded", () => initAll());
document.addEventListener("htmx:afterSettle", (e) => initAll(e.target));
```

```html
<div data-ui="otp" data-length="6" data-name="code" data-input-id="id_code"></div>
```

### ۸.۴. اعتبارسنجی دو لایه

- **سمت کلاینت:** فقط تجربه‌ی کاربری (تشخیص اپراتور، ماسک، ارقام فارسی).
- **سمت سرور:** اعتبارسنجی قطعی با پایتون و همان قواعد `lib/persian`:
  - موبایل: نرمال‌سازی + پیش‌شماره‌های معتبر
  - کد ملی: رقم کنترل
  - شبا: حذف `IR`، تبدیل حروف، mod 97
  - کارت: Luhn + BIN بانک
  - کد پستی: ۱۰ رقم و قاعده‌ی صفر ابتدایی

### ۸.۵. گالری کامپوننت

یک مسیر فقط‌خواندنی `/dev/ui/` (محدود به `DEBUG` یا `is_staff`) با تمام variantها، حالت‌های hover/focus/disabled/error و RTL. این صفحه:

- منبع حقیقت بصری تیم می‌شود؛
- از واگرایی کامپوننت‌ها جلوگیری می‌کند؛
- تست دستی را سریع می‌کند.

### ۸.۶. تست

- تست واحد تمپلیت‌تگ‌ها و اعتبارسنجی‌های پایتون.
- تست رندر کامپوننت‌های کلیدی (وجود کلاس‌ها و حالت‌ها).
- تست دود مرورگر برای فرم‌های واریز/OTP/تسویه.
- بررسی بودجه: JS و CSS اضافه‌شده، LCP/CLS در صفحات اصلی.

---

## ۹. اولویت‌بندی (MoSCoW)

**Must (بدون این‌ها شروع نکن):** توکن‌های سازگاری، `price`، `button`، `input`، `field`، `alert`، `fa`/`fa_number`، گالری، مجوز.

**Should:** `amount-input`، `phone-input`، `otp-field`، `stepper`، `stat`، `timeline`، `empty-state`، `skeleton`، `pagination`، اعتبارسنجی پایتون.

**Could:** `date-picker`، `address-picker`، `data-table`، `receipt`، `checkout`، `auth`، نمودارهای شمسی.

**Won't (در این فاز):** React runtime، تقویم گانت/شیفت، شیدرهای WebGL، مهاجرت از Chart.js، بازنویسی کامل داشبورد.

---

## ۱۰. ریسک‌ها و کاهش آن‌ها

| ریسک | اثر | کاهش |
| --- | --- | --- |
| دو سیستم طراحی موازی | ظاهر ناهمگون و بدهی فنی | توکن مشترک + گالری + ممنوعیت رنگ دستی |
| پورت state ری‌اکت به JS | باگ تعاملی | فقط کامپوننت‌های لازم، تست مرورگر، الگوی `data-ui` |
| فراموشی `htmx:afterSettle` | کامپوننت‌ها بعد از تعویض DOM کار نمی‌کنند | `initAll` مرکزی + تست HTMX |
| تغییرات بالادست کتابخانه | کد پورت‌شده قدیمی می‌شود | اسنپ‌شات با نسخه + ارتقای دستی |
| حجیم شدن CSS/JS | افت سرعت | فقط کامپوننت‌های استفاده‌شده، بودجه‌ی اندازه، پاک‌سازی |
| ارقام فارسی در مقادیر فرم | خطای اعتبارسنجی/درگاه | قانون «نمایش فارسی، مقدار لاتین» + تست |
| مجوز/انتساب | ریسک حقوقی | نگه‌داری MIT/ISC در `vendor/` و اشاره در README |
| تقویم شمسی نادرست | خطای تاریخ سفارش/گزارش | استفاده از `jdatetime` سمت سرور و تست مرزی |

---

## ۱۱. اسپرینت اول پیشنهادی (۷ گام عملی)

1. اسنپ‌شات رجیستری + مجوز + `docs/VIBEFARSI.md`.
2. افزودن توکن‌های سازگاری به `input.css` و build.
3. ساخت `templates/components/ui/{button,input,price,badge,alert,card}.html`.
4. ساخت `utils/templatetags/ui.py` + تست‌ها.
5. ساخت `/dev/ui/` و نمایش همه‌ی حالت‌ها.
6. مهاجرت پایلوت: کارت محصول + فیلد مبلغ صفحه واریز.
7. اجرای تست‌ها، اندازه‌گیری حجم/سرعت و بازبینی بصری در موبایل و دسکتاپ.

**تعریف Done اسپرینت:** هیچ تغییر بصری ناخواسته‌ای در صفحات پایلوت نباشد؛ تست‌ها سبز؛ حجم CSS/JS اضافه‌شده زیر بودجه؛ کد کامپوننت‌ها در گالری مستند شده باشد.

---

## ۱۲. تصمیم‌هایی که باید گرفته شود

1. **تأیید گزینه A** (پورت بدون React) به‌عنوان مسیر اصلی.
2. **جداکننده هزارگان:** `٬` وایب‌فارسی یا `,` فعلی؟ پیشنهاد: `٬` در نمایش‌های جدید با تمپلیت‌تگ مشترک.
3. **React island:** آیا برای تقویم/گانت در آینده مجاز است یا فعلاً ممنوع؟
4. **دامنه‌ی MVP:** فقط فرم‌ها و صفحات خرید، یا شامل داشبورد هم بشود؟

---

## پیوست: منابع و نحوه‌ی دریافت کد

- سایت: <https://vibefarsi.ir>
- مستندات و شروع سریع: <https://vibefarsi.ir/docs>
- فهرست ماشین‌خوان رجیستری: `https://vibefarsi.ir/r`
- نمونه‌ی آیتم: `https://vibefarsi.ir/r/components/price.json`، `/r/lib/persian.json`، `/r/templates/checkout.json`
- مخزن: <https://github.com/TronIsHere/vibefarsiui> (MIT)
- MCP برای Cursor/Claude Code: `https://vibefarsi.ir/mcp` (اختیاری)

> توجه: `npx vibefarsi init` در این پروژه اجرا نشود؛ فرض آن Next.js/Vite است و فایل‌های TypeScript و tsconfig می‌سازد. دریافت کد باید از رجیستری JSON یا کپی دستی صفحه‌ی کامپوننت انجام شود.
