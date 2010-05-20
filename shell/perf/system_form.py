from models import System
import re

from django import forms
from django.forms.util import ValidationError

class NameField(forms.CharField):
    # HORRIBLE hack to allow validation to pass when we haven't changed the name
    # of the edited system, to allow it to "conflict" with itself
    existing_ok_name = None

    def clean(self, value):
        value = forms.CharField.clean(self, value)
        
        if not re.match(r'^[A-Za-z0-9_.]+-[A-Za-z0-9_.]+-[A-Za-z0-9_.]+(-[A-Za-z0-9_.]+)?$', value):
            raise ValidationError("Name isn't formatted appropriately")

        if value != NameField.existing_ok_name:
            try:
                old = System.objects.get(name=value)
            except System.DoesNotExist:
                old = None

            if old:
                raise ValidationError("Name is already in use")

        return value

class SystemForm(forms.Form):
    name = NameField(max_length=255,
                     help_text='''
Name of the system. Should be of the form:
'<owner_or_location>-<operating_system>-<graphics>[-<extra>]'.
For example 'rhwestford-fedora14.rawhide-intel.G965' or 'otaylor-fedora13-radeon.rv350-laptop'.)
''')
    owner_email = forms.EmailField(max_length=255,
                                   help_text='''
Contact email for the person responsible for this system. This will be displayed publically on the web interface.
''')
    operating_system = forms.CharField(max_length=255,
                                       help_text='''
Operating system. For example, 'Ubuntu 10.04' or 'Fedora 14 Rawhide'.
''')
    graphics = forms.CharField(max_length=255,
                               help_text='''
Graphics processor. For example, 'Intel 945GM' or 'AMD Radeon HD 4650'.
For NVIDIA cards, indicate the driver being used with '(nvidia)' or
'(nouveau)'. For AMD cards, add '(fglrx)' if using the closed-source
Catalyst drivers.''')
    processor = forms.CharField(max_length=255,
                                help_text='''
System CPU. For example, 'Intel Core 2 Duo P8600 (2.4GHz)'.''')


    notes = forms.CharField(required=False,
                            widget=forms.widgets.Textarea)
    
