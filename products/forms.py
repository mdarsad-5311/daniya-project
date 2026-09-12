from django import forms
from .models import Review, ContactMessage


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'comment')
        widgets = {
            'rating': forms.Select(choices=[(rating, f'{rating} star') for rating in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 4, 'maxlength': 1000}),
        }

    def clean_rating(self):
        rating = self.cleaned_data['rating']
        if not 1 <= rating <= 5:
            raise forms.ValidationError('Rating must be between 1 and 5 stars.')
        return rating


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ('name', 'email', 'subject', 'message')
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Your name',
                'class': 'flex h-10 w-full rounded-2xl border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#486551]',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'you@email.com',
                'class': 'flex h-10 w-full rounded-2xl border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#486551]',
            }),
            'subject': forms.TextInput(attrs={
                'placeholder': 'How can we help?',
                'class': 'flex h-10 w-full rounded-2xl border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#486551]',
            }),
            'message': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Tell us more…',
                'class': 'flex min-h-[80px] w-full rounded-2xl border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#486551]',
            }),
        }