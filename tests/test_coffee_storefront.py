import re
"""Storefront behaviour introduced with the specialty-coffee redesign: coffee facets, merchandising,
reviews from the storefront, newsletter, SEO output and the demo seed."""
import json

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse

from accounts.models import NewsletterSubscriber
from catalog.models import Category, Product, ProductImage, ProductVariant, Review
from operations.models import Inventory, Warehouse
from sales import services

pytestmark = pytest.mark.django_db


@pytest.fixture
def coffee_catalog(db):
    filter_cat = Category.objects.create(name="Filter Coffee", slug="filter-coffee", position=1, image_url="https://example.test/f.jpg")
    gear = Category.objects.create(name="Equipment", slug="equipment", position=2)
    from catalog.models import Brand
    house = Brand.objects.create(name="House", slug="house")
    warehouse = Warehouse.objects.create(name="Valencia", code="VAL", city="Valencia")
    specs = [
        ("ETH", "Ethiopia Sidamo", filter_cat, "14.50", None, "Ethiopia", "LIGHT", "v60,chemex", "Jasmine, peach", True, 20),
        ("COL", "Colombia Huila", filter_cat, "13.00", "14.50", "Colombia", "MEDIUM_LIGHT", "v60,aeropress,batch", "Apple, caramel", True, 20),
        ("BRA", "Brazil Cerrado", filter_cat, "11.50", None, "Brazil", "MEDIUM", "espresso,moka", "Hazelnut, chocolate", False, 0),
        ("DRP", "Ceramic Dripper", gear, "24.00", None, "", "", "v60", "", True, 5),
    ]
    products = {}
    for sku, name, category, price, compare, origin, roast, brew, notes, featured, stock in specs:
        product = Product.objects.create(
            sku=sku, name=name, slug=sku.lower(), category=category, brand=house, purchase_cost=5, sale_price=price,
            compare_at_price=compare, origin=origin, roast_level=roast, brew_methods=brew, tasting_notes=notes, featured=featured,
            kind=Product.Kind.COFFEE if origin else Product.Kind.EQUIPMENT, short_description=f"{name} short copy",
            highlights="Sweet\nClean", brew_guide="Grind 15 g\nPour 250 g", origin_story="A farm story.",
            specs={} if origin else {"Material": "Ceramic"})
        ProductImage.objects.create(product=product, url=f"https://images.unsplash.com/photo-{sku}", primary=True, alt_text=name)
        variant = ProductVariant.objects.create(product=product, sku=f"{sku}-250", name="250 g · Whole bean")
        Inventory.objects.create(variant=variant, warehouse=warehouse, physical=stock)
        if origin:
            kilo = ProductVariant.objects.create(product=product, sku=f"{sku}-1KG", name="1 kg", price=str(float(price) * 3.4))
            Inventory.objects.create(variant=kilo, warehouse=warehouse, physical=stock)
        products[sku] = product
    return products


# ---------------------------------------------------------------------------
# Catalog facets & merchandising
# ---------------------------------------------------------------------------

def test_catalog_filters_by_origin_roast_and_brew_method(client, coffee_catalog):
    names = lambda response: sorted(p.name for p in response.context["page"].object_list)
    assert names(client.get(reverse("product_list"), {"origin": "Ethiopia"})) == ["Ethiopia Sidamo"]
    assert names(client.get(reverse("product_list"), {"roast": ["LIGHT", "MEDIUM"]})) == ["Brazil Cerrado", "Ethiopia Sidamo"]
    assert names(client.get(reverse("product_list"), {"brew": "v60"})) == ["Ceramic Dripper", "Colombia Huila", "Ethiopia Sidamo"]
    assert names(client.get(reverse("product_list"), {"on_sale": "1"})) == ["Colombia Huila"]
    assert names(client.get(reverse("product_list"), {"q": "hazelnut"})) == ["Brazil Cerrado"]
    assert names(client.get(reverse("product_list"), {"roast": "BOGUS"})) == names(client.get(reverse("product_list")))


def test_catalog_facets_only_offer_values_present_in_scope(client, coffee_catalog):
    response = client.get(reverse("category_detail", args=["equipment"]))
    assert response.context["origins"] == [] and response.context["roasts"] == []
    assert [code for code, _ in response.context["brews"]] == ["v60"]
    everything = client.get(reverse("product_list"))
    assert everything.context["origins"] == ["Brazil", "Colombia", "Ethiopia"]


def test_home_shows_featured_coffee_first_and_offers(client, coffee_catalog):
    response = client.get(reverse("storefront"))
    # featured coffee first, then featured gear; the row is topped up with a non-featured product to reach four
    assert [p.name for p in response.context["featured"]] == ["Colombia Huila", "Ethiopia Sidamo", "Ceramic Dripper", "Brazil Cerrado"]
    assert [p.name for p in response.context["on_sale"]] == ["Colombia Huila"]
    html = response.content.decode()
    assert "−10%" in html and "WELCOME10" in html and 'property="og:image"' in html


def test_product_card_shows_discount_low_stock_and_from_price(client, coffee_catalog):
    html = client.get(reverse("product_list")).content.decode()
    assert "−10%" in html           # Colombia compare-at price 14.50 -> 13.00
    assert "Only 5 left" in html    # dripper stock 5 <= reorder point
    assert "Sold out" in html       # Brazil has no stock
    assert "<span class=\"from\">from</span>" in html  # coffees have a 1 kg variant at another price


def test_product_page_renders_coffee_blocks_and_json_ld(client, coffee_catalog):
    response = client.get(reverse("product_detail", args=["eth"]))
    html = response.content.decode()
    for block in ("Why you'll love this coffee", "Coffee profile", "Recommended brewing methods", "How to brew",
                  "About the origin", "Frequently asked questions", "Size &amp; grind"):
        assert block in html, block
    data = json.loads(response.context["json_ld"])
    assert data["@type"] == "Product" and data["offers"]["@type"] == "AggregateOffer"
    assert data["offers"]["lowPrice"] == "14.50" and data["offers"]["availability"].endswith("InStock")
    gear = client.get(reverse("product_detail", args=["drp"])).content.decode()
    assert "Specifications" in gear and "Coffee profile" not in gear and "Ceramic" in gear


def test_product_page_sold_out_state(client, coffee_catalog):
    html = client.get(reverse("product_detail", args=["bra"])).content.decode()
    assert "Sold out." in html and 'action="/cart/add/"' not in html and "Notify me" in html


def test_category_ordering_follows_position(client, coffee_catalog):
    Category.objects.filter(slug="equipment").update(position=0)
    response = client.get(reverse("storefront"))
    assert [c.slug for c in response.context["nav_categories"]] == ["equipment", "filter-coffee"]


# ---------------------------------------------------------------------------
# Reviews & newsletter from the storefront
# ---------------------------------------------------------------------------

def test_customer_can_submit_review_which_awaits_moderation(client, coffee_catalog):
    user = User.objects.create_user("bea", "bea@example.test", "S3cret-pass")
    product = coffee_catalog["ETH"]
    url = reverse("review_create", args=[product.slug])
    assert client.post(url, {"rating": 5, "comment": "Lovely"}).status_code == 302  # anonymous -> login redirect
    assert Review.objects.count() == 0
    client.force_login(user)
    client.post(url, {"rating": 5, "comment": "Jasmine all the way."})
    review = Review.objects.get()
    assert review.status == "PENDING" and review.verified_purchase is False
    page = client.get(product.get_absolute_url()).content.decode()
    assert "Jasmine all the way." not in page and "awaiting moderation" in page
    Review.objects.filter(pk=review.pk).update(status="APPROVED")
    assert "Jasmine all the way." in client.get(product.get_absolute_url()).content.decode()
    client.post(url, {"rating": 1, "comment": "again"})
    assert Review.objects.count() == 1


def test_review_is_marked_verified_after_a_paid_order(client, coffee_catalog):
    user = User.objects.create_user("cal", "cal@example.test", "S3cret-pass")
    product = coffee_catalog["COL"]
    cart = services.get_active_cart(user)
    services.add_to_cart(cart, product.variants.first(), 1)
    order = services.checkout(cart)
    services.pay(order, True)
    client.force_login(user)
    client.post(reverse("review_create", args=[product.slug]), {"rating": 4, "comment": "Sweet."})
    assert Review.objects.get().verified_purchase is True


def test_newsletter_subscribe_is_idempotent_and_validates(client, coffee_catalog):
    response = client.post(reverse("newsletter_subscribe"), {"email": "Fan@Example.test", "source": "home", "next": "/"})
    assert response.status_code == 302 and NewsletterSubscriber.objects.get().email == "fan@example.test"
    client.post(reverse("newsletter_subscribe"), {"email": "fan@example.test"})
    assert NewsletterSubscriber.objects.count() == 1
    client.post(reverse("newsletter_subscribe"), {"email": "not-an-email"})
    assert NewsletterSubscriber.objects.count() == 1


# ---------------------------------------------------------------------------
# SEO & static pages
# ---------------------------------------------------------------------------

def test_sitemap_robots_and_static_pages(client, coffee_catalog):
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200 and b"/catalog/eth/" in sitemap.content and b"/about/" in sitemap.content
    robots = client.get("/robots.txt")
    assert robots.status_code == 200 and b"Sitemap:" in robots.content
    assert client.get(reverse("about")).status_code == 200
    assert client.get(reverse("shipping_returns")).status_code == 200
    assert client.get("/catalog/missing-coffee/").status_code == 404


def test_page_titles_and_meta_descriptions(client, coffee_catalog):
    html = client.get(reverse("product_detail", args=["col"])).content.decode()
    assert "<title>Colombia Huila — Apple, caramel |" in html
    assert '<meta name="description" content="Colombia Huila short copy">' in html
    assert '<meta property="og:type" content="product">' in html


# ---------------------------------------------------------------------------
# Admin ↔ storefront
# ---------------------------------------------------------------------------

def test_admin_edit_is_reflected_in_storefront(client, coffee_catalog):
    admin = User.objects.create_superuser("boss", "boss@example.test", "S3cret-pass")
    client.force_login(admin)
    product = coffee_catalog["ETH"]
    changelist = client.get(reverse("admin:catalog_product_changelist"))
    assert changelist.status_code == 200 and "Ethiopia Sidamo" in changelist.content.decode()
    change = client.get(reverse("admin:catalog_product_change", args=[product.pk]))
    assert change.status_code == 200 and 'name="brew_methods"' in change.content.decode()
    form = client.get(reverse("admin:catalog_product_change", args=[product.pk])).context["adminform"].form
    data = {name: (field.value() if field.value() is not None else "") for name, field in ((f.name, f) for f in form)}
    data.update({"name": "Ethiopia Sidamo Reserve", "tasting_notes": "Rose, apricot", "brew_methods": ["aeropress"],
                 "compare_at_price": "17.00", "specs": "{}", "status": "ACTIVE", "active": "on", "featured": "on",
                 "variants-TOTAL_FORMS": 0, "variants-INITIAL_FORMS": 0, "images-TOTAL_FORMS": 0, "images-INITIAL_FORMS": 0,
                 "price_history-TOTAL_FORMS": 0, "price_history-INITIAL_FORMS": 0})
    response = client.post(reverse("admin:catalog_product_change", args=[product.pk]), data)
    assert response.status_code == 302, response.content.decode()[:2000]
    product.refresh_from_db()
    assert product.brew_methods == "aeropress" and product.is_on_sale and product.discount_percent == 15
    page = client.get(product.get_absolute_url()).content.decode()
    assert "Ethiopia Sidamo Reserve" in page and "Rose" in page and "−15%" in page


# ---------------------------------------------------------------------------
# Demo seed
# ---------------------------------------------------------------------------

def test_seed_demo_builds_a_complete_store(client, db):
    call_command("seed_demo", verbosity=0)
    live = Product.objects.storefront()
    assert 15 <= live.count() <= 25 and Product.objects.filter(status="DRAFT").exists()
    assert Category.objects.count() >= 4 and all(c.image_url for c in Category.objects.all())
    assert all(p.images.exists() and p.variants.exists() for p in live)
    assert live.filter(featured=True).count() >= 4 and live.filter(compare_at_price__gt=0).count() >= 3
    assert live.filter(kind="COFFEE").exclude(tasting_notes="").count() >= 10
    assert Review.objects.filter(status="APPROVED").count() >= 20
    call_command("seed_demo", verbosity=0)  # idempotent
    assert Product.objects.count() == 26
    assert client.get(reverse("storefront")).status_code == 200
    assert client.get(live.first().get_absolute_url()).status_code == 200


@pytest.mark.django_db
def test_static_assets_are_cache_busted(client):
    """CSS/JS links carry a version so browsers never render the storefront with a stale stylesheet."""
    html = client.get("/").content.decode()
    assert re.search(r'css/storefront\.css\?v=\d+"', html)
    assert re.search(r'js/storefront\.js\?v=\d+"', html)
