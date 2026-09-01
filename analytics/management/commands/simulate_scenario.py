from decimal import Decimal
from django.core.management.base import BaseCommand,CommandError
from catalog.models import Product,PriceHistory
from operations.models import Campaign,Inventory,Supplier
class Command(BaseCommand):
    help="Inject a named educational anomaly"
    def add_arguments(self,p): p.add_argument("scenario",choices=["bad_supplier","failed_campaign","stockout","price_increase","fraud_spike","logistics_delay","return_spike"])
    def handle(self,*a,**o):
        s=o["scenario"]
        if s=="bad_supplier": Supplier.objects.order_by("id").update(reliability_score=65)
        elif s=="failed_campaign": c=Campaign.objects.order_by("-spend").first(); c.spend*=3; c.save()
        elif s=="stockout": Inventory.objects.filter(variant__product=Product.objects.first()).update(physical=0,reserved=0)
        elif s=="price_increase":
            p=Product.objects.first(); old=p.sale_price; p.sale_price=(old*Decimal("1.20")).quantize(Decimal(".01")); p.save(); PriceHistory.objects.create(product=p,old_price=old,new_price=p.sale_price)
        elif s=="logistics_delay": Supplier.objects.update(default_lead_days=45)
        self.stdout.write(self.style.SUCCESS(f"Injected scenario: {s}"))
