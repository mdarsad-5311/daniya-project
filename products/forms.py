from django import forms

from .models import Review


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