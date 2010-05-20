# These are settings that are independent of the installation. Don't change
# anything here; the settings that are edited are in local_settings.py

import os
from local_settings import *

LANGUAGE_CODE = 'en-us'

SITE_ID = 1
USE_I18N = False

STATIC_DOC_ROOT = os.path.join(APP_ROOT, 'static')
TEMPLATE_DIRS = ( os.path.join(APP_ROOT, 'templates') )

MEDIA_ROOT = os.path.join(DATA_ROOT, 'uploads')

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'shell.urls'

INSTALLED_APPS = (
    'shell.perf',
    'django.contrib.contenttypes'
)
