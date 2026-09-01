"""Synthetic commercial activity: orders and everything that hangs off them.

Nothing here calls ``sales.services``. Orders are assembled as plain rows and written with
``bulk_create``, so no confirmation e-mail, payment-gateway call or stock reservation can fire.
"""
import datetime as dt
import uuid
from decimal import Decimal

from django.utils import timezone

from catalog.models import Review
from operations.models import Campaign, CampaignDailyMetric, ProductEvent, Warehouse
from sales.models import (Discount, DiscountRedemption, Order, OrderHistory, OrderItem, Payment, Refund,
                          ReturnHistory, ReturnRequest, Shipment, Subscription, SubscriptionEvent)

from . import reference as ref
from .distributions import (carrier_health, demand_factor, equipment_appetite, money, mobile_share,
                            paid_social_efficiency, seasonal_product_boost)
from .persistence import bulk_insert

FREE_SHIPPING_EUR = Decimal("35")
# Statuses an order can still be sitting in, by how many days have passed since it was placed.
IN_FLIGHT = [(1, ["PENDING_PAYMENT", "PAID"]), (3, ["PAID", "PROCESSING", "PACKED"]), (8, ["SHIPPED"])]
TERMINAL = [("DELIVERED", 0.755), ("CANCELLED", 0.112), ("REFUNDED", 0.052),
            ("RETURNED", 0.048), ("PENDING_PAYMENT", 0.033)]


class OrderBuilder:
    def __init__(self, config, picker, batch):
        self.config = config
        self.pick = picker
        self.batch = batch
        self.tz = timezone.get_current_timezone()
        self.now = timezone.now()
        self.warehouses = list(Warehouse.objects.filter(active=True).order_by("id"))
        self.products = self._load_products()
        self.discounts = list(Discount.objects.filter(active=True))
        self.campaigns = {c.utm_campaign or c.name: c for c in Campaign.objects.all()}
        # One review per customer and product is a database constraint; repeat buyers would break it.
        self._reviewed = set(Review.objects.values_list("customer_id", "product_id"))
        self.counts = {}

    # ------------------------------------------------------------------ catalogue
    def _load_products(self):
        """Products with their sellable variants, plus a popularity weight with a long tail."""
        from catalog.models import Product

        rows = []
        products = list(Product.objects.storefront().select_related("category")
                        .prefetch_related("variants").order_by("id"))
        for rank, product in enumerate(products):
            variants = [v for v in product.variants.all() if v.active]
            if not variants:
                continue
            weight = 1 / (rank + 1) ** 0.55
            if product.featured:
                weight *= 2.4
            rows.append((product, variants, weight))
        return rows

    def _pick_product(self, day):
        """Popularity, seasonality and the slow rise of brewing equipment decide what sells."""
        gear = equipment_appetite(day, self.config.date_from, self.config.date_to)
        weights = []
        for product, _variants, base in self.products:
            weight = base * seasonal_product_boost(product, day)
            if product.kind == "EQUIPMENT":
                weight *= gear
            weights.append(weight)
        return self.pick.rng.choices(self.products, weights=weights, k=1)[0]

    # ------------------------------------------------------------------ entry point
    def build(self, customers, progress=None):
        orders, items, history, payments, refunds, returns, return_history = [], [], [], [], [], [], []
        shipments, redemptions, events, reviews = [], [], [], []
        subscriptions, subscription_events = [], []

        for position, customer in enumerate(customers, start=1):
            for order_day in self._order_days(customer):
                self._compose(customer, order_day, orders, items, history, payments, refunds,
                              returns, return_history, shipments, redemptions, events, reviews)
            self._browse_without_buying(customer, events)
            if self.config.generate_subscriptions:
                self._subscribe(customer, subscriptions, subscription_events)
            if progress and position % 250 == 0:
                progress(position, len(orders))

        self._persist(orders, items, history, payments, refunds, returns, return_history,
                      shipments, redemptions, events, reviews, subscriptions, subscription_events)
        if self.config.generate_events:
            self._campaign_metrics(events)
        return self.counts

    # ------------------------------------------------------------------ how often a customer buys
    def _order_days(self, customer):
        """A long-tailed order count, then dates that respect seasonality and the registration date."""
        config, pick = self.config, self.pick
        low, high = config.min_orders_per_user, config.max_orders_per_user
        if high == 0:
            return []
        # Most customers land near the minimum; a small group of loyalists reaches the maximum.
        count = pick.power_law(low, high, exponent=2.8 / max(customer.repeat_factor, 0.3))
        count = max(low, min(high, count))
        propensity = customer.order_propensity
        if propensity < 1 and count > low and pick.chance(1 - propensity):
            count -= 1
        if count <= 0:
            return []

        first_possible = max(customer.registered_at.date(), config.date_from)
        if first_possible > config.date_to:
            return []
        span = [first_possible + dt.timedelta(days=i) for i in range((config.date_to - first_possible).days + 1)]
        weights = [demand_factor(day, config.date_from) for day in span]
        if customer.channel[0] == "Paid Social":
            weights = [w * paid_social_efficiency(d, config.date_from, config.date_to)
                       for w, d in zip(weights, span)]
        days = pick.rng.choices(span, weights=weights, k=count)
        return sorted(days)

    # ------------------------------------------------------------------ one order
    def _compose(self, customer, day, orders, items, history, payments, refunds, returns,
                 return_history, shipments, redemptions, events, reviews):
        pick, dirty = self.pick, self.config.include_dirty_data
        placed_at = pick.datetime_in_day(day, self.tz)
        if placed_at < customer.registered_at:
            placed_at = customer.registered_at + dt.timedelta(minutes=pick.integer(3, 600))
        if placed_at > self.now:
            placed_at = self.now - dt.timedelta(minutes=pick.integer(5, 240))

        currency = customer.currency
        fx = Decimal(str(round(pick.jitter(ref.FX_TO_EUR[currency], 0.035), 6)))
        country = customer.country
        session_id = uuid.uuid4().hex

        # --- lines ---------------------------------------------------------------
        # basket_factor carries the segment, channel and country differences into the basket.
        appetite = customer.basket_factor * pick.lognormal_factor(0.5)
        line_count = min(8, max(1, int(round(1.15 * appetite ** 0.45))))
        wholesale = customer.segment == "WHOLESALE" or pick.chance(0.004)
        chosen, seen = [], set()
        for _ in range(line_count):
            product, variants, _w = self._pick_product(day)
            variant = pick.choice(variants)
            if variant.pk in seen:
                continue
            seen.add(variant.pk)
            if wholesale:
                quantity = pick.integer(25, 110)
            else:
                quantity = pick.weighted([(1, 0.62), (2, 0.22), (3, 0.09), (4, 0.04), (6, 0.02), (12, 0.01)])
                if appetite > 1.6 and pick.chance(0.35):
                    quantity += 1
            chosen.append((product, variant, quantity))
        if not chosen:
            return

        subtotal = Decimal("0")
        line_rows = []
        for position, (product, variant, quantity) in enumerate(chosen):
            unit_price = money(Decimal(str(variant.effective_price)) / fx)
            unit_cost = money(Decimal(str(product.purchase_cost)) / fx)
            subtotal += unit_price * quantity
            line_rows.append((position, product, variant, quantity, unit_price, unit_cost))

        # --- coupon --------------------------------------------------------------
        discount_row, discount_amount, coupon = None, Decimal("0"), ""
        if self.discounts and pick.chance(0.27 if customer.channel[0] != "Email" else 0.58):
            discount_row = pick.choice(self.discounts)
            if discount_row.kind == "PERCENT":
                discount_amount = money(subtotal * discount_row.value / 100)
            elif discount_row.kind == "FIXED":
                discount_amount = money(min(Decimal(str(discount_row.value)) / fx, subtotal))
            coupon = discount_row.code
        discount_amount = min(discount_amount, subtotal)

        # --- shipping and VAT ----------------------------------------------------
        net = subtotal - discount_amount
        carrier = self._carrier(country[2], day)
        shipping = Decimal("0") if net * fx >= FREE_SHIPPING_EUR else money(Decimal(str(carrier[4])) / fx)
        total = net + shipping
        tax_amount = Decimal("0")
        for _pos, product, _variant, quantity, unit_price, _cost in line_rows:
            gross = unit_price * quantity
            if subtotal:
                gross -= discount_amount * gross / subtotal
            rate = Decimal(str(product.tax_rate)) / 100
            tax_amount += gross - gross / (1 + rate)
        tax_amount += shipping - shipping / Decimal("1.21")

        # --- status and its timeline --------------------------------------------
        status = self._status(day, country, customer.refund_factor)
        stamps = self._timeline(placed_at, status, country, carrier, day)
        warehouse = self._warehouse(country[2])
        channel_group, utm_source, utm_medium = customer.channel[0], customer.channel[1], customer.channel[2]
        utm_campaign = customer.profile.acquisition_campaign
        device = customer.device
        if pick.chance(0.22):  # people switch devices between visits
            share = mobile_share(day, self.config.date_from, self.config.date_to)
            device = pick.weighted([("mobile", share), ("tablet", ref.TABLET_SHARE),
                                    ("desktop", max(0.05, 1 - share - ref.TABLET_SHARE))])
        device_row = next(d for d in ref.DEVICES if d[0] == device)

        city = customer.profile.city or pick.choice(ref.CITIES[country[1]])
        order = Order(
            customer=customer.user, status=status, warehouse=warehouse,
            subtotal=money(subtotal), discount_amount=money(discount_amount), tax_amount=money(tax_amount),
            total=money(total), shipping_amount=money(shipping),
            currency=currency, fx_rate=fx,
            fraud_score=pick.weighted([(0, 0.70), (10, 0.16), (30, 0.09), (60, 0.04), (90, 0.01)]),
            source=utm_source, channel=("MOBILE_WEB" if device == "mobile" else "WEB"),
            channel_group=channel_group, utm_source=utm_source, utm_medium=utm_medium,
            utm_campaign=utm_campaign, utm_content=pick.choice(["", "", "hero", "carousel_a", "story_2"]),
            referrer_domain=customer.channel[8], landing_page=customer.channel[9],
            device=device, browser=pick.choice(device_row[1]), os=pick.choice(device_row[2]),
            session_id=session_id, campaign=self.campaigns.get(utm_campaign),
            discount=discount_row, coupon_code=coupon,
            market=country[2], shipping_country_code=country[1], shipping_region=customer.profile.region,
            shipping_name=f"{customer.user.first_name} {customer.user.last_name}",
            shipping_city=city, shipping_country=country[0],
            shipping_postal_code=customer.profile.postal_code,
            contact_email=customer.user.email,
            is_gift=pick.chance(0.22 if day.month in (11, 12) else 0.06),
            created_at=placed_at, **stamps,
        )
        if dirty:
            # Optional fields that a real shop simply fails to capture some of the time.
            if pick.chance(0.13):
                order.utm_campaign = ""
            if pick.chance(0.08):
                order.device, order.browser, order.os = "", "", ""
            if pick.chance(0.07):
                order.shipping_region = ""
            if pick.chance(0.04):
                order.shipping_city = order.shipping_city.upper()
        if order.status == "CANCELLED":
            order.cancel_reason = pick.weighted(ref.CANCEL_REASONS)
        order.is_test_data, order.test_batch = True, self.batch
        orders.append(order)

        for position, product, variant, quantity, unit_price, unit_cost in line_rows:
            gross = unit_price * quantity
            share = (discount_amount * gross / subtotal) if subtotal else Decimal("0")
            rate = Decimal(str(product.tax_rate)) / 100
            items.append(OrderItem(
                order=order, variant=variant, product_name=product.name, sku=variant.sku,
                quantity=quantity, unit_price=unit_price, unit_cost=unit_cost, tax_rate=product.tax_rate,
                discount_amount=money(share), position=position, warehouse=warehouse,
                tax_amount=money((gross - share) - (gross - share) / (1 + rate))))

        self._history_rows(order, history)
        self._payments(order, customer, history, payments, refunds)
        if status in {"SHIPPED", "DELIVERED", "RETURNED", "REFUNDED"}:
            self._shipment(order, carrier, city, shipments)
        if status in {"RETURNED", "REFUNDED"}:
            self._return(order, line_rows, returns, return_history, refunds)
        elif status == "DELIVERED" and self.pick.chance(0.018 * customer.refund_factor):
            self._goodwill_refund(order, refunds)
        if discount_row is not None and discount_amount > 0:
            redemptions.append(DiscountRedemption(
                discount=discount_row, order=order, customer=customer.user, code=coupon,
                amount=money(discount_amount), currency=currency, created_at=placed_at))
        if self.config.generate_events:
            self._purchase_session(order, customer, line_rows, session_id, events)
        if status == "DELIVERED" and self.pick.chance(0.085):
            self._review(order, customer, line_rows, reviews)

        # A double-submitted checkout: the same basket a minute later, cancelled as a duplicate.
        if dirty and pick.chance(0.006):
            twin = Order(**{f.name: getattr(order, f.name) for f in Order._meta.concrete_fields
                            if f.name not in {"id", "access_token"}})
            twin.pk = None
            twin.access_token = uuid.uuid4()
            twin.created_at = placed_at + dt.timedelta(seconds=pick.integer(35, 180))
            twin.status, twin.cancel_reason = "CANCELLED", "DUPLICATE"
            twin.cancelled_at = twin.created_at + dt.timedelta(hours=pick.integer(1, 20))
            twin.paid_at = twin.shipped_at = twin.delivered_at = twin.refunded_at = None
            orders.append(twin)
            for position, product, variant, quantity, unit_price, unit_cost in line_rows:
                items.append(OrderItem(order=twin, variant=variant, product_name=product.name, sku=variant.sku,
                                       quantity=quantity, unit_price=unit_price, unit_cost=unit_cost,
                                       tax_rate=product.tax_rate, position=position, warehouse=warehouse))
            self._history_rows(twin, history)

    # ------------------------------------------------------------------ status helpers
    def _status(self, day, country, refund_factor=1.0):
        age = (self.now.date() - day).days
        for limit, options in IN_FLIGHT:
            if age <= limit:
                return self.pick.choice(options)
        weights = []
        for status, weight in TERMINAL:
            if status == "CANCELLED":
                weight *= country[8]
            elif status in {"REFUNDED", "RETURNED"}:
                weight *= refund_factor
            weights.append((status, weight))
        return self.pick.weighted(weights)

    def _timeline(self, placed_at, status, country, carrier, day):
        """Timestamps that can never contradict each other: paid < shipped < delivered < refunded."""
        pick = self.pick
        stamps = {"paid_at": None, "shipped_at": None, "delivered_at": None, "cancelled_at": None, "refunded_at": None}
        if status == "PENDING_PAYMENT":
            return stamps
        if status == "CANCELLED":
            if pick.chance(0.45):
                stamps["paid_at"] = placed_at + dt.timedelta(minutes=pick.integer(1, 90))
            stamps["cancelled_at"] = (stamps["paid_at"] or placed_at) + dt.timedelta(hours=pick.integer(1, 96))
            return stamps
        stamps["paid_at"] = placed_at + dt.timedelta(minutes=pick.integer(1, 240))
        if status == "PAID":
            return stamps
        handling = dt.timedelta(hours=pick.integer(6, 60))
        if status in {"PROCESSING", "PACKED"}:
            return stamps
        stamps["shipped_at"] = stamps["paid_at"] + handling
        if status == "SHIPPED":
            return stamps
        transit = country[9] * carrier[2] / 2.4 * carrier_health(carrier[0], day, self.config.date_from, self.config.date_to)
        stamps["delivered_at"] = stamps["shipped_at"] + dt.timedelta(hours=max(8, int(pick.jitter(transit * 24, 0.35))))
        if status in {"RETURNED", "REFUNDED"}:
            stamps["refunded_at"] = stamps["delivered_at"] + dt.timedelta(days=pick.integer(2, 25))
        for key, value in stamps.items():
            if value is not None and value > self.now:
                stamps[key] = self.now - dt.timedelta(minutes=pick.integer(1, 600))
        return stamps

    def _history_rows(self, order, history):
        steps = [("", "PENDING_PAYMENT", order.created_at, "customer")]
        if order.paid_at:
            steps.append(("PENDING_PAYMENT", "PAID", order.paid_at, "payment_gateway"))
        if order.shipped_at:
            steps.append(("PAID", "PROCESSING", order.paid_at + dt.timedelta(hours=2), "warehouse"))
            steps.append(("PROCESSING", "PACKED", order.shipped_at - dt.timedelta(hours=1), "warehouse"))
            steps.append(("PACKED", "SHIPPED", order.shipped_at, "warehouse"))
        if order.delivered_at:
            steps.append(("SHIPPED", "DELIVERED", order.delivered_at, "carrier"))
        if order.cancelled_at:
            steps.append((order.status, "CANCELLED", order.cancelled_at, "system"))
        if order.refunded_at:
            steps.append(("DELIVERED", order.status, order.refunded_at, "support"))
        for from_status, to_status, at, actor in steps:
            history.append(OrderHistory(order=order, from_status=from_status, to_status=to_status,
                                        created_at=at, actor=actor, note=""))

    # ------------------------------------------------------------------ money movements
    def _payments(self, order, customer, history, payments, refunds):
        pick = self.pick
        method, _share, failure_rate, fee_pct, fee_fixed, settle_days = pick.row(ref.PAYMENT_METHODS, 1)
        base = dict(order=order, amount=order.total, currency=order.currency, fx_rate=order.fx_rate,
                    method=method, gateway="simulated",
                    card_brand=pick.choice(ref.CARD_BRANDS) if method == "CARD" else "",
                    card_last4=str(pick.integer(1000, 9999)) if method in {"CARD", "APPLE_PAY", "GOOGLE_PAY"} else "")
        attempt = 1
        # A declined first attempt is common; most customers simply try again.
        if pick.chance(failure_rate):
            failed_at = order.created_at + dt.timedelta(minutes=pick.integer(1, 25))
            payments.append(Payment(**base, status="FAILED", attempt=attempt, reference=uuid.uuid4().hex,
                                    failure_code=pick.weighted(ref.FAILURE_CODES), created_at=failed_at,
                                    processed_at=failed_at, message="Declined by the issuer"))
            history.append(OrderHistory(order=order, from_status=order.status, to_status=order.status,
                                        created_at=failed_at, actor="payment_gateway", note="Payment failed"))
            attempt += 1
        if order.paid_at is None:
            return
        fee = money(order.total * Decimal(str(fee_pct)) + Decimal(str(fee_fixed)) / order.fx_rate)
        settled = order.paid_at + dt.timedelta(days=settle_days)
        payments.append(Payment(
            **base, status="SUCCEEDED", attempt=attempt, reference=uuid.uuid4().hex,
            created_at=order.paid_at, processed_at=order.paid_at, fee_amount=fee,
            settled_at=settled if settled < self.now else None, message="Approved"))
        if order.status == "CANCELLED" and order.cancelled_at:
            refunds.append(Refund(order=order, amount=order.total, currency=order.currency, fx_rate=order.fx_rate,
                                  reason="CANCELLED_ORDER", status="SUCCEEDED", initiated_by="SYSTEM",
                                  reference=uuid.uuid4().hex, created_at=order.cancelled_at,
                                  processed_at=order.cancelled_at + dt.timedelta(days=pick.integer(1, 6))))

    def _goodwill_refund(self, order, refunds):
        pick = self.pick
        amount = money(order.total * Decimal(str(round(pick.rng.uniform(0.08, 0.4), 2))))
        at = order.delivered_at + dt.timedelta(days=pick.integer(1, 20))
        if at > self.now:
            return
        refunds.append(Refund(order=order, amount=amount, currency=order.currency, fx_rate=order.fx_rate,
                              reason=pick.weighted([("GOODWILL", 0.5), ("LATE_DELIVERY", 0.3), ("DAMAGED_IN_TRANSIT", 0.2)]),
                              status="SUCCEEDED", initiated_by="SUPPORT", reference=uuid.uuid4().hex,
                              created_at=at, processed_at=at + dt.timedelta(days=pick.integer(0, 4))))

    def _return(self, order, line_rows, returns, return_history, refunds):
        pick = self.pick
        requested_at = order.refunded_at or (order.delivered_at + dt.timedelta(days=pick.integer(1, 20)))
        picked = line_rows[:1] if len(line_rows) == 1 else line_rows[:pick.integer(1, min(2, len(line_rows)))]
        for _position, product, variant, quantity, unit_price, _cost in picked:
            returned_qty = quantity if quantity == 1 else pick.integer(1, quantity)
            amount = money(unit_price * returned_qty)
            status = pick.weighted([("REFUNDED", 0.68), ("RECEIVED", 0.12), ("APPROVED", 0.10),
                                    ("REJECTED", 0.06), ("REQUESTED", 0.04)])
            received_at = requested_at + dt.timedelta(days=pick.integer(2, 12)) if status in {"RECEIVED", "REFUNDED"} else None
            resolved_at = (received_at or requested_at) + dt.timedelta(days=pick.integer(1, 8)) if status in {"REFUNDED", "REJECTED"} else None
            request = ReturnRequest(
                order_item=None, quantity=returned_qty, reason=pick.weighted(ref.RETURN_REASONS),
                status=status, refund_amount=amount if status == "REFUNDED" else Decimal("0"),
                refund_currency=order.currency, restock=pick.chance(0.6), damaged=pick.chance(0.18),
                resolution="REFUND" if status == "REFUNDED" else pick.choice(["", "REPLACEMENT", "STORE_CREDIT"]),
                carrier=pick.choice(["", "Correos Express", "DHL", "GLS"]),
                customer_comment="" if pick.chance(0.55) else pick.choice(
                    ["Arrived past the roast window.", "Not what I expected from the notes.",
                     "Box was crushed on arrival.", "Ordered the wrong grind."]),
                created_at=requested_at, received_at=received_at, resolved_at=resolved_at)
            # order_item is attached after the items have primary keys (see _persist).
            request._pending = (order, variant.pk)
            returns.append(request)
            return_history.append((request, "", "REQUESTED", requested_at))
            if received_at:
                return_history.append((request, "REQUESTED", "RECEIVED", received_at))
            if resolved_at:
                return_history.append((request, "RECEIVED", status, resolved_at))
            if status == "REFUNDED":
                refunds.append(Refund(order=order, amount=amount, currency=order.currency, fx_rate=order.fx_rate,
                                      reason="RETURN", status="SUCCEEDED", initiated_by="SUPPORT",
                                      reference=uuid.uuid4().hex, created_at=resolved_at,
                                      processed_at=resolved_at + dt.timedelta(days=pick.integer(0, 5)),
                                      return_request=request))

    # ------------------------------------------------------------------ logistics
    def _carrier(self, market, day):
        options = [c for c in ref.CARRIERS if market in c[1]] or [ref.CARRIERS[3]]
        return self.pick.choice(options)

    def _warehouse(self, market):
        if not self.warehouses:
            return None
        if market == "Iberia":
            return self.pick.weighted([(self.warehouses[0], 0.72)] +
                                      [(w, 0.14) for w in self.warehouses[1:]])
        return self.pick.choice(self.warehouses)

    def _shipment(self, order, carrier, city, shipments):
        pick = self.pick
        status = "DELIVERED" if order.delivered_at else pick.weighted(
            [("IN_TRANSIT", 0.62), ("OUT_FOR_DELIVERY", 0.24), ("PICKED_UP", 0.14)])
        if order.delivered_at is None and pick.chance(carrier[3]):
            status = pick.weighted([("FAILED", 0.5), ("RETURNED_TO_SENDER", 0.35), ("LOST", 0.15)])
        transit_days = carrier[2] * carrier_health(carrier[0], order.created_at.date(),
                                                   self.config.date_from, self.config.date_to)
        shipments.append(Shipment(
            order=order, warehouse=order.warehouse, carrier=carrier[0],
            service_level=pick.weighted(ref.SERVICE_LEVELS), tracking_number=uuid.uuid4().hex[:14].upper(),
            status=status, destination_country_code=order.shipping_country_code, destination_city=city,
            weight_grams=pick.integer(280, 4200), cost=money(pick.jitter(carrier[4], 0.2)), currency="EUR",
            delivery_attempts=1 if status == "DELIVERED" else pick.weighted([(1, 0.7), (2, 0.22), (3, 0.08)]),
            created_at=order.shipped_at or order.created_at, shipped_at=order.shipped_at,
            estimated_delivery=(order.shipped_at or order.created_at).date() + dt.timedelta(days=max(1, round(transit_days))),
            delivered_at=order.delivered_at))

    # ------------------------------------------------------------------ behaviour
    def _purchase_session(self, order, customer, line_rows, session_id, events):
        """The clicks that led to this order, so the funnel has a converting path."""
        base = self._event_base(order, customer, session_id)
        at = order.created_at - dt.timedelta(minutes=self.pick.integer(3, 45))
        events.append(ProductEvent(kind="SESSION_STARTED", created_at=at, **base))
        at += dt.timedelta(seconds=self.pick.integer(10, 120))
        if self.pick.chance(0.42):
            events.append(ProductEvent(kind="SEARCH_PERFORMED", created_at=at, search_term=self.pick.choice(ref.SEARCH_TERMS),
                                       results_count=self.pick.integer(0, 26), **base))
            at += dt.timedelta(seconds=self.pick.integer(5, 90))
        for _position, product, variant, quantity, unit_price, _cost in line_rows:
            events.append(ProductEvent(kind="PRODUCT_VIEWED", product=product, variant=variant, created_at=at, **base))
            at += dt.timedelta(seconds=self.pick.integer(15, 200))
            events.append(ProductEvent(kind="ADD_TO_CART", product=product, variant=variant, quantity=quantity,
                                       value=money(unit_price * quantity), created_at=at, **base))
            at += dt.timedelta(seconds=self.pick.integer(10, 120))
        if self.pick.chance(0.11):
            product, variant = line_rows[0][1], line_rows[0][2]
            events.append(ProductEvent(kind="REMOVE_FROM_CART", product=product, variant=variant, created_at=at, **base))
            at += dt.timedelta(seconds=self.pick.integer(5, 60))
        events.append(ProductEvent(kind="CHECKOUT_STARTED", value=order.total, created_at=at, **base))
        at += dt.timedelta(seconds=self.pick.integer(20, 240))
        events.append(ProductEvent(kind="PAYMENT_SUBMITTED", value=order.total, created_at=at, **base))
        if order.paid_at is not None:
            events.append(ProductEvent(kind="PURCHASE_COMPLETED", value=order.total,
                                       created_at=order.paid_at, **base))

    def _browse_without_buying(self, customer, events):
        """Sessions that drop out somewhere in the funnel — most traffic never converts."""
        if not self.config.generate_events:
            return
        pick, config = self.pick, self.config
        sessions = pick.power_law(0, 14, exponent=1.9)
        # Cheap traffic buys less: the same visit count converts worse on social.
        sessions = int(sessions * (1.6 if customer.channel[0] == "Paid Social" else 1.0))
        first = max(customer.registered_at.date(), config.date_from)
        if first > config.date_to:
            return
        span_days = (config.date_to - first).days
        for _ in range(sessions):
            day = first + dt.timedelta(days=pick.integer(0, span_days)) if span_days else first
            at = pick.datetime_in_day(day, self.tz)
            if at > self.now:
                continue
            share = mobile_share(day, config.date_from, config.date_to)
            device = pick.weighted([("mobile", share), ("tablet", ref.TABLET_SHARE),
                                    ("desktop", max(0.05, 1 - share - ref.TABLET_SHARE))])
            device_row = next(d for d in ref.DEVICES if d[0] == device)
            bot = pick.chance(0.012)
            base = dict(customer=customer.user, session_id=uuid.uuid4().hex, source=customer.channel[1],
                        medium=customer.channel[2], utm_campaign=customer.profile.acquisition_campaign,
                        channel_group=customer.channel[0], referrer_domain=customer.channel[8],
                        landing_page=customer.channel[9], device=device, browser=pick.choice(device_row[1]),
                        os=pick.choice(device_row[2]), country=customer.country[0], country_code=customer.country[1],
                        region=customer.profile.region, city=customer.profile.city, market=customer.country[2],
                        campaign=self.campaigns.get(customer.profile.acquisition_campaign), is_bot=bot,
                        is_test_data=True, test_batch=self.batch)
            events.append(ProductEvent(kind="SESSION_STARTED", created_at=at, **base))
            depth = pick.weighted([(0, 0.34), (1, 0.31), (2, 0.20), (3, 0.11), (4, 0.04)])
            at += dt.timedelta(seconds=pick.integer(8, 90))
            if depth >= 1:
                product = self._pick_product(day)[0]
                events.append(ProductEvent(kind="PRODUCT_VIEWED", product=product, created_at=at, **base))
                at += dt.timedelta(seconds=pick.integer(15, 240))
            if depth >= 2:
                product, variants, _w = self._pick_product(day)
                events.append(ProductEvent(kind="ADD_TO_CART", product=product, variant=pick.choice(variants),
                                           quantity=1, created_at=at, **base))
                at += dt.timedelta(seconds=pick.integer(20, 300))
            if depth >= 3:
                events.append(ProductEvent(kind="CHECKOUT_STARTED", created_at=at, **base))
                at += dt.timedelta(seconds=pick.integer(30, 400))
            if depth >= 4:
                events.append(ProductEvent(kind="PAYMENT_SUBMITTED", created_at=at, **base))

    def _event_base(self, order, customer, session_id):
        return dict(customer=customer.user, session_id=session_id, source=order.utm_source, medium=order.utm_medium,
                    utm_campaign=order.utm_campaign, channel_group=order.channel_group,
                    referrer_domain=order.referrer_domain, landing_page=order.landing_page,
                    device=order.device, browser=order.browser, os=order.os,
                    country=order.shipping_country, country_code=order.shipping_country_code,
                    region=order.shipping_region, city=order.shipping_city, market=order.market,
                    campaign=order.campaign, is_test_data=True, test_batch=self.batch)

    # ------------------------------------------------------------------ satisfaction
    def _review(self, order, customer, line_rows, reviews):
        pick = self.pick
        product = next((row[1] for row in line_rows
                        if (customer.user.pk, row[1].pk) not in self._reviewed), None)
        if product is None:
            return
        at = order.delivered_at + dt.timedelta(days=pick.integer(2, 40))
        if at > self.now:
            return
        self._reviewed.add((customer.user.pk, product.pk))
        # Late deliveries and social-sourced buyers rate a little lower.
        late = order.delivered_at - order.shipped_at > dt.timedelta(days=6) if order.shipped_at else False
        weights = [(5, 0.48), (4, 0.27), (3, 0.13), (2, 0.07), (1, 0.05)]
        if late or customer.channel[0] == "Paid Social":
            weights = [(5, 0.30), (4, 0.24), (3, 0.19), (2, 0.14), (1, 0.13)]
        reviews.append(Review(
            customer=customer.user, product=product, order=order, rating=pick.weighted(weights),
            title=pick.choice(["", "Lovely cup", "Good but pricey", "Will reorder", "Not for me"]),
            comment=pick.choice(["", "Balanced and sweet, exactly as described.", "Arrived quickly, tastes great.",
                                 "Too acidic for my taste.", "Great value for a single origin."]),
            status="APPROVED" if pick.chance(0.88) else pick.choice(["PENDING", "REJECTED"]),
            channel=pick.weighted([("EMAIL", 0.55), ("WEB", 0.36), ("SUPPORT", 0.09)]),
            language=customer.profile.preferred_language, country_code=order.shipping_country_code,
            helpful_votes=pick.power_law(0, 40, 2.6), verified_purchase=True,
            moderated_at=at + dt.timedelta(days=pick.integer(0, 3)),
            responded_at=at + dt.timedelta(days=pick.integer(1, 9)) if pick.chance(0.3) else None,
            created_at=at))

    # ------------------------------------------------------------------ subscriptions
    def _subscribe(self, customer, subscriptions, events):
        pick = self.pick
        if not pick.chance(0.11 * min(customer.repeat_factor, 2.0)):
            return
        coffee = [row for row in self.products if row[0].kind in {"COFFEE", "SUBSCRIPTION"}]
        if not coffee:
            return
        product, variants, _w = pick.choice(coffee)
        variant = pick.choice(variants)
        first = max(customer.registered_at.date(), self.config.date_from)
        if first >= self.config.date_to:
            return
        started_on = first + dt.timedelta(days=pick.integer(0, (self.config.date_to - first).days))
        started_at = pick.datetime_in_day(started_on, self.tz)
        if started_at > self.now:
            return
        plan = pick.weighted([("MONTHLY", 0.52), ("BIWEEKLY", 0.24), ("WEEKLY", 0.13), ("QUARTERLY", 0.11)])
        age_days = (self.now.date() - started_on).days
        # Churn hazard grows with age and bites harder on the shortest plan.
        hazard = min(0.92, age_days / 420) * (1.35 if plan == "WEEKLY" else 1.0)
        status = "ACTIVE"
        cancelled_at = paused_at = None
        if pick.chance(hazard):
            status = "CANCELLED"
            cancelled_at = started_at + dt.timedelta(days=pick.integer(14, max(15, age_days)))
            if cancelled_at > self.now:
                cancelled_at = self.now - dt.timedelta(days=pick.integer(0, 5))
        elif pick.chance(0.09):
            status = "PAUSED"
            paused_at = started_at + dt.timedelta(days=pick.integer(20, max(21, age_days)))
            if paused_at > self.now:
                paused_at = None
                status = "ACTIVE"
        subscription = Subscription(
            customer=customer.user, variant=variant, plan=plan, status=status,
            quantity=pick.weighted([(1, 0.74), (2, 0.19), (3, 0.07)]),
            unit_price=money(Decimal(str(variant.effective_price)) / Decimal(str(ref.FX_TO_EUR[customer.currency]))),
            currency=customer.currency, discount_percent=pick.choice([0, 0, 5, 10]),
            channel_group=customer.channel[0], utm_source=customer.channel[1],
            utm_campaign=customer.profile.acquisition_campaign,
            started_at=started_at, paused_at=paused_at, cancelled_at=cancelled_at,
            next_delivery_on=None if status == "CANCELLED" else self.now.date() + dt.timedelta(days=pick.integer(1, 30)),
            cancel_reason=pick.weighted(ref.SUBSCRIPTION_CANCEL_REASONS) if status == "CANCELLED" and pick.chance(0.62) else "",
            is_test_data=True, test_batch=self.batch)
        subscriptions.append(subscription)
        events.append((subscription, "CREATED", "", "ACTIVE", started_at))
        renewals = min(24, age_days // {"WEEKLY": 7, "BIWEEKLY": 14, "MONTHLY": 30, "QUARTERLY": 91}[plan])
        at = started_at
        for _ in range(max(0, renewals)):
            at = at + dt.timedelta(days={"WEEKLY": 7, "BIWEEKLY": 14, "MONTHLY": 30, "QUARTERLY": 91}[plan])
            if cancelled_at and at > cancelled_at or at > self.now:
                break
            kind = pick.weighted([("RENEWED", 0.88), ("SKIPPED", 0.08), ("PAYMENT_FAILED", 0.04)])
            events.append((subscription, kind, "ACTIVE", "ACTIVE", at))
        if paused_at:
            events.append((subscription, "PAUSED", "ACTIVE", "PAUSED", paused_at))
        if cancelled_at:
            events.append((subscription, "CANCELLED", "ACTIVE", "CANCELLED", cancelled_at))

    # ------------------------------------------------------------------ marketing spend
    def _campaign_metrics(self, events):
        """Daily ad-platform figures roughly consistent with the sessions that were generated."""
        pick = self.pick
        campaigns = [c for c in Campaign.objects.all() if c.channel_group in
                     {"Paid Search", "Paid Social", "Affiliate", "Email", "Display"}]
        if not campaigns:
            return
        rows = []
        for campaign in campaigns:
            for offset in range(self.config.days):
                day = self.config.date_from + dt.timedelta(days=offset)
                if not (campaign.start_date <= day <= campaign.end_date):
                    continue
                factor = demand_factor(day, self.config.date_from)
                spend = Decimal(str(round(pick.jitter(float(campaign.spend or 60) / 30 * factor, 0.3), 2)))
                if campaign.channel_group == "Paid Social":
                    # Same money, steadily fewer clicks for it towards the end of the period.
                    spend *= Decimal(str(round(1 + 0.9 * (offset / max(self.config.days - 1, 1)), 4)))
                    efficiency = paid_social_efficiency(day, self.config.date_from, self.config.date_to)
                else:
                    efficiency = 1.0
                clicks = max(0, int(pick.jitter(float(spend) * 2.4 * efficiency, 0.25)))
                rows.append(CampaignDailyMetric(
                    campaign=campaign, date=day, spend=money(spend), currency=campaign.currency or "EUR",
                    impressions=max(clicks, int(pick.jitter(clicks * pick.integer(28, 70), 0.2))),
                    clicks=clicks, sessions=int(clicks * pick.rng.uniform(0.82, 0.98)),
                    new_customers=max(0, int(pick.jitter(clicks * 0.022 * efficiency, 0.5))),
                    is_test_data=True, test_batch=self.batch))
        existing = set(CampaignDailyMetric.objects.filter(
            date__range=(self.config.date_from, self.config.date_to)).values_list("campaign_id", "date"))
        rows = [r for r in rows if (r.campaign_id, r.date) not in existing]
        self.counts["campaign_metrics"] = len(bulk_insert(CampaignDailyMetric, rows))

    # ------------------------------------------------------------------ writing
    def _persist(self, orders, items, history, payments, refunds, returns, return_history,
                 shipments, redemptions, events, reviews, subscriptions, subscription_events):
        bulk_insert(Order, orders, historic_fields=["created_at"])
        bulk_insert(OrderItem, items)
        bulk_insert(OrderHistory, history, historic_fields=["created_at"])
        bulk_insert(Payment, payments, historic_fields=["created_at"])

        # Returns point at a concrete order line, which only exists once the items have primary keys.
        by_key = {(item.order_id, item.variant_id): item for item in items}
        resolved = []
        for request in returns:
            order, variant_id = request._pending
            item = by_key.get((order.pk, variant_id))
            if item is None:
                continue
            request.order_item = item
            resolved.append(request)
        bulk_insert(ReturnRequest, resolved, historic_fields=["created_at"])
        bulk_insert(ReturnHistory, [ReturnHistory(return_request=r, from_status=f, to_status=t, created_at=at)
                                    for r, f, t, at in return_history if r.pk])
        bulk_insert(Refund, [r for r in refunds if r.return_request is None or r.return_request.pk])
        bulk_insert(Shipment, shipments)
        bulk_insert(DiscountRedemption, redemptions)
        bulk_insert(Review, reviews, historic_fields=["created_at"])
        bulk_insert(Subscription, subscriptions)
        bulk_insert(SubscriptionEvent, [SubscriptionEvent(subscription=s, kind=k, from_status=f, to_status=t, created_at=at)
                                        for s, k, f, t, at in subscription_events if s.pk])
        bulk_insert(ProductEvent, events)
        self.counts.update({
            "orders": len(orders), "order_items": len(items), "order_history": len(history),
            "payments": len(payments), "refunds": len(refunds), "returns": len(resolved),
            "shipments": len(shipments), "discount_redemptions": len(redemptions), "reviews": len(reviews),
            "subscriptions": len(subscriptions), "subscription_events": len(subscription_events),
            "product_events": len(events),
        })
