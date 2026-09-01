import pytest
from django.contrib.auth.models import User,Group
from rest_framework.test import APIClient
from catalog.models import Brand,Category,Product

@pytest.mark.django_db
def test_catalog_public_read_but_write_requires_staff():
    c=Category.objects.create(name="Toys",slug="toys"); b=Brand.objects.create(name="Acme",slug="acme"); Product.objects.create(sku="T1",name="Toy",slug="toy",category=c,brand=b,purchase_cost=1,sale_price=2)
    client=APIClient(); assert client.get("/api/catalog/products/").status_code==200; u=User.objects.create_user("customer"); client.force_authenticate(u); assert client.delete("/api/catalog/products/1/").status_code==403

@pytest.mark.django_db
def test_analytics_role_is_enforced():
    client=APIClient(); u=User.objects.create_user("customer"); client.force_authenticate(u); assert client.get("/api/analytics/sales/").status_code==403
    g=Group.objects.create(name="Analyst"); u.groups.add(g); assert client.get("/api/analytics/sales/").status_code==200

