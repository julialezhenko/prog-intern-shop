# Business Rules

## Catalog
- A product is visible to customers (storefront and public API) only when `active = True` **and**
  `status = ACTIVE`. Staff can preview hidden products on the storefront and see them in the API.
- Each product has at least one variant; the variant price overrides the product price when set.
- Availability = `physical − reserved`, summed over active variants across all warehouses. Products with zero
  availability are shown as *Out of stock* and cannot be added to the cart.
- Every change of `sale_price` creates a `PriceHistory` row (signal), whatever the entry point.
- Exactly one product image is primary; the admin normalises this on save.

## Cart and discounts
- Registered customers have one active cart; anonymous visitors have a guest cart remembered in the session.
  Logging in merges the guest cart into the customer's cart (quantities are added, capped at available stock) and
  keeps the guest's discount code if the customer had none.
- Cart item quantity is positive and can never exceed the currently available quantity.
- Only purchasable variants (active variant of a visible product) can be added.
- A discount applies when it is active, inside its date window, the subtotal reaches `minimum_cart`, and
  `times_used < usage_limit`. `FIXED` discounts are capped at the subtotal; `PERCENT` discounts apply to the
  subtotal. VAT is computed on the undiscounted line amounts. Checkout increments `times_used`.

## Checkout and orders
- Checkout rejects an empty cart, an already checked-out cart, and lines whose product became unavailable.
- Guest checkout requires an e-mail address. A password-less customer record (`CustomerProfile.is_guest`) is
  created once per e-mail and reused; the order gets an `access_token` so the guest can open, pay and cancel it
  through the confirmation link without an account.
- Allocation: if one warehouse can fulfil every line, the lowest-id such warehouse ships the whole order;
  otherwise each line is shipped from the lowest-id warehouse holding enough stock, and a line is split across
  warehouses only when no single warehouse holds enough. Each order line records its warehouse; `Order.warehouse`
  is the warehouse carrying most lines. Stock is reserved per line (row-locked) and the order stores a snapshot
  of name, SKU, unit price, cost and tax rate.
- The order stores the shipping address and contact details given at checkout.
- Orders start in `PENDING_PAYMENT`. Payment goes through the configured gateway; only the last four card
  digits are stored. `SUCCEEDED` moves the order to `PAID`, `FAILED` keeps it payable, `PENDING` waits for the
  provider webhook (`confirm_payment` is idempotent).
- Orders left in `PENDING_PAYMENT` for `ORDER_PAYMENT_TIMEOUT_HOURS` are cancelled by the
  `expire_unpaid_orders` job, which releases their reservations. Paid orders trigger a confirmation e-mail.
- Lifecycle: `PENDING_PAYMENT → PAID → PROCESSING → PACKED → SHIPPED → DELIVERED → RETURNED → REFUNDED`.
  `CANCELLED` is allowed from `NEW`, `PENDING_PAYMENT`, `PAID` and `PROCESSING`.
- Cancellation releases reservations; shipment reduces physical and reserved stock. Every stock change is an
  append-only `InventoryMovement`. Physical stock can never fall below reserved stock.
- Customers can cancel their own orders online only while the status is `NEW`, `PENDING_PAYMENT` or `PAID`.
  Staff drive all other transitions from the admin or `POST /api/sales/orders/{id}/transition/`.
- Returns can be requested by the order owner for delivered orders, for at most the ordered quantity;
  refund amount, restock and damage flags are staff-only fields.

## Risk and access
- Fraud score is educational: orders above €500 / €1,000 add 10 / 30 points and failed payments in the last
  24 h add up to 30.
- Customers only ever see their own carts, orders and returns. Catalog/operations writes require staff.
  Analytics endpoints require staff or the *Analyst*, *Admin* or *Store Manager* group.

## Coffee storefront additions (August 2026)

* **Product kinds** — `COFFEE`, `EQUIPMENT`, `BUNDLE`, `SUBSCRIPTION`. The kind decides which product-page blocks are
  rendered (coffee profile / brew guide / origin story vs. specifications) and which FAQ set is shown.
* **Coffee profile** — origin, region, producer, variety, process, roast level, altitude, tasting notes (CSV) and brew
  methods (CSV of codes from `catalog/content.py`). Origin, roast and brew method drive the catalog facets.
* **Merchandising** — `featured` products fill the home page best-sellers row (coffee first); `compare_at_price` above
  the sale price shows a discount badge and the “On offer” facet. Category `position` orders the navigation.
* **VAT** — consumer prices are VAT-inclusive. `cart_totals()` extracts the VAT contained in the (discounted) total;
  `Order.tax_amount` is informational.
* **Reviews** — customers can submit one review per product from the product page; it is `PENDING` until approved in
  the admin and flagged `verified_purchase` when a paid order contains the product.
* **Newsletter** — `accounts.NewsletterSubscriber`, unique by e-mail, captured from the home page, footer and sold-out
  product pages (`source` records where).
