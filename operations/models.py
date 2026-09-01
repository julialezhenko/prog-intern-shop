from django.db import models
from django.core.validators import MinValueValidator,MaxValueValidator


class Warehouse(models.Model):
    name=models.CharField(max_length=120); code=models.CharField(max_length=20,unique=True); address=models.CharField(max_length=200,blank=True); city=models.CharField(max_length=80); country=models.CharField(max_length=80,default="Spain"); active=models.BooleanField(default=True)
    country_code=models.CharField(max_length=2,blank=True); region=models.CharField(max_length=80,blank=True); market=models.CharField(max_length=40,blank=True,db_index=True)
    timezone=models.CharField(max_length=60,blank=True); opened_on=models.DateField(null=True,blank=True)
    def __str__(self): return self.code


class Inventory(models.Model):
    warehouse=models.ForeignKey(Warehouse,on_delete=models.PROTECT,related_name="inventory"); variant=models.ForeignKey("catalog.ProductVariant",on_delete=models.PROTECT,related_name="inventory"); physical=models.PositiveIntegerField(default=0); reserved=models.PositiveIntegerField(default=0); incoming=models.PositiveIntegerField(default=0); damaged=models.PositiveIntegerField(default=0)
    @property
    def available(self): return self.physical-self.reserved
    class Meta: constraints=[models.UniqueConstraint(fields=["warehouse","variant"],name="unique_inventory_row"),models.CheckConstraint(check=models.Q(physical__gte=models.F("reserved")),name="physical_gte_reserved")]


class InventoryMovement(models.Model):
    class Kind(models.TextChoices): RECEIPT="RECEIPT"; RESERVE="RESERVE"; RELEASE="RELEASE"; SHIP="SHIP"; RETURN="RETURN"; DAMAGE="DAMAGE"; ADJUST="ADJUST"; TRANSFER_OUT="TRANSFER_OUT"; TRANSFER_IN="TRANSFER_IN"
    inventory=models.ForeignKey(Inventory,on_delete=models.PROTECT,related_name="movements"); kind=models.CharField(max_length=20,choices=Kind.choices,db_index=True); quantity=models.IntegerField(); reference_type=models.CharField(max_length=40); reference_id=models.CharField(max_length=64); created_at=models.DateTimeField(auto_now_add=True,db_index=True); metadata=models.JSONField(default=dict,blank=True)


class InventorySnapshot(models.Model):
    """Weekly stock photograph. ``Inventory`` only holds today's numbers, so history lives here."""
    snapshot_date=models.DateField(db_index=True); warehouse=models.ForeignKey(Warehouse,on_delete=models.CASCADE,related_name="snapshots"); variant=models.ForeignKey("catalog.ProductVariant",on_delete=models.CASCADE,related_name="snapshots")
    physical=models.PositiveIntegerField(default=0); reserved=models.PositiveIntegerField(default=0); incoming=models.PositiveIntegerField(default=0); damaged=models.PositiveIntegerField(default=0)
    unit_cost=models.DecimalField(max_digits=12,decimal_places=2,default=0,help_text="Cost price on that date; multiply by physical for stock value.")
    is_test_data=models.BooleanField(default=False,db_index=True)
    test_batch=models.ForeignKey("analytics.TestDataBatch",null=True,blank=True,on_delete=models.SET_NULL,related_name="snapshots")
    class Meta:
        ordering=["-snapshot_date","warehouse_id"]
        constraints=[models.UniqueConstraint(fields=["snapshot_date","warehouse","variant"],name="unique_inventory_snapshot")]


class Supplier(models.Model):
    name=models.CharField(max_length=160); country=models.CharField(max_length=80); email=models.EmailField(blank=True); default_lead_days=models.PositiveIntegerField(default=14); reliability_score=models.DecimalField(max_digits=5,decimal_places=2,validators=[MinValueValidator(0),MaxValueValidator(100)]); active=models.BooleanField(default=True)
    country_code=models.CharField(max_length=2,blank=True); region=models.CharField(max_length=80,blank=True)
    currency=models.CharField(max_length=3,default="EUR"); payment_terms_days=models.PositiveIntegerField(default=30)
    contract_started_on=models.DateField(null=True,blank=True); contact_name=models.CharField(max_length=120,blank=True)
    def __str__(self): return self.name


class SupplierProduct(models.Model):
    supplier=models.ForeignKey(Supplier,on_delete=models.CASCADE,related_name="products"); variant=models.ForeignKey("catalog.ProductVariant",on_delete=models.CASCADE,related_name="suppliers"); supplier_sku=models.CharField(max_length=64); purchase_price=models.DecimalField(max_digits=12,decimal_places=2); lead_days=models.PositiveIntegerField(default=14); minimum_order_quantity=models.PositiveIntegerField(default=1)
    currency=models.CharField(max_length=3,default="EUR"); is_preferred=models.BooleanField(default=False)
    class Meta: constraints=[models.UniqueConstraint(fields=["supplier","variant"],name="unique_supplier_variant")]


class PurchaseOrder(models.Model):
    class Status(models.TextChoices): DRAFT="DRAFT"; SUBMITTED="SUBMITTED"; CONFIRMED="CONFIRMED"; PARTIAL="PARTIALLY_RECEIVED"; RECEIVED="RECEIVED"; CANCELLED="CANCELLED"
    supplier=models.ForeignKey(Supplier,on_delete=models.PROTECT,related_name="purchase_orders"); warehouse=models.ForeignKey(Warehouse,on_delete=models.PROTECT); status=models.CharField(max_length=24,choices=Status.choices,default=Status.DRAFT,db_index=True); expected_delivery=models.DateField(); created_at=models.DateTimeField(auto_now_add=True,db_index=True)
    reference=models.CharField(max_length=40,blank=True); currency=models.CharField(max_length=3,default="EUR"); fx_rate=models.DecimalField(max_digits=12,decimal_places=6,default=1)
    freight_cost=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    submitted_at=models.DateTimeField(null=True,blank=True); confirmed_at=models.DateTimeField(null=True,blank=True); received_at=models.DateTimeField(null=True,blank=True); cancelled_at=models.DateTimeField(null=True,blank=True)
    notes=models.CharField(max_length=255,blank=True)
    class Meta: ordering=["-created_at","-id"]


class PurchaseOrderItem(models.Model):
    purchase_order=models.ForeignKey(PurchaseOrder,on_delete=models.CASCADE,related_name="items"); variant=models.ForeignKey("catalog.ProductVariant",on_delete=models.PROTECT); quantity=models.PositiveIntegerField(); received_quantity=models.PositiveIntegerField(default=0); unit_cost=models.DecimalField(max_digits=12,decimal_places=2)


class Transfer(models.Model):
    class Status(models.TextChoices): DRAFT="DRAFT"; IN_TRANSIT="IN_TRANSIT"; RECEIVED="RECEIVED"; CANCELLED="CANCELLED"
    source=models.ForeignKey(Warehouse,on_delete=models.PROTECT,related_name="outgoing_transfers"); destination=models.ForeignKey(Warehouse,on_delete=models.PROTECT,related_name="incoming_transfers"); variant=models.ForeignKey("catalog.ProductVariant",on_delete=models.PROTECT); quantity=models.PositiveIntegerField(); status=models.CharField(max_length=20,choices=Status.choices,default=Status.DRAFT); created_at=models.DateTimeField(auto_now_add=True)
    dispatched_at=models.DateTimeField(null=True,blank=True); received_at=models.DateTimeField(null=True,blank=True); reason=models.CharField(max_length=60,blank=True)


class Campaign(models.Model):
    class Objective(models.TextChoices): ACQUISITION="ACQUISITION"; RETENTION="RETENTION"; BRAND="BRAND"; PROMOTION="PROMOTION"; WINBACK="WINBACK"
    class Status(models.TextChoices): PLANNED="PLANNED"; RUNNING="RUNNING"; PAUSED="PAUSED"; FINISHED="FINISHED"
    name=models.CharField(max_length=160); source=models.CharField(max_length=40,db_index=True); medium=models.CharField(max_length=40); utm_campaign=models.CharField(max_length=100,blank=True); start_date=models.DateField(); end_date=models.DateField(); spend=models.DecimalField(max_digits=14,decimal_places=2); active=models.BooleanField(default=True)
    channel_group=models.CharField(max_length=40,blank=True,db_index=True,help_text="Paid Search, Paid Social, Email, Affiliate, Display…")
    objective=models.CharField(max_length=20,choices=Objective.choices,default=Objective.ACQUISITION)
    status=models.CharField(max_length=15,choices=Status.choices,default=Status.RUNNING,db_index=True)
    budget=models.DecimalField(max_digits=14,decimal_places=2,default=0,help_text="Planned budget; compare with the spend actually booked in campaign metrics.")
    currency=models.CharField(max_length=3,default="EUR")
    target_market=models.CharField(max_length=40,blank=True); target_country_code=models.CharField(max_length=2,blank=True)
    owner=models.CharField(max_length=80,blank=True)
    def __str__(self): return self.name


class CampaignDailyMetric(models.Model):
    """Daily media buying facts as they arrive from the ad platforms — one row per campaign and day.

    Only raw counters are stored; CTR, CPC, CPM, ROAS and CAC are left to be derived.
    """
    campaign=models.ForeignKey(Campaign,on_delete=models.CASCADE,related_name="daily_metrics")
    date=models.DateField(db_index=True); spend=models.DecimalField(max_digits=12,decimal_places=2,default=0); currency=models.CharField(max_length=3,default="EUR")
    impressions=models.PositiveIntegerField(default=0); clicks=models.PositiveIntegerField(default=0); sessions=models.PositiveIntegerField(default=0)
    new_customers=models.PositiveIntegerField(default=0,help_text="As reported by the ad platform, which does not always agree with the shop database.")
    is_test_data=models.BooleanField(default=False,db_index=True)
    test_batch=models.ForeignKey("analytics.TestDataBatch",null=True,blank=True,on_delete=models.SET_NULL,related_name="campaign_metrics")
    class Meta:
        ordering=["-date","campaign_id"]
        constraints=[models.UniqueConstraint(fields=["campaign","date"],name="unique_campaign_day")]


class ProductEvent(models.Model):
    class Kind(models.TextChoices): SESSION="SESSION_STARTED"; VIEW="PRODUCT_VIEWED"; SEARCH="SEARCH_PERFORMED"; ADD="ADD_TO_CART"; REMOVE="REMOVE_FROM_CART"; CHECKOUT="CHECKOUT_STARTED"; PAYMENT="PAYMENT_SUBMITTED"; PURCHASE="PURCHASE_COMPLETED"; NEWSLETTER="NEWSLETTER_SIGNUP"; REVIEW="REVIEW_SUBMITTED"
    kind=models.CharField(max_length=30,choices=Kind.choices,db_index=True); customer=models.ForeignKey("auth.User",null=True,blank=True,on_delete=models.SET_NULL); session_id=models.CharField(max_length=64,db_index=True); product=models.ForeignKey("catalog.Product",null=True,blank=True,on_delete=models.SET_NULL); campaign=models.ForeignKey(Campaign,null=True,blank=True,on_delete=models.SET_NULL); source=models.CharField(max_length=40,default="direct",db_index=True); device=models.CharField(max_length=30,blank=True,db_index=True); country=models.CharField(max_length=80,blank=True); context=models.JSONField(default=dict,blank=True); created_at=models.DateTimeField(db_index=True)
    medium=models.CharField(max_length=40,blank=True); utm_campaign=models.CharField(max_length=100,blank=True); channel_group=models.CharField(max_length=40,blank=True,db_index=True)
    referrer_domain=models.CharField(max_length=120,blank=True); landing_page=models.CharField(max_length=200,blank=True)
    browser=models.CharField(max_length=40,blank=True); os=models.CharField(max_length=40,blank=True)
    country_code=models.CharField(max_length=2,blank=True,db_index=True); region=models.CharField(max_length=80,blank=True); city=models.CharField(max_length=80,blank=True); market=models.CharField(max_length=40,blank=True)
    variant=models.ForeignKey("catalog.ProductVariant",null=True,blank=True,on_delete=models.SET_NULL)
    quantity=models.PositiveIntegerField(null=True,blank=True); value=models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True,help_text="Monetary value attached to the event, when there is one.")
    search_term=models.CharField(max_length=120,blank=True); results_count=models.PositiveIntegerField(null=True,blank=True)
    is_bot=models.BooleanField(default=False,db_index=True)
    is_test_data=models.BooleanField(default=False,db_index=True,help_text="Row created by the admin test-data generator; never real business data.")
    test_batch=models.ForeignKey("analytics.TestDataBatch",null=True,blank=True,on_delete=models.SET_NULL,related_name="events")
    class Meta:
        ordering=["-created_at","-id"]
        indexes=[models.Index(fields=["created_at","kind"],name="ops_event_created_kind"),models.Index(fields=["session_id","created_at"],name="ops_event_session_idx")]
