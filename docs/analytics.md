# Analytics

The API is split in two. Transactional endpoints run the shop. **Reporting datasets** are read-only,
require a reporting role, and expose the raw grain: rows to extract, join and aggregate yourself.

Roles that may read the datasets: `Analyst`, `Store Manager`, `Marketing Manager`, `Admin`, or any staff account.

## What is served, and what is not

Raw sums and counts are served. These are **not**, on purpose — deriving them is the exercise:

conversion and funnel rates · average order value · customer lifetime value · retention and cohort
matrices · ROAS, CPC, CPM, CAC · churn rate · margin percentage · RFM scores · period-over-period deltas.

`GET /api/analytics/dimensions/` returns the machine-readable version of this list.

## Fact tables

| Endpoint | Grain | Use it for |
|---|---|---|
| `/api/sales/orders/` | one order | revenue, discounts, attribution, geography, lifecycle timestamps |
| `/api/sales/order-items/` | one order line | products, categories, basket size, unit economics |
| `/api/sales/order-history/` | one status change | time in state, fulfilment speed, cancellation paths |
| `/api/sales/payments/` | one payment attempt | methods, declines, retries, fees, settlement lag |
| `/api/sales/refunds/` | one refund | full and partial refunds, reasons, net revenue |
| `/api/sales/returns/` | one return request | return reasons, resolutions, restocking |
| `/api/sales/shipments/` | one parcel | carrier performance, delivery times, failed deliveries |
| `/api/sales/subscriptions/` | one plan | churn, tenure, plan mix (`/{id}/events/` for the lifecycle) |
| `/api/sales/discount-redemptions/` | one coupon use | promo effectiveness, discount depth by channel |
| `/api/operations/events/` | one behavioural event | funnels, sessions, devices, search terms |
| `/api/operations/campaign-metrics/` | one campaign-day | spend, impressions, clicks, sessions |
| `/api/operations/inventory-snapshots/` | one stock row per week | stock value, cover, stockouts over time |
| `/api/operations/movements/` | one stock movement | receipts, reservations, shipments, damage |
| `/api/operations/purchase-orders/` | one PO | supplier lead time and reliability |
| `/api/catalog/price-history/` | one price change | price effects on volume and revenue |
| `/api/catalog/product-status-history/` | one visibility change | what was actually on sale in a period |
| `/api/catalog/reviews/` | one review | satisfaction by product, channel and country |

## Dimension tables

| Endpoint | Joins on |
|---|---|
| `/api/customers/profiles/` | `user_id` → `order.customer` — geography, market, segment, lifecycle stage, tier, acquisition |
| `/api/customers/segment-history/` | CRM attribute changes over time |
| `/api/catalog/products/` | `variant.product_id` — category, brand, tags, kind, roast, origin, cost |
| `/api/catalog/categories/` | `parent` gives the second level |
| `/api/catalog/tags/` | overlapping merchandising labels |
| `/api/operations/warehouses/` | fulfilment location, market |
| `/api/operations/suppliers/` | country, lead time, payment terms |
| `/api/operations/campaigns/` | channel group, objective, budget |

## Query conventions

Every dataset endpoint accepts the same shapes:

```
?status=PAID,SHIPPED            multi-value filter, comma separated
?created_at_after=2026-01-01    inclusive lower bound on a timestamp
?created_at_before=2026-06-30   inclusive upper bound
?ordering=-total                sort, prefix with - for descending
?search=ethiopia                free-text over the endpoint's text columns
?page=3&page_size=1000          pagination, up to 2000 rows per page
```

Each fact table exposes bounds on its own meaningful timestamps — orders take `created_at`, `paid_at`,
`shipped_at`, `delivered_at` and `cancelled_at`.

## Grouping endpoints

```
GET /api/analytics/timeseries/?grain=month&date_from=2025-01-01
GET /api/analytics/breakdown/?dimension=channel_group&secondary=device
GET /api/analytics/breakdown/?dimension=category        # switches the grain to order lines
GET /api/analytics/events/?dimension=device&grain=month
GET /api/analytics/payments/?dimension=failure_code
GET /api/analytics/fulfilment/?dimension=carrier&grain=month
GET /api/analytics/refunds/?dimension=reason
GET /api/analytics/media/?grain=month&by=campaign
GET /api/analytics/dimensions/
```

`grain` is `day`, `week` or `month`. `dimension` and `secondary` come from `/dimensions/`.
The original ten endpoints (`sales`, `revenue`, `orders`, `products`, `customers`, `inventory`,
`marketing`, `returns`, `suppliers`, `funnel`) are unchanged.

## Two traps worth knowing about

**Currency.** `order.total` is in `order.currency`. `SUM(total)` across the table is meaningless —
about 5% of orders are in SEK, DKK, GBP or CHF and a naive sum overstates revenue by roughly a factor of two.
Multiply by `fx_rate`, the rate captured at checkout.

**VAT.** Prices are consumer prices including VAT. `tax_amount` is the VAT *contained* in the total,
not added on top. Net revenue is `total - tax_amount - refunds`.

## Generating a dataset

Admin → Analytics → Test data batches → **Generate test users & orders**, or:

```bash
python manage.py generate_test_data --users 2500 --min-orders 0 --max-orders 15 \
    --date-from 2025-01-01 --date-to 2026-09-01 --seed 20260901 --dirty
```

Every generated row carries `is_test_data=true` and a `test_batch` id, so it can be filtered out
(`?is_test_data=false`) or removed in one action. See `docs/test-data-generator.md`.
