from random import sample
from django import forms
from django.utils.timezone import now
from dateutil.rrule import DAILY, MO, TU, WE, TH, FR, SA, rrule
from localflavor.us import forms as us_forms
from .models import *
import ipdb

class SendToMobileForm(forms.Form):
    stock_number = forms.CharField(max_length=20,widget=forms.HiddenInput())
    vin = forms.CharField(max_length=20,widget=forms.HiddenInput())
    year_mfd = forms.IntegerField(widget=forms.HiddenInput())
    make = forms.ModelChoiceField(queryset=VehicleMake.objects.all(),widget=forms.HiddenInput())
    model = forms.ModelChoiceField(queryset=VehicleModel.objects.all(),widget=forms.HiddenInput())
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    phone = us_forms.USPhoneNumberField(required=True)

class ContactForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField(required=False)
    address = forms.CharField(required=False)
    city = forms.CharField(max_length=100)
    state = us_forms.USStateField(widget=us_forms.USStateSelect)
    zip_code = us_forms.USZipCodeField()
    phone = us_forms.USPhoneNumberField(required=False)
    message = forms.CharField(widget=forms.TextInput())

    def clean(self):
        cleaned_data = super(ContactForm, self).clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        if len(email)==0 and len(phone)==0:
            # At least one of them has to be provided
            msg = "At least one of email or phone have to be provided"
            self.add_error('email', msg)
            self.add_error('phone', msg)

class VehicleEnquiryForm(forms.Form):
    # always have the same field names stock_number, vin, year_mfd, make, model
    # look at inventory.models.Vehicle.handlebars_context for explanation
    stock_number = forms.CharField(max_length=20,widget=forms.HiddenInput())
    vin = forms.CharField(max_length=20,widget=forms.HiddenInput())
    year_mfd = forms.IntegerField(widget=forms.HiddenInput())
    make = forms.ModelChoiceField(queryset=VehicleMake.objects.all(),widget=forms.HiddenInput())
    model = forms.ModelChoiceField(queryset=VehicleModel.objects.all(),widget=forms.HiddenInput())
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField(required=False)
    address = forms.CharField(required=False)
    city = forms.CharField(max_length=100)
    state = us_forms.USStateField(widget=us_forms.USStateSelect)
    zip_code = us_forms.USZipCodeField()
    phone = us_forms.USPhoneNumberField(required=False)
    message = forms.CharField(widget=forms.TextInput())

    def clean(self):
        cleaned_data = super(VehicleEnquiryForm, self).clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        if len(email)==0 and len(phone)==0:
            # At least one of them has to be provided
            msg = "At least one of email or phone have to be provided"
            self.add_error('email', msg)
            self.add_error('phone', msg)

class TestDriveForm(VehicleEnquiryForm):

    def date_choices():
        rul = rrule(DAILY,
                dtstart=now().replace(hour=9, minute=0, second=0, microsecond=0),
                byweekday=(MO,TU,WE,TH,FR,SA),
                count=12
                )
        allowed_dates = ((x.strftime("%A %b %d, %Y"), x.strftime("%A %b %d, %Y")) for x in rul)
        return allowed_dates

    slots = (
            '7 am - 9 am',
            '9 am - 11 am',
            '11 am - 1 pm',
            '1 pm - 3 pm',
            '3 pm - 5 pm',
            '5 pm - 7 pm',
            '7 pm - 9 pm',
            )
    slot_choices = ((x,x) for x in slots)
    schedule_date = forms.ChoiceField(choices=date_choices)
    scheduled_slot = forms.ChoiceField(choices=slot_choices)
