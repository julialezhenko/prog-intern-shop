# Sondermark Coffee Roasters — storefront on the CommerceLab platform

A specialty-coffee e-commerce MVP: a fictional Valencia roastery selling single origins, espresso blends, decaf,
drip bags, gift boxes, subscriptions and brewing equipment. The store runs on **CommerceLab**, a readable
**Django 4.2 modular monolith** (storefront + admin + REST API + inventory + analytics) that is also used as the
codebase for the developer internship (see `docs/internship-*.md`).



## Quick start (local, SQLite)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                      # optional: every setting has a safe local default
python manage.py migrate
python manage.py seed_demo                # 26 products, 14 categories, tags, warehouses, suppliers, campaigns, POs
python manage.py generate_test_data --users 2500 --max-orders 15 \
    --date-from 2025-01-01 --date-to 2026-09-01 --seed 20260901 --dirty   # ~175k rows of analysable history
python manage.py runserver
```

* Storefront: http://localhost:8000/ · Admin: http://localhost:8000/admin/ · API docs: http://localhost:8000/api/docs/
* Demo accounts (password `CommerceLab123!`): `customer`, `admin` (superuser), `manager`, `warehouse`, `analyst`.
* Checkout uses a **simulated card gateway** — `4242 4242 4242 4242` is approved, `4000 0000 0000 0002` is declined
  (the full list is shown on the payment page). No real payment is ever taken.
* Coupon codes: `WELCOME10`, `BREWGEAR5`, `SUBSCRIBE15`, `BLACKFRIDAY20`, `FREIGHTFREE`, `CAFE25`,
  `COMEBACK12`, `PARTNER10` (see the Discounts admin for thresholds).

Docker: `docker compose up --build` starts the app (Gunicorn), a Celery worker + beat, PostgreSQL 16 and Redis;
run `docker compose exec app python manage.py migrate && docker compose exec app python manage.py seed_demo` once.

Tests: `pytest` (137 tests, ~35 s).

## What the store does

| Area | Highlights |
|---|---|
| Home | Hero, category tiles, best sellers, welcome-offer band, “find your coffee” by brew method / roast, why-us, new arrivals, subscription band, editorial, reviews, FAQ, newsletter, footer |
| Catalog | Search (name, notes, origin, SKU…), facets for roast level, origin, brewing method, price, stock and offers; sort; pagination; category pages; active-filter chips; mobile filter drawer |
| Product page | Gallery, tasting-note chips, variant picker (size & grind / plan / colour), quantity stepper, live price, stock line, trust row, roast meter, “why you’ll love it”, coffee profile, brewing methods, brew recipe, origin story, specs (equipment), reviews + review form, FAQ, related products, JSON-LD |
| Cart & checkout | Guest or logged-in carts (merged on login), quantity steppers, coupon codes, VAT-inclusive totals, split-warehouse allocation, tokenised guest order links, demo card payment, confirmation page + e-mail, order history, cancellation |
| Admin | Coffee profile fields, featured flag, compare-at price, brew-method checkboxes, image upload or URL, inline variants/images/price history, category images & ordering, reviews moderation, newsletter subscribers, KPI dashboard, orders with status actions |
| SEO | Titles, meta descriptions, canonical + Open Graph tags, Product JSON-LD, `sitemap.xml`, `robots.txt`, semantic headings, alt text, 404/500 pages |
| Background jobs | Celery (eager without a broker): unpaid-order expiry, cart cleanup, order confirmation e-mails |
| Reporting | Read-only fact and dimension datasets over the whole domain, multi-value and date-range filters, sorting, search, large pages, and grouping endpoints that return raw sums only |
| Test data | Admin generator for synthetic customers and orders, with seeds, dirty-data mode and exact one-click cleanup |

## Analytics & reporting

The API is deliberately split. Transactional endpoints run the shop; **reporting datasets** are read-only,
need a reporting role (`Analyst`, `Store Manager`, `Marketing Manager`, `Admin` or staff) and expose the
raw grain so that metrics get derived rather than served:

```bash
curl -u analyst:CommerceLab123! \
  "http://localhost:8000/api/sales/orders/?status=DELIVERED,SHIPPED&created_at_after=2026-01-01&ordering=-total&page_size=500"
curl -u analyst:CommerceLab123! "http://localhost:8000/api/sales/order-items/?category=3&order__created_at_after=2026-01-01"
curl -u analyst:CommerceLab123! "http://localhost:8000/api/operations/events/?kind=SESSION_STARTED,PURCHASE_COMPLETED&device=mobile"
curl -u analyst:CommerceLab123! "http://localhost:8000/api/analytics/breakdown/?dimension=channel_group&secondary=device"
curl -u analyst:CommerceLab123! "http://localhost:8000/api/analytics/timeseries/?grain=month&date_from=2025-01-01"
curl -u analyst:CommerceLab123! "http://localhost:8000/api/analytics/dimensions/"
```

Conversion rates, average order value, lifetime value, retention and cohort matrices, ROAS/CPC/CAC,
churn and period-over-period deltas are **not** served — `/api/analytics/dimensions/` lists exactly what is
withheld. Two things to watch when computing them yourself: `order.total` is in `order.currency`
(multiply by `fx_rate` for euros), and `tax_amount` is the VAT *contained* in the total, not added to it.

Full dataset and dimension reference: `docs/analytics.md`.

## Generating data for exercises

**Admin → Analytics → Test data batches → Generate test users & orders** (superusers only) fills the
database with synthetic customers and their order history: pick the number of users, the minimum and
maximum orders per user, the period, a random seed and whether to include realistic data quality issues.
Progress is shown while it runs, and one action removes exactly what was generated.

Generated rows carry `is_test_data=true` and a `test_batch` id, use the undeliverable `example.com`
domain and have unusable passwords. The generator writes rows with `bulk_create` and never goes through
`sales.services`, so no confirmation e-mail, gateway call or stock movement can be triggered by it.
Filter it out of any dataset endpoint with `?is_test_data=false`.

The dataset carries seasonality, differing channel and regional performance, cancellations, refunds,
outliers, missing values and several patterns that are only discoverable by analysing it.
See `docs/test-data-generator.md`.

## Project layout

```
config/      settings, urls, Celery app, custom AdminSite with KPI dashboard
accounts/    registration/profile, CustomerProfile (geography, acquisition, segmentation), segment history,
             NewsletterSubscriber, AuditLog, customer dimension API
catalog/     Category (two levels)/Brand/Tag/Product/Variant/Image/Review/PriceHistory/ProductStatusHistory,
             storefront views, API, content (FAQ, brew methods), demo_catalog.py (seed data), sitemaps
sales/       Cart/Order/OrderItem/Payment/Refund/ReturnRequest/Shipment/Subscription/Discount models,
             services (the only place stock or order state changes), payments gateway, storefront + API views
operations/  Warehouses, inventory + weekly snapshots, suppliers, purchase orders, transfers, campaigns +
             daily media metrics, behavioural product events
analytics/   Reporting API, TestDataBatch, generation/ (the admin test-data generator),
             management commands (seed_demo, generate_test_data, simulate_business)
config/      settings, urls, api.py (shared pagination/roles/filters), Celery app, admin site with KPI dashboard
templates/   base layout, catalog/, sales/, accounts/, registration/, admin/index.html
static/      css/storefront.css, js/storefront.js (progressive enhancement only), img/favicon.svg
tests/       pytest suite (storefront, cart flow, checkout, guest/split/payments, admin & API, coffee storefront)
docs/        architecture, business rules, testing, images (photo credits), internship material
```

## Configuration

Everything is read from environment variables (see `.env.example`): `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`,
`POSTGRES_*` (SQLite when unset), `STORE_NAME`/`STORE_SHORT_NAME`/`STORE_CURRENCY`, `SITE_URL`, `EMAIL_BACKEND`,
`PAYMENT_GATEWAY`, `PAYMENT_WEBHOOK_SECRET`, `ORDER_PAYMENT_TIMEOUT_HOURS`, `CART_RETENTION_DAYS`,
`CELERY_BROKER_URL` (tasks run inline when empty), `MEDIA_ROOT`, `STOREFRONT_PAGE_SIZE`.

## Business rules worth knowing

* A product is visible only when `active=True` **and** `status=ACTIVE` (`Product.objects.storefront()` is the single rule
  used by the storefront, the public API, the sitemap and the dashboard).
* Prices are consumer prices **including VAT**; the VAT contained in an order is recorded, not added on top.
* Stock = physical − reserved, summed over active variants and warehouses. Checkout reserves, shipping deducts,
  cancelling releases. Orders can be split across warehouses per line.
* Unpaid orders expire after `ORDER_PAYMENT_TIMEOUT_HOURS`; reviews are moderated before they appear and are marked
  “verified purchase” when the customer has a paid order containing the product.

More detail: `docs/architecture.md`, `docs/business-rules.md`, `docs/analytics.md`,
`docs/test-data-generator.md`, `docs/testing.md`, `docs/images.md`.
