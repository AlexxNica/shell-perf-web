from django.conf import settings
from django.conf.urls.defaults import *

urlpatterns = patterns('',
                       (r'^$', 'django.views.generic.simple.redirect_to',
                            { 'url': 'home', 'permanent': True }),
                       (r'^activate$', 'shell.perf.views.activate'),
                       (r'^confirm_edit$', 'shell.perf.views.confirm_edit'),
                       (r'^home$', 'shell.perf.views.home'),
                       (r'^register$', 'shell.perf.views.register'),
                       (r'^system/(?P<name>[^/]+)/admin$', 'shell.perf.views.system_admin'),
                       (r'^system/(?P<name>[^/]+)/edit$', 'shell.perf.views.system_edit'),
                       (r'^system/(?P<name>[^/]+)/mail_key$', 'shell.perf.views.system_mail_key'),
                       (r'^system/(?P<name>[^/]+)/upload$', 'shell.perf.views.system_upload'),
                       (r'^system/(?P<name>[^/]+)$', 'shell.perf.views.system_view'),
                       (r'^systems$', 'shell.perf.views.systems'),
                       (r'^static/(?P<path>.*)$', 'django.views.static.serve',
                            {'document_root': settings.STATIC_DOC_ROOT })
                       )
