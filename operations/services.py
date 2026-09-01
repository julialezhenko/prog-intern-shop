from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Inventory,InventoryMovement
def _row(variant_id,warehouse_id): return Inventory.objects.select_for_update().get(variant_id=variant_id,warehouse_id=warehouse_id)
@transaction.atomic
def reserve(variant_id,warehouse_id,quantity,ref_type,ref_id):
    if quantity<=0: raise ValidationError("Quantity must be positive")
    row=_row(variant_id,warehouse_id)
    if row.available<quantity: raise ValidationError("Insufficient available stock")
    row.reserved+=quantity; row.save(update_fields=["reserved"]); InventoryMovement.objects.create(inventory=row,kind="RESERVE",quantity=quantity,reference_type=ref_type,reference_id=ref_id); return row
@transaction.atomic
def release(variant_id,warehouse_id,quantity,ref_type,ref_id):
    row=_row(variant_id,warehouse_id)
    if row.reserved<quantity: raise ValidationError("Cannot release more than reserved")
    row.reserved-=quantity; row.save(update_fields=["reserved"]); InventoryMovement.objects.create(inventory=row,kind="RELEASE",quantity=quantity,reference_type=ref_type,reference_id=ref_id); return row
@transaction.atomic
def ship(variant_id,warehouse_id,quantity,ref_type,ref_id):
    row=_row(variant_id,warehouse_id)
    if row.reserved<quantity or row.physical<quantity: raise ValidationError("Invalid shipment quantity")
    row.physical-=quantity; row.reserved-=quantity; row.save(update_fields=["physical","reserved"]); InventoryMovement.objects.create(inventory=row,kind="SHIP",quantity=-quantity,reference_type=ref_type,reference_id=ref_id); return row
@transaction.atomic
def receive(variant_id,warehouse_id,quantity,ref_type,ref_id):
    row=Inventory.objects.select_for_update().get_or_create(variant_id=variant_id,warehouse_id=warehouse_id)[0]; row.physical+=quantity; row.incoming=max(0,row.incoming-quantity); row.save(); InventoryMovement.objects.create(inventory=row,kind="RECEIPT",quantity=quantity,reference_type=ref_type,reference_id=ref_id); return row

