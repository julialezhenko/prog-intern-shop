"""Fixed vocabulary shared by the user and order builders.

The numbers here are what makes the dataset behave like a business rather than like noise: channels
differ in volume, conversion and basket size, countries differ in cancellation and delivery quality,
and devices differ in how well they convert. Nothing in the generated rows says so.
"""
import datetime as dt

# --- acquisition -----------------------------------------------------------------------------
# (channel_group, utm_source, utm_medium, share of new visitors, order propensity, basket factor,
#  refund propensity, repeat propensity, referrer domain, landing page)
CHANNELS = [
    ("Paid Social",   "meta",      "paid_social", 0.26, 0.55, 0.86, 1.75, 0.55, "facebook.com",     "/catalog/?utm=social"),
    ("Paid Search",   "google",    "cpc",         0.20, 1.05, 1.00, 1.00, 0.90, "google.com",       "/catalog/"),
    ("Organic Search","google",    "organic",     0.19, 1.10, 1.02, 0.85, 1.05, "google.com",       "/"),
    ("Direct",        "direct",    "none",        0.14, 1.00, 1.05, 0.80, 1.10, "",                 "/"),
    ("Email",         "newsletter","email",       0.09, 1.55, 1.12, 0.60, 2.10, "",                 "/catalog/?utm=email"),
    ("Referral",      "partner",   "referral",    0.07, 1.15, 1.62, 0.75, 1.25, "cafeblog.es",      "/catalog/coffee/"),
    ("Affiliate",     "affiliate", "affiliate",   0.05, 0.80, 0.92, 1.20, 0.70, "cupsandbeans.com", "/catalog/"),
]

UTM_CAMPAIGNS = {
    "Paid Social":    ["always_on_prospecting", "retargeting_dynamic", "reels_brand", "black_friday_social"],
    "Paid Search":    ["brand_exact", "generic_specialty_coffee", "competitor_terms", "shopping_feed"],
    "Organic Search": [""],
    "Direct":         [""],
    "Email":          ["weekly_roast_note", "welcome_flow", "winback_90d", "subscriber_only_drop"],
    "Referral":       ["blog_partnerships", ""],
    "Affiliate":      ["affiliate_network_q3", "coupon_sites"],
}

# --- geography -------------------------------------------------------------------------------
# (country, iso, market, currency, share, region list, order propensity, basket factor,
#  cancellation factor, delivery days base, language)
COUNTRIES = [
    ("Spain",       "ES", "Iberia",  "EUR", 0.34, ["Comunidad Valenciana", "Madrid", "Cataluna", "Andalucia", "Pais Vasco"], 1.00, 1.00, 1.00, 2.0, "es"),
    ("France",      "FR", "France",  "EUR", 0.12, ["Ile-de-France", "Occitanie", "Nouvelle-Aquitaine", "Bretagne"],          0.95, 1.04, 1.05, 3.0, "fr"),
    ("Germany",     "DE", "DACH",    "EUR", 0.13, ["Bayern", "Berlin", "Nordrhein-Westfalen", "Hamburg"],                    1.05, 1.10, 0.90, 3.2, "de"),
    ("Italy",       "IT", "Italy",   "EUR", 0.09, ["Lombardia", "Lazio", "Piemonte", "Veneto"],                              0.90, 0.94, 2.30, 4.6, "it"),
    ("Portugal",    "PT", "Iberia",  "EUR", 0.06, ["Lisboa", "Porto", "Algarve"],                                            0.92, 0.90, 1.10, 2.6, "pt"),
    ("Netherlands", "NL", "Benelux", "EUR", 0.06, ["Noord-Holland", "Zuid-Holland", "Utrecht"],                              1.08, 1.12, 0.85, 3.1, "nl"),
    ("Belgium",     "BE", "Benelux", "EUR", 0.04, ["Vlaanderen", "Wallonie", "Brussels"],                                    1.00, 1.05, 0.95, 3.0, "nl"),
    ("Sweden",      "SE", "Nordics", "SEK", 0.05, ["Stockholm", "Vastra Gotaland", "Skane"],                                 1.02, 1.34, 0.80, 4.0, "sv"),
    ("Denmark",     "DK", "Nordics", "DKK", 0.03, ["Hovedstaden", "Midtjylland"],                                            1.02, 1.30, 0.80, 4.0, "da"),
    ("Switzerland", "CH", "DACH",    "CHF", 0.03, ["Zurich", "Geneve", "Bern"],                                              0.98, 1.45, 0.85, 4.2, "de"),
    ("United Kingdom","GB","UK",     "GBP", 0.05, ["England", "Scotland", "Wales"],                                          0.88, 1.08, 1.15, 5.0, "en"),
]

CITIES = {
    "ES": ["Valencia", "Madrid", "Barcelona", "Sevilla", "Bilbao", "Zaragoza", "Malaga"],
    "FR": ["Paris", "Toulouse", "Bordeaux", "Lyon", "Nantes"],
    "DE": ["Munchen", "Berlin", "Koln", "Hamburg", "Frankfurt"],
    "IT": ["Milano", "Roma", "Torino", "Bologna"],
    "PT": ["Lisboa", "Porto", "Faro"],
    "NL": ["Amsterdam", "Rotterdam", "Utrecht"],
    "BE": ["Antwerpen", "Brussel", "Gent"],
    "SE": ["Stockholm", "Goteborg", "Malmo"],
    "DK": ["Kobenhavn", "Aarhus"],
    "CH": ["Zurich", "Geneve", "Basel"],
    "GB": ["London", "Manchester", "Edinburgh", "Bristol"],
}

# Reference rates to EUR, jittered slightly per order so analysts see a moving rate.
FX_TO_EUR = {"EUR": 1.0, "GBP": 1.17, "CHF": 1.06, "SEK": 0.087, "DKK": 0.134, "USD": 0.92}

# --- technology ------------------------------------------------------------------------------
# (device, browser choices, os choices, conversion factor, basket factor)
DEVICES = [
    ("desktop", ["Chrome", "Safari", "Firefox", "Edge"], ["Windows", "macOS", "Linux"], 1.00, 1.00),
    ("mobile",  ["Chrome Mobile", "Safari Mobile", "Samsung Internet"], ["iOS", "Android"], 0.55, 0.87),
    ("tablet",  ["Safari Mobile", "Chrome Mobile"], ["iPadOS", "Android"], 0.78, 1.05),
]
# Share of mobile sessions at the start and at the end of the generated period.
MOBILE_SHARE_START, MOBILE_SHARE_END = 0.34, 0.63
TABLET_SHARE = 0.07

# --- payments --------------------------------------------------------------------------------
# (method, share, failure rate, fee percent, fee fixed, settlement days)
PAYMENT_METHODS = [
    ("CARD",         0.52, 0.075, 0.0145, 0.25, 2),
    ("PAYPAL",       0.16, 0.055, 0.0230, 0.35, 1),
    ("APPLE_PAY",    0.11, 0.030, 0.0150, 0.20, 2),
    ("GOOGLE_PAY",   0.06, 0.035, 0.0150, 0.20, 2),
    ("KLARNA",       0.08, 0.110, 0.0290, 0.40, 7),
    ("BANK_TRANSFER",0.05, 0.020, 0.0000, 0.00, 4),
    ("GIFT_CARD",    0.02, 0.010, 0.0000, 0.00, 0),
]
CARD_BRANDS = ["visa", "mastercard", "amex", "maestro"]
FAILURE_CODES = [("insufficient_funds", 0.34), ("do_not_honor", 0.24), ("expired_card", 0.12),
                 ("incorrect_cvc", 0.10), ("card_velocity_exceeded", 0.07), ("issuer_unavailable", 0.07),
                 ("fraud_suspected", 0.06)]

# --- fulfilment ------------------------------------------------------------------------------
# (carrier, markets served, base transit days, failure rate, cost)
CARRIERS = [
    ("Correos Express", {"Iberia"},                    1.6, 0.010, 3.90),
    ("SEUR",            {"Iberia", "France"},          2.1, 0.014, 4.60),
    ("DHL",             {"DACH", "Benelux", "France"}, 2.4, 0.008, 6.20),
    ("GLS",             {"DACH", "Benelux", "Nordics", "France", "Italy"}, 3.0, 0.017, 5.40),
    ("Poste Italiane",  {"Italy"},                     4.4, 0.045, 4.20),
    ("Royal Mail",      {"UK"},                        3.4, 0.022, 6.80),
    ("PostNord",        {"Nordics"},                   3.2, 0.015, 7.10),
]
SERVICE_LEVELS = [("STANDARD", 0.74), ("EXPRESS", 0.14), ("PICKUP_POINT", 0.11), ("SAME_DAY", 0.01)]

# --- customers -------------------------------------------------------------------------------
SEGMENTS = [("RETAIL", 0.855), ("HORECA", 0.075), ("CORPORATE", 0.045), ("WHOLESALE", 0.025)]
SEGMENT_BASKET = {"RETAIL": 1.0, "HORECA": 3.4, "CORPORATE": 4.1, "WHOLESALE": 8.5}
TIERS = [("BRONZE", 0.62), ("SILVER", 0.27), ("GOLD", 0.11)]

FIRST_NAMES = [
    "Anna", "Marta", "Laura", "Elena", "Carmen", "Lucia", "Paula", "Sofia", "Clara", "Irene", "Nuria", "Alba",
    "Javier", "Carlos", "Miguel", "Pablo", "Sergio", "Alvaro", "Diego", "Hugo", "Adrian", "Ruben", "Ivan",
    "Sophie", "Camille", "Juliette", "Manon", "Chloe", "Louis", "Hugo", "Nathan", "Theo", "Antoine",
    "Lena", "Hannah", "Emilia", "Mia", "Lukas", "Jonas", "Felix", "Tobias", "Matthias", "Sebastian",
    "Giulia", "Chiara", "Francesca", "Alessandro", "Lorenzo", "Matteo", "Marco",
    "Sanne", "Femke", "Daan", "Sven", "Bram", "Astrid", "Ingrid", "Erik", "Nils", "Oskar", "Freja",
    "Emily", "Olivia", "Jack", "Harry", "Grace", "Ana", "Ines", "Tiago", "Rui",
]
LAST_NAMES = [
    "Garcia", "Martinez", "Lopez", "Sanchez", "Perez", "Gomez", "Fernandez", "Ruiz", "Diaz", "Moreno",
    "Alvarez", "Romero", "Navarro", "Torres", "Vidal", "Serrano", "Blanco", "Castro",
    "Dubois", "Lefevre", "Moreau", "Laurent", "Girard", "Bonnet",
    "Muller", "Schmidt", "Schneider", "Fischer", "Weber", "Wagner", "Becker", "Hoffmann",
    "Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Conti",
    "de Vries", "van Dijk", "Bakker", "Jansen", "Visser",
    "Andersson", "Johansson", "Karlsson", "Nilsson", "Larsen", "Nielsen", "Hansen",
    "Smith", "Jones", "Taylor", "Brown", "Wilson", "Silva", "Costa", "Oliveira",
]
COMPANY_WORDS = ["Cafe", "Roasters", "Bar", "Bistro", "Kaffee", "Coffee House", "Espresso Bar", "Deli", "Studio", "Collective"]

# E-mail domain reserved by RFC 2606: nothing sent there can reach a real person.
TEST_EMAIL_DOMAIN = "example.com"

SEARCH_TERMS = ["ethiopia", "decaf", "espresso blend", "v60", "filter coffee", "gift box", "grinder",
                "cold brew", "subscription", "single origin", "colombia", "light roast", "chemex"]

CANCEL_REASONS = [("CUSTOMER_REQUEST", 0.33), ("PAYMENT_TIMEOUT", 0.24), ("PAYMENT_FAILED", 0.16),
                  ("OUT_OF_STOCK", 0.12), ("ADDRESS_INVALID", 0.07), ("SUSPECTED_FRAUD", 0.05), ("DUPLICATE", 0.03)]
RETURN_REASONS = [("TASTE_NOT_AS_EXPECTED", 0.25), ("CHANGED_MIND", 0.19), ("DAMAGED", 0.14), ("LATE_DELIVERY", 0.12),
                  ("WRONG_PRODUCT", 0.10), ("STALE_ON_ARRIVAL", 0.09), ("DEFECTIVE", 0.07), ("OTHER", 0.04)]
SUBSCRIPTION_CANCEL_REASONS = [("TOO_MUCH_COFFEE", 0.26), ("PRICE", 0.21), ("SWITCHED_ROASTER", 0.15),
                               ("DELIVERY_ISSUES", 0.14), ("QUALITY", 0.10), ("MOVED", 0.08), ("PAYMENT_FAILED", 0.06)]

# --- demand shape ------------------------------------------------------------------------------
# Month-of-year multiplier: gifting peaks in Nov/Dec, the Spanish summer is quiet.
MONTH_FACTOR = {1: 0.78, 2: 0.88, 3: 0.97, 4: 1.00, 5: 1.03, 6: 0.94,
                7: 0.72, 8: 0.66, 9: 1.14, 10: 1.12, 11: 1.46, 12: 1.88}
WEEKDAY_FACTOR = {0: 1.12, 1: 1.14, 2: 1.08, 3: 1.05, 4: 0.98, 5: 0.82, 6: 0.81}
MONTHLY_GROWTH = 0.018  # compounding underlying growth of the business

# Days that get an unusual traffic or demand spike, expressed as (month, day, factor).
SPIKE_DAYS = [(11, 29, 4.2), (11, 30, 2.6), (12, 1, 2.1), (7, 12, 2.4)]


def month_index(day: dt.date, start: dt.date) -> int:
    return (day.year - start.year) * 12 + (day.month - start.month)
