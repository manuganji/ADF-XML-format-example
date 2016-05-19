import json
from functools import partial, lru_cache
from operator import itemgetter, contains
from django.utils.timezone import datetime, timedelta
import requests

import ipdb

from django.utils.text import slugify
from django.db import models
from django.forms import widgets
from django.core.urlresolvers import reverse
from django.conf import settings

CSV_TO_MODEL_FIELD_MAP = {
    'Stock': 'stock_number',
    'VIN': 'vin',
    'Year': 'year_mfd',
    'Trim': 'trim',
    'ExteriorColor':    'exterior_color',
    'InteriorColor':    'interior_color',
    'EngineCylinders':  'cylinders',
    'Transmission': 'transmission',
    'Miles': 'miles',
    'SellingPrice': 'selling_price',
    'MSRP': 'msrp',
    'BookValue': 'book_value',
    'Invoice': 'invoice',
    'Description': 'description',
    'Options': 'options',
    'Categorized Options': 'cat_options',
    'Special Field 1': 'special_field1',
    'Special Field 2': 'special_field2',
    'Special Field 3': 'special_field3',
    'Special Field 4': 'special_field4',
    'Style_Description': 'style_description',
    'Ext_Color_Generic': 'ext_color_generic',
    'Ext_Color_Code': 'ext_color_code',
    'Int_Color_Generic': 'int_color_generic',
    'Int_Color_Code': 'int_color_code',
    'Int_Upholstery': 'int_upholstery',
    'Engine_Block_Type': 'eng_block',
    'Engine_Aspiration_Type': 'aspiration',
    'Engine_Description': 'eng_desc',
    'Transmission_Speed': 'transmission_speed',
    'Transmission_Description': 'transmission_desc',
    'Drivetrain': 'drive_train',
    'Fuel_Type': 'fuel',
    'CityMPG': 'city_mpg',
    'HighwayMPG': 'highway_mpg',
    'EPAClassification': 'epa_class',
    'Wheelbase_Code': 'wheelbase',
    'Internet_Price': 'internet_price',
    'Misc_Price1': 'misc_price1',
    'Misc_Price2': 'misc_price2',
    'Misc_Price3': 'misc_price3',
    'Factory_Codes': 'factory_codes',
    'MarketClass': 'market_class',
    'PassengerCapacity': 'passenger_capacity',
    'EngineDisplacementCubicInches': 'disp_cub_inches',
}

# params: 1. <String> new_or_used_str which has values of 'New' or 'Used'
# returns: 2. <Boolean> True for 'New' and False for 'Used'
# raises Unknown classification error
def vehicle_type_to_boolean(new_or_used_str):
    if new_or_used_str == 'New':
        return True
    elif new_or_used_str == 'Used':
        return False
    else:
        raise Exception("Unknown Vehicle Type Passed")

# params: 1. <String> cert_str which has values of 'True' or 'False'
# returns: 2. <Boolean> True for 'True' and False for 'False'
# raises Unknown classification error
def cert_to_boolean(cert_str):
    if cert_str == 'True':
        return True
    elif cert_str == 'False':
        return False
    else:
        raise Exception("Unknown Certification Status Passed")

def number_displacement(str_val):
    l_indx = str_val.find('L')
    return float(str_val[:l_indx])

# params:
# 1. vehicle_obj: <Vehicle>
# 2. img_url: <String>
# returns:
# VehicleImage
def vehicle_image_obj_mkr(vehicle_obj, img_url):
    return VehicleImage(vehicle=vehicle_obj, url=img_url.strip())

# params:
# 1. field_name: <String>
# returns:
# whether it's a float field in Vehicle Model
@lru_cache()
def is_float_field(field_name):
   return field_name in Vehicle.FLOAT_FIELDS

# params:
# 1. field_name: <String>
# returns:
# whether it's a int field in Vehicle Model
@lru_cache()
def is_int_field(field_name):
   return field_name in Vehicle.INT_FIELDS


# params:
# 1. field_name: <String>
# returns:
# <Boolean> whether it's an ignored column in the csv right now
@lru_cache()
def is_ignored_col(field_name):
   return field_name in ['DealerPhoneNumber', 'DealerAddress',
                         'DealerName', 'DealerZip',
                         'DealerCity', 'Model',
                         'Body', 'ModelNumber',
                         'Doors', 'ImageList']

# params:
# 1. vehicle: <Vehicle>
# 2. mapped_field_name: <String>
# 3. val: <Any>
# returns:
# <Vehicle> vehicle with the field updated
def handle_direct_field(vehicle, mapped_field_name, val):
    if is_int_field(mapped_field_name):
        try:
            setattr(vehicle, mapped_field_name, int(val))
        except ValueError as e:
            setattr(vehicle, mapped_field_name, 0)
    elif is_float_field(mapped_field_name):
        try:
            setattr(vehicle, mapped_field_name, float(val))
        except ValueError as e:
            setattr(vehicle, mapped_field_name, 0.0)
    else:
        setattr(vehicle, mapped_field_name, val)
    return vehicle

# params:
# 1. key_map: <Dict>
# 2. row: a row of <csv.DictReader>
# returns: <Vehicle>
def parse_csv_row(key_map, row):
    vehicle = Vehicle()
    for key, val in row.items():
        mapped_field_name = key_map.get(key,None)

        if is_ignored_col(key):
            continue
        elif not mapped_field_name is None:
            vehicle = handle_direct_field(vehicle, mapped_field_name, val)
            continue
        else:
            if key == 'Type':
                vehicle.is_new = vehicle_type_to_boolean(val)
            elif key == 'Certified':
                vehicle.certified = cert_to_boolean(val)
            elif key == 'Make':
                vehicle.make, is_new_make = VehicleMake.objects.get_or_create(name=val)
            elif key == 'EngineDisplacement':
                vehicle.displacement = number_displacement(val)
            elif key == 'DateInStock':
                vehicle.date_in_stock = datetime.strptime(val, '%m/%d/%Y')
            else:
                print('Unknown column in csv field '+ key)

    # body style
    vehicle.body, is_new_body = BodyStyle.objects.get_or_create(
        name=row['Body']
    )

    # vehicle model
    vehicle.model, is_new_model = VehicleModel.objects.get_or_create(
        make=vehicle.make,
        number=row['ModelNumber'],
        name=row['Model'],
        doors=int(row['Doors']),
    )
    vehicle.save()
    vehicle_image_for_vehicle = partial(vehicle_image_obj_mkr, vehicle)
    bulk_list = map(vehicle_image_for_vehicle, row['ImageList'].split(','))
    VehicleImage.objects.bulk_create(bulk_list)
    return vehicle

cust_parse_csv_row = partial(parse_csv_row, CSV_TO_MODEL_FIELD_MAP)

class VehicleMake(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class BodyStyle(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class VehicleModel(models.Model):
    make = models.ForeignKey(VehicleMake)
    number = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    doors = models.PositiveIntegerField()

    def __str__(self):
        return self.make.name + ' ' +self.number + '-' + self.name

def flatten_values_list(values_qs):
    return [val[0] for val in values_qs]

class VehicleManager(models.Manager):

    def new(self):
        return self.filter(is_new=True)

    def used(self):
        return self.filter(is_new=False)

    def dch_certified(self):
        return self.filter(is_new=False, certified=True).exclude(make__name='Acura')

    def acura_certified(self):
        return self.filter(is_new=False, certified=True, make__name='Acura')

    def specials(self):
        today = datetime.today()
        delta = timedelta(days=45) # the number of days changes from dealership to dealership
        return self.filter(date_in_stock__lte=today-delta)

    def used_specials(self):
        return self.specials().filter(is_new=False)

    def new_specials(self):
        return self.specials().filter(is_new=True)

class Vehicle(models.Model):

    INT_FIELDS = [
        'year_mfd',
        'cylinders',
        'displacement',
        'miles',
        'selling_price',
        'msrp',
        'book_value',
        'invoice',
        'transmission_speed',
        'city_mpg',
        'highway_mpg',
        'internet_price',
        'misc_price1',
        'misc_price2',
        'misc_price3',
        'passenger_capacity',
    ]

    FLOAT_FIELDS = [
        'wheelbase',
        'displacement',
        'disp_cub_inches',
    ]

    is_new = models.BooleanField(verbose_name="New")
    stock_number = models.CharField(max_length=20, verbose_name="Stock")
    vin = models.CharField(max_length=20, verbose_name="VIN")
    year_mfd = models.PositiveIntegerField(verbose_name="Year")
    make = models.ForeignKey(VehicleMake)
    model = models.ForeignKey(VehicleModel)
    body = models.ForeignKey(BodyStyle)
    trim = models.CharField(max_length=100)
    exterior_color = models.CharField(max_length=100)
    interior_color = models.CharField(max_length=100)
    # Honda Accord may come in 3 different numbers of cylinders
    cylinders = models.PositiveIntegerField()
    displacement = models.PositiveIntegerField() # always in L
    transmission = models.CharField(max_length=20)
    miles = models.PositiveIntegerField()
    selling_price = models.PositiveIntegerField()
    msrp = models.PositiveIntegerField(verbose_name="MSRP")
    book_value = models.PositiveIntegerField()
    invoice = models.PositiveIntegerField()
    certified = models.BooleanField()
    date_in_stock = models.DateField()
    description = models.TextField()
    options = models.TextField()
    cat_options = models.TextField(verbose_name="Categorized options")
    special_field1 = models.CharField(max_length=100, blank=True)
    special_field2 = models.CharField(max_length=100, blank=True)
    special_field3 = models.CharField(max_length=100, blank=True)
    special_field4 = models.CharField(max_length=100, blank=True)
    style_description = models.CharField(max_length=200)
    ext_color_generic = models.CharField(max_length=100)
    ext_color_code = models.CharField(max_length=20)
    int_color_generic = models.CharField(max_length=100)
    int_color_code = models.CharField(max_length=20)
    int_upholstery = models.CharField(max_length=200, blank=True)
    eng_block = models.CharField(max_length=10, verbose_name="Engine Block")
    aspiration = models.CharField(max_length=100, verbose_name="Engine Aspiration")
    eng_desc = models.CharField(max_length=100, verbose_name="Engine Description")
    transmission_speed = models.PositiveIntegerField()
    transmission_desc = models.CharField(max_length=100, verbose_name="Transmission Description")
    drive_train = models.CharField(max_length=10)
    fuel = models.CharField(max_length=20)
    city_mpg = models.PositiveIntegerField()
    highway_mpg = models.PositiveIntegerField()
    epa_class = models.CharField(max_length=100, verbose_name="EPA Classification")
    wheelbase = models.FloatField()
    internet_price = models.PositiveIntegerField()
    misc_price1 = models.PositiveIntegerField(null=True, blank=True)
    misc_price2 = models.PositiveIntegerField(null=True, blank=True)
    misc_price3 = models.PositiveIntegerField(null=True, blank=True)
    factory_codes = models.CharField(max_length=20, blank=True)
    market_class = models.CharField(max_length=100, verbose_name="Market Class")
    passenger_capacity = models.PositiveIntegerField()
    disp_cub_inches = models.FloatField(verbose_name="Displacement in Cubic Inches")
    slug = models.SlugField(max_length=200, unique=True)

    objects = VehicleManager()

    def __str__(self):
        return self.stock_number + ' ' + str(self.model)

    @property
    def thumbnail(self):
        return self.vehicleimage_set.first().url

    def get_categorized_options(self):
        cats = {}
        for cat_opt in self.cat_options.split('~'):
            cat, opt = cat_opt.split('@')
            try:
                cats[cat].append(opt)
            except KeyError as e:
                cats[cat] = [opt]
        return cats

    def get_similar_vehicles(self):
        if self.is_new and self.model.vehicle_set.exclude(id=self.id).count() > 0:
            qs = self.model.vehicle_set.exclude(id=self.id)
        else:
            LOOKUP_WINDOW = 50
            qs = Vehicle.objects.filter(
                msrp__lte=self.msrp+LOOKUP_WINDOW,
                msrp__gte=self.msrp-LOOKUP_WINDOW,
            ).exclude(id=self.id)

        return qs[:6]

    def get_absolute_url(self):
        return reverse('vehicle_details', kwargs={
            'stock_id':self.stock_number,
            'slug':self.slug
        })

    def get_shortened_url(self):
        api_url = settings.GOOGLE_API_ENDPOINT + settings.GOOGL_URLSHORTENER_APIKEY
        headers = {
            'Content-Type':'application/json',
        }
        body = json.dumps({
            'longUrl': settings.SITE_URL + self.get_absolute_url()
        })
        resp = requests.post(api_url, data=body, headers=headers).json()
        return resp['id']

    def handlebars_context(self):
        return json.dumps({
            'stock_number': self.stock_number,
            'make': self.make.id,
            'model': self.model.id,
            'make_name': self.make.name,
            'model_name': self.model.name,
            'vin': self.vin,
            'year_mfd': self.year_mfd,
            'body': self.body.name,
            'thumbnail': self.thumbnail,
            'trim': self.trim,
        })

    def save(self, *args, **kwargs):
        if (self.slug == "") or (self.slug is None) :
            slug_input = "vehicle " + self.make.name + " " + self.model.name
            slug_input += " " + str(self.year_mfd)
            slug_input += " Verona NJ "
            slug_input += self.stock_number
            self.slug = slugify(slug_input)[:200] # truncate to field size
        super(Vehicle, self).save(*args, **kwargs)

class VehicleImage(models.Model):
    # array of images
    vehicle = models.ForeignKey(Vehicle)
    url = models.URLField(max_length=300)

    def __str__(self):
        return self.url
