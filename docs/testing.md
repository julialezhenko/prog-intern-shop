# Testing and QA

Run the full suite with `pytest` (SQLite in-memory; ~10 s, 53 tests). The suite lives in `tests/` and shares fixtures from
`tests/conftest.py` (`catalog`: five products covering live / out-of-stock / draft / inactive; `customer`; `staff`).

| File | Covers |
|---|---|
| `test_inventory.py` | reserve / release / ship traceability, oversell prevention |
| `test_checkout.py` | service-level checkout → pay → ship workflow and stock effects |
| `test_api.py` | public read vs staff write on the catalog API, analyst role on analytics |
| `test_storefront.py` | home, search, filters, sort, pagination, category page, empty state, visibility rules (draft/inactive → 404, staff preview), public API hides non-live products |
| `test_cart_flow.py` | login redirect, full purchase journey (cart → checkout → declined + successful payment), validation, discount codes and usage counting, customer cancellation releasing stock, order privacy, registration |
| `test_admin_and_api.py` | admin dashboard and product pages, bulk activate/deactivate reflected in the storefront, price history signal, order lifecycle actions, API `add_item` validation, owner-scoped returns |
| `test_guest_split_payments.py` | guest checkout (password-less customer, token link, confirmation e-mail), guest-cart merge on login, multi-warehouse allocation and split shipments, Luhn/test cards, webhook settlement (signature, idempotency), API card payment, order expiry and cart cleanup jobs, `expire_unpaid_orders` command, image upload vs URL |

Other checks used in CI: `python manage.py check` and `python manage.py makemigrations --check`.

## Manual smoke test

1. `seed_demo` → open `/`, browse a category, search, filter by price/stock, open a product.
2. As a guest, add to cart, apply `WELCOME10`, check out with an e-mail, pay with `4000 0000 0000 0002` (declined) then `4242 4242 4242 4242`; log in as `customer` and confirm the guest cart merges.
3. Log in to `/admin/` as `admin`: dashboard KPIs, deactivate a product (disappears from the storefront), edit a
   price (row appears in Price history), move the order to PROCESSING → PACKED → SHIPPED (stock deducted).

## Load and concurrency notes

Recommended load profiles: 100 concurrent catalog readers, 500 API readers, 1,000 product requests.
Concurrency testing should target simultaneous reservation of the final units on PostgreSQL, since SQLite does
not reproduce row-lock behaviour.
