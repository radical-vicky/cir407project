# forms.py
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import UserProfile, UserWallet, Consultation

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'address', 'profile_picture', 'date_of_birth']

class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = UserWallet
        fields = ['mpesa_number', 'paypal_email', 'preferred_payment_method']

class DepositForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    payment_method = forms.ChoiceField(choices=UserWallet.PAYMENT_METHODS)

class WithdrawalForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    payment_method = forms.ChoiceField(choices=UserWallet.PAYMENT_METHODS)

class ConsultationBookingForm(forms.ModelForm):
    scheduled_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=True
    )
    
    class Meta:
        model = Consultation
        fields = ['title', 'level', 'description', 'scheduled_date', 'meeting_platform']
        
    def clean_scheduled_date(self):
        scheduled_date = self.cleaned_data.get('scheduled_date')
        if scheduled_date and scheduled_date <= timezone.now():
            raise ValidationError('Please select a future date and time for your consultation.')
        return scheduled_date