from django import forms

COUNTRIES = ["Spain", "Portugal", "France", "Germany", "Italy", "Netherlands", "Poland", "Other"]


class AddToCartForm(forms.Form):
    variant = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    quantity = forms.IntegerField(min_value=1, max_value=99, initial=1)


class UpdateCartItemForm(forms.Form):
    item = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    quantity = forms.IntegerField(min_value=0, max_value=99)


class DiscountForm(forms.Form):
    code = forms.CharField(max_length=40, required=False, widget=forms.TextInput(attrs={"placeholder": "Discount code"}))


class CheckoutForm(forms.Form):
    shipping_name = forms.CharField(label="Full name", max_length=160)
    contact_email = forms.EmailField(label="Email", help_text="Guests receive the order link at this address.")
    contact_phone = forms.CharField(label="Phone", max_length=40, required=False)
    shipping_address = forms.CharField(label="Street address", max_length=255)
    shipping_city = forms.CharField(label="City", max_length=80)
    shipping_postal_code = forms.CharField(label="Postal code", max_length=20)
    shipping_country = forms.ChoiceField(label="Country", choices=[(c, c) for c in COUNTRIES], initial="Spain")
    customer_note = forms.CharField(label="Delivery note", max_length=500, required=False,
                                    widget=forms.Textarea(attrs={"rows": 2}))


class CardPaymentForm(forms.Form):
    """Card details are passed straight to the gateway and never stored (only the last four digits are kept)."""
    holder = forms.CharField(label="Name on card", max_length=120)
    number = forms.CharField(label="Card number", max_length=23,
                             widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "cc-number",
                                                           "placeholder": "4242 4242 4242 4242"}))
    expiry = forms.CharField(label="Expiry (MM/YY)", max_length=5,
                             widget=forms.TextInput(attrs={"placeholder": "12/30", "autocomplete": "cc-exp"}))
    cvc = forms.CharField(label="CVC", max_length=4, widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "cc-csc"}))

    def clean_number(self):
        digits = "".join(ch for ch in self.cleaned_data["number"] if ch.isdigit())
        if len(digits) < 12:
            raise forms.ValidationError("Enter a valid card number.")
        return digits

    def clean_expiry(self):
        value = self.cleaned_data["expiry"].strip()
        try:
            month, year = value.split("/")
            month, year = int(month), int(year)
        except ValueError:
            raise forms.ValidationError("Use the MM/YY format.")
        from datetime import date
        if not 1 <= month <= 12:
            raise forms.ValidationError("Invalid month.")
        today = date.today()
        if (2000 + year, month) < (today.year, today.month):
            raise forms.ValidationError("This card has expired.")
        return value

    def clean_cvc(self):
        cvc = self.cleaned_data["cvc"].strip()
        if not cvc.isdigit() or len(cvc) not in (3, 4):
            raise forms.ValidationError("CVC must be 3 or 4 digits.")
        return cvc
