from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    image_url = models.URLField(blank=True, help_text="Used when no image file is uploaded.")
    position = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first in the navigation.")

    class Meta:
        ordering = ["position", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("category_detail", kwargs={"category_slug": self.slug})

    @property
    def image_src(self):
        return self.image.url if self.image else self.image_url


LIVE_PRODUCT = Q(active=True, status="ACTIVE")


def live_category_counts():
    """Top-level categories with the number of live products in them *or in their subcategories*.

    Category pages resolve a parent to "itself plus its children", so the navigation has to count the
    same way; otherwise a parent whose products all sit in subcategories looks empty and disappears.
    """
    from django.db.models import Count, Q as _Q

    return (Category.objects.filter(parent__isnull=True)
            .annotate(product_count=Count(
                "products", filter=_Q(products__active=True, products__status="ACTIVE"), distinct=True)
                + Count("children__products",
                        filter=_Q(children__products__active=True, children__products__status="ACTIVE"),
                        distinct=True))
            .filter(product_count__gt=0).order_by("position", "name"))  # GROUP BY queries ignore Meta.ordering


class Brand(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Free-form merchandising labels (gift, limited, decaf, subscription-friendly...).

    Products carry several; unlike ``category`` they overlap, which makes them a second, independent
    segmentation dimension for reporting.
    """

    class Group(models.TextChoices):
        MERCHANDISING = "MERCHANDISING", "Merchandising"
        AUDIENCE = "AUDIENCE", "Audience"
        OCCASION = "OCCASION", "Occasion"
        ATTRIBUTE = "ATTRIBUTE", "Attribute"

    name = models.CharField(max_length=60)
    slug = models.SlugField(unique=True)
    group = models.CharField(max_length=20, choices=Group.choices, default=Group.MERCHANDISING, db_index=True)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["group", "name"]

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def storefront(self):
        """Products that customers may see and buy: the single visibility rule for the public catalog and API."""
        return self.filter(active=True, status=Product.Status.ACTIVE)

    def with_stock(self):
        """Annotate the sellable quantity (physical - reserved) summed over every variant and warehouse."""
        return self.annotate(
            stock_available=Sum(F("variants__inventory__physical") - F("variants__inventory__reserved"),
                                filter=Q(variants__active=True))
        )

    def in_stock(self):
        return self.with_stock().filter(stock_available__gt=0)


class Product(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        ACTIVE = "ACTIVE"
        DISCONTINUED = "DISCONTINUED"

    class Kind(models.TextChoices):
        COFFEE = "COFFEE", "Coffee"
        EQUIPMENT = "EQUIPMENT", "Brewing equipment"
        BUNDLE = "BUNDLE", "Gift box / bundle"
        SUBSCRIPTION = "SUBSCRIPTION", "Subscription"

    class Roast(models.TextChoices):
        LIGHT = "LIGHT", "Light"
        MEDIUM_LIGHT = "MEDIUM_LIGHT", "Medium-light"
        MEDIUM = "MEDIUM", "Medium"
        MEDIUM_DARK = "MEDIUM_DARK", "Medium-dark"
        DARK = "DARK", "Dark"

    class Process(models.TextChoices):
        WASHED = "WASHED", "Washed"
        NATURAL = "NATURAL", "Natural"
        HONEY = "HONEY", "Honey"
        ANAEROBIC = "ANAEROBIC", "Anaerobic"
        DECAF_EA = "DECAF_EA", "Sugarcane EA decaf"
        DECAF_SWP = "DECAF_SWP", "Swiss Water decaf"

    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.COFFEE,
                            help_text="Controls which product-page sections are shown.")
    short_description = models.CharField(max_length=255, blank=True, help_text="One sentence shown under the title and on cards.")
    description = models.TextField(blank=True)
    featured = models.BooleanField(default=False, db_index=True, help_text="Shown in the home page best-sellers section.")
    compare_at_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                           help_text="Previous / list price; when higher than the sale price a discount badge is shown.")
    # Coffee profile (blank for equipment)
    origin = models.CharField(max_length=80, blank=True, help_text="Country, e.g. Ethiopia. Blends: 'Brazil, Colombia'.")
    region = models.CharField(max_length=120, blank=True)
    producer = models.CharField(max_length=120, blank=True, help_text="Farm, washing station or cooperative.")
    variety = models.CharField(max_length=120, blank=True)
    process = models.CharField(max_length=20, choices=Process.choices, blank=True)
    roast_level = models.CharField(max_length=20, choices=Roast.choices, blank=True)
    altitude = models.CharField(max_length=60, blank=True, help_text="e.g. 1,900–2,100 m")
    tasting_notes = models.CharField(max_length=200, blank=True, help_text="Comma separated, e.g. Jasmine, bergamot, peach")
    brew_methods = models.CharField(max_length=200, blank=True,
                                    help_text="Comma separated codes: v60, chemex, aeropress, french_press, espresso, moka, cold_brew, batch")
    # Storefront content blocks
    highlights = models.TextField(blank=True, help_text="'Why you'll love it' bullets — one per line.")
    brew_guide = models.TextField(blank=True, help_text="Recipe steps — one per line.")
    origin_story = models.TextField(blank=True, help_text="Editorial paragraph(s) about the origin / maker.")
    story_image_url = models.URLField(blank=True, help_text="Large lifestyle image for the story section.")
    specs = models.JSONField(default=dict, blank=True, help_text='Equipment specifications, e.g. {"Material": "Ceramic"}.')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")
    origin_country_code = models.CharField(max_length=2, blank=True, db_index=True,
                                           help_text="ISO code of the growing country; blank for blends and equipment.")
    weight_grams = models.PositiveIntegerField(null=True, blank=True, help_text="Net weight of the base unit; NULL for subscriptions.")
    is_limited = models.BooleanField(default=False, help_text="Micro-lot or one-off release that is not restocked.")
    is_seasonal = models.BooleanField(default=False)
    launched_at = models.DateField(null=True, blank=True, help_text="First day on sale; NULL for products migrated from the old shop.")
    discontinued_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=21)
    active = models.BooleanField(default=True)
    reorder_point = models.PositiveIntegerField(default=10)
    preferred_reorder_quantity = models.PositiveIntegerField(default=50)
    safety_stock = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["active", "status"], name="catalog_product_visible_idx")]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("product_detail", kwargs={"slug": self.slug})

    @property
    def is_visible(self):
        return self.active and self.status == self.Status.ACTIVE

    @property
    def primary_image(self):
        images = list(self.images.all())
        if not images:
            return None
        return next((i for i in images if i.primary), images[0])

    @property
    def available_quantity(self):
        annotated = getattr(self, "stock_available", None)
        if annotated is not None:
            return max(annotated, 0)
        total = self.variants.filter(active=True).aggregate(
            q=Sum(F("inventory__physical") - F("inventory__reserved")))["q"]
        return max(total or 0, 0)

    @property
    def in_stock(self):
        return self.available_quantity > 0

    @property
    def margin_percent(self):
        if not self.sale_price:
            return Decimal("0")
        return ((self.sale_price - self.purchase_cost) / self.sale_price * 100).quantize(Decimal("0.1"))

    # --- storefront helpers -------------------------------------------------
    @property
    def is_coffee(self):
        return self.kind == self.Kind.COFFEE

    @property
    def is_on_sale(self):
        return bool(self.compare_at_price and self.compare_at_price > self.sale_price)

    @property
    def discount_percent(self):
        if not self.is_on_sale:
            return 0
        return int(round((1 - self.sale_price / self.compare_at_price) * 100))

    @staticmethod
    def _split(value, sep=","):
        return [part.strip() for part in (value or "").split(sep) if part.strip()]

    @property
    def tasting_notes_list(self):
        return self._split(self.tasting_notes)

    @property
    def brew_method_codes(self):
        return [code.lower().replace("-", "_") for code in self._split(self.brew_methods)]

    @property
    def highlights_list(self):
        return self._split(self.highlights, "\n")

    @property
    def brew_steps(self):
        return self._split(self.brew_guide, "\n")

    @property
    def profile_rows(self):
        """(label, value) pairs for the 'Coffee profile' block; only filled-in fields are shown."""
        rows = [("Origin", self.origin), ("Region", self.region), ("Producer", self.producer), ("Variety", self.variety),
                ("Process", self.get_process_display() if self.process else ""),
                ("Roast", self.get_roast_level_display() if self.roast_level else ""), ("Altitude", self.altitude)]
        return [(label, value) for label, value in rows if value]

    @property
    def price_range(self):
        """(min, max) effective price across active variants — cards show 'from €x' when they differ."""
        prices = [v.effective_price for v in self.variants.all() if v.active] or [self.sale_price]
        return min(prices), max(prices)


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=160)
    attributes = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    @property
    def effective_price(self):
        return self.price if self.price is not None else self.product.sale_price

    @property
    def available_quantity(self):
        total = self.inventory.aggregate(q=Sum(F("physical") - F("reserved")))["q"]
        return max(total or 0, 0)

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class ProductImage(models.Model):
    """An image is either uploaded (``image``) or referenced by URL (``url``); ``src`` hides the difference."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/%Y/%m/", blank=True, null=True)
    url = models.URLField(blank=True)
    alt_text = models.CharField(max_length=200, blank=True)
    primary = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-primary", "position", "id"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.image and not self.url:
            raise ValidationError("Upload an image file or provide an image URL.")

    @property
    def src(self):
        if self.image:
            return self.image.url
        return self.url

    def __str__(self):
        return self.alt_text or self.src or f"Image #{self.pk}"


class PriceHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="price_history")
    old_price = models.DecimalField(max_digits=12, decimal_places=2)
    new_price = models.DecimalField(max_digits=12, decimal_places=2)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name_plural = "price history"


class ProductStatusHistory(models.Model):
    """Every visibility change (DRAFT -> ACTIVE -> DISCONTINUED) with the moment it happened."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    note = models.CharField(max_length=200, blank=True)
    changed_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-changed_at", "-id"]
        verbose_name_plural = "product status history"

    def __str__(self):
        return f"{self.product_id}: {self.from_status or '-'} -> {self.to_status}"


class Wishlist(models.Model):
    customer = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist")
    products = models.ManyToManyField(Product, blank=True)


class Review(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"

    class Channel(models.TextChoices):
        WEB = "WEB", "Website form"
        EMAIL = "EMAIL", "Post-purchase e-mail"
        SUPPORT = "SUPPORT", "Collected by support"
        IMPORT = "IMPORT", "Imported from the old shop"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    order = models.ForeignKey("sales.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="reviews",
                              help_text="Set when the review was collected after a known purchase.")
    title = models.CharField(max_length=160, blank=True)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.WEB, db_index=True)
    language = models.CharField(max_length=5, blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    helpful_votes = models.PositiveIntegerField(default=0)
    verified_purchase = models.BooleanField(default=False)
    moderated_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True, help_text="When the shop replied; NULL when never answered.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["customer", "product"], name="unique_product_review")]
