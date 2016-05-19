from django.shortcuts import render
from django.core.urlresolvers import reverse_lazy
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.utils.timezone import now
from django.views.generic import FormView
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.contrib import messages
from .forms import *
from lxml import etree
import ipdb
from string import ascii_letters, digits
from random import sample
import json
from twilio.rest import TwilioRestClient

def get_contact_node(first_name="", last_name="", phone="",
        email="", address="", city="", state="",
        zip_code=""):

    street = etree.Element("street")
    street.text = address

    city_node = etree.Element("city")
    city_node.text = city

    regioncode = etree.Element("regioncode")
    regioncode.text = state

    postalcode = etree.Element("postalcode")
    postalcode.text = zip_code

    address = etree.Element("address")
    address.append(street)
    address.append(city_node)
    address.append(regioncode)
    address.append(postalcode)

    first_name_node = etree.Element("name", part="first")
    first_name_node.text = first_name

    last_name_node = etree.Element("name", part="last")
    last_name_node.text = last_name

    phone_node = etree.Element("phone", time="nopreference")
    phone_node.set("type", "phone")
    phone_node.text = phone

    email_node = etree.Element("email")
    email_node.text = email

    contact_node = etree.Element("contact")
    contact_node.append(first_name_node)
    contact_node.append(last_name_node)
    contact_node.append(email_node)
    contact_node.append(phone_node)
    contact_node.append(address)

    return contact_node

def get_provider_node():
    # add service provider's details
    name_node = etree.Element("name", part="full")
    name_node.text = "Dealership Website Provider"
    url_node = etree.Element("url")
    url_node.text = "http://www.example.com"
    provider_node = etree.Element("provider")
    provider_node.append(name_node)
    provider_node.append(url_node)
    return provider_node

def get_vendor_node():
    vendorname_node = etree.Element("vendorname")
    vendorname_node.text = "Acura"
    url_node = etree.Element("url")
    url_node.text = "http://www.example.com/"
    contact_node = get_contact_node(
        phone="855-464-5522",
        address="Montclair Acura, 100 Bloomfield Avenue",
        city = "Verona",
        state = "NJ",
        zip_code = "07044",
    )

    vendor_node = etree.Element("vendor")
    vendor_node.append(vendorname_node)
    vendor_node.append(url_node)
    vendor_node.append(contact_node)
    return vendor_node

def get_requestdate_node():
    ts = now().replace(microsecond=0)
    # request timestamp
    requestdate_node = etree.Element("requestdate")
    requestdate_node.text = ts.isoformat()
    return requestdate_node

class ADFFormView(FormView):
    """
    Must implement adfxml which is called when the form is valid

    def adfxml(self, form, prospect_node):
        # modified prospect_node without destroying
        # all new data are 'append'ed
        returns prospect_node
        ...
    """

    to_email = "leads@example.com"
    subject_line = "Acura - Contact Request"

    def adfxml(self, form, prospect_node):
        raise ImproperlyConfigured('adfxml method not implemented to populate prospect_node.')

    def mail_adfxml(self, form):
        xml_decl = """<?xml version="1.0" encoding="UTF-8"?><?adf version="1.0"?>"""
        adf_node = etree.Element("adf")

        prospect_node = etree.Element("prospect")
        prospect_node.append(get_requestdate_node())
        prospect_node.append(get_provider_node())
        prospect_node.append(get_vendor_node())

        prospect_node = self.adfxml(form, prospect_node)
        adf_node.append(prospect_node)
        if settings.DEBUG:
            print(etree.tostring(adf_node, encoding='unicode', pretty_print=True))
        total_xml = xml_decl + etree.tostring(adf_node, encoding='unicode')

        """ mail the xml to self.to_email now """
        subject, from_email, to = self.subject_line, settings.DEFAULT_FROM_EMAIL, self.to_email
        text_content = total_xml
        send_mail(subject, text_content, from_email, [to], fail_silently=False)

    def form_valid(self, form):
        self.mail_adfxml(form)
        return super(ADFFormView, self).form_valid(form)

class ContactFormView(ADFFormView):
    template_name = "full_contact_form.html"
    form_class = ContactForm
    success_url = reverse_lazy('contact-thankyou')
    to_email = "leads@example.com"
    subject_line = "Montclair Acura - Contact Request"

    def adfxml(self, form, prospect_node):

        comments_node = etree.Element("comments")
        comments_node.text = form.cleaned_data['message']

        customer_node = etree.Element("customer")
        customer_node.append(get_contact_node(
                first_name = form.cleaned_data['first_name'],
                last_name = form.cleaned_data['last_name'],
                phone = form.cleaned_data['phone'],
                email = form.cleaned_data['email'],
                address = form.cleaned_data["address"],
                city = form.cleaned_data["city"],
                state = form.cleaned_data["state"],
                zip_code = form.cleaned_data["zip_code"]
            )
        )
        customer_node.append(comments_node)

        prospect_node.append(customer_node)
        return prospect_node

def get_timeframe_node(description="", earliestdate="", latestdate=""):
    timeframe_desc_node = etree.Element("description")
    timeframe_desc_node.text = description

    earliestdate_node = etree.Element("earliestdate")
    earliestdate_node.text = earliestdate

    timeframe_node = etree.Element("timeframe")
    timeframe_node.append(timeframe_desc_node)
    timeframe_node.append(earliestdate_node)

    return timeframe_node

def get_vehicle_node(form, interest_type=None):
    year_node = etree.Element("year")
    year_node.text = str(form.cleaned_data['year_mfd'])
    make_node = etree.Element("make")
    make_node.text = form.cleaned_data['make'].name
    model_node = etree.Element("model")
    model_node.text = form.cleaned_data['model'].name
    stock_node = etree.Element("stock")
    stock_node.text = form.cleaned_data['stock_number']
    vin_node = etree.Element("vin")
    vin_node.text = form.cleaned_data['vin']

    vehicle_node = etree.Element("vehicle")
    if not interest_type is None:
        vehicle_node.set("interest", interest_type)

    vehicle_node.append(year_node)
    vehicle_node.append(make_node)
    vehicle_node.append(model_node)
    vehicle_node.append(stock_node)
    vehicle_node.append(vin_node)
    return vehicle_node

def get_customer_node(form):
    """
        Returns a customer info tag with basic information
    """

    customer_node = etree.Element("customer")
    customer_node.append(get_contact_node(
            first_name = form.cleaned_data['first_name'],
            last_name = form.cleaned_data['last_name'],
            phone = form.cleaned_data['phone'],
            email = form.cleaned_data['email'],
            address = form.cleaned_data["address"],
            city = form.cleaned_data["city"],
            state = form.cleaned_data["state"],
            zip_code = form.cleaned_data["zip_code"]
        )
    )
    return customer_node

class TestDriveFormView(ADFFormView):
    template_name = "test_drive_form.html"
    form_class = TestDriveForm
    success_url = reverse_lazy('testdrive')
    to_email = "leads@example.com"
    subject_line = "Montclair Acura - Test Drive Request"

    def form_valid(self, form):
        self.mail_adfxml(form)
        response = HttpResponse()
        response['REDIRECT_LOCATION'] = reverse_lazy('testdrive-thankyou')
        return response

    def adfxml(self, form, prospect_node):
        vehicle_node = get_vehicle_node(form, interest_type="test-drive")
        customer_node = get_customer_node(form)

        schedule_date = datetime.strptime(form.cleaned_data["schedule_date"], "%A %b %d, %Y")
        slot_description = form.cleaned_data["scheduled_slot"] + " on " + schedule_date.strftime("%A %b %d, %Y")

        comments_node = etree.Element("comments")
        comments_node = "Test Drive requested between" + slot_description + "\n" + form.cleaned_data['message']

        customer_node.append(comments_node)

        customer_node.append(get_timeframe_node(
            description=slot_description,
            earliestdate=schedule_date.replace(hour=9).isoformat(),
            )
        )

        prospect_node.append(vehicle_node)
        prospect_node.append(customer_node)
        return prospect_node

class RequestQuoteFormView(ADFFormView):
    template_name = "request_quote_form.html"
    form_class = VehicleEnquiryForm
    success_url = reverse_lazy('requestquote')
    to_email = "leads@example.com"
    subject_line = "Montclair Acura - Request for Quotation"

    def form_valid(self, form):
        self.mail_adfxml(form)
        response = HttpResponse()
        response['REDIRECT_LOCATION'] = reverse_lazy('requestquote-thankyou')
        return response

    def adfxml(self, form, prospect_node):
        vehicle_node = get_vehicle_node(form, interest_type="buy")
        customer_node = get_customer_node(form)

        comments_node = etree.Element("comments")
        comments_node.text = "Request for Quotation \n" + form.cleaned_data['message']
        customer_node.append(comments_node)

        prospect_node.append(vehicle_node)
        prospect_node.append(customer_node)
        return prospect_node

class RequestInfoFormView(ADFFormView):
    template_name = "request_info_form.html"
    form_class = VehicleEnquiryForm
    success_url = reverse_lazy('requestinfo')
    to_email = "leads@example.com"
    subject_line = "Montclair Acura - Request for Information"

    def form_valid(self, form):
        self.mail_adfxml(form)
        response = HttpResponse()
        response['REDIRECT_LOCATION'] = reverse_lazy('requestinfo-thankyou')
        return response

    def adfxml(self, form, prospect_node):
        vehicle_node = get_vehicle_node(form, interest_type="buy")
        customer_node = get_customer_node(form)

        comments_node = etree.Element("comments")
        comments_node.text = "Request for Information \n" + form.cleaned_data['message']
        customer_node.append(comments_node)

        prospect_node.append(vehicle_node)
        prospect_node.append(customer_node)
        return prospect_node

class ConfirmAvailabilityFormView(ADFFormView):
    template_name = "confirm_availability_form.html"
    form_class = VehicleEnquiryForm
    success_url = reverse_lazy('confirmavailability')
    to_email = "leads@example.com"
    subject_line = "Montclair Acura - Confirm Availability"

    def form_valid(self, form):
        self.mail_adfxml(form)
        response = HttpResponse()
        response['REDIRECT_LOCATION'] = reverse_lazy('confirmavailability-thankyou')
        return response

    def adfxml(self, form, prospect_node):
        vehicle_node = get_vehicle_node(form, interest_type="buy")
        customer_node = get_customer_node(form)

        comments_node = etree.Element("comments")
        comments_node.text = "Request to confirm availability \n" + form.cleaned_data['message']
        customer_node.append(comments_node)

        prospect_node.append(vehicle_node)
        prospect_node.append(customer_node)
        return prospect_node

class VehicleFinanceFormView(ADFFormView):
    template_name = "confirm_availability_form.html"
    form_class = VehicleEnquiryForm
    success_url = reverse_lazy('confirmavailability')
    to_email = "leads@example.com"
    subject_line = "Montclair Acura - Enquiry about Finance"

    def form_valid(self, form):
        self.mail_adfxml(form)
        response = HttpResponse()
        response['REDIRECT_LOCATION'] = reverse_lazy('confirmavailability-thankyou')
        return response

    def adfxml(self, form, prospect_node):
        vehicle_node = get_vehicle_node(form, interest_type="buy")
        customer_node = get_customer_node(form)

        comments_node = etree.Element("comments")
        comments_node.text = "Request to confirm availability \n" + form.cleaned_data['message']
        customer_node.append(comments_node)

        prospect_node.append(vehicle_node)
        prospect_node.append(customer_node)
        return prospect_node

class SendToMobileFormView(ADFFormView):
    template_name = "send_to_mobile_form.html"
    form_class = SendToMobileForm
    success_url = reverse_lazy('sendtomobile')
    to_email = "leads@example.com"
    subject_line = "Montclair Acura - Lead via Send To Mobile"

    def adfxml(self, form, prospect_node):

        vehicle_node = get_vehicle_node(form, interest_type="buy")
        customer_node = etree.Element("customer")
        customer_node.append(get_contact_node(
                first_name = form.cleaned_data['first_name'],
                last_name = form.cleaned_data['last_name'],
                phone = form.cleaned_data['phone'],
            )
        )

        comments_node = etree.Element("comments")
        comments_node.text = "Request to send information to mobile"
        customer_node.append(comments_node)

        prospect_node.append(vehicle_node)
        prospect_node.append(customer_node)
        return prospect_node

    def form_valid(self, form):
        vehicle = Vehicle.objects.get(stock_number=form.cleaned_data['stock_number'])
        short_link = vehicle.get_shortened_url()
        twilio_client = TwilioRestClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = twilio_client.messages.create(
            to='+1 ' + form.cleaned_data['phone'],
            from_=settings.TWILIO_NUMBER,
            body="Link to the vehicle "+ short_link
        )
        self.mail_adfxml(form)
        return HttpResponse("<h2>Thank you! You should receive the link on your phone shortly.</h2>")
