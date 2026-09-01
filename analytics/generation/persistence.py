"""Bulk-writing helpers.

Two things matter here:

* rows go in with ``bulk_create``, which does not fire ``post_save``, so nothing the shop normally does
  on save (confirmation e-mails, gateway calls, stock movements) can be triggered by generated data;
* ``auto_now_add`` columns are rewritten afterwards, because ``bulk_create`` stamps them with "now" and
  the whole point of the dataset is that it lies in the past.
"""
from django.db import transaction

CHUNK = 2_000


def _auto_now_add_fields(model, wanted):
    return [f for f in wanted if getattr(model._meta.get_field(f), "auto_now_add", False)]


def bulk_insert(model, objects, historic_fields=(), chunk=CHUNK):
    """Insert ``objects`` in chunks and restore any ``auto_now_add`` values listed in ``historic_fields``.

    Each chunk commits on its own: the writer never holds a long transaction, which keeps the admin
    progress page readable while a large run is in flight.
    """
    if not objects:
        return []
    created = []
    fixups = _auto_now_add_fields(model, historic_fields)
    for start in range(0, len(objects), chunk):
        window = objects[start:start + chunk]
        if fixups:
            keep = [{f: getattr(o, f) for f in fixups} for o in window]
        with transaction.atomic():
            model.objects.bulk_create(window, batch_size=chunk)
            if fixups:
                for obj, values in zip(window, keep):
                    for name, value in values.items():
                        setattr(obj, name, value)
                model.objects.bulk_update(window, fixups, batch_size=chunk)
        created.extend(window)
    return created
