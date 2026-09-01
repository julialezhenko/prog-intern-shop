import pytest
from django.contrib.auth.models import User

from catalog.models import Brand, Category, Product, ProductImage, ProductVariant
from operations.models import Inventory, Warehouse


@pytest.fixture
def catalog(db):
    """A small, fully stocked catalog with one hidden draft product."""
    electronics = Category.objects.create(name="Electronics", slug="electronics", description="Gadgets")
    home = Category.objects.create(name="Home", slug="home")
    brand = Brand.objects.create(name="Acme", slug="acme")
    warehouse = Warehouse.objects.create(name="Madrid", code="MAD", city="Madrid")
    products = {}
    for sku, name, category, price, status, active, stock in [
        ("P1", "Wireless Earbuds", electronics, "59.90", "ACTIVE", True, 10),
        ("P2", "Bluetooth Speaker", electronics, "89.00", "ACTIVE", True, 0),
        ("P3", "Table Lamp", home, "35.50", "ACTIVE", True, 4),
        ("P4", "Secret Draft", electronics, "10.00", "DRAFT", True, 10),
        ("P5", "Retired Kettle", home, "20.00", "ACTIVE", False, 10),
    ]:
        product = Product.objects.create(sku=sku, name=name, slug=sku.lower(), category=category, brand=brand,
                                         purchase_cost=5, sale_price=price, status=status, active=active, tax_rate=21)
        ProductImage.objects.create(product=product, url=f"https://example.test/{sku}.jpg", primary=True)
        variant = ProductVariant.objects.create(product=product, sku=f"{sku}-STD", name="Standard")
        Inventory.objects.create(variant=variant, warehouse=warehouse, physical=stock)
        products[sku] = product
    return {"products": products, "warehouse": warehouse, "brand": brand, "categories": {"electronics": electronics, "home": home}}


@pytest.fixture
def customer(db):
    return User.objects.create_user("alice", "alice@example.test", "S3cret-pass")


@pytest.fixture
def staff(db):
    return User.objects.create_user("staffer", "staff@example.test", "S3cret-pass", is_staff=True, is_superuser=True)
