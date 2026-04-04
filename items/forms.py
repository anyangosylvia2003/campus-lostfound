from django import forms
from django.conf import settings
from .models import Item, CAMPUS_LOCATIONS
import os


class ItemForm(forms.ModelForm):
    """Single form for both Lost and Found items with all structured fields."""

    class Meta:
        model = Item
        fields = [
            'title', 'description', 'item_type', 'category',
            'brand', 'color',
            'location', 'location_detail',
            'date', 'time_of_day',
            'image',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief title, e.g. "Black Samsung laptop"',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Describe the item — model, markings, contents...',
            }),
            'item_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Apple, Samsung, Nike (optional)',
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Black, Silver, Blue/White (optional)',
            }),
            'location': forms.Select(attrs={'class': 'form-select'},
                                     choices=CAMPUS_LOCATIONS),
            'location_detail': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Extra detail — floor, room number, near what? (optional)',
            }),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time_of_day': forms.TimeInput(attrs={
                'class': 'form-control', 'type': 'time',
            }),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and not isinstance(image, str):
            if image.size > settings.MAX_UPLOAD_SIZE:
                raise forms.ValidationError("Image must be smaller than 5MB.")
            ext = os.path.splitext(image.name)[1].lower()
            allowed = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            if ext not in allowed:
                raise forms.ValidationError("Only JPEG, PNG, GIF, and WebP images are allowed.")
        return image


class SearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by title, description, brand...',
        })
    )
    item_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + Item.TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'All Categories')] + Item.CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    color = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Color (optional)',
        })
    )
    location = forms.ChoiceField(
        required=False,
        choices=[('', 'All Locations')] + [(loc, loc) for _, loc in CAMPUS_LOCATIONS if loc],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + Item.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ContactOwnerForm(forms.Form):
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. I think I found your item!',
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Describe how you can help, where you are, best time to meet, etc.',
        })
    )
