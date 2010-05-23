from cStringIO import StringIO
import datetime
from gzip import GzipFile
import hmac
try:
    import json
except:
    import simplejson as json
import re

from django.shortcuts import render_to_response
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, Http404
from django.views.decorators.http import require_POST

from models import Metric, System, SystemEdit, Report
from report_table import ReportTable, RunTable
from system_form import SystemForm, NameField
import signed_request
import util

class BadEditAuth(Exception):
    pass

def _check_edit_auth(request, action):
    if request.method == 'POST':
        d = request.POST
    else:
        d = request.GET
    
    if not 'edit' in d:
        raise BadEditAuth('edit parameter not specified')
    if not 'auth' in d:
        raise BadEditAuth('auth parameter not specified')

    try:
        edit_id = int(d['edit'])
    except ValueError:
        raise BadEditAuth('bad edit id')

    try:
        edit = SystemEdit.objects.get(id=edit_id)
    except SystemEdit.DoesNotExist:
        raise BadEditAuth('bad edit id')

    if not edit.check_auth(action, d['auth']):
        raise BadEditAuth('bad auth parameter')

    return edit, d['auth']

def activate(request):
    try:
        edit, auth = _check_edit_auth(request, "activate")
    except BadEditAuth, e:
        return HttpResponseForbidden(str(e))

    if not edit.confirmed and request.method == 'POST':
        system = System(name=edit.name,
                        owner_email=edit.owner_email,
                        operating_system=edit.operating_system,
                        graphics=edit.graphics,
                        processor=edit.processor,
                        notes=edit.notes,
                        secret_key=edit.secret_key)
        system.save()
        edit.system = system
        edit.confirmed = True
        edit.save()
        
    return render_to_response('pages/activate.html',
                              { 'page': 'activate',
                                'page_title': "Activate System",
                                'settings': settings,
                                'auth': auth, 
                                'edit': edit })

def confirm_edit(request):
    try:
        edit, auth = _check_edit_auth(request, "confirm")
    except BadEditAuth, e:
        return HttpResponseForbidden(str(e))

    if request.method == 'POST':
        system = edit.system
        system.name = edit.name
        system.owner_email = edit.owner_email
        system.operating_system = edit.operating_system
        system.graphics = edit.graphics
        system.processor = edit.processor
        system.notes = edit.notes
        system.save()
        
        edit.confirmed = True
        edit.save()
        
    return render_to_response('pages/confirm_edit.html',
                              { 'page': 'confirm_edit',
                                'page_title': 'Confirm Edit',
                                'settings': settings,
                                'auth': auth,
                                'edit': edit,
                                'system': edit.system })

def home(request):
    recent_reports = Report.objects.order_by('-date')[0:20]

    reports = []
    systems = set()
    for report in recent_reports:
        if report.system in systems:
            continue
        systems.add(report.system)
        reports.append(report)
        if len(reports) > 5:
            break

    report_table = ReportTable()
    for report in reports:
        report_table.add_report(report, report.system.name,
                                "system/%s" % report.system.name)

    return render_to_response('pages/home.html',
                              { 'page': 'home',
                                'settings': settings,
                                'report_table': report_table })
    
def _do_register(form):
    edit = SystemEdit(date=datetime.datetime.now(),
                      confirmed=False,
                      name=form.cleaned_data['name'],
                      owner_email=form.cleaned_data['owner_email'],
                      operating_system=form.cleaned_data['operating_system'],
                      graphics=form.cleaned_data['graphics'],
                      processor=form.cleaned_data['processor'],
                      notes=form.cleaned_data['notes'],
                      secret_key=util.random_key())
    edit.save()
    
    activation_link = "activate?edit=%d&auth=%s" % (edit.id, edit.make_auth("activate"))

    util.send_email('mails/activate.txt',
                    { 'settings': settings,
                      'system': edit,
                      'activation_link': activation_link },
                    edit.owner_email)

    return edit

def register(request):
    if request.method == 'POST':
        form = SystemForm(request.POST)
        if form.is_valid():
            edit =_do_register(form)
            return render_to_response('pages/system_registered.html',
                                      { 'page': 'system_registered',
                                        'page_title': "System Registered",
                                        'settings': settings,
                                        'edit': edit })

    else:
        form = SystemForm()
    return render_to_response('pages/register.html',
                              { 'page': 'register',
                                'page_title': "Register",
                                'settings': settings,
                                'form': form,
                                'form_action': 'register',
                                'form_submit': "Register" })

def systems(request):
    systems = System.objects.all()
    return render_to_response('pages/systems.html',
                              { 'page': 'systems',
                                'page_title': "All Systems",
                                'settings': settings,
                                'systems': systems })

def system_admin(request, system_name):
    try:
        system = System.objects.get(name=system_name)
    except System.DoesNotExist:
        raise Http404

    return render_to_response('pages/system_admin.html',
                              { 'page': 'system_admin',
                                'page_title': "Administer System",
                                'settings': settings,
                                'system': system })

def _do_edit(system, form):
    edit = SystemEdit(system=system,
                      date=datetime.datetime.now(),
                      confirmed=False,
                      name=form.cleaned_data['name'],
                      owner_email=form.cleaned_data['owner_email'],
                      operating_system=form.cleaned_data['operating_system'],
                      graphics=form.cleaned_data['graphics'],
                      processor=form.cleaned_data['processor'],
                      notes=form.cleaned_data['notes'],
                      secret_key=util.random_key())
    edit.save()
    
    confirm_link = "confirm_edit?edit=%d&auth=%s" % (edit.id, edit.make_auth("confirm"))

    util.send_email('mails/confirm_edit.txt',
                    { 'settings': settings,
                      'system': system,
                      'edit': edit,
                      'confirm_link': confirm_link },
                    system.owner_email)

    return edit

def report_json(request, system_name, report_id):
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        raise Http404

    if system_name != report.system.name:
        raise Http404

    response = HttpResponse(mimetype="application/json")

    gunzip = GzipFile(report.upload.path, "r")
    reportContents = gunzip.read()

    return HttpResponse(reportContents, mimetype="application/json")

def report_view(request, system_name, report_id):
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        raise Http404

    if system_name != report.system.name:
        raise Http404

    gunzip = GzipFile(report.upload.path, "r")
    report_contents = gunzip.read()
    report_json = json.loads(report_contents)

    run_table = RunTable(report_json)

    return render_to_response('pages/report_view.html',
                              { 'page': 'report_view',
                                'page_title': report.system.name,
                                'settings': settings,
                                'report': report,
                                'report_json': report_json,
                                'report_table': run_table})

def system_edit(request, system_name):
    try:
        system = System.objects.get(name=system_name)
    except System.DoesNotExist:
        raise Http404

    no_changes = False

    try:
        NameField.existing_ok_name = system.name
        if request.method == 'POST':
            form = SystemForm(request.POST)

            if form.is_valid():
                if (form.cleaned_data['name'] == system.name and
                    form.cleaned_data['owner_email'] == system.owner_email and
                    form.cleaned_data['operating_system'] == system.operating_system and
                    form.cleaned_data['graphics'] == system.graphics and
                    form.cleaned_data['processor'] == system.processor and
                    form.cleaned_data['notes'] == system.notes):
                    
                    no_changes = True
                else:
                    edit =_do_edit(system, form)
                    return render_to_response('pages/system_edit_submitted.html',
                                              { 'page': 'edit_ok',
                                                'page_title': "Edit Submitted",
                                                'settings': settings,
                                                'system': system })
        else:
            form = SystemForm({ 'name': system.name,
                                'owner_email': system.owner_email,
                                'operating_system': system.operating_system,
                                'graphics': system.graphics,
                                'processor': system.processor,
                                'notes': system.notes })

        return render_to_response('pages/system_edit.html',
                                  { 'page': 'edit',
                                    'page_title': "Edit System",
                                    'settings': settings,
                                    'no_changes': no_changes,
                                    'form': form,
                                    'form_action': 'system/%d/edit' % system.id,
                                    'form_submit': "Submit",
                                    'system': system })
    finally:
        NameField.existing_ok_name = None

def system_mail_key(request, system_name):
    try:
        system = System.objects.get(name=system_name)
    except System.DoesNotExist:
        raise Http404

    mailed = False
    if request.method == 'POST':    
        util.send_email('mails/mail_key.txt',
                        { 'settings': settings,
                          'system': system },
                        system.owner_email)
        mailed = True

    return render_to_response('pages/system_mail_key.html',
                              { 'page': 'system_mail_key',
                                'page_title': 'Mail Secret Key',
                                'settings': settings,
                                'mailed': mailed,
                                'system': system })

# Failsafe to prevent memory exhaustion when reading report into memory
# or parsing JSON. We store the report gzip'ed so disk space usage
# will be significantly less than this.
MAX_CONTENT_LENGTH = 4 * 1024 * 1024

@require_POST
def system_upload(request, system_name):
    try:
        system = System.objects.get(name=system_name)
    except System.DoesNotExist:
        raise Http404

    content_length = int(request.META['CONTENT_LENGTH'])
    if content_length > MAX_CONTENT_LENGTH:
        return HttpResponseBadRequest("Report too big")

    try:
        signed_request.check_signature(request, system.secret_key)
    except signed_request.BadSignature, e:
        return HttpResponseForbidden(str(e))

    reportContents = util.application_json_to_unicode(request.raw_post_data)
    reportJson = json.loads(reportContents)

    date = util.parse_isodate(reportJson['date'])

    metrics = reportJson['metrics']

    for name in metrics:
        metric = metrics[name]
        units = metric['units']
        values = metric['values']
        
        time_exponent = 0
        for m in re.finditer(r'(/\s+)?(\S+)[^\S]*', metric['units']):
            inverse = m.group(1) is not None
            unit = m.group(2)
            if unit in ('s', 'ms', 'us'):
                if inverse:
                    time_exponent -= 1
                else:
                    time_exponent = 1

        # Least contaminated run is shortest run
        if time_exponent > 0:
            value = min(values)
        elif time_exponent < 0:
            value = max(values)
        else:
            # median
            l = len(values)
            s = sorted(values)
            if l % 2 == 1:
                value = s[int(l/2)]
            else:
                value = (s[l/2 - 1] + s[l/2]) / 2

        metric['value'] = value

    report = Report(system=system, date=date)
    
    filename = system_name + "-" + date.strftime("%Y%m%d-%H%M%S") + ".gz"
    str_io = StringIO()
    gz = GzipFile(filename, mode="wb", fileobj=str_io)
    gz.write(reportContents.encode("UTF-8"))
    gz.close()

    # so just compress into a memory buffer and save that.
    report.upload.save(filename,
                       ContentFile(str_io.getvalue()))
    report.save()

    
    for name in metrics:
        metric = metrics[name]
        description = metric['description']
        units = metric['units']
        value = metric['value']

        storedMetric = Metric(name=name,
                              description=description,
                              units=units,
                              report=report,
                              value=value)
        storedMetric.save()

    return HttpResponse("Report upload succeeded", 'text/plain; charset=UTF-8"', 200)

def system_view(request, system_name):
    try:
        system = System.objects.get(name=system_name)
    except System.DoesNotExist:
        raise Http404

    reports = Report.objects.filter(system=system).order_by('-date')[0:5]

    report_table = ReportTable()
    for report in reports:
        report_table.add_report(report,
                                report.date.strftime("%y-%m-%d"),
                                "report/%s/%d" % (system.name, report.id))

    return render_to_response('pages/system_view.html',
                              { 'page': 'system_view',
                                'page_title': system.name,
                                'settings': settings,
                                'system': system,
                                'report_table': report_table })
