import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

CURRENCIES = [("EUR", "Euro"), ("GBP", "Pound sterling"), ("CHF", "Swiss franc"), ("SEK", "Swedish krona"),
              ("DKK", "Danish krone"), ("USD", "US dollar")]


class Discount(models.Model):
    class Kind(models.TextChoices): FIXED="FIXED"; PERCENT="PERCENT"; FREE_SHIPPING="FREE_SHIPPING"
    code=models.CharField(max_length=40,unique=True); kind=models.CharField(max_length=15,choices=Kind.choices); value=models.DecimalField(max_digits=10,decimal_places=2); minimum_cart=models.DecimalField(max_digits=12,decimal_places=2,default=0); starts_at=models.DateTimeField(); ends_at=models.DateTimeField(); usage_limit=models.PositiveIntegerField(default=100); times_used=models.PositiveIntegerField(default=0); active=models.BooleanField(default=True)
    # Reporting attributes: which campaign the code belongs to and who it was meant for.
    name=models.CharField(max_length=120,blank=True); description=models.CharField(max_length=255,blank=True)
    campaign=models.ForeignKey("operations.Campaign",null=True,blank=True,on_delete=models.SET_NULL,related_name="discounts")
    channel=models.CharField(max_length=40,blank=True,help_text="Where the code was distributed: email, influencer, print, support…")
    first_order_only=models.BooleanField(default=False); max_per_customer=models.PositiveIntegerField(default=1)
    currency=models.CharField(max_length=3,choices=CURRENCIES,default="EUR",help_text="Only meaningful for FIXED codes.")
    def __str__(self): return self.code


class Cart(models.Model):
    # customer is NULL for guest (session) carts; they are merged into the user's cart on login.
    customer=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.CASCADE,related_name="carts"); active=models.BooleanField(default=True); discount=models.ForeignKey(Discount,null=True,blank=True,on_delete=models.SET_NULL); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    # Visit context, so an abandoned cart can be attributed like an order.
    session_id=models.CharField(max_length=64,blank=True,db_index=True); device=models.CharField(max_length=30,blank=True); browser=models.CharField(max_length=40,blank=True)
    utm_source=models.CharField(max_length=40,blank=True); utm_medium=models.CharField(max_length=40,blank=True); utm_campaign=models.CharField(max_length=100,blank=True)
    channel_group=models.CharField(max_length=40,blank=True,db_index=True); country_code=models.CharField(max_length=2,blank=True); currency=models.CharField(max_length=3,choices=CURRENCIES,default="EUR")
    abandoned_at=models.DateTimeField(null=True,blank=True,help_text="Set by the cleanup job when a cart was never checked out.")
    is_test_data=models.BooleanField(default=False,db_index=True,help_text="Row created by the admin test-data generator; never real business data.")
    test_batch=models.ForeignKey("analytics.TestDataBatch",null=True,blank=True,on_delete=models.SET_NULL,related_name="carts")
    @property
    def subtotal(self): return sum((i.variant.effective_price*i.quantity for i in self.items.select_related("variant__product")),Decimal("0"))
    @property
    def item_count(self): return sum(i.quantity for i in self.items.all())
    @property
    def is_guest(self): return self.customer_id is None
    def __str__(self): return f"Cart #{self.id} ({self.customer or 'guest'})"


class CartItem(models.Model):
    cart=models.ForeignKey(Cart,on_delete=models.CASCADE,related_name="items"); variant=models.ForeignKey("catalog.ProductVariant",on_delete=models.PROTECT); quantity=models.PositiveIntegerField(validators=[MinValueValidator(1)]); added_at=models.DateTimeField(auto_now_add=True,null=True)
    @property
    def line_total(self): return self.variant.effective_price*self.quantity
    class Meta: ordering=["id"]; constraints=[models.UniqueConstraint(fields=["cart","variant"],name="unique_cart_variant")]


class Order(models.Model):
    class Status(models.TextChoices): NEW="NEW"; PENDING_PAYMENT="PENDING_PAYMENT"; PAID="PAID"; PROCESSING="PROCESSING"; PACKED="PACKED"; SHIPPED="SHIPPED"; DELIVERED="DELIVERED"; CANCELLED="CANCELLED"; RETURNED="RETURNED"; REFUNDED="REFUNDED"
    class Channel(models.TextChoices): WEB="WEB","Website"; MOBILE_WEB="MOBILE_WEB","Mobile website"; PHONE="PHONE","Phone order"; MARKETPLACE="MARKETPLACE","Marketplace"; SUBSCRIPTION="SUBSCRIPTION","Subscription renewal"; POS="POS","Roastery counter"
    class CancelReason(models.TextChoices): PAYMENT_TIMEOUT="PAYMENT_TIMEOUT"; PAYMENT_FAILED="PAYMENT_FAILED"; OUT_OF_STOCK="OUT_OF_STOCK"; CUSTOMER_REQUEST="CUSTOMER_REQUEST"; SUSPECTED_FRAUD="SUSPECTED_FRAUD"; DUPLICATE="DUPLICATE"; ADDRESS_INVALID="ADDRESS_INVALID"
    customer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="orders"); status=models.CharField(max_length=20,choices=Status.choices,default=Status.NEW,db_index=True); warehouse=models.ForeignKey("operations.Warehouse",null=True,on_delete=models.PROTECT)
    subtotal=models.DecimalField(max_digits=12,decimal_places=2); discount_amount=models.DecimalField(max_digits=12,decimal_places=2,default=0); tax_amount=models.DecimalField(max_digits=12,decimal_places=2,default=0); total=models.DecimalField(max_digits=12,decimal_places=2); fraud_score=models.PositiveSmallIntegerField(default=0); source=models.CharField(max_length=40,default="direct",db_index=True); created_at=models.DateTimeField(auto_now_add=True,db_index=True); updated_at=models.DateTimeField(auto_now=True)
    shipping_amount=models.DecimalField(max_digits=10,decimal_places=2,default=0,help_text="Delivery charged to the customer, included in total.")
    # --- money: orders are placed in the customer's currency; fx_rate converts one unit to EUR ---
    currency=models.CharField(max_length=3,choices=CURRENCIES,default="EUR",db_index=True)
    fx_rate=models.DecimalField(max_digits=12,decimal_places=6,default=Decimal("1.000000"),help_text="Rate to EUR captured at checkout. total * fx_rate = EUR value.")
    # --- lifecycle timestamps (NULL until the step happens) ---
    paid_at=models.DateTimeField(null=True,blank=True,db_index=True); shipped_at=models.DateTimeField(null=True,blank=True); delivered_at=models.DateTimeField(null=True,blank=True); cancelled_at=models.DateTimeField(null=True,blank=True); refunded_at=models.DateTimeField(null=True,blank=True)
    cancel_reason=models.CharField(max_length=30,choices=CancelReason.choices,blank=True)
    # --- acquisition / session context (last touch) ---
    channel=models.CharField(max_length=20,choices=Channel.choices,default=Channel.WEB,db_index=True)
    channel_group=models.CharField(max_length=40,blank=True,db_index=True,help_text="Reporting bucket: Paid Search, Paid Social, Organic, Email, Referral, Direct.")
    utm_source=models.CharField(max_length=40,blank=True); utm_medium=models.CharField(max_length=40,blank=True); utm_campaign=models.CharField(max_length=100,blank=True); utm_content=models.CharField(max_length=100,blank=True)
    referrer_domain=models.CharField(max_length=120,blank=True); landing_page=models.CharField(max_length=200,blank=True)
    device=models.CharField(max_length=30,blank=True,db_index=True); browser=models.CharField(max_length=40,blank=True); os=models.CharField(max_length=40,blank=True)
    session_id=models.CharField(max_length=64,blank=True,db_index=True,help_text="Joins the order to its browsing session in operations_productevent.")
    campaign=models.ForeignKey("operations.Campaign",null=True,blank=True,on_delete=models.SET_NULL,related_name="orders")
    discount=models.ForeignKey(Discount,null=True,blank=True,on_delete=models.SET_NULL,related_name="orders"); coupon_code=models.CharField(max_length=40,blank=True)
    subscription=models.ForeignKey("Subscription",null=True,blank=True,on_delete=models.SET_NULL,related_name="orders")
    # --- geography ---
    market=models.CharField(max_length=40,blank=True,db_index=True); shipping_country_code=models.CharField(max_length=2,blank=True,db_index=True); shipping_region=models.CharField(max_length=80,blank=True)
    is_gift=models.BooleanField(default=False); gift_message=models.CharField(max_length=255,blank=True)
    # Shipping / contact snapshot captured at checkout (blank for simulated orders).
    access_token=models.UUIDField(default=uuid.uuid4,editable=False,unique=True)  # lets guests open/pay their order from the confirmation link
    shipping_name=models.CharField(max_length=160,blank=True); shipping_address=models.CharField(max_length=255,blank=True); shipping_city=models.CharField(max_length=80,blank=True); shipping_postal_code=models.CharField(max_length=20,blank=True); shipping_country=models.CharField(max_length=80,blank=True); contact_email=models.EmailField(blank=True); contact_phone=models.CharField(max_length=40,blank=True); customer_note=models.CharField(max_length=500,blank=True)
    is_test_data=models.BooleanField(default=False,db_index=True,help_text="Row created by the admin test-data generator; never real business data.")
    test_batch=models.ForeignKey("analytics.TestDataBatch",null=True,blank=True,on_delete=models.SET_NULL,related_name="orders")
    class Meta:
        ordering=["-created_at","-id"]
        indexes=[models.Index(fields=["created_at","status"],name="sales_order_created_status"),models.Index(fields=["channel_group","created_at"],name="sales_order_channel_idx")]
    def __str__(self): return f"Order #{self.id}"
    @property
    def is_paid(self): return self.status not in {"NEW","PENDING_PAYMENT","CANCELLED"}
    @property
    def can_pay(self): return self.status=="PENDING_PAYMENT"
    @property
    def can_cancel(self): return self.status in {"NEW","PENDING_PAYMENT","PAID","PROCESSING"}
    @property
    def is_guest_order(self): return not self.customer.has_usable_password()
    @property
    def warehouses(self): return sorted({i.warehouse.code for i in self.items.all() if i.warehouse_id})


class OrderItem(models.Model):
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name="items"); variant=models.ForeignKey("catalog.ProductVariant",on_delete=models.PROTECT); product_name=models.CharField(max_length=200); sku=models.CharField(max_length=64); quantity=models.PositiveIntegerField(); unit_price=models.DecimalField(max_digits=12,decimal_places=2); unit_cost=models.DecimalField(max_digits=12,decimal_places=2); tax_rate=models.DecimalField(max_digits=5,decimal_places=2); discount_amount=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    warehouse=models.ForeignKey("operations.Warehouse",null=True,blank=True,on_delete=models.PROTECT,related_name="order_items")  # fulfilment warehouse of this line (split orders)
    position=models.PositiveSmallIntegerField(default=0,help_text="Order of the line in the basket.")
    tax_amount=models.DecimalField(max_digits=12,decimal_places=2,default=0,help_text="VAT contained in this line after its share of the order discount.")
    refunded_quantity=models.PositiveIntegerField(default=0)
    class Meta: ordering=["position","id"]
    @property
    def line_total(self): return self.unit_price*self.quantity
    def __str__(self): return f"{self.quantity} x {self.product_name}"


class OrderHistory(models.Model):
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name="history"); from_status=models.CharField(max_length=20,blank=True); to_status=models.CharField(max_length=20); note=models.CharField(max_length=255,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    actor=models.CharField(max_length=60,blank=True,help_text="Who caused the change: customer, staff username, system job…")
    class Meta: ordering=["created_at","id"]; verbose_name_plural="order history"


class Payment(models.Model):
    class Status(models.TextChoices): PENDING="PENDING"; SUCCEEDED="SUCCEEDED"; FAILED="FAILED"; REFUNDED="REFUNDED"; PARTIALLY_REFUNDED="PARTIALLY_REFUNDED"; CANCELLED="CANCELLED"
    class Method(models.TextChoices): CARD="CARD","Credit / debit card"; PAYPAL="PAYPAL","PayPal"; APPLE_PAY="APPLE_PAY","Apple Pay"; GOOGLE_PAY="GOOGLE_PAY","Google Pay"; BANK_TRANSFER="BANK_TRANSFER","Bank transfer"; KLARNA="KLARNA","Klarna"; GIFT_CARD="GIFT_CARD","Gift card"; COD="COD","Cash on delivery"
    order=models.ForeignKey(Order,on_delete=models.PROTECT,related_name="payments"); amount=models.DecimalField(max_digits=12,decimal_places=2); refunded_amount=models.DecimalField(max_digits=12,decimal_places=2,default=0); status=models.CharField(max_length=24,choices=Status.choices,default=Status.PENDING,db_index=True); reference=models.CharField(max_length=80,unique=True); created_at=models.DateTimeField(auto_now_add=True,db_index=True)
    gateway=models.CharField(max_length=30,default="simulated"); card_last4=models.CharField(max_length=4,blank=True); message=models.CharField(max_length=255,blank=True)
    method=models.CharField(max_length=20,choices=Method.choices,default=Method.CARD,db_index=True); card_brand=models.CharField(max_length=20,blank=True)
    currency=models.CharField(max_length=3,choices=CURRENCIES,default="EUR"); fx_rate=models.DecimalField(max_digits=12,decimal_places=6,default=Decimal("1.000000"))
    fee_amount=models.DecimalField(max_digits=10,decimal_places=2,default=0,help_text="Processing fee kept by the provider.")
    attempt=models.PositiveSmallIntegerField(default=1,help_text="1 for the first try; retries after a decline increment it.")
    failure_code=models.CharField(max_length=40,blank=True,help_text="Provider decline code, e.g. insufficient_funds, do_not_honor.")
    processed_at=models.DateTimeField(null=True,blank=True); settled_at=models.DateTimeField(null=True,blank=True,help_text="When the money reached the shop account; NULL while in transit.")
    class Meta: ordering=["-created_at"]
    def __str__(self): return f"{self.reference[:8]} {self.status}"


class Refund(models.Model):
    """A movement of money back to the customer. An order may have several (partial refunds)."""
    class Status(models.TextChoices): PENDING="PENDING"; SUCCEEDED="SUCCEEDED"; FAILED="FAILED"
    class Reason(models.TextChoices): RETURN="RETURN"; GOODWILL="GOODWILL"; LATE_DELIVERY="LATE_DELIVERY"; DAMAGED_IN_TRANSIT="DAMAGED_IN_TRANSIT"; PRICE_ADJUSTMENT="PRICE_ADJUSTMENT"; CANCELLED_ORDER="CANCELLED_ORDER"; DUPLICATE_CHARGE="DUPLICATE_CHARGE"
    class Initiator(models.TextChoices): CUSTOMER="CUSTOMER"; SUPPORT="SUPPORT"; SYSTEM="SYSTEM"
    order=models.ForeignKey(Order,on_delete=models.PROTECT,related_name="refunds"); payment=models.ForeignKey(Payment,null=True,blank=True,on_delete=models.SET_NULL,related_name="refunds")
    return_request=models.ForeignKey("ReturnRequest",null=True,blank=True,on_delete=models.SET_NULL,related_name="refunds")
    amount=models.DecimalField(max_digits=12,decimal_places=2); currency=models.CharField(max_length=3,choices=CURRENCIES,default="EUR"); fx_rate=models.DecimalField(max_digits=12,decimal_places=6,default=Decimal("1.000000"))
    reason=models.CharField(max_length=30,choices=Reason.choices,db_index=True); status=models.CharField(max_length=15,choices=Status.choices,default=Status.SUCCEEDED,db_index=True)
    initiated_by=models.CharField(max_length=15,choices=Initiator.choices,default=Initiator.SUPPORT)
    reference=models.CharField(max_length=80,blank=True); note=models.CharField(max_length=255,blank=True)
    created_at=models.DateTimeField(db_index=True); processed_at=models.DateTimeField(null=True,blank=True)
    class Meta: ordering=["-created_at","-id"]
    def __str__(self): return f"Refund {self.amount} {self.currency} on order #{self.order_id}"


class ReturnRequest(models.Model):
    class Status(models.TextChoices): REQUESTED="REQUESTED"; APPROVED="APPROVED"; REJECTED="REJECTED"; RECEIVED="RECEIVED"; REFUNDED="REFUNDED"
    class Reason(models.TextChoices): DEFECTIVE="DEFECTIVE"; DAMAGED="DAMAGED"; WRONG="WRONG_PRODUCT"; FIT="DID_NOT_FIT"; MIND="CHANGED_MIND"; LATE="LATE_DELIVERY"; TASTE="TASTE_NOT_AS_EXPECTED"; STALE="STALE_ON_ARRIVAL"; OTHER="OTHER"
    class Resolution(models.TextChoices): REFUND="REFUND"; REPLACEMENT="REPLACEMENT"; STORE_CREDIT="STORE_CREDIT"; NONE="NONE"
    order_item=models.ForeignKey(OrderItem,on_delete=models.PROTECT,related_name="returns"); quantity=models.PositiveIntegerField(); reason=models.CharField(max_length=30,choices=Reason.choices,db_index=True); status=models.CharField(max_length=20,choices=Status.choices,default=Status.REQUESTED,db_index=True); refund_amount=models.DecimalField(max_digits=12,decimal_places=2,default=0); restock=models.BooleanField(default=False); damaged=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True,db_index=True)
    resolution=models.CharField(max_length=20,choices=Resolution.choices,blank=True); refund_currency=models.CharField(max_length=3,choices=CURRENCIES,default="EUR")
    carrier=models.CharField(max_length=40,blank=True); tracking_number=models.CharField(max_length=60,blank=True)
    customer_comment=models.TextField(blank=True,help_text="Free text from the return form; often left empty.")
    received_at=models.DateTimeField(null=True,blank=True); resolved_at=models.DateTimeField(null=True,blank=True)
    class Meta: ordering=["-created_at","-id"]


class ReturnHistory(models.Model):
    return_request=models.ForeignKey(ReturnRequest,on_delete=models.CASCADE,related_name="history"); from_status=models.CharField(max_length=20,blank=True); to_status=models.CharField(max_length=20); note=models.CharField(max_length=255,blank=True); created_at=models.DateTimeField(db_index=True)
    class Meta: ordering=["created_at","id"]; verbose_name_plural="return history"


class Shipment(models.Model):
    """One parcel. Split orders produce one shipment per fulfilling warehouse."""
    class Status(models.TextChoices): LABEL_CREATED="LABEL_CREATED"; PICKED_UP="PICKED_UP"; IN_TRANSIT="IN_TRANSIT"; OUT_FOR_DELIVERY="OUT_FOR_DELIVERY"; DELIVERED="DELIVERED"; FAILED="FAILED"; RETURNED_TO_SENDER="RETURNED_TO_SENDER"; LOST="LOST"
    class Service(models.TextChoices): STANDARD="STANDARD"; EXPRESS="EXPRESS"; PICKUP_POINT="PICKUP_POINT"; SAME_DAY="SAME_DAY"
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name="shipments"); warehouse=models.ForeignKey("operations.Warehouse",null=True,on_delete=models.PROTECT,related_name="shipments")
    carrier=models.CharField(max_length=40,db_index=True); service_level=models.CharField(max_length=20,choices=Service.choices,default=Service.STANDARD)
    tracking_number=models.CharField(max_length=60,blank=True); status=models.CharField(max_length=25,choices=Status.choices,default=Status.LABEL_CREATED,db_index=True)
    destination_country_code=models.CharField(max_length=2,blank=True); destination_city=models.CharField(max_length=80,blank=True)
    weight_grams=models.PositiveIntegerField(null=True,blank=True); cost=models.DecimalField(max_digits=10,decimal_places=2,default=0,help_text="What the carrier charges the shop."); currency=models.CharField(max_length=3,choices=CURRENCIES,default="EUR")
    delivery_attempts=models.PositiveSmallIntegerField(default=0)
    created_at=models.DateTimeField(db_index=True); shipped_at=models.DateTimeField(null=True,blank=True); estimated_delivery=models.DateField(null=True,blank=True); delivered_at=models.DateTimeField(null=True,blank=True)
    class Meta: ordering=["-created_at","-id"]
    def __str__(self): return self.tracking_number or f"Shipment #{self.id}"


class Subscription(models.Model):
    """A recurring coffee plan. Renewals appear as orders carrying ``Order.subscription``."""
    class Status(models.TextChoices): ACTIVE="ACTIVE"; PAUSED="PAUSED"; CANCELLED="CANCELLED"; EXPIRED="EXPIRED"
    class Plan(models.TextChoices): WEEKLY="WEEKLY"; BIWEEKLY="BIWEEKLY"; MONTHLY="MONTHLY"; QUARTERLY="QUARTERLY"
    class CancelReason(models.TextChoices): TOO_MUCH_COFFEE="TOO_MUCH_COFFEE"; PRICE="PRICE"; QUALITY="QUALITY"; DELIVERY_ISSUES="DELIVERY_ISSUES"; MOVED="MOVED"; SWITCHED_ROASTER="SWITCHED_ROASTER"; PAYMENT_FAILED="PAYMENT_FAILED"; OTHER="OTHER"
    customer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="subscriptions")
    variant=models.ForeignKey("catalog.ProductVariant",on_delete=models.PROTECT,related_name="subscriptions")
    plan=models.CharField(max_length=15,choices=Plan.choices,default=Plan.MONTHLY,db_index=True); status=models.CharField(max_length=15,choices=Status.choices,default=Status.ACTIVE,db_index=True)
    quantity=models.PositiveIntegerField(default=1); unit_price=models.DecimalField(max_digits=12,decimal_places=2); currency=models.CharField(max_length=3,choices=CURRENCIES,default="EUR")
    discount_percent=models.DecimalField(max_digits=5,decimal_places=2,default=0)
    channel_group=models.CharField(max_length=40,blank=True); utm_source=models.CharField(max_length=40,blank=True); utm_campaign=models.CharField(max_length=100,blank=True)
    started_at=models.DateTimeField(db_index=True); next_delivery_on=models.DateField(null=True,blank=True)
    paused_at=models.DateTimeField(null=True,blank=True); cancelled_at=models.DateTimeField(null=True,blank=True,db_index=True)
    cancel_reason=models.CharField(max_length=30,choices=CancelReason.choices,blank=True,help_text="Optional exit-survey answer; frequently left empty.")
    is_test_data=models.BooleanField(default=False,db_index=True,help_text="Row created by the admin test-data generator; never real business data.")
    test_batch=models.ForeignKey("analytics.TestDataBatch",null=True,blank=True,on_delete=models.SET_NULL,related_name="subscriptions")
    class Meta: ordering=["-started_at","-id"]
    def __str__(self): return f"Subscription #{self.id} ({self.plan})"


class SubscriptionEvent(models.Model):
    class Kind(models.TextChoices): CREATED="CREATED"; RENEWED="RENEWED"; SKIPPED="SKIPPED"; PAUSED="PAUSED"; RESUMED="RESUMED"; PLAN_CHANGED="PLAN_CHANGED"; PAYMENT_FAILED="PAYMENT_FAILED"; CANCELLED="CANCELLED"
    subscription=models.ForeignKey(Subscription,on_delete=models.CASCADE,related_name="events"); kind=models.CharField(max_length=20,choices=Kind.choices,db_index=True)
    from_status=models.CharField(max_length=15,blank=True); to_status=models.CharField(max_length=15,blank=True); note=models.CharField(max_length=200,blank=True)
    created_at=models.DateTimeField(db_index=True)
    class Meta: ordering=["created_at","id"]


class DiscountRedemption(models.Model):
    """Which order actually used which code — ``Discount.times_used`` is only a running counter."""
    discount=models.ForeignKey(Discount,on_delete=models.CASCADE,related_name="redemptions"); order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name="redemptions")
    customer=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="discount_redemptions")
    code=models.CharField(max_length=40,db_index=True); amount=models.DecimalField(max_digits=12,decimal_places=2); currency=models.CharField(max_length=3,choices=CURRENCIES,default="EUR")
    created_at=models.DateTimeField(db_index=True)
    class Meta: ordering=["-created_at","-id"]
