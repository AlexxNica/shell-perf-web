import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'shell.settings'

sys.path.append(os.path.dirname(__file__))
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
