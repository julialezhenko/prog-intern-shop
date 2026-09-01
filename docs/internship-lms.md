# CommerceLab Internship — Project Description

## Project name
**CommerceLab** — an educational e-commerce platform (storefront + admin + REST API + analytics).

## Project overview
CommerceLab is a working online shop written in Python/Django. Customers browse a catalog, add products to a
cart, check out with a shipping address and pay (payments are simulated). Staff manage the catalog, prices,
images, stock and orders in a Django admin that has a KPI dashboard. A REST API with OpenAPI documentation
exposes the same data to external clients, and read-only analytics endpoints plus deterministic data generators
provide realistic datasets for analysis.

The code base is a readable modular monolith, deliberately small enough that an intern can understand every
module in the first week, yet complete enough to host real feature work, QA automation and analytics.

## Business context and problem
The fictional retailer is **Sondermark Coffee Roasters**, a specialty-coffee store (filter coffee, espresso, decaf, drip bags & gifts, subscriptions, brewing equipment — see `catalog/demo_catalog.py`).

- a storefront that only shows products that are live and in stock, driven entirely by admin data;
- an operations team that can create, price, activate and retire products without developer help;
- orders that never oversell stock, with a traceable lifecycle from payment to delivery;
- reliable data for sales, marketing, inventory and customer analysis.

## Target users
- **Customers** — browse, search, filter, buy, follow orders.
- **Store managers / merchandisers** — catalog, prices, images, discounts, reviews, orders (admin).
- **Warehouse staff** — inventory, movements, suppliers, purchase orders (admin / API).
- **Analysts** — `/api/analytics/*` datasets and direct SQL over the relational schema.
- **Developers / integrators** — REST API + Swagger.

## Major functionality (implemented)
| Area | Features |
|---|---|
| Storefront | Home with live categories and new arrivals; catalog with search, brand / price / in-stock filters, four sort orders and pagination; category pages; product page with image gallery, variants, stock, VAT-inclusive price, approved reviews and related products; empty / not-found / out-of-stock states |
| Accounts | Registration (creates a customer profile and the *Customer* group), login / logout, profile editing, password change |
| Cart & checkout | Guest (session) or customer cart merged on login, quantity update / remove, discount codes, stock-aware validation, checkout form with shipping and contact details, guest checkout with tokenised order link, multi-warehouse allocation (split only when needed) |
| Orders | Card payment through a pluggable gateway (bundled simulated provider with deterministic test cards and an async webhook), automatic expiry of unpaid orders, confirmation e-mail, order history, order detail with timeline, per-warehouse lines and payments, customer self-cancellation before fulfilment |
| Admin | KPI dashboard (live products, reorder alerts, orders today, awaiting payment, revenue 7 d / month, pending reviews, recent orders); product management with variant / image (upload or URL) / price-history inlines, inline price & status edits, bulk activate / deactivate / discontinue / draft; categories & brands with product counts; review moderation; orders with items, payments, history and lifecycle actions (processing → packed → shipped → delivered, cancel); discounts; inventory, movements, suppliers, purchase orders, transfers, campaigns; users with profile inline |
| API | `/api/catalog/*` (products with images/variants/stock, categories, brands, reviews, wishlist, product images), `/api/sales/*` (carts with `add_item` / `remove_item` / `apply_discount` / `checkout`, orders with `pay` / `cancel` / `transition`, returns), `/api/operations/*`, `/api/analytics/*`; OpenAPI schema at `/api/schema/`, Swagger UI at `/api/docs/` |
| Data tooling | `seed_demo` (120 products with images, 2 variants for ~30 %, 3 warehouses, 8 suppliers, campaigns, reviews, demo users), `simulate_business` (sessions, product events, carts, orders and payments over N days with seasonality), `simulate_scenario` (stockout, price increase, bad supplier, failed campaign, logistics delay) |

## Architecture
Django 4.2 modular monolith with five business apps and one config package:

```
config/      settings, URLs, CommerceLabAdminSite (dashboard)
accounts/    CustomerProfile, AuditLog, registration & profile views
catalog/     Category, Brand, Product, ProductVariant, ProductImage, PriceHistory, Review, Wishlist
             storefront views, REST API, admin, price-history signal
sales/       Discount, Cart, CartItem, Order, OrderItem, OrderHistory, Payment, ReturnRequest
             services.py (cart, discounts, checkout, transitions, payment), views, API, admin
operations/  Warehouse, Inventory, InventoryMovement, Supplier, SupplierProduct, PurchaseOrder,
             Transfer, Campaign, ProductEvent; services.py (reserve / release / ship / receive)
analytics/   analytics endpoints + seed / simulation commands
templates/   base layout, storefront, cart / checkout / orders, auth, admin dashboard
static/css/  one hand-written stylesheet, no build step
tests/       pytest suite (24 tests)
```

Views (HTML and API) never mutate stock or order status directly — they call service functions that run in
database transactions with row locks. See `docs/architecture.md` and `docs/business-rules.md`.

### Backend
Python 3.12, Django 4.2, Django REST Framework 3.15, django-filter, drf-spectacular, WhiteNoise, Gunicorn, Celery (Redis broker in Docker; inline execution locally), Pillow.

### Frontend
Server-rendered Django templates (`templates/`) with a single CSS file (`static/css/storefront.css`), responsive
down to mobile widths, no JavaScript framework. The REST API is the boundary for any future SPA work.

### Database
PostgreSQL 16 in Docker Compose; SQLite for local development and tests. Schema is managed by Django
migrations (`*/migrations/`). Key relations: Product 1‑n ProductVariant 1‑n Inventory (per warehouse);
Cart 1‑n CartItem → ProductVariant; Order 1‑n OrderItem (snapshot) / OrderHistory / Payment;
OrderItem 1‑n ReturnRequest; ProductEvent and Campaign feed the funnel and marketing analytics.

### APIs
Session or Basic auth. Catalog endpoints are publicly readable (non-staff only see live products) and
staff-writable. Cart / order / return endpoints are owner-scoped; staff see everything. Analytics endpoints
require staff or the Analyst / Admin / Store Manager group. Pagination (25 per page), filtering, search and
ordering follow DRF conventions.

### Admin functionality
`/admin/` — Django admin with a custom `AdminSite` that injects dashboard KPIs into the index page. Demo
accounts: `admin` (superuser), `manager` (Store Manager: catalog + sales), `warehouse` (operations).

## Expected student workflow
1. Clone the repository, create the virtualenv, run migrations and `seed_demo`; optionally `simulate_business`.
2. Read `README.md`, `docs/architecture.md` and `docs/business-rules.md`; click through the storefront and admin
   with the demo accounts; open Swagger.
3. Pick a task from the internship task board, read its acceptance criteria, and create a branch
   `role/task-id-short-name`.
4. Implement in small commits with tests (`pytest`), keep migrations reversible, update docs.
5. Open a pull request with screenshots / evidence, request a review, address feedback, demo the result.
6. Submit the weekly internship report in the LMS.

## Development environment
- Python 3.12, `pip install -r requirements.txt` (or Docker Compose with PostgreSQL).
- `.env.example` documents every environment variable; never commit `.env` or secrets.
- `.github/workflows/ci.yml` runs `manage.py check`, `makemigrations --check` and `pytest` on every push.

## How to run the project
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py simulate_business --days 45 --customers 150 --seed 42
python manage.py runserver
```
Storefront: http://localhost:8000/ · Admin: http://localhost:8000/admin/ · Swagger: http://localhost:8000/api/docs/
All demo users share the password `CommerceLab123!`.

## How to run tests
```bash
pytest                       # whole suite
pytest tests/test_cart_flow.py -k discount   # one area
python manage.py check && python manage.py makemigrations --check
```

## Main technical challenges (what interns will learn)
- Keeping one source of truth for catalog visibility and stock across storefront, API and admin.
- Transactional stock reservation, multi-warehouse allocation, oversell prevention and append-only movement logs.
- Guest identity (session carts, password-less customers, tokenised order access) and cart merging on login.
- Payment gateway abstraction, idempotent webhooks and background jobs that keep stock honest (order expiry).
- Order lifecycle state machines with side effects (release on cancel, deduct on ship).
- Snapshotting prices / costs into orders so analytics stay correct after price changes.
- Owner-scoped API authorization and staff-only writes.
- Deterministic data generation for reproducible analytics and tests.
- Server-rendered UX states (loading is synchronous, but empty / error / out-of-stock / hidden states matter).

## Known limitations (honest scope)
No live payment provider is wired (the gateway abstraction, test cards and webhook are); reviews are created via
the API and moderated in the admin (no storefront review form — task FE-02); returns and purchase-order receiving
have models/APIs but no workflow (tasks PY-01 / PY-02); analytics are live aggregations (task DA-06).
