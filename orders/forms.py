from django import forms
from .models import Order


class OrderForm(forms.ModelForm):
    """
    Customer-details form for the checkout page.

    Built from the existing Order model fields.
    """

    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'address', 'city', 'postal_code']
        labels = {
            'first_name': 'First name',
            'last_name': 'Last name',
            'email': 'Email address',
            'address': 'Shipping address',
            'city': 'City',
            'postal_code': 'Postal / ZIP code',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={
                'placeholder': 'Jane',
                'class': 'checkout-input',
                'autocomplete': 'given-name',
            }),
            'last_name': forms.TextInput(attrs={
                'placeholder': 'Doe',
                'class': 'checkout-input',
                'autocomplete': 'family-name',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'jane@example.com',
                'class': 'checkout-input',
                'autocomplete': 'email',
            }),
            'address': forms.TextInput(attrs={
                'placeholder': '123 Rose Garden Lane',
                'class': 'checkout-input',
                'autocomplete': 'street-address',
            }),
            'city': forms.TextInput(attrs={
                'placeholder': 'Mumbai',
                'class': 'checkout-input',
                'autocomplete': 'address-level2',
            }),
            'postal_code': forms.TextInput(attrs={
                'placeholder': '400001',
                'class': 'checkout-input',
                'autocomplete': 'postal-code',
            }),
        }
