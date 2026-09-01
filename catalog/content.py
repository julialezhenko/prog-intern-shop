"""Static storefront content: brewing methods, FAQ blocks, trust badges.

Kept in code (not the database) because it is editorial copy that changes with a deploy,
while products, prices and stock live in the admin.
"""

# code -> (label, short description, inline SVG icon)
_ICON = {
    "cone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h16l-6 10v4H10v-4L4 5z"/><path d="M7 5l5 8 5-8"/></svg>',
    "flask": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3h6M10 3v5l-5 9a3 3 0 0 0 2.6 4.5h8.8A3 3 0 0 0 19 17l-5-9V3"/><path d="M8.5 14h7"/></svg>',
    "press": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="8" width="12" height="13" rx="2"/><path d="M12 3v5M9 3h6M6 13h12"/></svg>',
    "cup": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h12v6a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V8z"/><path d="M16 10h2a2.5 2.5 0 0 1 0 5h-2M6 4c.5.8.5 1.6 0 2.4M9.5 4c.5.8.5 1.6 0 2.4M13 4c.5.8.5 1.6 0 2.4"/></svg>',
    "moka": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3h8l1 7H7l1-7zM7 10l-1 10h12l-1-10"/><path d="M18 12h2v3h-2"/></svg>',
    "ice": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M7 4h10l-1 16H8L7 4z"/><path d="M7.5 10h9M10 13l2 2 2-2"/></svg>',
    "pot": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9h12v9a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3V9z"/><path d="M9 9V6a3 3 0 0 1 6 0v3M18 12h1.5a1.5 1.5 0 0 1 0 3H18"/></svg>',
}

BREW_METHODS = {
    "v60": ("V60 / pour-over", "Clean, bright cups that show off origin character.", _ICON["cone"]),
    "chemex": ("Chemex", "Thick filter, very clean body — great for sharing.", _ICON["flask"]),
    "aeropress": ("AeroPress", "Fast, forgiving and sweet; perfect for travel.", _ICON["press"]),
    "french_press": ("French press", "Full body and heavy texture; grind coarse.", _ICON["pot"]),
    "espresso": ("Espresso", "Concentrated, syrupy shots; also great with milk.", _ICON["cup"]),
    "moka": ("Moka pot", "Strong stovetop coffee with a classic Mediterranean profile.", _ICON["moka"]),
    "cold_brew": ("Cold brew", "Slow-steeped, low acidity and naturally sweet.", _ICON["ice"]),
    "batch": ("Batch brewer", "Consistent filter coffee for the office or a crowd.", _ICON["flask"]),
}

ROAST_SCALE = ["LIGHT", "MEDIUM_LIGHT", "MEDIUM", "MEDIUM_DARK", "DARK"]

TRUST_POINTS = [
    ("Roasted to order", "Every bag is roasted in Valencia the week it ships, with the roast date printed on the label."),
    ("Free EU shipping", "Free tracked delivery across the EU on every order, dispatched within 48 hours."),
    ("Traceable sourcing", "We buy from named farms and washing stations and pay well above the commodity price."),
    ("Happiness guarantee", "Not your cup? Tell us within 30 days and we will replace it or refund you."),
]

COFFEE_FAQ = [
    ("How fresh is the coffee when it arrives?",
     "We roast in small batches several times a week and ship within 48 hours of roasting. The roast date is printed on every bag; most coffees taste best between 7 and 35 days after roasting."),
    ("Should I buy whole bean or ground?",
     "Whole bean keeps its aroma for weeks longer. If you do not have a grinder, choose a ground option that matches your brewer — we grind immediately before packing."),
    ("How should I store the coffee?",
     "Keep the bag sealed with the one-way valve, away from light, heat and moisture. Do not refrigerate or freeze opened bags — condensation is the enemy of flavour."),
    ("What do the tasting notes mean?",
     "They describe the flavours our cupping table finds in the coffee — nothing is added. A light roast washed Ethiopian naturally tastes floral and tea-like; a Brazilian natural tastes chocolatey and nutty."),
    ("Which coffee should I pick for my brewer?",
     "Use the 'Suitable for' icons on each product. Light roasts shine in pour-over brewers, while medium and medium-dark roasts are easier to dial in on espresso and moka pots."),
]

EQUIPMENT_FAQ = [
    ("Does the equipment come with a warranty?",
     "Yes — two years against manufacturing defects on all grinders, kettles and scales, and 12 months on glass and ceramic."),
    ("Can I return an item I have opened?",
     "Unused brewing equipment can be returned within 30 days in its original packaging. Coffee and filters are perishable and cannot be returned once opened."),
    ("Do you ship equipment together with coffee?",
     "Yes. Everything in one order ships together from the nearest warehouse, usually within 48 hours."),
]

SHIPPING_FAQ = [
    ("How much is shipping?",
     "Shipping is free on every order within the EU. Orders are dispatched from Valencia, Madrid or Barcelona within 48 hours and typically arrive in 1–3 working days in Spain and 3–6 days elsewhere in the EU."),
    ("Can I change or cancel my order?",
     "You can cancel from the order page until the order is packed. After that, contact us and we will sort it out."),
    ("Is payment secure?",
     "Card details are sent straight to the payment provider and never touch our servers. This demo store uses a simulated gateway, so no real charge is ever made."),
    ("Do you offer subscriptions?",
     "Yes — pick a filter or espresso subscription, choose the rhythm, and pause or skip any time from your account."),
]

HOME_FAQ = COFFEE_FAQ[:3] + SHIPPING_FAQ[:2]

STORE_FACTS = {
    "founded": 2017,
    "city": "Valencia",
    "origins": 9,
    "roast_days": "Mon · Wed · Fri",
}
