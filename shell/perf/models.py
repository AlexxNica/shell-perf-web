from django.conf import settings
from django.db import models

import util

class System(models.Model):
    name = models.CharField(max_length=255, unique=True)
    owner_email = models.CharField(max_length=255)
    operating_system = models.CharField(max_length=255)
    graphics = models.CharField(max_length=255)
    processor = models.CharField(max_length=255)
    notes = models.CharField(max_length=1023)
    secret_key = models.CharField(max_length=32)

class SystemEdit(models.Model):
    system = models.ForeignKey(System, null=True)
    date = models.DateTimeField()
    confirmed = models.BooleanField()

    name = models.CharField(max_length=255)
    owner_email = models.CharField(max_length=255)
    operating_system = models.CharField(max_length=255)
    graphics = models.CharField(max_length=255)
    processor = models.CharField(max_length=255)
    notes = models.CharField(max_length=1023)
    secret_key = models.CharField(max_length=32)

    def make_auth(self, action):
        return 'sha1_' + util.hmac_sha1(settings.SECRET_KEY, action + "&" + str(self.id)).hexdigest()

    def check_auth(self, action, supplied):
        expected = self.make_auth(action)
        import sys
        print >>sys.stderr, expected, supplied
        return expected == supplied

class Report(models.Model):
    system = models.ForeignKey(System)
    date = models.DateTimeField()
    upload = models.FileField(upload_to='reports')

class Metric(models.Model):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    units = models.CharField(max_length=255)
    report = models.ForeignKey(Report)
    value = models.FloatField()
