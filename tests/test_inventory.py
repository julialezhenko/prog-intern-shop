import pytest
from catalog.models import Brand,Category,Product,ProductVariant
from operations.models import Warehouse,Inventory,InventoryMovement
from operations.services import reserve,release,ship
from rest_framework.exceptions import ValidationError

@pytest.fixture
def stock(db):
    c=Category.objects.create(name="Electronics",slug="electronics"); b=Brand.objects.create(name="Acme",slug="acme"); p=Product.objects.create(sku="P1",name="Phone",slug="phone",category=c,brand=b,purchase_cost=100,sale_price=200); v=ProductVariant.objects.create(product=p,sku="P1-B",name="Black"); w=Warehouse.objects.create(name="Madrid",code="MAD",city="Madrid"); return Inventory.objects.create(variant=v,warehouse=w,physical=10)

def test_reserve_release_and_ship_are_traceable(stock):
    reserve(stock.variant_id,stock.warehouse_id,4,"TEST","1"); stock.refresh_from_db(); assert stock.available==6
    release(stock.variant_id,stock.warehouse_id,1,"TEST","1"); ship(stock.variant_id,stock.warehouse_id,3,"TEST","1"); stock.refresh_from_db(); assert (stock.physical,stock.reserved)==(7,0); assert InventoryMovement.objects.count()==3

def test_cannot_oversell(stock):
    with pytest.raises(ValidationError): reserve(stock.variant_id,stock.warehouse_id,11,"TEST","1")

