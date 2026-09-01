from decimal import Decimal

from django import template
from django.utils.html import format_html, mark_safe

from catalog.content import BREW_METHODS, ROAST_SCALE

register = template.Library()


@register.filter
def money(value):
    """Format a Decimal/number as 12.50 (no currency) — templates prepend the store currency."""
    if value in (None, ""):
        return ""
    return f"{Decimal(value).quantize(Decimal('0.01')):,.2f}"


@register.filter
def brew_method(code):
    return BREW_METHODS.get(code, (code.replace("_", " ").title(), "", ""))


@register.filter
def brew_methods_for(product):
    return [(code, *BREW_METHODS[code]) for code in product.brew_method_codes if code in BREW_METHODS]


@register.filter
def roast_index(level):
    return ROAST_SCALE.index(level) + 1 if level in ROAST_SCALE else 0


@register.simple_tag
def stars(rating, size="sm"):
    """Accessible 5-star rating; rating may be a float average."""
    try:
        value = float(rating or 0)
    except (TypeError, ValueError):
        value = 0
    full = int(value + 0.5)
    glyphs = "".join('<span class="star on">★</span>' if i < full else '<span class="star">★</span>' for i in range(5))
    return format_html('<span class="stars {}" role="img" aria-label="Rated {} out of 5">{}</span>', size, f"{value:.1f}", mark_safe(glyphs))


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Current querystring with some parameters replaced/removed (value None removes)."""
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value is None or value == "":
            params.pop(key, None)
        else:
            params[key] = value
    params.pop("page", None)
    return params.urlencode()


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None


@register.filter
def initials(user):
    name = (getattr(user, "first_name", "") or getattr(user, "username", "") or "?").strip()
    return name[:1].upper()


@register.filter
def display_name(user):
    first, last = (getattr(user, "first_name", "") or "").strip(), (getattr(user, "last_name", "") or "").strip()
    if first:
        return f"{first} {last[:1]}." if last else first
    return getattr(user, "username", "Customer")


@register.filter
def img(url, params="w=900&q=75"):
    """Append sizing parameters to Unsplash/imgix style URLs; leave uploaded files untouched."""
    if not url or "images.unsplash.com" not in url:
        return url
    base = url.split("?")[0]
    return f"{base}?auto=format&fit=crop&{params}"
