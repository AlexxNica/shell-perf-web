from django.conf import settings
from django.conf.urls.defaults import *

urlpatterns = patterns('',
                       (r'^$', 'django.views.generic.simple.redirect_to',
                            { 'url': 'home', 'permanent': True }),
                       (r'^activate$', 'shell.perf.views.activate'),
                       (r'^confirm_edit$', 'shell.perf.views.confirm_edit'),
                       (r'^home$', 'shell.perf.views.home'),
                       (r'^register$', 'shell.perf.views.register'),
                       # The system name is included in the report URls only to make the
                       # the URLs more self-documenting
                       (r'^report/(?P<system_name>[^/]+)/(?P<report_id>\d+)/json$', 'shell.perf.views.report_json'),
                       (r'^report/(?P<system_name>[^/]+)/(?P<report_id>\d+)$', 'shell.perf.views.report_view'),
                       (r'^system/(?P<system_name>[^/]+)/admin$', 'shell.perf.views.system_admin'),
                       (r'^system/(?P<system_name>[^/]+)/edit$', 'shell.perf.views.system_edit'),
                       (r'^system/(?P<system_name>[^/]+)/mail_key$', 'shell.perf.views.system_mail_key'),
                       (r'^system/(?P<system_name>[^/]+)/upload$', 'shell.perf.views.system_upload'),
                       (r'^system/(?P<system_name>[^/]+)$', 'shell.perf.views.system_view'),
                       (r'^systems$', 'shell.perf.views.systems'),
                       (r'^static/(?P<path>.*)$', 'django.views.static.serve',
                            {'document_root': settings.STATIC_DOC_ROOT })
                       )
