import pytest
from django.contrib.auth.models import User
from catalog.models import Brand,Category,Product,ProductVariant
from operations.models import Warehouse,Inventory
from sales.models import Cart,CartItem
from sales.services import checkout,pay,transition

@pytest.mark.django_db
def test_checkout_payment_shipment_workflow():
    u=User.objects.create_user("buyer"); c=Category.objects.create(name="Home",slug="home"); b=Brand.objects.create(name="Acme",slug="acme"); p=Product.objects.create(sku="P1",name="Lamp",slug="lamp",category=c,brand=b,purchase_cost=10,sale_price=20,tax_rate=20); v=ProductVariant.objects.create(product=p,sku="P1-S",name="Standard"); w=Warehouse.objects.create(name="Madrid",code="MAD",city="Madrid"); inv=Inventory.objects.create(variant=v,warehouse=w,physical=5); cart=Cart.objects.create(customer=u); CartItem.objects.create(cart=cart,variant=v,quantity=2)
    order=checkout(cart); inv.refresh_from_db(); assert inv.reserved==2 and order.items.first().product_name=="Lamp"
    pay(order); transition(order,"PROCESSING"); transition(order,"PACKED"); transition(order,"SHIPPED"); inv.refresh_from_db(); assert (inv.physical,inv.reserved)==(3,0)

