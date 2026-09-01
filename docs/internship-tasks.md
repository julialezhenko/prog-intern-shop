# CommerceLab Internship — Specialist Tasks

Every task extends or validates the implemented MVP. Tasks are grouped by specialisation; each intern takes at least one. The LMS twin of this document is `courses/commercelab-internship.en.yaml` in the LMS repository (one ASSIGNMENT lesson per task) and `courses/commercelab-internship.tasks.yaml` (Task Board seed).

## Specialist → task → main deliverable

| Specialist | Task | Main deliverable |
|---|---|---|
| Data Analytics | DA-01 – Executive sales & margin dashboard | Dashboard file or hosted link |
| Data Analytics | DA-02 – Marketing channel performance (CAC & ROAS) | Dashboard or notebook |
| Data Analytics | DA-03 – Customer RFM segmentation & retention cohorts | Notebook / SQL |
| Data Analytics | DA-04 – Product funnel analytics (view → cart → checkout → purchase) | Funnel dashboard or notebook |
| Data Analytics | DA-05 – Inventory health & replenishment recommendations | Dashboard / notebook |
| Data Analytics | DA-06 – Analytical dataset (star schema) & data-quality audit | SQL views |
| QA | QA-01 – End-to-end storefront regression suite (Playwright) | e2e project |
| QA | QA-02 – REST API contract & authorization test suite | API test project |
| QA | QA-03 – Admin panel acceptance & permissions testing | Test plan |
| QA | QA-04 – Order & inventory integrity under concurrency and load | Concurrency tests |
| Frontend | FE-01 – Catalog filtering UX: facets, chips and mobile filter drawer | Template/CSS/JS changes |
| Frontend | FE-02 – Product page: review form, wishlist button and accessible gallery | Templates/JS/CSS |
| Frontend | FE-03 – Mini-cart, AJAX add-to-cart and order tracking stepper | JS/CSS/templates |
| Python / Django / SQL | PY-01 – Returns & refunds workflow (services, admin, API) | Services |
| Python / Django / SQL | PY-02 – Purchase-order receiving & velocity-based reorder report | Services |

# Data Analytics tasks

Analytical work on the orders, customers, marketing, funnel and inventory data produced by seed_demo and simulate_business.

## DA-01 – Executive sales & margin dashboard
**Role:** Data Analytics · **Priority:** High

### Context
Orders snapshot unit price, unit cost and tax per line (sales_orderitem), so revenue and margin can be computed exactly as of the moment of sale. Management has no single trusted view of growth and profitability.

### Objective
Build a monthly executive dashboard (Power BI, Looker Studio, Metabase or a Python/Plotly notebook) that explains revenue, margin and order volume and reconciles to the source tables.

### Requirements
1. Generate data with `seed_demo --seed 42` and `simulate_business --days 365 --customers 2000 --seed 42`.
2. Define and document gross revenue, discount, VAT, net revenue, gross margin, margin %, AOV, orders and units; exclude CANCELLED orders and state how REFUNDED orders are treated.
3. Provide monthly and weekly trends with drill-downs by category, brand and acquisition source.
4. Add a reconciliation sheet proving your totals equal a direct SQL sum over sales_order / sales_orderitem and equal `/api/analytics/sales/`.
5. Write a one-page findings memo with at least three evidence-backed insights (e.g. seasonality, margin by category, discount impact).

### Technical requirements
- SQL against SQLite or PostgreSQL (tables: sales_order, sales_orderitem, catalog_product, catalog_category, accounts_customerprofile).
- Charts follow the one-metric-per-visual rule; every figure carries its definition.
- All SQL/notebooks committed under `analytics/notebooks/DA-01/` (new folder) with a README.

### Acceptance criteria
- Totals reconcile to source within €0.01 for every month.
- Dashboard filters (period, category, source) work and screenshots are attached.
- Metric definitions are written down and match what the SQL computes.
- Findings memo contains three quantified insights.

### Expected deliverables
- Dashboard file or hosted link
- SQL / notebook
- Reconciliation evidence
- Findings memo (Markdown or PDF)
- Pull request with the README

### Optional bonus
- Add a next-month revenue forecast with a baseline comparison.
- Flag months where margin % drops more than 3 pp and explain why.

## DA-02 – Marketing channel performance (CAC & ROAS)
**Role:** Data Analytics · **Priority:** Medium

### Context
Campaigns carry spend per source (operations_campaign), customers carry an acquisition source (accounts_customerprofile) and orders carry `source`. Nobody has compared channel quality.

### Objective
Evaluate google, meta, organic, email, referral and direct acquisition: spend, customers, orders, revenue, CAC, ROAS and repeat-purchase rate per channel, and recommend where to move budget.

### Requirements
1. Reproduce the inputs with seed 42; document exactly which simulation parameters you used.
2. Compute per-channel customers acquired, first orders, repeat orders, revenue, CAC = spend / new customers, ROAS = revenue / spend.
3. State your attribution assumptions (first touch via customer_profile.acquisition_source vs order.source) and quantify how the two differ.
4. Compare `/api/analytics/marketing/` with your own calculation and explain any discrepancy.
5. Deliver a recommendation with the expected effect of shifting 20 % of spend between two channels.

### Technical requirements
- SQL or pandas over operations_campaign, accounts_customerprofile, sales_order, operations_productevent.
- Handle channels without spend (organic/direct) explicitly — no division by zero, no fake ROAS.

### Acceptance criteria
- Metrics reproduce from the documented seed.
- Paid and organic denominators are explicit.
- Recommendation quantifies the trade-off and its assumptions.

### Expected deliverables
- Dashboard or notebook
- SQL
- Channel recommendation memo
- Pull request

### Optional bonus
- Add monthly acquisition cohorts with 90-day revenue per channel.

## DA-03 – Customer RFM segmentation & retention cohorts
**Role:** Data Analytics · **Priority:** Medium

### Context
Customer profiles and order history exist but there are no customer-level aggregates or segments.

### Objective
Build reusable RFM segments, monthly acquisition cohorts and a simple LTV estimate that marketing can act on.

### Requirements
1. Compute recency, frequency and monetary value per customer from non-cancelled orders; define scoring rules and segment names (e.g. Champions, At risk, Lost).
2. Produce acquisition cohorts (month of first order) with repeat-purchase retention by month 1, 2, 3.
3. Estimate 6-month LTV per segment and per acquisition source.
4. Export a `customer_segments.csv` (customer_id, segment, r, f, m, first_order_month, ltv_6m) and document how to refresh it.

### Technical requirements
- SQL window functions or pandas; all code in `analytics/notebooks/DA-03/`.
- Segmentation must be deterministic (same input → same segments).

### Acceptance criteria
- Every customer with at least one order maps to exactly one segment.
- Cohort denominators reconcile to the customer counts.
- At least two actionable segments are described with a suggested action.

### Expected deliverables
- Notebook / SQL
- Segment export
- Charts
- Findings memo
- Pull request

### Optional bonus
- Add a churn-probability model and evaluate it with a temporal split.

## DA-04 – Product funnel analytics (view → cart → checkout → purchase)
**Role:** Data Analytics · **Priority:** Medium

### Context
`operations_productevent` records SESSION_STARTED, PRODUCT_VIEWED, ADD_TO_CART, CHECKOUT_STARTED and PURCHASE_COMPLETED with session_id, product, source and device.

### Objective
Identify products, categories and sources with abnormal funnel leakage and propose the five highest-impact fixes.

### Requirements
1. Sessionise events and compute step conversion and abandonment per product, category and source.
2. Validate the instrumentation: find sessions with impossible orderings or missing steps and quantify them.
3. Rank five opportunities by potential extra orders (views × conversion gap).
4. Compare your results with `/api/analytics/funnel/` and describe what that endpoint is missing.

### Technical requirements
- SQL / pandas over operations_productevent joined to catalog_product and catalog_category.
- Stable denominators: a step counts once per session.

### Acceptance criteria
- Funnel steps use stable, documented denominators.
- Duplicate or out-of-order events are detected and handled.
- Five opportunities are ranked with numbers.

### Expected deliverables
- Funnel dashboard or notebook
- Validation SQL
- Prioritised findings
- Pull request

### Optional bonus
- Propose and prototype a better `/api/analytics/funnel/` response shape (per product / per source).

## DA-05 – Inventory health & replenishment recommendations
**Role:** Data Analytics · **Priority:** Medium

### Context
Inventory rows hold physical / reserved / incoming per variant and warehouse; movements are append-only; products define reorder points and preferred quantities; supplier products carry lead times.

### Objective
Recommend replenishment actions per SKU and warehouse using sales velocity, available stock, reorder points and supplier lead time.

### Requirements
1. Compute daily sales velocity (last 30 / 90 days) per variant from order items of shipped or paid orders.
2. Compute days of cover = available / velocity, flag stockouts and near-stockouts, and compare with `/api/operations/reorder/`.
3. Produce a recommendation table (variant, warehouse, available, velocity, days_of_cover, lead_days, recommended_qty, urgency).
4. Investigate whether one warehouse (e.g. Valencia) is structurally worse and quantify it.
5. Run `simulate_scenario stockout` and show that your report detects it.

### Technical requirements
- SQL over operations_inventory, operations_inventorymovement, sales_orderitem, operations_supplierproduct, catalog_product.

### Acceptance criteria
- Available = physical − reserved everywhere.
- Recommendations are reproducible from the documented seed.
- Limitations (no demand forecast, single warehouse per order) are explicit.

### Expected deliverables
- Dashboard / notebook
- SQL
- Recommendation CSV
- Assumptions note
- Pull request

### Optional bonus
- Add lead-time-based safety stock and ABC classification.

## DA-06 – Analytical dataset (star schema) & data-quality audit
**Role:** Data Analytics · **Priority:** High

### Context
`docs/analytics.md` describes fact and dimension datasets (fact_orders, fact_order_items, fact_product_events, dims) that do not physically exist; analysts query raw tables each time.

### Objective
Materialise a documented analytical dataset as SQL views (or CSV exports) and audit the operational data for quality issues.

### Requirements
1. Create `fact_orders`, `fact_order_items`, `fact_product_events`, `dim_customer`, `dim_product`, `dim_category`, `dim_warehouse`, `dim_campaign` as SQL views in `analytics/sql/` plus a management command or script that (re)creates them on SQLite and PostgreSQL.
2. Write a data dictionary (column, type, source, definition, grain).
3. Run a data-quality audit: orphan rows, negative or zero prices, orders whose total ≠ subtotal − discount + tax, products without variants or images, duplicate SKUs, sessions without SESSION_STARTED; report counts and sample rows.
4. Where the audit finds real defects in the generators or services, open issues with reproduction steps.

### Technical requirements
- Plain SQL compatible with both SQLite and PostgreSQL (document any divergence).
- Optional: Python script using Django's connection to create the views.

### Acceptance criteria
- Views create cleanly on a fresh `seed_demo` + `simulate_business` database.
- Data dictionary covers every column.
- Audit report lists each check, its SQL and its result.

### Expected deliverables
- SQL views
- Creation script
- Data dictionary
- Audit report
- Pull request

### Optional bonus
- Add dbt-style tests (row counts, uniqueness, referential integrity) runnable from pytest.

# QA tasks

Test automation, regression design and integrity testing across the storefront, admin and REST API.

## QA-01 – End-to-end storefront regression suite (Playwright)
**Role:** QA · **Priority:** High

### Context
The storefront now covers registration, login, catalog search/filters, product page, cart, discount codes, checkout, simulated payment, order history and cancellation — but only Django test-client tests exist, no browser automation.

### Objective
Create a maintainable Playwright (Python or TypeScript) suite that protects the critical customer journey.

### Requirements
1. Cover at least ten independent scenarios: register, login/logout, search, category + price + in-stock filters, sorting, pagination, product page out-of-stock state, add/update/remove cart items, invalid discount, valid WELCOME10, checkout validation errors, declined then successful payment, order appears in history, cancel unpaid order.
2. Use the seed data (`seed_demo --seed 42`) and resilient selectors (roles/labels, not CSS classes).
3. Run headless in CI via a new GitHub Actions job; capture traces and screenshots on failure.
4. Write a short test plan mapping scenarios to business rules in `docs/business-rules.md`.

### Technical requirements
- Playwright; page-object or fixture pattern; tests under `e2e/`.
- Database reset strategy documented (fresh SQLite per run is acceptable).

### Acceptance criteria
- Suite passes twice in a row on a clean checkout.
- A failing step is identifiable from the report without re-running.
- CI job is green and documented in README.

### Expected deliverables
- e2e project
- Test plan
- CI workflow change
- README section
- Pull request

### Optional bonus
- Mobile viewport run (375 px) and an axe-core accessibility scan of five pages.

## QA-02 – REST API contract & authorization test suite
**Role:** QA · **Priority:** High

### Context
DRF exposes catalog, sales, operations and analytics endpoints with an OpenAPI schema. Authorization rules differ per role (anonymous, customer, staff, analyst) and per object (owner scoping).

### Objective
Build a black-box API regression suite that proves the contract and the permission matrix.

### Requirements
1. Produce a permission matrix (endpoint × role × expected status) for every router in `/api/schema/` and automate it.
2. Test pagination, filters (`category`, `min_price`, `availability`), search and ordering on `/api/catalog/products/`; non-staff must never receive DRAFT or inactive products.
3. Test cart actions (`add_item` validation, stock limits, `apply_discount`, `checkout` with shipping) and order actions (`pay` twice, `cancel` after shipment, staff-only `transition`).
4. Prove object isolation: customer A cannot read or mutate customer B's carts, orders or returns.
5. Validate responses against the OpenAPI schema (e.g. schemathesis or openapi-core).

### Technical requirements
- pytest + requests (or Postman/Newman) against a running server; isolated test users created through the admin or fixtures.
- Machine-readable report (JUnit XML) produced in CI.

### Acceptance criteria
- At least 40 assertions across all four API areas.
- Every permission-matrix cell is executed.
- CI command documented; report attached to the PR.

### Expected deliverables
- API test project
- Permission matrix
- Report
- README
- Pull request

### Optional bonus
- Schema fuzzing with schemathesis and a list of any 5xx found.

## QA-03 – Admin panel acceptance & permissions testing
**Role:** QA · **Priority:** Medium

### Context
The Django admin is the operations team's only tool: product CRUD with inlines, bulk actions, price edits, review moderation, order lifecycle actions and role-based access for `admin`, `manager` and `warehouse`.

### Objective
Design and automate acceptance tests for the admin, including negative paths, and report defects.

### Requirements
1. Write a test plan covering product create/edit/archive, bulk activate/deactivate, inline price edit → PriceHistory row, primary-image normalisation, category/brand management, review approve/reject, order actions (legal and illegal transitions), discount limits.
2. Verify role boundaries: `manager` cannot see operations models, `warehouse` cannot see orders, `analyst` cannot log in to the admin.
3. Automate at least 15 checks with Django's test client or Playwright; the rest are manual with evidence.
4. File defects with severity, steps, expected/actual and screenshots.

### Technical requirements
- pytest-django tests under `tests/admin/` or Playwright under `e2e/admin/`.
- Use `seed_demo` accounts.

### Acceptance criteria
- Plan maps every admin feature listed in README to at least one test.
- Role boundaries are proven by automated tests.
- Defect reports are reproducible.

### Expected deliverables
- Test plan
- Automated tests
- Defect reports
- Pull request

### Optional bonus
- Regression checklist template reusable for future releases.

## QA-04 – Order & inventory integrity under concurrency and load
**Role:** QA · **Priority:** Medium

### Context
Checkout reserves stock with row locks; cancellation releases it; shipment deducts it. SQLite cannot reproduce lock contention, so these invariants are unverified on PostgreSQL.

### Objective
Prove that stock never goes negative and totals stay consistent under concurrent checkouts, and establish a performance baseline for the catalog.

### Requirements
1. Run the stack on PostgreSQL (docker compose) and write a concurrency test where N customers check out the last units of the same variant simultaneously; assert exactly the available quantity is sold and the rest receive a clean 400.
2. Cover cancel/ship sequences and discount usage limits under parallel requests.
3. Build a k6 or Locust scenario: 100 concurrent catalog readers, 50 product-page readers, 20 cart writers; record p95 latency and error rate.
4. Verify every stock change has a matching InventoryMovement and that order history rows exist for each transition.

### Technical requirements
- pytest with threads/processes or a Locust script; PostgreSQL required.
- Results recorded with environment details.

### Acceptance criteria
- No oversell under concurrency; evidence attached.
- Baseline thresholds documented.
- Any defect has a reproduction and severity.

### Expected deliverables
- Concurrency tests
- Load script
- Results report
- Pull request

### Optional bonus
- Profile the slowest query and propose an index with before/after timings.

# Frontend tasks

Storefront UX work inside the existing Django template + CSS stack, using the REST API where interactivity is needed.

## FE-01 – Catalog filtering UX: facets, chips and mobile filter drawer
**Role:** Frontend · **Priority:** High

### Context
The catalog page (`templates/catalog/product_list.html`, `catalog/storefront_views.py`) supports search, brand, price, in-stock and sorting through a plain form, without facet counts or a mobile-friendly layout.

### Objective
Make filtering fast and understandable on desktop and mobile without leaving the Django template stack.

### Requirements
1. Show counts next to each brand/category facet (computed in the view; no N+1 queries — prove it with `django-debug-toolbar` or `assertNumQueries`).
2. Render active-filter chips with one-click removal; keep all state in the URL so pages are shareable.
3. Add a price range control (two inputs or a slider) with validation messages.
4. On screens < 860 px, move filters into an accessible off-canvas drawer (focus trap, Escape closes, aria-expanded).
5. Keep the page fully usable without JavaScript.

### Technical requirements
- Django templates + CSS + small vanilla JS module in `static/js/`; no framework.
- Add view tests for facet counts and chips.

### Acceptance criteria
- Every control changes results and is reflected in the URL.
- Query count on the catalog page does not grow with the number of products.
- Keyboard-only navigation works; Lighthouse accessibility ≥ 90 on the catalog page.

### Expected deliverables
- Template/CSS/JS changes
- View tests
- Before/after screenshots (desktop + mobile)
- Pull request

### Optional bonus
- Instant search suggestions using `/api/catalog/products/?search=`.

## FE-02 – Product page: review form, wishlist button and accessible gallery
**Role:** Frontend · **Priority:** Medium

### Context
Reviews and wishlists exist only through the API (`/api/catalog/reviews/`, `/api/catalog/wishlist/`). The product page has a basic click-to-swap gallery.

### Objective
Let logged-in customers review products and save them to a wishlist from the product page, and make the gallery accessible.

### Requirements
1. Add a review form (rating 1–5 with a star widget, comment) for authenticated users; submit via fetch to the existing API with CSRF handling, show 'pending moderation' state, handle the unique-review error gracefully.
2. Add a wishlist toggle button that uses the wishlist API and reflects state on reload; add a `/wishlist/` page listing saved products.
3. Rebuild the gallery as a keyboard-navigable component (arrow keys, thumbnails as buttons, alt text, focus styles) with a lightbox/zoom.
4. Progressive enhancement: the form must also work as a normal POST to a new Django view if JS is disabled.

### Technical requirements
- Vanilla JS modules in `static/js/`, Django views/templates for the no-JS path, tests for the views.
- Reuse existing serializers/permissions — do not duplicate business rules.

### Acceptance criteria
- A customer can submit one review, see it pending, and see it on the page after admin approval.
- Wishlist state persists and the wishlist page lists saved products.
- Gallery passes keyboard navigation and screen-reader labelling checks.

### Expected deliverables
- Templates/JS/CSS
- Django views + tests
- Screenshots
- Pull request

### Optional bonus
- Average-rating histogram and 'verified purchase' filter.

## FE-03 – Mini-cart, AJAX add-to-cart and order tracking stepper
**Role:** Frontend · **Priority:** Medium

### Context
Adding to cart performs a full-page POST/redirect; order status is shown as a badge and a text timeline.

### Objective
Improve the shopping and post-purchase experience with lightweight interactivity built on the existing API.

### Requirements
1. Implement AJAX add-to-cart on product cards and the product page using `/api/sales/carts/{id}/add_item/`, with optimistic badge update, error toast for stock errors and fallback to the normal form without JS.
2. Add a mini-cart drawer (items, quantities, totals, links) reachable from the header; accessible dialog semantics.
3. Replace the order status badge with a visual stepper (Pending payment → Paid → Processing → Packed → Shipped → Delivered) that handles CANCELLED/RETURNED branches.
4. Add a return-request form on delivered orders posting to `/api/sales/returns/` (quantity ≤ ordered, reason select) with validation feedback.

### Technical requirements
- Vanilla JS + CSS; Django templates; reuse `cart_totals` for server-rendered totals.
- Tests for the template rendering of the stepper in each status.

### Acceptance criteria
- Add-to-cart works with and without JS.
- Mini-cart totals equal the cart page totals.
- Stepper renders correctly for every Order.Status value.
- Return form enforces the quantity rule and shows API errors.

### Expected deliverables
- JS/CSS/templates
- Tests
- Screen recording or screenshots
- Pull request

### Optional bonus
- Persist the last-used shipping address in the profile and prefill checkout from it.

# Python / Django / SQL tasks

Backend features that extend the services, admin, API and SQL layer.

## PY-01 – Returns & refunds workflow (services, admin, API)
**Role:** Python / Django / SQL · **Priority:** High

### Context
`ReturnRequest` has statuses REQUESTED → APPROVED/REJECTED → RECEIVED → REFUNDED and restock/damaged flags, but nothing moves a return through that lifecycle or touches stock or payments.

### Objective
Implement the full returns workflow following the existing service-function pattern.

### Requirements
1. Add `sales/services.py` functions: `approve_return`, `reject_return`, `receive_return` (creates a RETURN movement and restocks or marks damaged), `refund_return` (updates Payment.refunded_amount, Payment status, and moves the Order to RETURNED/REFUNDED when fully refunded) — all transactional, with explicit transition rules and `OrderHistory` rows.
2. Expose staff-only API actions on `/api/sales/returns/{id}/` (`approve`, `reject`, `receive`, `refund`) with serializers and proper status codes.
3. Add admin actions and a read-only timeline inline on the return.
4. Show return status on the customer's order page.
5. Write tests for every legal and illegal transition, restock vs damaged, partial and full refunds.

### Technical requirements
- Follow `transition()`/`reserve()` conventions: `@transaction.atomic`, `select_for_update`, `ValidationError` for rule violations.
- Migration only if you add fields (e.g. `processed_at`, `processed_by`).

### Acceptance criteria
- Stock and movements are consistent after receive/restock.
- Refund amounts never exceed the payment.
- Customers cannot call staff actions; all paths covered by tests.

### Expected deliverables
- Services
- API + serializers
- Admin changes
- Templates
- Tests
- Docs update
- Pull request

### Optional bonus
- Email notification stub via Django's console email backend.

## PY-02 – Purchase-order receiving & velocity-based reorder report
**Role:** Python / Django / SQL · **Priority:** Medium

### Context
Purchase orders and items exist with `received_quantity`, and `operations.services.receive()` can book stock, but there is no receiving workflow and `/api/operations/reorder/` uses a static threshold.

### Objective
Let warehouse staff receive purchase orders (partially or fully) and replace the static reorder list with a velocity-based recommendation backed by SQL.

### Requirements
1. Implement `receive_purchase_order(po, lines)` in `operations/services.py`: validates quantities, updates `received_quantity`, creates RECEIPT movements, decrements `incoming`, sets PARTIALLY_RECEIVED / RECEIVED, and records who received it.
2. Expose it as a staff-only API action and as an admin action/form on PurchaseOrder.
3. Rewrite `ReorderViewSet` to compute 30-day sales velocity per variant/warehouse with a single annotated query (or a SQL view), days of cover, supplier lead time, and a recommended quantity; support filters by warehouse and urgency and pagination.
4. Add indexes where the query plan shows sequential scans; include EXPLAIN output for PostgreSQL.
5. Tests for receiving (partial, over-receipt rejected, idempotency) and for the reorder calculation on a fixture with known velocities.

### Technical requirements
- Django ORM annotations/Subquery or raw SQL view; migrations for indexes/new fields.
- Keep `/api/operations/reorder/` backward compatible (same keys, new optional keys).

### Acceptance criteria
- Receiving never double-books stock on retry.
- Reorder endpoint returns correct numbers for the fixture and completes in < 300 ms at demo scale on PostgreSQL.
- Documentation of the formula in `docs/business-rules.md`.

### Expected deliverables
- Services
- API
- Admin
- Migrations
- Tests
- Query-plan evidence
- Pull request

### Optional bonus
- Management command that drafts purchase orders for every urgent recommendation.

## Shared team responsibilities

- Keep work linked to the Task Board card; use focused branches and pull requests.
- Review across disciplines when API, metric or workflow contracts change.
- Maintain tests, seed reproducibility, migrations and documentation.
- Demo integrated outcomes, record decisions and close with a retrospective.
