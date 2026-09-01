import random,uuid
from datetime import datetime,timedelta,time
from django.contrib.auth.models import User,Group
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import CustomerProfile
from catalog.models import Product
from operations.models import ProductEvent
from sales.models import Cart,CartItem,Order,Payment
from sales.services import checkout,pay,transition
class Command(BaseCommand):
    help="Generate deterministic, seasonal and popularity-weighted commerce activity"
    def add_arguments(self,p):
        p.add_argument("--days",type=int,default=30); p.add_argument("--customers",type=int,default=200); p.add_argument("--start-date"); p.add_argument("--seed",type=int,default=42)
    def handle(self,*a,**o):
        rng=random.Random(o["seed"]); products=list(Product.objects.filter(active=True).prefetch_related("variants"));
        if not products: self.stderr.write("Run seed_demo first"); return
        start=datetime.strptime(o["start_date"],"%Y-%m-%d").date() if o["start_date"] else timezone.now().date()-timedelta(days=o["days"])
        group=Group.objects.get_or_create(name="Customer")[0]; sources=["google","meta","organic","email","referral","direct"]
        customers=[]
        for i in range(o["customers"]):
            username=f"sim{o['seed']}_{i:05}"; u,_=User.objects.get_or_create(username=username); u.groups.add(group); CustomerProfile.objects.get_or_create(user=u,defaults={"country":rng.choice(["Spain","France","Germany","Portugal"]),"city":rng.choice(["Madrid","Valencia","Barcelona"]),"acquisition_source":rng.choices(sources,[25,20,25,12,8,10])[0]}); customers.append(u)
        weights=[1/(i+1)**0.8 for i in range(len(products))]
        for day in range(o["days"]):
            date=start+timedelta(days=day); seasonal=1.8 if (date.month==11 and date.day>=20) or date.month==12 else 1.0; weekend=1.2 if date.weekday()>=5 else 1.0
            for _ in range(max(1,int(len(customers)*.10*seasonal*weekend))):
                customer=rng.choice(customers); product=rng.choices(products,weights=weights,k=1)[0]; ts=timezone.make_aware(datetime.combine(date,time(rng.randrange(8,23),rng.randrange(60)))); session=uuid.uuid4().hex; source=customer.customer_profile.acquisition_source
                ProductEvent.objects.create(kind="SESSION_STARTED",customer=customer,session_id=session,source=source,created_at=ts); ProductEvent.objects.create(kind="PRODUCT_VIEWED",customer=customer,session_id=session,product=product,source=source,created_at=ts)
                if rng.random()<.18:
                    ProductEvent.objects.create(kind="ADD_TO_CART",customer=customer,session_id=session,product=product,source=source,created_at=ts); cart=Cart.objects.create(customer=customer); CartItem.objects.create(cart=cart,variant=product.variants.first(),quantity=1)
                    if rng.random()<.55:
                        ProductEvent.objects.create(kind="CHECKOUT_STARTED",customer=customer,session_id=session,product=product,source=source,created_at=ts)
                        try:
                            order=checkout(cart); payment=pay(order,rng.random()>.08)
                            Order.objects.filter(pk=order.pk).update(created_at=ts); Payment.objects.filter(pk=payment.pk).update(created_at=ts)
                            if payment.status=="SUCCEEDED": ProductEvent.objects.create(kind="PURCHASE_COMPLETED",customer=customer,session_id=session,product=product,source=source,created_at=ts)
                        except Exception: cart.delete()
        self.fulfil(rng)
        self.stdout.write(self.style.SUCCESS(f"Simulation complete: {o['days']} days, seed {o['seed']}"))

    @staticmethod
    def fulfil(rng):
        """Move paid orders along the fulfilment pipeline by age: shipped after 2 days, delivered after 6, a few cancelled."""
        now=timezone.now()
        for order in Order.objects.filter(status="PAID").order_by("created_at"):
            age=(now-order.created_at).days
            try:
                if age>=2 and rng.random()<.05: transition(order,"CANCELLED",note="Cancelled by customer (simulated)"); continue
                if age>=1: transition(order,"PROCESSING",note="Simulated")
                if age>=2: transition(order,"PACKED",note="Simulated"); transition(order,"SHIPPED",note="Simulated")
                if age>=6: transition(order,"DELIVERED",note="Simulated")
            except Exception: continue
