# Test data generator

An admin-only tool that fills the database with synthetic customers and their commercial history,
for analytics, SQL, BI and API exercises and for testing filtering, pagination and reporting at scale.

It is development and demo tooling, not business functionality.

## Using it

**Admin → Analytics → Test data batches → Generate test users & orders** (superusers only).

| Setting | Meaning |
|---|---|
| Number of users | 1 – 20 000. Quick-pick buttons for 10 / 100 / 500 / 1 000 / 5 000, or type any number. |
| Minimum / maximum orders per user | Bounds on the per-customer draw. `0` as a minimum leaves part of the base without orders. |
| Period from / to | Registrations and orders are spread across this window. |
| Random seed | Same seed plus same settings reproduces the same dataset. Leave empty for a random one. |
| Include realistic data quality issues | Missing cities, absent UTM tags, inconsistent capitalisation, near-duplicate customers, double-submitted orders. |
| Generate behavioural events | Sessions, views, add-to-cart and checkout steps. Needed for funnel work. |
| Generate subscriptions | Recurring plans with renewals, pauses and cancellations. |
| Batch label | Free text, shown in the batch list. |

The run happens in the background; the progress page polls and then shows a summary of what was written.

From the command line:

```bash
python manage.py generate_test_data --users 2500 --min-orders 0 --max-orders 15 \
    --date-from 2025-01-01 --date-to 2026-09-01 --seed 20260901 --dirty --label "Cohort exercise"
python manage.py generate_test_data --delete            # every batch
python manage.py generate_test_data --delete --batch 4  # one batch
```

## What gets written

Per run, roughly proportional to the number of users:

customers and CRM profiles · CRM attribute history · orders · order lines · order status history ·
payments including declines and retries · refunds, full and partial · return requests and their history ·
shipments · coupon redemptions · reviews · subscriptions and their events · behavioural events ·
campaign day metrics.

2 500 users over 20 months with a maximum of 15 orders each produces about 175 000 rows in around
20 seconds on SQLite.

## How generated data is identified

Every synthetic row carries `is_test_data = True` and a `test_batch` foreign key to the
`analytics.TestDataBatch` row that produced it. Deletion is driven by those two columns only — never by
name patterns, e-mail domains or date ranges — so real customers and real orders cannot be caught by it.

Generated accounts are additionally recognisable: addresses use the reserved `example.com` domain
(RFC 2606, undeliverable) and every account has an unusable password, so none of them can be logged into.

Reports can exclude them with `?is_test_data=false` on any dataset endpoint.

## Why it cannot cause side effects

The generator never calls `sales.services`. Rows are assembled in memory and written with `bulk_create`,
which does not fire `post_save`. Nothing that the shop normally does on save can therefore run:

* no order confirmation e-mail and no Celery task — `transition()` is never called, so
  `send_order_confirmation` is never scheduled;
* no payment gateway call — `charge()` is never called; `Payment` rows are written directly;
* no stock movement — `reserve()` / `ship()` are never called, so today's inventory is untouched;
* no webhook or CRM integration, because none of them are reached.

`tests/test_test_data_generator.py` asserts each of these.

## Deleting it

**Admin → Test data batches → Delete generated test data**, or the batch-specific link. Both show the
row counts first and delete only after confirmation. Deletion runs in one transaction and walks the
relations children-first, because several of them are `PROTECT`ed.

## Architecture

`analytics/generation/`

| Module | Responsibility |
|---|---|
| `config.py` | `GeneratorConfig` — the settings, validated and normalised |
| `reference.py` | Fixed vocabulary: channels, countries, devices, carriers, payment methods, demand shape |
| `distributions.py` | `Picker` and the weighted, seasonal and long-tailed helpers |
| `users.py` | `UserBuilder` — accounts, CRM profiles, attribute history |
| `orders.py` | `OrderBuilder` — orders, lines, payments, refunds, returns, shipments, events, subscriptions |
| `persistence.py` | Chunked `bulk_insert`, and restoring `auto_now_add` columns to their historic values |
| `service.py` | `TestDataGeneratorService` — orchestration, progress, batch bookkeeping |
| `cleanup.py` | `count_test_data` / `delete_test_data` |

The admin layer (`analytics/admin.py`, `analytics/forms.py`) only handles permissions, the form and
progress reporting.

## Distributions

Nothing is drawn uniformly. Order counts per customer follow a long tail, so most customers buy once or
twice and a small group buys often. Product popularity decays with rank. Demand follows month, weekday
and a compounding growth trend, with a handful of spike days. Order status is drawn from a realistic mix
(roughly 70 % delivered, 11 % cancelled, 10 % returned or refunded, the rest still in flight), adjusted by
how long ago the order was placed.

Several patterns are deliberately embedded and are only visible through analysis; they are not named in
any field or comment. Regenerating with the same seed reproduces them exactly.
