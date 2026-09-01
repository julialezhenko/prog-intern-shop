from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(choices=[(i, f"{i} star{'s' if i > 1 else ''}") for i in range(5, 0, -1)], coerce=int,
                                    widget=forms.RadioSelect, initial=5)

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 4, "placeholder": "How did you brew it? What did you taste?"})}


class NewsletterForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "aria-label": "Email address",
                                                            "autocomplete": "email"}))
    source = forms.CharField(required=False, widget=forms.HiddenInput, initial="footer")
