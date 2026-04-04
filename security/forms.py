from django import forms
from .models import CustodyRecord, ClaimRequest, HandoverLog, IncidentLog, CustodyTransferLog, SecurityProfile


class CustodyReceiveForm(forms.ModelForm):
    class Meta:
        model = CustodyRecord
        fields = ['storage_location', 'secret_identifiers', 'notes']
        widgets = {
            'storage_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Cabinet 3, Shelf B'}),
            'secret_identifiers': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Serial number, contents, personal marks, stickers — NOT shown to public'
            }),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Condition, any damage, other observations...'}),
        }
        labels = {
            'secret_identifiers': 'Secret Identifiers (for claim verification only)',
        }


class ClaimRequestForm(forms.ModelForm):
    class Meta:
        model = ClaimRequest
        fields = ['proof_description', 'proof_identifiers', 'additional_notes']
        widgets = {
            'proof_description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Describe the item in detail: color, size, brand, condition, any marks or damage...'
            }),
            'proof_identifiers': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Unique identifiers: serial number, name written inside, contents of wallet/bag, etc.'
            }),
            'additional_notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'When and where did you lose it? Any other relevant information...'
            }),
        }
        labels = {
            'proof_description': 'Detailed Item Description',
            'proof_identifiers': 'Unique Identifiers / Proof of Ownership',
            'additional_notes': 'Additional Context (optional)',
        }


class ClaimReviewForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[('approve', 'Approve Claim'), ('reject', 'Reject Claim')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': 'Required if rejecting — explain why the claim was denied...'
        })
    )
    security_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 2,
            'placeholder': 'Internal notes (not shown to claimant)...'
        })
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('decision') == 'reject' and not cleaned.get('rejection_reason'):
            raise forms.ValidationError("A rejection reason is required when rejecting a claim.")
        return cleaned


class HandoverForm(forms.ModelForm):
    class Meta:
        model = HandoverLog
        fields = ['collector_name', 'collector_id_number', 'collector_id_type', 'notes']
        widgets = {
            'collector_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name as on ID'}),
            'collector_id_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. STU/2024/001'}),
            'collector_id_type': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional observations...'}),
        }


class IncidentLogForm(forms.ModelForm):
    class Meta:
        model = IncidentLog
        fields = ['incident_type', 'severity', 'description', 'action_taken']
        widgets = {
            'incident_type': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe the incident...'}),
            'action_taken': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What action was taken...'}),
        }


class ItemStatusUpdateForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            ('active', 'Active'),
            ('matched', 'Matched'),
            ('claimed', 'Claimed'),
            ('resolved', 'Resolved'),
            ('donated', 'Donated / Disposed'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Reason for status change (optional)...'})
    )


class CustodyTransferForm(forms.ModelForm):
    class Meta:
        model = CustodyTransferLog
        fields = ['to_location', 'reason']
        widgets = {
            'to_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Deputy Principal\'s Office',
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Reason for transfer (optional)...',
            }),
        }
        labels = {
            'to_location': 'New Location',
        }


class PromoteToSecurityForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=None,  # set in __init__
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Select User',
        help_text='Only users without an existing security profile are shown.',
    )
    badge_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. SEC-001',
        }),
    )
    office_location = forms.CharField(
        max_length=200,
        initial='Main Security Office',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Main Security Office',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        # Only show users who don't already have a security profile
        already_staff = SecurityProfile.objects.values_list('user_id', flat=True)
        self.fields['user'].queryset = (
            User.objects.exclude(id__in=already_staff).order_by('username')
        )

    def clean_badge_number(self):
        badge = self.cleaned_data.get('badge_number')
        if SecurityProfile.objects.filter(badge_number=badge).exists():
            raise forms.ValidationError('This badge number is already in use.')
        return badge


class SecurityProfileEditForm(forms.ModelForm):
    class Meta:
        model = SecurityProfile
        fields = ['badge_number', 'office_location', 'is_active']
        widgets = {
            'badge_number': forms.TextInput(attrs={'class': 'form-control'}),
            'office_location': forms.TextInput(attrs={'class': 'form-control'}),
        }
