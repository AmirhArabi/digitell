# Product Requirements Document (PRD) --- Zitro Shop (فروشگاه اینترنتی زیترو)

> **Document type:** Evidence-based, current-state PRD / codebase audit.
> **Audience:** Product owner, developers, reviewers. **Basis:** Direct
> inspection of the repository at commit `fb71e2a` plus targeted
> read-only runtime checks (documented in
> [§19](#19-evidence-and-source-references)). Every status below is
> derived from source code or from a check that was actually executed.
> Where evidence is missing, the item is explicitly marked
> **Unverified** instead of being assumed. **Last updated:** 2026-10-13.

------------------------------------------------------------------------

## 1. Product Overview

**Zitro Shop (زیترو)** is a Persian-language (RTL) e-commerce web
application for digital goods --- mobile phones, tablets, laptops,
smartwatches, gaming gear, headphones, speakers, accessories and
storage. It is a **Django monolith with server-rendered templates, HTMX
partial refresh and a hand-built staff dashboard**; there is no separate
SPA, no REST/GraphQL API and no headless CMS.

Two distinct surfaces exist inside one codebase:

1.  **Storefront** (`/`, `/shop/`, `/products/...`, `/blog/...`,
    `/cart/`, `/orders/...`, `/tickets/`, `/accounts/...`) --- public
    browsing, guest/user cart, checkout, a **simulated** payment
    gateway, order tracking, support tickets and a customer profile with
    order history.
2.  **Seller/staff dashboard** (`/dashboard/`, staff-only) --- catalog
    management, inventory, orders, customers, coupons, banners, blog
    content, support tickets, site settings, KPI overview and a full
    analytics/reporting page with 8 charts and 3 CSV exports.

Verified technology stack (from
[config/settings.py](config/settings.py), [package.json](package.json)
and the installed interpreter):

  --------------------------------------------------------------------------------------------------------------------------------
  Layer                   Technology                    Evidence
  ----------------------- ----------------------------- --------------------------------------------------------------------------
  Language / runtime      Python 3.14.6                 `python --version`; README claim of Python 3.14 matches

  Framework               Django 6.1.1                  `django.get_version()`

  Database                SQLite (`db.sqlite3`)         `DATABASES` in [config/settings.py](config/settings.py#L79-L84)

  Templating              Django Templates +            `INSTALLED_APPS`, `intcomma` used in checkout
                          `django.contrib.humanize`     

  Interactivity           HTMX via `django_htmx`        `django_htmx.middleware.HtmxMiddleware`, `request.htmx` branches

  CSS                     Tailwind CSS v4.3.3           [package.json](package.json), [static/css/input.css](static/css/input.css)
                          (`@tailwindcss/cli`)          

  Charts                  Chart.js UMD bundle vendored  [static/js/vendor/chart.umd.min.js](static/js/vendor/chart.umd.min.js),
                          locally                       [static/js/dashboard-charts.js](static/js/dashboard-charts.js)

  Static/media            WhiteNoise middleware +       [config/settings.py](config/settings.py),
                          `MEDIA_ROOT`/`STATIC_ROOT`;   [config/urls.py](config/urls.py#L22-L24)
                          DEBUG-mode static serving     

  Font                    Vazirmatn via Google Fonts    [templates/base.html](templates/base.html),
                                                        [templates/orders/mock_payment.html](templates/orders/mock_payment.html)
  --------------------------------------------------------------------------------------------------------------------------------

**Not present (explicitly checked):** Django REST Framework or any
serializers, any `forms.py` module (all input handling is raw
`request.POST`), Celery/background workers, Redis, email/SMS providers,
real payment gateways, `requirements.txt`, Dockerfile or CI
configuration.

------------------------------------------------------------------------

## 2. Product Vision and Objectives

The repository contains **no formal vision statement**. The only
product-intent documents are [README.md](README.md) and
[docs/ROADMAP_ADMIN_PANEL.md](docs/ROADMAP_ADMIN_PANEL.md).

Objectives that *can* be verified from those documents and from the code
they describe:

-   Rebuild the Zitro digital-goods store as a modern Django +
    Tailwind + HTMX platform (README introduction).
-   Provide a **first-party seller dashboard** that removes dependence
    on Django's built-in admin: "فهرست کامل قابلیت‌ها و پلن اولویت‌بندی در
    سند نقشه راه پنل ادمین" (README §4; roadmap intro).
-   Support Iranian market conventions: prices in Toman, Persian RTL UI,
    Vazirmatn font, Tehran timezone, Persian numerals in admin inputs,
    Excel-friendly (`utf-8-sig` + BOM) CSV exports.
-   Market differentiated services that are **not** implemented in code:
    instalment purchase without guarantor and a Shaparak-style online
    gateway.

Objectives that are **aspirational only** (roadmap Phase 4) are listed
in [§16](#16-planned-features-and-future-scope) and are not presented as
current capability anywhere in this document.

------------------------------------------------------------------------

## 3. Current Product Scope

### 3.1 In scope today (verified)

-   Anonymous browsing of home, catalog, category pages, product detail,
    blog, FAQ, contact, instalment-info, order tracking, login/register.
-   Guest cart (session-keyed) and authenticated cart (user-keyed), with
    HTMX add/increase/decrease/remove and live badge.
-   Checkout: recipient/shipping address form, shipping method radio
    group, coupon apply/remove, order creation with immutable item
    snapshot.
-   Simulated online payment gateway and cash-on-delivery; order
    invoice/success page; public order tracking.
-   Customer support tickets (chat-style, customer ⇄ staff) with
    status/priority/category and HTMX polling.
-   Staff dashboard covering catalog, inventory, orders, customers,
    coupons, banners, blog, tickets, settings, overview KPIs and
    reports/CSV exports.
-   Django admin, registered **only** for `Group`, `Ticket`,
    `TicketMessage` (verified at runtime --- see
    [§15](#15-current-limitations-and-known-gaps)).

### 3.2 Deliberately simulated, not real

-   Online payment is a **mock gateway**
    (`orders.views.mock_payment_view`, template
    [templates/orders/mock_payment.html](templates/orders/mock_payment.html)
    branded "شبیه‌ساز پرداخت الکترونیک زیترو"). No PSP SDK, merchant
    credentials or callback verification exists.
-   Instalment/SnappPay is **marketing copy only**; no payment method or
    credit provider is wired.
-   Order tracking is a database lookup, not a carrier integration.

### 3.3 Out of scope / absent

-   Multi-vendor marketplace, multi-language, multi-currency, tax
    engine, returns/RMA workflow, warehouse/lot tracking, review
    moderation, recommendations/ML, mobile app or API for third parties.

------------------------------------------------------------------------

## 4. Target Users and Roles

### 4.1 Customer roles that exist in code

  ----------------------------------------------------------------------------------------------------------
  Role              How it is determined  Capabilities           Evidence
  ----------------- --------------------- ---------------------- -------------------------------------------
  Anonymous visitor no session user       browse                 [products/views.py](products/views.py),
                                          catalog/blog/content   [cart/views.py](cart/views.py),
                                          pages, live search,    [orders/views.py](orders/views.py)
                                          order tracking lookup, 
                                          guest cart, checkout,  
                                          create an order        

  Registered        `accounts.User`,      everything above +     [accounts/views.py](accounts/views.py),
  customer          `is_staff=False`      profile with order     [tickets/views.py](tickets/views.py)
                                          history, support       
                                          tickets                
                                          (`login_required`)     

  Staff ("فروشنده"  `is_staff=True`       full `/dashboard/`     [dashboard/views.py](dashboard/views.py),
  / dashboard                             access, every          [dashboard/urls.py](dashboard/urls.py)
  operator)                               management screen,     
                                          grant/revoke           
                                          `is_staff` on other    
                                          users                  

  Superuser         `is_superuser=True`   same as staff here; no no `is_superuser` check anywhere outside
                                          extra gating exists in Django internals
                                          application code       
  ----------------------------------------------------------------------------------------------------------

### 4.2 Role distinctions that do **not** exist yet

-   **No granular roles** (e.g. warehouse clerk, support agent,
    marketer). Every staff user sees every dashboard screen; the roadmap
    lists this as Phase 4 (items 4.1--4.2) and it is **Planned**.
-   `Ticket.assigned_to` exists and is auto-assigned to the replying
    staff member, but assignment grants no special permissions.
-   `User.is_verified` exists as a field but is never written by any
    view or form (only
    [seed_data.py](products/management/commands/seed_data.py#L317) sets
    it `True` for demo users). It is used read-only for a ✓ badge in
    [templates/dashboard/customers.html](templates/dashboard/customers.html)
    and
    [templates/dashboard/customer_detail.html](templates/dashboard/customer_detail.html).

------------------------------------------------------------------------

## 5. User Journeys and Workflows

### 5.1 Browse → cart → checkout → payment (verified from code + tests)

1.  Visitor lands on `/` --- [home.views.index_view](home/views.py)
    assembles hero banners, top-level categories, special offers,
    featured products, hard-coded `smartphones` / `laptops`+`gaming`
    rails, brand strip and latest blog posts.
2.  `/shop/` or `/shop/category/<slug>/` ---
    [products.views.shop_view](products/views.py) filters by category
    (parent category includes descendants), text query `q` (title,
    `title_en`, SKU, short description), brand slugs, `in_stock`,
    `special`, `min_price`/`max_price`, and sorts by
    newest/cheapest/expensive/discount/popular. HTMX requests return
    only
    [product_grid.html](templates/products/partials/product_grid.html).
3.  Product detail `GET /products/<pk>/<slug>/` ---
    [products.views.product_detail_view](products/views.py) increments
    `views_count` with `Product.objects.filter(pk=pk).update(...)`,
    computes `installment_amount = round(price/4)` and shows up to 8
    same-category related products. **Lookup is by `pk` only --- the
    `slug` segment is not validated.**
4.  Add to cart `POST /cart/add/<product_id>/` ---
    [cart.views.cart_add_view](cart/views.py) is `@require_POST`,
    creates/reuses a `Cart` (by `user` when authenticated, else by
    `session_key`) and a unique `CartItem` per product; HTMX responses
    return [cart_badge.html](templates/cart/partials/cart_badge.html).
5.  Cart page `/cart/` --- increase/decrease (decrease to 0 deletes the
    line), remove; all HTMX endpoints return
    [cart_table.html](templates/cart/partials/cart_table.html) with
    recalculated totals.
6.  Checkout `/orders/checkout/` --- requires a non-empty cart,
    otherwise redirects to `/shop/` with a warning. POST requires
    `recipient_name`, `recipient_phone`, `city`, `shipping_address`
    (server-side check: `if not all([...])`); `province` and
    `postal_code` are collected but **not** in the required set.
7.  Coupon `POST /orders/checkout/coupon/` --- stores the code in
    `request.session['coupon_code']` after
    `Coupon.validate_for(cart.total_price)` succeeds; an empty value
    clears it.
8.  Order is created with a `ZT-XXXXXX` number
    ([orders/models.py](orders/models.py) `Order.save`), item rows
    snapshotting title/SKU/unit price/quantity/line total, plus
    `discount_amount` (= cart's compare-price saving),
    `coupon_discount`, `shipping_cost` and `final_amount`.
9.  `mock_gateway` → redirect to `/orders/payment/<order_number>/` where
    "success" sets `payment_status='successful'`, `status='paid'`,
    `transaction_id = TRX-XXXXXXXXXX`, empties the cart and increments
    `coupon.used_count`; "cancel/fail" sets `payment_status='failed'`
    and returns to the cart (`status` stays `pending`).
10. `cod` → cart is emptied, `status='paid'` immediately with
    `transaction_id` left empty.
11. Success page `/orders/success/<order_number>/` renders the printable
    invoice.

This exact path (HTMX add-to-cart → checkout POST → mock payment success
→ `paid` + `TRX-` prefix) is asserted by
`products.tests.ZitroShopTestCase.test_checkout_and_payment_flow` and
`test_cart_add_and_htmx_flow`, and both pass.

### 5.2 Public order tracking

`/orders/tracking/` accepts GET or POST with `order_number` and an
**optional** `phone`; it filters `order_number__iexact` and, when a
phone is supplied, `recipient_phone__icontains`. No authentication and
no rate limit. Verified reachable with HTTP 200 for an anonymous client.

### 5.3 Support ticket conversation

Customer: `/tickets/` list (status filter) → `/tickets/new/` form →
`POST /tickets/new/save/` creates `Ticket` (`TK-XXXXXXXX`) + first
`TicketMessage` → `/tickets/<pk>/` chat view →
`POST /tickets/<pk>/reply/` (re-opens `ANSWERED`/`CLOSED` tickets as
`IN_PROGRESS`) → `POST /tickets/<pk>/close/`. `/tickets/<pk>/messages/`
returns [tickets/\_messages.html](templates/tickets/_messages.html) for
HTMX polling.

Staff: `/dashboard/tickets/` (status filter + search over
subject/number/username/phone/message body) → `/dashboard/tickets/<pk>/`
with `action=reply` (staff message, sets `customer_unread`, auto-assigns
`assigned_to` to the replying user, moves `NEW`/`IN_PROGRESS` →
`ANSWERED`) and `action=status` (sets any status, sets/clears
`closed_at`). `/dashboard/tickets/<pk>/messages/` is the staff polling
partial. The dashboard sidebar shows an unread-ticket badge via
[tickets/context_processors.py](tickets/context_processors.py).

**This whole module has no automated tests** (there is no
`tickets/tests.py`).

### 5.4 Staff management workflows

Each workflow is a list page → form page → POST → `redirect` with a
Django `messages` toast. Evidence:
[dashboard/urls.py](dashboard/urls.py) and the corresponding views in
[dashboard/views.py](dashboard/views.py). Verified by
`dashboard.tests.DashboardAccessTests.test_staff_can_open_every_dashboard_page`
(25 URLs return 200) and the CRUD test classes.

------------------------------------------------------------------------

## 6. Functional Requirements

Conventions used below:

-   **Status** ∈ {Implemented, Partially Implemented, UI Only / Backend
    Missing, Planned, Unverified}.
-   **Implemented** means the full described workflow exists in code
    *and* either an automated test exercises it or a read-only runtime
    check confirmed the page responds successfully. Interactive browser
    click-paths and payment-provider behaviour are called out explicitly
    where they were not exercised.
-   Requirement IDs are stable. `FR-*` = functional, `NFR-*` =
    non-functional, `SEC-*` = security/privacy.

### 6.1 Authentication, accounts and identity

**FR-001 --- Customer registration** - Status: Implemented - Module:
`accounts` - Description: `/accounts/register/` collects username,
optional phone, first/last name, password + confirmation; rejects
password mismatch, duplicate username and duplicate phone; creates the
user via `User.objects.create_user(...)` and logs them in immediately. -
Evidence: [accounts/views.py](accounts/views.py) `register_view`;
[accounts/urls.py](accounts/urls.py);
[templates/accounts/register.html](templates/accounts/register.html).
HTTP 200 verified for anonymous GET. - Acceptance criteria (verified
from code): mismatched passwords, duplicate username and duplicate phone
each produce an error message and re-render the form; a valid submission
logs in and redirects to `home:index`. - Note:
`settings.AUTH_PASSWORD_VALIDATORS` is configured but `create_user()`
does not run validators, so no password strength rule is enforced at
registration (see SEC-001).

**FR-002 --- Login by username or Iranian mobile number** - Status:
Implemented - Module: `accounts` - Description: `/accounts/login/`
accepts one `login_id` field; it first calls
`authenticate(username=login_id, ...)`, and on failure looks up
`User.phone_number == login_id` and authenticates with that user's
username. Authenticated users are redirected away from the page; `next`
is honoured. - Evidence: [accounts/views.py](accounts/views.py)
`login_view`. - Acceptance criteria: valid username+password logs in;
valid phone+password logs in; wrong credentials render the form with an
error message; `?next=` is respected.

**FR-003 --- Logout** - Status: Implemented --- Module: `accounts` ---
`/accounts/logout/` calls `logout()` and redirects home. Evidence:
[accounts/views.py](accounts/views.py).

**FR-004 --- Customer profile with order history** - Status:
Implemented - Module: `accounts` - Description: `/accounts/profile/`
(`login_required`) shows the user's orders with line items and a total,
plus a sidebar with links to tracking, dashboard (staff only) and
logout. Addresses are queried and passed in context. - Evidence:
[accounts/views.py](accounts/views.py) `profile_view`;
[templates/accounts/profile.html](templates/accounts/profile.html). -
Gap: the `addresses` context variable is **not rendered** by the
template; the address block exists only in the dashboard customer file.

**FR-005 --- Saved delivery address book (CRUD)** - Status: Partially
Implemented (model + read-only display only) - Module: `accounts` -
Description: `accounts.Address` models title, recipient name/phone,
province, city, postal address, postal code, default flag and
timestamp. - Evidence: [accounts/models.py](accounts/models.py#L34-L70);
[accounts/migrations/0001_initial.py](accounts/migrations/0001_initial.py).
The only read is `customer.addresses.all()` in
[dashboard/views.py](dashboard/views.py) `customer_detail_view`,
rendered by
[templates/dashboard/customer_detail.html](templates/dashboard/customer_detail.html). -
Gap: no create/update/delete view, no URL, no customer-facing form, and
checkout does **not** offer saved addresses (it re-types the address
every time). Acceptance criteria cannot be stated for a workflow that
does not exist.

**FR-006 --- Phone/identity verification and OTP** - Status: Planned
(not on the roadmap either --- identified gap) - Module: `accounts` -
Description: `User.is_verified` exists but no code path sets it (except
the demo seeder). There is no OTP generation, SMS provider or
verification screen. - Evidence:
[accounts/models.py](accounts/models.py#L19-L22);
[products/management/commands/seed_data.py](products/management/commands/seed_data.py#L317).

**FR-007 --- Password reset / change** - Status: Planned (not on the
roadmap --- identified gap) - Description: no `password_reset` URL,
template or email sending exists. `django.contrib.auth` URL includes are
not used; only four explicit account routes exist. - Evidence:
[accounts/urls.py](accounts/urls.py).

**FR-008 --- Password strength enforcement** - Status: Partially
Implemented --- validators are configured but not applied by the
registration flow. See SEC-001.

### 6.2 Catalog and storefront

**FR-010 --- Catalog browsing with filters, search and sorting** -
Status: Implemented - Module: `products` - Description: `/shop/` lists
active products with filters (category incl. children, `q` across
title/title_en/SKU/short description, multi-brand via `brand=<slug>`
repeated params, in-stock, special-offer, min/max price) and 5 sort
modes. HTMX requests return the grid partial only. - Evidence:
[products/views.py](products/views.py) `shop_view`;
[products/urls.py](products/urls.py);
[templates/products/shop.html](templates/products/shop.html);
[templates/products/partials/product_grid.html](templates/products/partials/product_grid.html).
Tested by
`products.tests.ZitroShopTestCase.test_shop_and_category_endpoints`
(passes). HTTP 200 verified for `/shop/`.

**FR-011 --- Category browsing including descendants** - Status:
Implemented - Description: `/shop/category/<slug>/` looks up an active
category and includes child-category products
(`cat_ids = [selected.id] + children ids`). Category slugs are
Persian-capable (`allow_unicode=True`,
`re_path(r'^shop/category/(?P<slug>[-\w]+)/$')`). - Evidence:
[products/views.py](products/views.py),
[products/urls.py](products/urls.py),
[products/models.py](products/models.py) `Category`. Tested
(`test_shop_and_category_endpoints`) and HTTP 200 verified for
`/shop/category/smartphones/`.

**FR-012 --- Product detail page** - Status: Implemented - Description:
gallery via `ProductImage` ordering/primary flag, price + strikethrough
compare price + auto-computed `discount_pct`, warranty, static rating,
dynamic specifications table, instalment teaser (`round(price/4)`),
add-to-cart HTMX form, related products, view counter increment. -
Evidence: [products/views.py](products/views.py) `product_detail_view`;
[products/models.py](products/models.py);
[templates/products/product_detail.html](templates/products/product_detail.html). -
Caveat: the route is `products/<pk>/<slug>/` but the view resolves by
`pk` only, so any slug returns the same product (no canonical-URL
enforcement).

**FR-013 --- Live search (HTMX, debounced)** - Status: Implemented -
Description: `/live-search/?q=` returns up to 6 active products matching
title/title_en/category name/brand name; queries shorter than 2
characters return an empty partial. The base template wires
`hx-trigger="keyup changed delay:300ms, search"`,
`hx-target="#search-results"` and a loading indicator; CSRF is injected
for HTMX by [static/js/htmx-config.js](static/js/htmx-config.js). -
Evidence: [products/views.py](products/views.py) `live_search_view`;
[templates/base.html](templates/base.html#L79-L97). Tested
(`test_live_search_endpoint`) and HTTP 200 verified.

**FR-014 --- Home page composition** - Status: Implemented -
Description: hero slider from `Banner(position='hero')` with touch/dot
navigation (inline JS), 8-category grid, `is_special_offer` rail,
`is_featured` rail, category rails keyed to hard-coded slugs
`smartphones` / `laptops` / `gaming`, brand strip, latest 3 published
posts, and `Banner` query for all active banners. - Evidence:
[home/views.py](home/views.py) `index_view`;
[templates/home/index.html](templates/home/index.html). HTTP 200
verified for `/`. - Caveat: the `smartphones` / `laptops` / `gaming`
rails are **hard-coded slug strings**; if those categories are renamed
the rails silently empty.

**FR-015 --- Product ratings** - Status: Partially Implemented (data
field only) - Description: `Product.rating` is a `DecimalField` with
default `4.5`, editable in the dashboard product form and displayed on
the storefront. There is no review model and no aggregation. - Evidence:
[products/models.py](products/models.py);
[dashboard/views.py](dashboard/views.py) `product_form_view`
(`product.rating = request.POST.get('rating') or 4.5`).

**FR-016 --- Product reviews / comments and moderation** - Status:
Planned - Description: no comment/review model exists. - Evidence:
[docs/ROADMAP_ADMIN_PANEL.md](docs/ROADMAP_ADMIN_PANEL.md) item 3.4
"کامنت/نظرات محصولات ... ⏳ فاز بعد".

**FR-017 --- Wishlist / favourites** - Status: Planned - Description: no
wishlist model, view or UI. A grep for `wishlist` / `favorite` /
`علاقه‌مندی` across templates and apps returned no matches. - Evidence:
roadmap item 3.5 ("لیست علاقه‌مندی و سبدهای رهاشده ... ⏳ فاز بعد").

**FR-018 --- Blog (articles and categories)** - Status: Implemented -
Description: `/blog/` lists published posts with categories;
`/blog/category/<slug>/` filters; `/blog/<slug>/` renders an article,
increments `views_count` and lists 4 recent posts. - Evidence:
[blog/views.py](blog/views.py), [blog/urls.py](blog/urls.py),
[blog/models.py](blog/models.py). HTTP 200 verified for `/blog/` and for
a real published slug.

**FR-019 --- Static informational pages (FAQ)** - Status: Implemented -
Description: `/faq/` renders a static template; no database content. -
Evidence: [home/views.py](home/views.py) `faq_view`;
[templates/home/faq.html](templates/home/faq.html). HTTP 200 verified.

**FR-020 --- Contact page with working message submission** - Status: UI
Only / Backend Missing - Description: `/contact/` renders contact
details and a "fast message" form whose submit handler is
`onsubmit="event.preventDefault(); alert(...)"`. No POST view, model or
email dispatch exists. - Evidence: [home/views.py](home/views.py)
`contact_view`;
[templates/home/contact.html](templates/home/contact.html#L52-L75). HTTP
200 verified, but the form cannot persist or send anything.

**FR-021 --- Instalment ("خرید اقساطی" / SnappPay) purchase flow** -
Status: UI Only / Backend Missing - Description: `/installment/` is a
3-step marketing/explainer page stating the customer can select an
"درگاه اعتباری اسنپ‌پی" at checkout and pay in 4 monthly instalments; the
product page shows `round(price/4)`. **Checkout offers only two
methods** --- `mock_gateway` and `cod` --- so the described instalment
option cannot be selected, and no credit provider integration exists. -
Evidence:
[templates/home/installment.html](templates/home/installment.html),
[templates/products/product_detail.html](templates/products/product_detail.html#L104-L107),
[orders/models.py](orders/models.py) `PAYMENT_METHOD_CHOICES`,
[templates/orders/checkout.html](templates/orders/checkout.html#L176-L185).

### 6.3 Cart

**FR-030 --- Cart add / update / remove with HTMX** - Status:
Implemented - Description: POST-only endpoints; guest carts keyed by
session key (created on demand), authenticated carts keyed by user;
`unique_together = ('cart','product')` prevents duplicate lines;
increase/decrease/remove return the cart-table partial; add returns the
badge partial; non-HTMX requests redirect. - Evidence:
[cart/views.py](cart/views.py), [cart/models.py](cart/models.py),
[cart/urls.py](cart/urls.py),
[templates/cart/cart_detail.html](templates/cart/cart_detail.html),
[templates/cart/partials/](templates/cart/partials/). Global cart
count/total reach every template through
[cart/context_processors.py](cart/context_processors.py). HTMX add is
asserted by `products.tests.test_cart_add_and_htmx_flow` (passes).

**FR-031 --- Cart totals and customer saving calculation** - Status:
Implemented - Description: `Cart.total_items`, `total_price`,
`total_compare_price`, `total_discount` (compare-price minus sale-price,
floored at 0) and Persian thousands-formatted variants on `Cart` and
`CartItem`. - Evidence: [cart/models.py](cart/models.py). - Note: the
same figure is stored on the order as `Order.discount_amount` labelled
"سود و تخفیف مشتری" and surfaced in reports as part of "تخفیف اعطاشده
(کد + سود)". It is a *customer saving*, not merchant margin --- see
[§8](#8-business-rules-and-constraints).

**FR-032 --- Stock-aware cart constraints** - Status: Partially
Implemented - Description: `cart_add_view` accepts any positive
`quantity` and does not compare it against `Product.stock_qty`; there is
no maximum per line and no validation of an `int()` cast (a non-numeric
`quantity` would raise). `Product.is_available` is recomputed as
`stock_qty > 0` on every `Product.save()`. - Evidence:
[cart/views.py](cart/views.py) `cart_add_view`;
[products/models.py](products/models.py) `Product.save`.

**FR-033 --- Guest-cart merge on login/registration** - Status: Planned
(identified gap; not on the roadmap) - Description: the login and
register views do not migrate a `session_key` cart to the newly
authenticated user, and `_get_or_create_cart` switches lookup keys
immediately on authentication. A guest cart therefore becomes
inaccessible after login. - Evidence:
[accounts/views.py](accounts/views.py), [cart/views.py](cart/views.py)
`_get_or_create_cart`,
[cart/context_processors.py](cart/context_processors.py).

### 6.4 Checkout, orders and payment

**FR-040 --- Checkout shipping-data form** - Status: Implemented -
Description: recipient name/phone, province, city, postal address,
postal code, order notes, shipping method and payment method. Server
validates that `recipient_name`, `recipient_phone`, `city` and
`shipping_address` are non-empty; invalid submissions re-render with an
error and recomputed totals. - Evidence:
[orders/views.py](orders/views.py) `checkout_view`;
[templates/orders/checkout.html](templates/orders/checkout.html).

**FR-041 --- Shipping method selection and cost rules** - Status:
Implemented - Description: four methods (`post`, `tipax`, `courier`,
`pickup`) are persisted on the order; the invalid value falls back to
`post`. Cost comes from `SiteSetting.shipping_cost`, waived when the
cart total reaches `SiteSetting.free_shipping_threshold` (\>0) or when
the cart is empty. - Evidence: [orders/models.py](orders/models.py)
`SHIPPING_CHOICES`; [orders/views.py](orders/views.py)
`_payment_summary`; [home/models.py](home/models.py) `SiteSetting`.
Asserted by `dashboard.tests.test_coupon_and_shipping_applied_to_order`
and `test_free_shipping_threshold` (pass). - Gap: all four methods cost
the same; there is no per-method or per-region pricing (roadmap item
4.7, Phase 4).

**FR-042 --- Coupon apply / remove at checkout** - Status: Implemented -
Description: code is stored in the session;
`Coupon.validate_for(amount)` enforces active flag,
`valid_from`/`valid_until`, `max_uses` vs `used_count`, and
`min_order_amount`, then computes percent (capped by
`max_discount_amount`) or fixed discount clipped to the order amount.
Empty submission removes the code. Codes are upper-cased/trimmed on
save. - Evidence: [orders/models.py](orders/models.py) `Coupon`;
[orders/views.py](orders/views.py) `apply_coupon_view`,
`_payment_summary`;
[templates/orders/checkout.html](templates/orders/checkout.html#L144-L162).
Asserted by
`dashboard.tests.test_invalid_coupon_is_rejected_when_applying` and
`test_expired_and_limited_coupons` (pass).

**FR-043 --- Order creation with immutable item snapshot and generated
number** - Status: Implemented - Description: `Order.save()` generates
`ZT-` + 6 uppercase hex characters when `order_number` is empty; each
`OrderItem` copies `product_title`, `product_sku`, `unit_price`,
`quantity` and `total_price` so later catalog edits do not alter
history. `OrderItem.product` uses `SET_NULL` so deleting a product keeps
the historical line. - Evidence: [orders/models.py](orders/models.py).
Asserted by `products.tests.test_checkout_and_payment_flow` (pass).

**FR-044 --- Simulated online payment gateway** - Status: Implemented
(as a simulation) - Description: `/orders/payment/<order_number>/`
renders a Shaparak-styled test page with success/cancel actions. Success
⇒ `payment_status='successful'`, `status='paid'`,
`transaction_id='TRX-'+10 hex`, cart emptied, coupon `used_count`
incremented, session coupon cleared, redirect to the invoice. Failure ⇒
`payment_status='failed'`, redirect to cart. - Evidence:
[orders/views.py](orders/views.py) `mock_payment_view`;
[templates/orders/mock_payment.html](templates/orders/mock_payment.html).
Asserted by `products.tests.test_checkout_and_payment_flow` (pass). -
Explicit limitation: this is **not** a real PSP integration (no merchant
ID, no signed callback, no verification of a real transaction).

**FR-045 --- Cash on delivery** - Status: Implemented - Description:
choosing `cod` empties the cart, sets `status='paid'`, increments coupon
usage when applicable, and redirects to the invoice. `payment_status`
stays `pending` and `transaction_id` is empty --- i.e. a COD order is
"paid" for status purposes but "pending" for payment purposes, an
inconsistency worth deciding on (see
[§18](#18-assumptions-and-unresolved-questions)). - Evidence:
[orders/views.py](orders/views.py) `checkout_view`.

**FR-046 --- Order invoice / success page** - Status: Implemented -
Description: `/orders/success/<order_number>/` renders order, items and
totals. - Evidence: [orders/views.py](orders/views.py)
`order_success_view`;
[templates/orders/order_success.html](templates/orders/order_success.html). -
Security caveat: unauthenticated and unowned --- anyone who knows an
order number can read the invoice (SEC-003).

**FR-047 --- Public order tracking** - Status: Implemented -
Description: `/orders/tracking/` (GET or POST) looks up by exact order
number and optional partial phone match, showing the workflow state. -
Evidence: [orders/views.py](orders/views.py) `order_tracking_view`;
[templates/orders/order_tracking.html](templates/orders/order_tracking.html).
HTTP 200 verified anonymously.

**FR-048 --- Stock deduction on purchase** - Status: Planned (identified
gap; not on the roadmap) - Description: no code decrements
`Product.stock_qty` or re-checks availability during checkout or
payment. `grep -rn "stock_qty" orders/ cart/` returns no non-migration
match, so paid orders leave inventory untouched; `Product.save()` only
recomputes the boolean `is_available`. - Evidence:
[orders/views.py](orders/views.py), [cart/views.py](cart/views.py),
[products/models.py](products/models.py).

**FR-049 --- Order status lifecycle** - Status: Implemented -
Description: `pending → paid → shipped → delivered`, plus `cancelled`;
`pending/successful/failed` payment states; transitions are performed
manually by staff (dashboard) and automatically by the two payment
branches. Cancelling an order with `payment_status='successful'` also
flips payment to `failed`. - Evidence:
[orders/models.py](orders/models.py);
[dashboard/views.py](dashboard/views.py) `order_update_view`,
`order_status_view`.

**FR-050 --- Transactional notifications (email/SMS)** - Status: Planned
(identified gap; roadmap item 4.8 covers marketing campaigns, not
transactional mail) - Description: no email backend beyond Django's
default console/SMTP setting (not configured), no SMS provider, no
`send_mail` call anywhere. - Evidence:
[config/settings.py](config/settings.py) (no `EMAIL_*` keys),
README/roadmap.

### 6.5 Staff dashboard

**FR-060 --- Staff-only dashboard access** - Status: Implemented -
Description: every view in [dashboard/views.py](dashboard/views.py) is
decorated with `staff_member_required(login_url='accounts:login')`
(aliased `staff`). Anonymous and non-staff users are redirected to
login. - Evidence: [dashboard/views.py](dashboard/views.py#L26-L27).
Asserted by
`dashboard.tests.DashboardAccessTests.test_anonymous_and_normal_user_are_blocked`
(pass); anonymous `GET /dashboard/` returned 302 at runtime and 200
after `force_login` of a staff user.

**FR-061 --- KPI overview, alerts and shortcuts** - Status:
Implemented - Description: total/today/7-day sales over successfully
paid orders; order counters by status; product counters
(total/active/inactive); customer count (`is_staff=False`); low-stock
and out-of-stock counters plus a low-stock list; active
coupon/category/attribute/banner/post counters; 7 recent orders; top 5
products by revenue. - Evidence:
[dashboard/views.py](dashboard/views.py) `overview_view`;
[templates/dashboard/overview.html](templates/dashboard/overview.html).
HTTP 200 verified for `/dashboard/`. - Caveat: the "هشدارهای عملیاتی"
panel covers **low stock / out-of-stock only**. Roadmap item 3.3
additionally claims expiring-coupon and unpaid-order alerts; no
coupon-expiry alert exists in the template, and the expiring-coupon part
of 3.3 is **not implemented** (see
[§15](#15-current-limitations-and-known-gaps)).

**FR-062 --- Reports and analytics page** - Status: Implemented -
Description: date range from `?from=`/`?to=` (default last 30 days, swap
if inverted) with an equal-length previous period for %-change
comparison. Eight Chart.js datasets: daily revenue/orders trend, weekday
totals (Saturday-first mapping), order-status split, payment-status
split, top-8 products, top-8 categories, stock-health distribution
(healthy/low/out), inventory value by category. Additional tables:
top-10 products with revenue share and current stock, dead stock (active
products with no paid sales in range), low-stock list, top-8 by
inventory value, top-8 customers, repeat-buyer count, coupon
performance, status/payment/shipping breakdowns. KPI list: revenue, paid
orders, AOV, items sold, unique buyers, new customers, total discount
granted, unpaid orders (with inverted tone). - Evidence:
[dashboard/views.py](dashboard/views.py) `reports_view`,
`_period_metrics`, `_inventory_snapshot`, `_sales_charts`;
[templates/dashboard/reports.html](templates/dashboard/reports.html);
[static/js/dashboard-charts.js](static/js/dashboard-charts.js). Asserted
by `dashboard.tests.test_reports_and_settings`,
`test_reports_filters_and_previous_period_comparison` (pass). HTTP 200
verified for `/dashboard/reports/`. - Caveat: the dead-stock query
selects active products never sold **in the range** from `OrderItem`,
and `_period_metrics` counts `unpaid` as
`orders.exclude(payment_status='successful')` (so failed *and* pending
are lumped together).

**FR-063 --- CSV exports (Excel/Persian friendly)** - Status:
Implemented - Description: three endpoints --- orders/sales
(`reports/export/`), per-product sales (`reports/export/products/`),
inventory (`reports/export/inventory/`) --- plus the order-list export
`orders/export/`. All write `utf-8-sig` with a BOM and Persian headers,
filenames including the date range. - Evidence:
[dashboard/views.py](dashboard/views.py) `csv_response`,
`reports_export_view`, `reports_products_export_view`,
`reports_inventory_export_view`, `orders_export_view`. Asserted by
`dashboard.tests.test_order_detail_update_status_and_export` and
`test_inventory_and_product_exports` (pass).

**FR-064 --- Product create/update with images and specifications** -
Status: Implemented - Description: form validates title + unique SKU +
category; slug auto-generated with uniqueness; `compare_at_price` drives
`discount_pct`; multi-file upload with a designated primary image;
specification rows rebuilt from parallel
`spec_name`/`spec_value`/`spec_unit` lists; availability recomputed from
stock. - Evidence: [dashboard/views.py](dashboard/views.py)
`product_form_view`, `save_uploaded_images`, `save_specifications`;
[templates/dashboard/product_form.html](templates/dashboard/product_form.html).
Asserted by
`dashboard.tests.test_create_product_with_images_and_specifications`,
`test_duplicate_sku_is_rejected`, `test_edit_and_toggle_product`,
`test_image_primary_and_delete` (pass). - Gap: no product
**duplicate/copy** action (roadmap item 1.1 claims "کپی سریع" as done;
no such code path exists).

**FR-065 --- Product list: filters, sorting, pagination, bulk
actions** - Status: Implemented - Description: search across
title/title_en/SKU; filters
category/brand/status(active,inactive,featured,special)/stock(out,low,in);
6 sort modes; 20-row pagination preserving filters; bulk
activate/deactivate/feature/feature/special/un-special/delete; per-row
toggles for active/featured/special. - Evidence:
[dashboard/views.py](dashboard/views.py) `product_list_view`,
`product_bulk_view`, `product_toggle_view`. Asserted by
`dashboard.tests.test_filters_and_bulk_actions`, `test_delete_product`
(pass).

**FR-066 --- Inventory management** - Status: Implemented - Description:
bulk-updates stock quantity and low-stock threshold per product with
`to_int` (Persian-numeral tolerant) parsing, ignoring unchanged rows;
filters by search/category/stock state; aggregates item count, unit
count and Toman value; renders at most the first 200 rows. - Evidence:
[dashboard/views.py](dashboard/views.py) `inventory_view`;
[templates/dashboard/inventory.html](templates/dashboard/inventory.html).
Asserted by `dashboard.tests.test_inventory_bulk_update` (pass).

**FR-067 --- Category tree management** - Status: Implemented -
Description: tree-ordered listing with depth indentation, search,
product-less count; form with optional parent (a category cannot be its
own parent; descendants are excluded from the parent choice list), SVG
icon, image, order, active flag; delete is blocked while the category
has products or children; toggle active. - Evidence:
[dashboard/views.py](dashboard/views.py) `category_tree`,
`category_options`, `category_*` views. Asserted by
`dashboard.tests.test_category_crud_and_parent_tree`,
`test_category_cannot_be_its_own_parent` (pass).

**FR-068 --- Brand management** - Status: Implemented - Description:
listing with per-brand product count and search; form (Persian/English
name, generated unique slug, order, active flag, logo); delete relies on
`Product.brand` `SET_NULL`. - Evidence:
[dashboard/views.py](dashboard/views.py) `brand_*`;
[products/models.py](products/models.py). Asserted by
`dashboard.tests.test_brand_crud` (pass).

**FR-069 --- Category attribute management** - Status: Implemented -
Description: attributes have name, optional category scope, unit, type
(text/number/select/boolean), newline-separated options, order and
active flag; quick-add from the list page plus a full edit form and
delete. - Evidence: [dashboard/views.py](dashboard/views.py)
`attribute_*`; [products/models.py](products/models.py)
`CategoryAttribute.options_list`. Asserted by
`dashboard.tests.test_attribute_crud_and_quick_add` (pass).

**FR-070 --- Banner/slider management with ordering** - Status:
Implemented - Description: four positions (`hero`, `banner_pair`,
`banner_wide`, `sidebar`); create/edit with required image on create,
link, button text, subtitle, position, order, active flag; up/down
reordering that swaps `order` values within a position; per-banner
toggle; delete. - Evidence: [dashboard/views.py](dashboard/views.py)
`banner_*`, `banner_move_view`; [home/models.py](home/models.py)
`Banner`. Asserted by `dashboard.tests.test_banner_crud_and_ordering`
and `test_edit_forms_render_with_existing_records` (pass).

**FR-071 --- Order management** - Status: Implemented - Description:
list with search (order number/phone/recipient/tracking code),
status/payment/method filters, optional date range, 25-row pagination
and per-status counters; detail page shows customer, address, items and
amounts; update/status endpoints set status, payment status, shipping
method, tracking code and internal `admin_note`; CSV export of the
filtered set. - Evidence: [dashboard/views.py](dashboard/views.py)
`_filtered_orders`, `order_list_view`, `order_detail_view`,
`order_update_view`, `order_status_view`, `orders_export_view`;
[templates/dashboard/order_detail.html](templates/dashboard/order_detail.html).
Asserted by `dashboard.tests.test_order_detail_update_status_and_export`
(pass).

**FR-072 --- Customer list with segmentation and customer file** -
Status: Implemented - Description: annotates orders count, paid orders,
total spent and last order; segments into
`vip / loyal / active / new / dormant / lead` (plus `staff`) with a vip
threshold derived from the top 10 % of spending floored at 50,000,000
Toman; search, role filter, 5 sort modes, in-Python pagination of 20;
KPI strip (all/customers/staff/buyers/no-order, average LTV, repeat
rate, last-30-day signups). Customer file shows profile card, order
totals, monthly purchase-trend chart (12 months via `TruncMonth`),
favourite products/category, addresses, cancelled and pending counts. -
Evidence: [dashboard/views.py](dashboard/views.py) `CUSTOMER_SEGMENTS`,
`_customer_segment`, `customer_list_view`, `customer_detail_view`;
[templates/dashboard/customers.html](templates/dashboard/customers.html),
[templates/dashboard/customer_detail.html](templates/dashboard/customer_detail.html).
Asserted by `dashboard.tests.test_customer_report_and_staff_toggle`,
`test_customer_segments_and_sorting`,
`test_customer_detail_page_and_chart`,
`test_non_staff_cannot_open_customer_pages` (pass).

**FR-073 --- Grant/revoke staff access from the dashboard** - Status:
Implemented - Module: `dashboard` - Description: POST to
`/dashboard/customers/<pk>/toggle-staff/` flips `User.is_staff`; a user
cannot toggle their own flag. - Evidence:
[dashboard/views.py](dashboard/views.py) `customer_toggle_staff_view`.
Asserted by `dashboard.tests.test_customer_report_and_staff_toggle`
(pass). - Risk: any staff member can promote any other user to staff
(privilege escalation), because there is no superuser check --- see
SEC-004.

**FR-074 --- Coupon management** - Status: Implemented - Description:
list with usage counts and aggregate used count; create/edit (code
uniqueness enforced, type percent/amount, value, min order, max
discount, max uses, active, `valid_from`/`valid_until` parsed from
`datetime-local` or date input), toggle, delete. - Evidence:
[dashboard/views.py](dashboard/views.py) `coupon_*`, `_parse_datetime`;
[orders/models.py](orders/models.py) `Coupon`. Asserted by
`dashboard.tests.test_coupon_crud` (pass).

**FR-075 --- Blog content management** - Status: Implemented -
Description: post list with search and published/draft filter plus
counts; post create/edit (title, slug, category, excerpt, content, cover
image, published flag, author = current user on create); toggle publish;
delete; blog-category create/edit and delete via POST endpoints. -
Evidence: [dashboard/views.py](dashboard/views.py) `post_*`,
`blog_category_*`. Asserted by
`dashboard.tests.test_post_crud_and_blog_categories` (pass).

**FR-076 --- Store settings management** - Status: Implemented -
Description: single `SiteSetting` row (`get_settings()` uses
`get_or_create(id=1)`) holding store name, slogan, phone, email,
address, working hours, telegram/instagram/whatsapp, default shipping
cost, free-shipping threshold, about text and footer note; editable at
`/dashboard/settings/`. - Evidence:
[dashboard/views.py](dashboard/views.py) `settings_view`;
[home/models.py](home/models.py) `SiteSetting`;
[templates/dashboard/settings.html](templates/dashboard/settings.html).
Asserted by `dashboard.tests.test_reports_and_settings` (pass). Consumed
site-wide via [home/context_processors.py](home/context_processors.py).

**FR-077 --- Support ticket management (staff side)** - Status:
Implemented (untested) - Description: see
[§5.3](#53-support-ticket-conversation). - Evidence:
[dashboard/views.py](dashboard/views.py) `ticket_list_view`,
`ticket_detail_view`, `ticket_messages_partial_view`;
[templates/dashboard/tickets.html](templates/dashboard/tickets.html),
[templates/dashboard/ticket_detail.html](templates/dashboard/ticket_detail.html).
**No automated test covers these views.**

**FR-078 --- Role-based access control and dashboard operator
management** - Status: Planned --- roadmap items 4.1, 4.2 (Phase 4, "⏳
فاز بعد").

**FR-079 --- Audit log of staff actions** - Status: Planned --- roadmap
item 3.6.

**FR-080 --- Backup and restore** - Status: Planned --- roadmap item
4.3.

**FR-081 --- Financial reporting and PSP settlement reconciliation** -
Status: Planned --- roadmap item 4.4.

**FR-082 --- Two-factor login and IP allowlist for the dashboard** -
Status: Planned --- roadmap item 4.5.

**FR-083 --- Managing static content pages (about, terms)** - Status:
Planned --- roadmap item 4.6.

**FR-084 --- Multi-region/multi-method shipping management** - Status:
Planned --- roadmap item 4.7.

**FR-085 --- Email/SMS marketing campaigns** - Status: Planned ---
roadmap item 4.8.

### 6.6 Customer support tickets

**FR-090 --- Customer ticket lifecycle** - Status: Implemented
(untested) - Description: login-required list/create/detail/reply/close;
`TK-XXXXXXXX` numbering; category (order/product/technical/guide/other),
priority (low/normal/high), optional order number, status
(`new/in_progress/answered/closed`), unread flags for each side,
`last_message_at` ordering, `closed_at`, and `TicketMessage` rows with a
display-name snapshot. - Evidence:
[tickets/models.py](tickets/models.py),
[tickets/views.py](tickets/views.py),
[tickets/urls.py](tickets/urls.py),
[templates/tickets/](templates/tickets/). No test file exists for this
app.

**FR-091 --- Ticket auto-refresh via HTMX polling** - Status:
Implemented (untested) - Description: `/tickets/<pk>/messages/` and
`/dashboard/tickets/<pk>/messages/` return message partials and reset
the respective unread flag. - Evidence:
[tickets/views.py](tickets/views.py),
[dashboard/views.py](dashboard/views.py),
[templates/tickets/\_messages.html](templates/tickets/_messages.html),
[templates/dashboard/ticket_messages.html](templates/dashboard/ticket_messages.html).

### 6.7 Data seeding and demo content

**FR-100 --- Seed command** - Status: Implemented - Description:
`python manage.py seed_data` creates the `admin/admin123` superuser
(only if absent), populates `SiteSetting`, brands, top-level categories
with inline SVG icons, products (with specifications) and demo customer
users; it is idempotent via `get_or_create`. - Evidence:
[products/management/commands/seed_data.py](products/management/commands/seed_data.py);
README §«اطلاعات ورود پیش‌فرض». The current `db.sqlite3` confirms the
effect: 13 products, 9 categories, 10 brands, 11 orders, 1 coupon, 1
ticket. **`seed_data` was not re-run during this audit.**

**FR-101 --- Local image population command** - Status: Implemented -
Description: `python manage.py populate_images` copies bundled images
from `utils/images/` (and a placeholder flow) into products, categories,
banners and posts using a hard-coded product-slug → filename map. -
Evidence:
[products/management/commands/populate_images.py](products/management/commands/populate_images.py),
[utils/images/](utils/images). Not executed during this audit.

------------------------------------------------------------------------

## 7. Feature Implementation Status

### 7.1 Summary table

  ------------------------------------------------------------------------------
  Area              Implemented          Partially /       Planned
                                         UI-only           
  ----------------- -------------------- ----------------- ---------------------
  Authentication &  login, logout,       address book      phone
  accounts          register, profile    (model only),     verification/OTP,
                                         password policy   password reset

  Catalog &         shop filters/sort,   ratings (data     reviews/moderation,
  storefront        categories, product  only), contact    wishlist
                    detail, live search, form (no          
                    home composition,    backend),         
                    blog, FAQ            instalment flow   
                                         (copy only)       

  Cart              add/update/remove    stock-aware       ---
                    (HTMX), totals       limits,           
                                         guest→user merge  

  Checkout & orders checkout form,       ---               stock deduction,
                    shipping, coupons,                     transactional
                    order + snapshot,                      email/SMS
                    mock gateway, COD,                     
                    invoice, tracking,                     
                    status lifecycle                       

  Staff dashboard   18 modules (see      ---               roles/RBAC, audit
                    FR-060...FR-077)                       log, backups,
                                                           settlement, 2FA/IP,
                                                           static pages,
                                                           shipping config,
                                                           campaigns

  Support tickets   full customer +      ---               ---
                    staff chat workflow                    

  Tooling           `seed_data`,         test coverage     CI, lint/format
                    `populate_images`,   uneven            pipeline
                    35 passing tests                       
  ------------------------------------------------------------------------------

### 7.2 Verified automated test results (executed in this audit)

    $ venv/Scripts/python.exe manage.py check
    System check identified no issues (0 silenced).

    $ venv/Scripts/python.exe manage.py makemigrations --check --dry-run
    No changes detected

    $ venv/Scripts/python.exe manage.py test
    Ran 35 tests in 33.024s
    OK

Test distribution: `dashboard/tests.py` --- 30 tests (access, CRUD,
exports, segmentation, storefront integration); `products/tests.py` ---
5 tests (model calculations, shop/category, live search, cart HTMX,
checkout+payment). Stub files with no tests: `accounts/tests.py`,
`cart/tests.py`, `blog/tests.py`, `home/tests.py`, `orders/tests.py`.
**`tickets` has no test module at all.**

### 7.3 Read-only runtime checks performed

Run against the existing `db.sqlite3` through `django.test.Client` (no
data mutation; product-detail and post-detail were deliberately not
fetched because they write a view counter):

-   Storefront/content routes returned 200: `/`, `/shop/`,
    `/shop/category/smartphones/`, `/blog/`, a real published
    `/blog/<slug>/`, `/faq/`, `/contact/`, `/installment/`,
    `/orders/tracking/`, `/accounts/login/`, `/accounts/register/`,
    `/live-search/?q=سامسونگ`.
-   `/dashboard/` returned 302 anonymously and 200 after `force_login`
    of the seeded staff user; `/dashboard/reports/` returned 200.
-   `admin.site` registered model list:
    `['Group', 'Ticket', 'TicketMessage']`.
-   Row counts in the current dev database: 13 products, 9 categories,
    10 brands, 11 orders, 1 coupon, 1 ticket.

**Not performed:** a real browser session, HTMX interaction in a
browser, concurrency/load testing, real PSP/SMS/email integration, and
any write-path manual test (all write behaviour claims above rest on
source code plus the automated tests).

------------------------------------------------------------------------

## 8. Business Rules and Constraints

Rules extracted from code (each verified in the referenced file):

1.  **Money** --- all amounts are Toman integers (`BigIntegerField`);
    prices are never decimals. Display formatting uses `f"{value:,}"`
    properties and `intcomma`.
2.  **Discount** ---
    `discount_pct = round((compare_at_price - price) / compare_at_price * 100)`
    and is reset to `0` when `compare_at_price` is missing or not
    greater than `price` ([products/models.py](products/models.py)
    `Product.save`).
3.  **Availability** --- `is_available = stock_qty > 0`, recomputed on
    every product save; it is **not** recomputed when stock changes
    through bulk `QuerySet.update()` (e.g. bulk actions do not touch
    stock, but `reports`/`inventory` saves go through `save()` and are
    fine).
4.  **Customer saving** --- cart/order `discount_amount` = sum of
    (compare price − sale price) × quantity, i.e. the customer's saving,
    described in the model as "سود و تخفیف مشتری".
5.  **Coupon** --- code is stored upper-cased; validation order is
    active → `valid_from` → `valid_until` → usage limit → minimum
    amount; percent discount is capped by `max_discount_amount` and the
    result is clipped to the order total; `used_count` increments only
    when a payment succeeds (mock gateway) or a COD order is placed.
6.  **Shipping** --- cost is a single global value; free above
    `free_shipping_threshold` (\>0) or when the cart total is 0.
7.  **Order number** --- `ZT-` + 6 hex characters; ticket number ---
    `TK-` + 8 hex characters; transaction id --- `TRX-` + 10 hex
    characters. All are generated server-side and non-editable.
8.  **Order immutability** --- historical line data (`product_title`,
    `product_sku`, `unit_price`, `total_price`) is snapshotted at order
    creation.
9.  **Status coupling** --- cancelling a *paid* order also sets
    `payment_status='failed'`; COD sets `status='paid'` while leaving
    `payment_status='pending'` (documented inconsistency, see §18).
10. **Cart identity** --- one cart per authenticated user; one cart per
    session key for guests; one line per product per cart.
11. **Dashboard authorization** --- a single gate: `is_staff`. No
    per-module or per-action permissions.
12. **Staff self-protection** --- a staff user cannot toggle their own
    `is_staff` flag.
13. **Category integrity** --- a category cannot be its own parent,
    cannot be deleted while it has products or children, and a product
    requires a category (`on_delete=PROTECT`).
14. **Attribute semantics** --- attributes are *definitions* for a
    category and are surfaced as suggestions in the product form; they
    are **not** persisted per product (specifications are stored
    separately as free-form `ProductSpecification` name/value rows).
15. **Persian input tolerance** --- dashboard numeric inputs accept
    Persian/Arabic-Indic digits, thousands separators and whitespace via
    `to_int`.
16. **Blog visibility** --- only `is_published=True` posts appear on the
    storefront; a draft slug returns 404 at the storefront URL.
17. **Ticket rules** --- closed tickets cannot receive customer messages
    (the customer view blocks it; the staff view re-opens on reply); a
    customer reply sets `staff_unread=True` and re-opens answered/closed
    tickets as `in_progress`.
18. **CSV encoding** --- exports are UTF-8 with BOM for Persian Excel
    compatibility.

------------------------------------------------------------------------

## 9. Data and Core Entities

All models are listed with their application, key fields and
relationships. No `forms.py` exists anywhere, so validation is
view-level.

### 9.1 `accounts`

-   **`User`** (extends `AbstractUser`;
    `AUTH_USER_MODEL = 'accounts.User'`) --- `phone_number` (unique,
    nullable), `avatar` (ImageField → `avatars/`), `is_verified` (bool,
    default False, never set by app code). `__str__` prefers full name →
    username → phone.
-   **`Address`** --- FK `user` (`CASCADE`, related_name `addresses`);
    title, recipient name/phone, province, city, postal address, postal
    code, `is_default`, `created_at`. **No CRUD path in the app.**

### 9.2 `products`

-   **`Category`** --- `name`, `name_en`, `slug` (unique, unicode),
    self-FK `parent` (`CASCADE`, `children`), `icon_svg` (raw SVG stored
    as text and injected with `|safe`), `image`, `order`, `is_active`.
    `get_absolute_url()` → `products:category_detail`.
-   **`Brand`** --- `name`, `name_en`, `slug` (unique, unicode), `logo`,
    `is_active`, `order`.
-   **`CategoryAttribute`** --- `name`, FK `category` (nullable =
    general), `unit`, `type` ∈ {text, number, select, boolean},
    `options` (newline-separated), `order`, `is_active`; helper
    `options_list`.
-   **`Product`** --- `title`, `title_en`, `slug` (unique unicode),
    `sku` (unique), FK `category` (`PROTECT`), FK `brand` (`SET_NULL`),
    short/full description, `price`, `compare_at_price`, `discount_pct`,
    `stock_qty`, `low_stock_threshold`, `is_available`, `is_active`,
    `is_featured`, `is_special_offer`, `warranty`, `rating`,
    `views_count`, timestamps. Properties: `primary_image`,
    `is_low_stock`, `formatted_price`, `formatted_compare_price`;
    `save()` computes slug fallback, discount and availability.
-   **`ProductImage`** --- FK `product` (`CASCADE`, `images`), `image` →
    `products/%Y/%m/`, `alt_text`, `is_primary`, `order`.
-   **`ProductSpecification`** --- FK `product` (`CASCADE`,
    `specifications`), `name`, `value`, `order`.

Slug caveat (observed at runtime): `slugify()` does not transliterate
Persian, so a Persian-only title falls back to `product-<pk>` --- the
live database contains a product whose slug is literally `product-13`.

### 9.3 `cart`

-   **`Cart`** --- `session_key` (unique, nullable), FK `user`
    (nullable, `carts`), timestamps; properties `total_items`,
    `total_price`, `total_compare_price`, `total_discount`, formatted
    variants.
-   **`CartItem`** --- FK `cart` (`CASCADE`, `items`), FK `product`
    (`CASCADE`, `cart_items`), `quantity`, `created_at`;
    `unique_together = ('cart','product')`; properties `line_total`,
    `line_compare_total`, `formatted_line_total`.

### 9.4 `orders`

-   **`Coupon`** --- `code` (unique, upper-cased on save), `title`,
    `discount_type` ∈ {percent, amount}, `value`, `min_order_amount`,
    `max_discount_amount`, `max_uses`, `used_count`, `valid_from`,
    `valid_until`, `is_active`, `created_at`; properties `is_expired`,
    `usage_left`; method
    `validate_for(amount) -> (ok, message, discount)`.
-   **`Order`** --- `order_number` (unique, generated), FK `user`
    (`SET_NULL`, `orders`), recipient name/phone, province, city,
    `shipping_address`, `postal_code`, `products_total`,
    `discount_amount`, `shipping_cost` (default 49 000), `final_amount`,
    `status` ∈ {pending, paid, shipped, delivered, cancelled},
    `payment_method` ∈ {mock_gateway, cod}, `payment_status` ∈ {pending,
    successful, failed}, `transaction_id`, FK `coupon` (`SET_NULL`),
    `coupon_code`, `coupon_discount`, `shipping_method` ∈ {post, tipax,
    courier, pickup}, `tracking_code`, `notes` (customer), `admin_note`
    (internal), timestamps.
-   **`OrderItem`** --- FK `order` (`CASCADE`, `items`), FK `product`
    (`SET_NULL`), `product_title`, `product_sku`, `unit_price`,
    `quantity`, `total_price`.

### 9.5 `blog`

-   **`BlogCategory`** --- `name`, `slug` (unique unicode), `order`.
-   **`Post`** --- `title`, `slug` (unique unicode), FK `category`
    (`SET_NULL`), FK `author` (`SET_NULL`, `blog_posts`), `cover_image`
    → `blog/%Y/%m/`, `excerpt`, `content`, `is_published`,
    `views_count`, timestamps; `get_absolute_url()`.

### 9.6 `home`

-   **`Banner`** --- `title`, `subtitle`, `image` → `banners/`,
    `link_url` (default `/`), `button_text`, `position` ∈ {hero,
    banner_pair, banner_wide, sidebar}, `order`, `is_active`.
-   **`SiteSetting`** --- singleton-style row read via `get_settings()`
    (`get_or_create(id=1)`): store name, slogan, phone, email, address,
    working hours, telegram/instagram/whatsapp, `shipping_cost`,
    `free_shipping_threshold`, `about_us`, `footer_note`.

### 9.7 `tickets`

-   **`Ticket`** --- `ticket_number` (generated), FK `user` (`CASCADE`,
    `tickets`), `subject`, `category` ∈ {order, product, technical,
    guide, other}, `priority` ∈ {low, normal, high}, `order_number`,
    `status` ∈ {new, in_progress, answered, closed}, FK `assigned_to`
    (`SET_NULL`), `customer_unread`, `staff_unread`, `created_at`,
    `updated_at`, `last_message_at`, `closed_at`; `close()`.
-   **`TicketMessage`** --- FK `ticket` (`CASCADE`, `messages`), FK
    `sender` (`SET_NULL`), `sender_name` snapshot, `is_staff_message`,
    `body`, `created_at`.

### 9.8 `dashboard`

-   **No models, no migrations.** The app exists only for views, URLs,
    tests and staff templates
    ([dashboard/models.py](dashboard/models.py) is the empty stub).

### 9.9 Migration state

All migrations are applied and the model definitions match the migration
state (`makemigrations --check` → "No changes detected"). Latest per
app: `home/0002_banner_button_text_banner_subtitle_and_more`,
`orders/0002_coupon_order_admin_note_order_coupon_code_and_more`,
`products/0003_product_low_stock_threshold_categoryattribute`,
`accounts/0001_initial`, `blog/0001_initial`, `cart/0001_initial`,
`tickets/0001_initial`. Three of these migration files are untracked in
git (`home/0002`, `orders/0002`, `products/0003`) --- they exist on disk
and are applied to the dev database.

------------------------------------------------------------------------

## 10. Authentication and Authorization

-   **Session authentication only** --- no tokens, JWT, OAuth or API
    keys. `LOGIN_URL='accounts:login'`,
    `LOGIN_REDIRECT_URL='home:index'`,
    `LOGOUT_REDIRECT_URL='home:index'`
    ([config/settings.py](config/settings.py)).
-   **Storefront pages are public** except `/accounts/profile/`,
    `/tickets/*` (`@login_required`).
-   **Dashboard is staff-only** through a shared `staff_member_required`
    decorator on every dashboard view.
-   **No permission checks beyond `is_staff`** --- the `assigned_to`
    field on tickets, `is_superuser` and Django's `Permission`/`Group`
    tables are unused by application code (only `Group` is visible in
    Django admin by default).
-   **Any staff user can promote any other user** to staff (FR-073 /
    SEC-004).
-   **Registration is open** with no CAPTCHA, email confirmation or rate
    limiting.
-   Login allows either username or phone, but there is no lockout after
    repeated failures.

**Unverified:** I did not perform an interactive login through the
browser using the README's `admin/admin123` credentials; authentication
behaviour is reported from code plus test-client `force_login` and the
automated tests' non-staff/anonymous redirect assertions.

------------------------------------------------------------------------

## 11. User Interface and Localization

-   **RTL Persian UI** throughout: `LANGUAGE_CODE='fa'`,
    `TIME_ZONE='Asia/Tehran'`, `USE_TZ=True`; base template sets
    `dir="rtl"` and the Vazirmatn font. The only `USE_I18N`-driven
    translation machinery used in practice is Django's built-in Persian
    locale formatting.
-   **Two layout shells:** [templates/base.html](templates/base.html)
    for the storefront (top bar, logo, live-search box, cart link,
    ticket link, category mega-nav, footer with contact info and static
    links) and
    [templates/dashboard/base_dashboard.html](templates/dashboard/base_dashboard.html)
    for the staff area (grouped sidebar, unread-ticket badge, RTL-aware
    tables).
-   **Visual system:** Tailwind utility classes with a Zitro palette
    derived from the README (`#1d4ed8` blue, `#f97316` orange) and a
    violet-to-indigo gradient family used across dashboards; rounded-3xl
    cards, subtle borders and shadow-xs are used consistently.
-   **Interaction patterns:** HTMX for live search, catalog filtering,
    cart badge/table and ticket polling; vanilla JS for the hero slider
    and the dashboard charts; `django.contrib.messages` toasts for every
    dashboard mutation.
-   **Persian numerals:** dashboard inputs normalise Persian digits;
    chart axes are converted to Persian digits (`to_fa`); amounts use
    thousands separators (`intcomma`).
-   **Consistency gaps (visual only, no functional impact):**
    [templates/orders/mock_payment.html](templates/orders/mock_payment.html)
    is a standalone HTML document (its own `<html>`/`<head>`, not
    extending `base.html`), so it repeats the font/CSS setup instead of
    inheriting the storefront shell; the dashboard has no `models.py`
    layer at all ([dashboard/models.py](dashboard/models.py) is an empty
    stub), so all dashboard state comes from the other apps' models.
-   **No accessibility audit exists** (no landmarks/labels review, no
    WCAG validation) --- see NFR-012.

------------------------------------------------------------------------

## 12. Integrations and External Dependencies

  ------------------------------------------------------------------------------------------------------------------------------------------
  Integration             Status                                 Evidence
  ----------------------- -------------------------------------- ---------------------------------------------------------------------------
  Payment gateway         **Simulated only** (no PSP)            `mock_payment_view`, Shaparak-styled template

  Instalment / credit     **Not integrated** (copy only)         [templates/home/installment.html](templates/home/installment.html)
  (SnappPay)                                                     

  Shipping carriers       **Not integrated** --- method is a     `Order.SHIPPING_CHOICES`, `orders_export_view`
  (post/tipax/courier)    stored label                           

  Email                   **Not integrated**                     no `EMAIL_*` settings, no `send_mail`

  SMS / OTP               **Not integrated**                     no provider code, no OTP model

  Analytics / error       **Not integrated**                     no Sentry/GA/Plausible snippet
  monitoring                                                     

  CDN / external assets   Google Fonts (Vazirmatn) at runtime;   [templates/orders/mock_payment.html](templates/orders/mock_payment.html),
                          Chart.js and HTMX behavior are         [static/js/vendor/chart.umd.min.js](static/js/vendor/chart.umd.min.js);
                          vendored/self-hosted                   note `django_htmx` provides middleware only --- the HTMX library itself is
                                                                 loaded in [templates/base.html](templates/base.html)

  Django admin            Registered for `Group`, `Ticket`,      runtime inspection of `admin.site._registry`
                          `TicketMessage` only                   

  Python packages         No                                     `ls requirements*.txt` → none
                          `requirements.txt`/`pyproject.toml`;   
                          the effective environment is `venv/`   
                          (Django 6.1.1 installed)               
  ------------------------------------------------------------------------------------------------------------------------------------------

README claim vs reality: README tells staff to use both `/dashboard/`
**and** `/admin/` for administration. In practice the Django admin
exposes only Groups and support tickets --- **no** product, order,
customer, coupon or blog management there.

------------------------------------------------------------------------

## 13. Non-Functional Requirements

**NFR-001 --- Persian RTL localization** - Status: Implemented ---
`LANGUAGE_CODE='fa'`, `TIME_ZONE='Asia/Tehran'`, `dir="rtl"`, Vazirmatn
font, Persian labels and thousands separators throughout.

**NFR-002 --- Responsive layout** - Status: Implemented --- Tailwind
responsive prefixes (`sm:`/`md:`/`lg:`) are used across storefront and
dashboard templates; mobile navigation is present in
[templates/base.html](templates/base.html). - Acceptance criteria: no
horizontal overflow at the 375 px/768 px/1280 px breakpoints ---
**Unverified** (no browser/visual test performed).

**NFR-003 --- Persian numeral and separator tolerant input** - Status:
Implemented --- `to_int()` in [dashboard/views.py](dashboard/views.py)
translates Persian/Arabic-Indic digits and strips `,`/`٬`/spaces; used
by product, inventory, coupon, category, brand, attribute and banner
forms.

**NFR-004 --- Database query efficiency** - Status: Partially
Implemented --- `select_related`/`prefetch_related` are used in the main
list/detail views (shop, product detail, dashboard lists, reports,
customer file); however `Customer_list_view` paginates in Python after
loading all annotated users, `inventory_view` renders at most 200 rows,
and `total_count = products.count()` issues an extra query per shop
request. - Acceptance criteria: none documented.

**NFR-005 --- Automated test coverage** - Status: Partially Implemented
--- 35 tests exist and pass, concentrated in `dashboard` (30) and
`products` (5). `accounts`, `cart`, `blog`, `home`, `orders` have empty
stubs and `tickets` has no test module. No coverage measurement is
configured.

**NFR-006 --- Pagination of large lists** - Status: Partially
Implemented --- dashboard products (20/page), orders (25/page) and
customers (20/page, in Python) are paginated; the storefront `/shop/`
renders **all** matching products in one response with no pagination or
lazy loading; blog and ticket lists are unpaginated.

**NFR-007 --- CSRF protection** - Status: Implemented ---
`CsrfViewMiddleware` is enabled; all forms include `{% csrf_token %}`;
[static/js/htmx-config.js](static/js/htmx-config.js) injects the
`X-CSRFToken` header for HTMX requests. Some destructive dashboard
endpoints are POST-only via `@require_POST`; several are not
(e.g. `product_delete_view`, `category_delete_view`,
`brand_delete_view`, `post_delete_view`, `coupon_delete_view`,
`attribute_delete_view` accept GET and act only when
`request.method == 'POST'`, so a GET is harmless but a CSRF-token-less
browser GET renders a delete form page rather than performing an
action).

**NFR-008 --- Static and media file serving** - Status: Implemented for
development --- `STATICFILES_DIRS`, `STATIC_ROOT`, WhiteNoise middleware
and DEBUG-mode `static()`/`media()` helpers. `collectstatic` has
produced `staticfiles/` (present on disk, git-ignored). - Production
caveat: with `DEBUG=True` and no `STATICFILES_STORAGE`/CDN
configuration, the current configuration is not production-ready.

**NFR-009 --- Environment and secret configuration** - Status: Not met
--- `SECRET_KEY` is hard-coded in
[config/settings.py](config/settings.py), `DEBUG=True`,
`ALLOWED_HOSTS=['*']`; there is no `.env` loading and `.env` is
git-ignored but no example file exists.

**NFR-010 --- Dependency and deployment manifests** - Status: Not met
--- no `requirements.txt`, `pyproject.toml`, `Pipfile`, `Dockerfile`,
`Procfile`, `gunicorn`/`uvicorn` config or CI workflow exists;
`package.json` pins Tailwind tooling only. Reproducing the environment
currently depends on the checked-out `venv/`.

**NFR-011 --- Logging, monitoring and auditability** - Status: Not met
--- only Django's default logging config applies; no structured logging,
no error tracking, no request tracing, and no audit trail of staff
actions (see FR-079).

**NFR-012 --- Accessibility** - Status: Unverified --- no audit was
performed and no accessibility acceptance criteria are documented.
Templates use semantic sections and labels in places, but this was not
systematically evaluated.

**NFR-013 --- Performance targets and load behaviour** - Status:
Unverified --- no documented targets exist (no SLA page-time, no
response-time budget), and no load or performance measurement was run
during this audit. The vendor Chart.js bundle and Tailwind's compiled
`output.css` are served locally, which avoids CDN latency but no
size/optimization analysis was done.

**NFR-014 --- Browser compatibility** - Status: Unverified --- JS relies
on modern APIs (DOM `change` events, `classList`, template literals,
`fetch`-free HTMX); no compatibility matrix is documented or tested.

------------------------------------------------------------------------

## 14. Security and Privacy Requirements

**SEC-001 --- Password policy enforcement** - Status: Partially
Implemented --- four validators are configured, but registration calls
`User.objects.create_user()` directly without `validate_password()`, so
only "password matches confirmation" is enforced. Acceptance criterion
(documented intent): weak/common/numeric passwords must be rejected at
registration --- **currently not satisfied**.

**SEC-002 --- Dashboard authorization** - Status: Implemented ---
`staff_member_required` on every dashboard view, verified by test and
runtime redirect check.

**SEC-003 --- Order and invoice data exposure** - Status: At risk ---
`/orders/success/<order_number>/` and `/orders/tracking/` are public and
the tracking view treats the phone as *optional*, so an attacker who
guesses or observes a 6-hex-character order number can read recipient
name, phone, full address and order contents. No ownership check, no
rate limit, no login requirement.

**SEC-004 --- Privilege escalation via staff toggle** - Status: At risk
--- any `is_staff` user can set `is_staff=True` on any other account
(only self-toggling is blocked). There is no superuser requirement, no
confirmation step and no audit log.

**SEC-005 --- Brute-force and abuse protection** - Status: Not
implemented --- no rate limiting/throttling, no CAPTCHA/Turnstile, no
account lockout on login, no abuse protection on live search or
tracking.

**SEC-006 --- Debug settings and secrets** - Status: At risk ---
`DEBUG=True`, hard-coded `SECRET_KEY`, `ALLOWED_HOSTS=['*']`. Running
as-is in production would leak tracebacks and serve media through the
development view.

**SEC-007 --- Uploaded media access control** - Status: At risk ---
product/category/brand/banner/avatar/blog images are served from a
public `MEDIA_URL` with no authorization; a leaked URL is permanent.
(Acceptable for public product imagery, but customer avatars are also in
this namespace.)

**SEC-008 --- Input validation** - Status: Partially Implemented --- no
Django forms are used anywhere; validation is hand-written per view.
Positive examples: required-field checks, SKU/coupon-code uniqueness,
self-parent prevention, allow-listed status/payment/shipping values,
`to_int` coercion, coupon/brand/category scoping. Weak examples:
`cart_add_view` calls `int()` on unvalidated POST data (a non-numeric
value raises), phone/postal formats are unvalidated, and the product
detail route ignores the slug segment.

**SEC-009 --- XSS surface** - Status: Partially Implemented --- template
auto-escaping is on and generally relied upon; the single `|safe` use is
`{{ cat.icon_svg|safe }}` in
[templates/home/index.html](templates/home/index.html#L142), which
renders raw SVG entered by staff in the dashboard category form. This is
an authenticated-staff-only input path, but it is an unvalidated HTML
injection vector from the admin UI to the public site. Blog post bodies
are rendered through normal auto-escaping (no WYSIWYG/rich text), so no
`|safe` HTML rendering exists for articles.

**SEC-010 --- Session and cookie hardening** - Status: Not implemented
--- no `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
`SECURE_SSL_REDIRECT`, HSTS, or `SESSION_COOKIE_HTTPONLY` overrides;
Django defaults apply.

**SEC-011 --- Privacy policy / consent** - Status: Not implemented ---
no privacy page, cookie-consent banner or data-retention policy exists
in code or documentation.

------------------------------------------------------------------------

## 15. Current Limitations and Known Gaps

### 15.1 Discrepancies between documentation and code (recorded, not resolved)

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------
  \#                      Document claim                                                       Repository reality
  ----------------------- -------------------------------------------------------------------- -------------------------------------------------------------------
  D1                      [README.md](README.md) and the roadmap present `/admin/` as the      Django admin registers **only** `Group`, `Ticket`, `TicketMessage`.
                          standard Django admin alongside the custom dashboard                 Every other app's `admin.py` is the untouched 3-line stub. Custom
                                                                                               `User` is **not** registered, so it cannot be managed there.

  D2                      Roadmap 1.1 marks product CRUD as "✅ موجود، تکمیل شد" including     No duplicate/copy product action exists in `dashboard/views.py`,
                          "کپی سریع" (quick copy)                                              `dashboard/urls.py` or the products template.

  D3                      Roadmap 3.3 claims operational alerts for "کسری موجودی، سفارش        The overview template only renders a stock alert panel and
                          پرداختنشده، کوپنهای در حال انقضا" (low stock, unpaid orders,         low-stock list. No coupon-expiry alert and no unpaid-order alert
                          expiring coupons)                                                    block exist.

  D4                      README §فروش و مشتریان describes customer file content as including  The customer file instead shows
                          "خلاصه سبد خرید رهاشده" (abandoned-cart summary)                     `pending_count = orders.filter(payment_status='pending').count()`
                                                                                               --- unpaid orders, not abandoned carts. There is no
                                                                                               cart-abandonment model or report. Roadmap 3.5 correctly lists
                                                                                               abandoned carts as future work, so README and roadmap disagree with
                                                                                               each other.

  D5                      [templates/home/installment.html](templates/home/installment.html)   Checkout offers only `mock_gateway` and `cod`; no instalment/credit
                          describes selecting the "درگاه اعتباری اسنپپی" at checkout for       payment method, provider or verification exists.
                          4-instalment payment                                                 

  D6                      README presents the Shaparak flow as "شبیهساز پرداخت آنلاین" --- an  The word "شبیهساز/آزمایشی" is prominent in the gateway template,
                          accurate description                                                 but the *success page and tracking page are indistinguishable from
                                                                                               a real paid order*, which can mislead operators testing the system.
                                                                                               No "test mode" flag exists on `Order`.

  D7                      README lists the blog app under key features but the roadmap's       Roadmap is incomplete relative to code (blog post/category CRUD
                          feature inventory (Phases 1--4) never mentions blog management,      exists).
                          which is fully implemented                                           

  D8                      README/roadmap do not mention the support ticket module at all       A complete customer + staff ticket system exists
                                                                                               ([tickets/](tickets/)).

  D9                      README states "دستهبندی درختی، برندها ... و مشخصات فنی" for products True, but attributes are *definitions/suggestions* only --- no
                                                                                               per-product attribute values are stored; specifications are
                                                                                               separate free-form rows. Language in README could be read as
                                                                                               implying attribute values are persisted.
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------

### 15.2 Functional gaps (no roadmap entry)

-   No stock deduction or availability re-check on purchase (FR-048);
    overselling is possible.
-   No guest-cart merge on login/registration (FR-033).
-   Cart does not respect `stock_qty` limits (FR-032).
-   No address book CRUD and checkout does not reuse saved addresses
    (FR-005).
-   No password reset, no OTP/verification (FR-006, FR-007).
-   No transactional emails/SMS (FR-050).
-   No pagination on the storefront catalog (NFR-006).
-   No `requirements.txt`/lockfile for Python dependencies (NFR-010).
-   Repository is not production-configurable (NFR-009, SEC-006).

### 15.3 Quality and structural observations

-   **No `forms.py` anywhere** --- all validation is bespoke view logic,
    which duplicates required-field/type handling and makes SEC-008
    issues likely as the surface grows.
-   **Mixed CRUD method handling** --- some deletions are
    `@require_POST`, others merely check `request.method == 'POST'`
    inside a GET-renderable view (see NFR-007).
-   **`dashboard` has no models** --- legitimate here, but it means all
    reporting logic lives in a single 1,952-line `views.py`, which is
    the largest file in the project and the natural refactor target.
-   **Dead/stale context values** --- e.g. `overview_view` computes
    `coupons_count` but the overview template never renders it;
    `cart_detail_view` passes `items` that the partial also recomputes.
-   **Untracked migrations** --- `home/0002`, `orders/0002`,
    `products/0003` are on disk and applied but not committed; a fresh
    clone from git would not have them.
-   **Untested modules** --- `tickets` (both sides), `accounts`, `cart`,
    `blog`, `home`, `orders` have no meaningful test coverage.
-   **Working tree carries uncommitted work** --- the initial repository
    state for this audit showed 24 modified files and 4 untracked items
    (including all three new migrations and
    `docs/ROADMAP_ADMIN_PANEL.md`); the PRD describes the on-disk state,
    not the last commit.

------------------------------------------------------------------------

## 16. Planned Features and Future Scope

Only items with explicit documentation are listed as **Planned**. Each
cites the roadmap status verbatim (⏳ فاز بعد / Phase 4).

  -----------------------------------------------------------------------
  Roadmap ID              Feature                 Roadmap status
  ----------------------- ----------------------- -----------------------
  3.4                     Product                 ⏳ Phase next
                          comments/reviews and    
                          moderation              

  3.5                     Wishlist and            ⏳ Phase next
                          abandoned-cart tracking 

  3.6                     Admin audit log         ⏳ Phase next

  4.1                     Roles and access levels ⏳ Phase 4
                          (Django Groups +        
                          permissions)            

  4.2                     Dashboard operator      ⏳ Phase 4
                          management (add/disable 
                          operators, assign       
                          access)                 

  4.3                     Backup and restore      ⏳ Phase 4
                          (DB + media)            

  4.4                     Financial reporting and ⏳ Phase 4
                          gateway settlement      
                          reconciliation          

  4.5                     Two-factor login and IP ⏳ Phase 4
                          allowlist               

  4.6                     Static content pages    ⏳ Phase 4
                          (about us, terms)       

  4.7                     Shipping management     ⏳ Phase 4
                          (methods, regions,      
                          costs)                  

  4.8                     Email/SMS marketing     ⏳ Phase 4
                          campaigns               
  -----------------------------------------------------------------------

Additional work identified by this audit that is **not** in the roadmap
but is required for a functioning store (no roadmap entry, no code):
stock deduction on purchase, guest-cart merging, address book CRUD,
password reset, transactional notifications, real payment integration,
and production settings/dependency pinning.

------------------------------------------------------------------------

## 17. Acceptance Criteria

Acceptance criteria are stated only for behaviour that is either
verified by an automated test or fully implemented in code (and, for the
routes below, confirmed with a successful read-only request). Criteria
are written as testable statements.

### 17.1 Criteria verified by the existing test suite (must keep passing)

-   **AC-01 (FR-060)** Anonymous or non-staff access to any
    `/dashboard/` URL redirects to `/accounts/login/`; staff access
    returns 200 for all 25 listed dashboard pages. ---
    `DashboardAccessTests.test_anonymous_and_normal_user_are_blocked`,
    `test_staff_can_open_every_dashboard_page`
-   **AC-02 (FR-064)** Creating a product with images and specification
    rows persists the product, its images (with a primary image) and its
    specifications; a duplicate SKU is rejected with an error message
    and no second product. ---
    `test_create_product_with_images_and_specifications`,
    `test_duplicate_sku_is_rejected`
-   **AC-03 (FR-065)** Product list filters, sorting and bulk actions
    produce the expected result sets and counts. ---
    `test_filters_and_bulk_actions`, `test_delete_product`,
    `test_edit_and_toggle_product`
-   **AC-04 (FR-066)** Bulk inventory submission updates only changed
    products' `stock_qty`/`low_stock_threshold`. ---
    `test_inventory_bulk_update`
-   **AC-05 (FR-067)** Categories can be created with parents and
    reordered/toggled; a category cannot be its own parent. ---
    `test_category_crud_and_parent_tree`,
    `test_category_cannot_be_its_own_parent`
-   **AC-06 (FR-068/FR-069/FR-074/FR-075)** Brand, attribute, coupon and
    blog CRUD flows save and delete as expected, including quick
    attribute add and blog categories. --- `test_brand_crud`,
    `test_attribute_crud_and_quick_add`, `test_coupon_crud`,
    `test_post_crud_and_blog_categories`
-   **AC-07 (FR-070)** Banner create/edit/toggle/reorder behaves as
    specified, and edit forms render existing values (including the
    existing image). --- `test_banner_crud_and_ordering`,
    `test_edit_forms_render_with_existing_records`
-   **AC-08 (FR-071/FR-063)** Order detail updates (status, payment,
    tracking code), order CSV export, and the reports/inventory/product
    exports return content with Persian headers. ---
    `test_order_detail_update_status_and_export`,
    `test_inventory_and_product_exports`
-   **AC-09 (FR-042/FR-041)** A valid coupon and the shipping threshold
    are applied to the created order's `final_amount`; free shipping
    applies above the configured threshold; an invalid coupon is
    rejected at apply time. ---
    `test_coupon_and_shipping_applied_to_order`,
    `test_free_shipping_threshold`,
    `test_invalid_coupon_is_rejected_when_applying`
-   **AC-10 (FR-072)** Customer segmentation and sorting behave as
    specified, the customer file renders with its chart data, and
    non-staff users cannot open customer pages. ---
    `test_customer_segments_and_sorting`,
    `test_customer_detail_page_and_chart`,
    `test_non_staff_cannot_open_customer_pages`
-   **AC-11 (FR-062)** The reports page honours `from`/`to` filters and
    computes the previous-period comparison. ---
    `test_reports_filters_and_previous_period_comparison`
-   **AC-12 (FR-030/FR-044)** Adding to cart over HTMX creates a cart
    with the right quantity/total, and the checkout →
    mock-payment-success path produces `payment_status='successful'`,
    `status='paid'` and a `TRX-` transaction id. ---
    `products.tests.test_cart_add_and_htmx_flow`,
    `test_checkout_and_payment_flow`
-   **AC-13 (FR-010/FR-011/FR-013)** Shop, category and live-search
    endpoints return 200 and contain expected product titles. ---
    `products.tests.test_shop_and_category_endpoints`,
    `test_live_search_endpoint`
-   **AC-14 (FR-043, business rules)** `discount_pct` is computed from
    `compare_at_price`, `is_available` from `stock_qty`, and
    `formatted_price` uses thousands separators. ---
    `products.tests.test_product_model_calculations`
-   **AC-15 (FR-014/FR-018/FR-019)** Staff-created
    banners/categories/posts appear on the storefront. ---
    `dashboard.tests.test_created_content_appears_on_storefront`

### 17.2 Criteria confirmed by read-only runtime checks

-   **AC-16** `python manage.py check` reports no issues and
    `makemigrations --check` reports no pending model changes.
-   **AC-17** The storefront and content routes listed in
    [§7.3](#73-read-only-runtime-checks-performed) return HTTP 200 for
    an anonymous client with the current database.
-   **AC-18** `/dashboard/` returns 302 for anonymous requests and 200
    after a staff login; `/dashboard/reports/` returns 200 for staff.

### 17.3 Acceptance criteria that cannot yet be met (stated as target behaviour)

-   **AC-19 (FR-048)** *Target:* paying for or delivering an order
    decrements `Product.stock_qty` by the ordered quantity and prevents
    ordering beyond available stock. *Current:* no code path changes
    stock on purchase.
-   **AC-20 (FR-032)** *Target:* the cart rejects quantities exceeding
    `stock_qty` (and shows a message). *Current:* no check exists.
-   **AC-21 (FR-033)** *Target:* logging in or registering while a guest
    cart exists transfers its lines to the user's cart. *Current:* no
    transfer occurs.
-   **AC-22 (FR-005)** *Target:* a customer can create, edit, delete and
    default a saved address, and checkout can select one. *Current:*
    model only.
-   **AC-23 (SEC-003)** *Target:* invoice and tracking pages require
    either ownership or a per-order secret (e.g. phone + order
    combination, or a signed link) and are rate limited. *Current:*
    public and guessable.
-   **AC-24 (SEC-001)** *Target:* registration rejects passwords that
    fail the configured validators. *Current:* validators are not
    invoked.
-   **AC-25 (FR-020)** *Target:* the contact form persists a message
    and/or sends a notification. *Current:* client-side alert only.
-   **AC-26 (FR-021)** *Target:* the instalment flow either ships as a
    selectable payment method with a real provider or is removed from
    the product page and the informational page. *Current:* UI copy with
    no backing capability.
-   **AC-27 (NFR-009/NFR-010)** *Target:* settings are
    environment-driven (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`,
    `EMAIL_*`), and a pinned Python dependency manifest plus a
    deployment configuration exist. *Current:* absent.

------------------------------------------------------------------------

## 18. Assumptions and Unresolved Questions

Explicit assumptions made while writing this PRD (each is a place where
the repository does not decide the answer):

1.  **Is the mock gateway intended to be replaced by a real PSP, or is
    it a permanent demo feature?** The code, README and roadmap disagree
    in emphasis; no PSP is chosen anywhere.
2.  **Is COD "paid" or "unpaid" until delivery?** Code sets
    `status='paid'` while leaving `payment_status='pending'`. Which one
    is authoritative for revenue reporting is undecided ---
    `reports_view` counts revenue only from
    `payment_status='successful'`, so COD revenue is currently invisible
    in reports.
3.  **Should `tickets` and the storefront rails (`smartphones`,
    `laptops`, `gaming`) be softened?** The hard-coded slugs and the
    untested ticket module suggest they were added recently (both appear
    in uncommitted work).
4.  **`is_verified` and `Address.is_default`** exist without behaviour;
    are they placeholders for the planned OTP and address-book features,
    or leftovers?
5.  **Is the storefront required to paginate?** NFR-006 documents the
    gap; no target page count or catalogue size requirement exists.
6.  **Who owns dashboard operator provisioning?** Today any staff member
    can promote others (SEC-004); a target policy (superuser-only?
    IT-approved?) is needed before FR-078 lands.
7.  **Which languages/currencies** --- the UI is Persian-only and
    Toman-only; no internationalization plan is documented beyond
    `USE_I18N=True`.
8.  **Where does deployment happen?** No target platform, container base
    or WSGI server is specified; WhiteNoise's presence hints at a
    PaaS-style deployment but nothing is configured.
9.  **Legal/privacy obligations** (Iranian e-commerce requirements, data
    retention, invoice numbering rules) are not addressed anywhere in
    the repository.
10. **The roadmap's Phase 1--3 "✅" claims** are broadly consistent with
    the code, with the specific exceptions recorded in §15.1 (D2, D3,
    D4). Whether the roadmap should be corrected or the features
    implemented is a product decision.

------------------------------------------------------------------------

## 19. Evidence and Source References

### 19.1 Commands executed during this audit (all read-only or non-mutating)

    python --version                              → Python 3.14.6
    python -c "import django; django.get_version()" → 6.1.1
    python manage.py check                        → "System check identified no issues (0 silenced)."
    python manage.py makemigrations --check --dry-run → "No changes detected"
    python manage.py test                         → "Ran 35 tests ... OK"
    python manage.py showmigrations               → all app migrations applied
    django.test.Client GET sweep (see §7.3)       → 200s for storefront/content routes; 302/200 for dashboard
    admin.site._registry inspection               → ['Group', 'Ticket', 'TicketMessage']
    ORM counts on db.sqlite3                      → 13 products, 9 categories, 10 brands, 11 orders, 1 coupon, 1 ticket

### 19.2 Primary source files inspected

-   **Project:** [README.md](README.md),
    [docs/ROADMAP_ADMIN_PANEL.md](docs/ROADMAP_ADMIN_PANEL.md),
    [config/settings.py](config/settings.py),
    [config/urls.py](config/urls.py), [manage.py](manage.py),
    [package.json](package.json), [.gitignore](.gitignore)
-   **accounts:** [models.py](accounts/models.py),
    [views.py](accounts/views.py), [urls.py](accounts/urls.py),
    [admin.py](accounts/admin.py),
    [migrations/0001_initial.py](accounts/migrations/0001_initial.py)
-   **products:** [models.py](products/models.py),
    [views.py](products/views.py), [urls.py](products/urls.py),
    [admin.py](products/admin.py),
    [management/commands/seed_data.py](products/management/commands/seed_data.py),
    [management/commands/populate_images.py](products/management/commands/populate_images.py),
    [migrations/](products/migrations/)
-   **cart:** [models.py](cart/models.py), [views.py](cart/views.py),
    [urls.py](cart/urls.py),
    [context_processors.py](cart/context_processors.py)
-   **orders:** [models.py](orders/models.py),
    [views.py](orders/views.py), [urls.py](orders/urls.py),
    [migrations/0002_coupon_order_admin_note_order_coupon_code_and_more.py](orders/migrations/0002_coupon_order_admin_note_order_coupon_code_and_more.py)
-   **home:** [models.py](home/models.py), [views.py](home/views.py),
    [urls.py](home/urls.py),
    [context_processors.py](home/context_processors.py),
    [migrations/](home/migrations/)
-   **blog:** [models.py](blog/models.py), [views.py](blog/views.py),
    [urls.py](blog/urls.py)
-   **tickets:** [models.py](tickets/models.py),
    [views.py](tickets/views.py), [urls.py](tickets/urls.py),
    [admin.py](tickets/admin.py),
    [context_processors.py](tickets/context_processors.py)
-   **dashboard:** [views.py](dashboard/views.py),
    [urls.py](dashboard/urls.py), [models.py](dashboard/models.py),
    [tests.py](dashboard/tests.py)
-   **Tests:** [products/tests.py](products/tests.py),
    [dashboard/tests.py](dashboard/tests.py), plus the empty stubs
    [accounts/tests.py](accounts/tests.py),
    [cart/tests.py](cart/tests.py), [blog/tests.py](blog/tests.py),
    [home/tests.py](home/tests.py), [orders/tests.py](orders/tests.py)
-   **Frontend:** [static/js/htmx-config.js](static/js/htmx-config.js),
    [static/js/dashboard-charts.js](static/js/dashboard-charts.js),
    [static/js/vendor/chart.umd.min.js](static/js/vendor/chart.umd.min.js),
    [static/css/input.css](static/css/input.css),
    [static/css/output.css](static/css/output.css)
-   **Templates (52 files)** under [templates/](templates/), including
    [base.html](templates/base.html),
    [home/index.html](templates/home/index.html),
    [home/installment.html](templates/home/installment.html),
    [home/contact.html](templates/home/contact.html),
    [dashboard/base_dashboard.html](templates/dashboard/base_dashboard.html),
    [dashboard/overview.html](templates/dashboard/overview.html),
    [dashboard/reports.html](templates/dashboard/reports.html),
    [orders/checkout.html](templates/orders/checkout.html),
    [orders/mock_payment.html](templates/orders/mock_payment.html)

### 19.3 Grep-based negative evidence (features that do not exist)

  -----------------------------------------------------------------------
  Search                              Result
  ----------------------------------- -----------------------------------
  `wishlist` / `favorite` /           no matches
  `علاقهمندی` across `templates`,     
  `products`, `orders`, `accounts`    

  `rest_framework` / `serializers` in no matches
  `config`                            

  `find . -name forms.py` (excluding  no matches
  venv/node_modules)                  

  `stock_qty` in `orders/` and        no matches → no stock deduction on
  `cart/` (excluding migrations)      purchase

  `send_mail` / `EMAIL_` settings     no matches

  `requirements*.txt`                 no file

  `Dockerfile` / CI workflow          no file

  "کپی"/"duplicate"/"copy" in         only `request.GET.copy()`
  dashboard product code              (pagination helper)

  expiring-coupon alert markup in     no matches
  dashboard overview                  

  `Address` usage in `accounts/`,     model + dashboard read only
  `orders/`, storefront templates     
  -----------------------------------------------------------------------

### 19.4 Explicitly unverified items

-   Interactive browser rendering, HTMX behaviour in a real browser,
    responsive breakpoints, and visual/accessibility quality.
-   Real payment, instalment, SMS and email integrations (they do not
    exist).
-   Concurrency, load and performance characteristics; resilience under
    simultaneous checkout of the last stock unit.
-   Behaviour of `seed_data` and `populate_images` when re-run (not
    executed here; both are written to be idempotent but this was not
    tested).
-   The README's advertised `admin/admin123` credentials were not used
    to log in interactively.

------------------------------------------------------------------------

*End of document. Any statement above that is not backed by code or by a
command listed in §19.1 should be treated as a gap to verify, not as a
specification.*
