from models import Metric
import math
import sys

BYTE_UNITS = {
    'B':   1,
    'KiB': 1024,
    'MiB': 1024*1024
}

TIME_UNITS = {
    's':  1,
    'ms': 0.001,
    'us': 0.000001
}

def format_values(values, units):
    # This routine figures out how to display the values on a line
    # of the report using three pieces of information
    #
    #  - The absolute magnitude of the values
    #  - The difference between the values
    #  - The units for the given metric
    #
    # I've marked various arbitrary parameters below as TWEAKABLE

    set_values = [v for v in values if v is not None]
    if len(set_values) == 0:
        return ['' for v in values], units
    high = max(max(set_values), - min(set_values))
    diff = max(set_values) - min(set_values)
    suffix = ''
    mult = 1

    if units in BYTE_UNITS:
        mult = BYTE_UNITS[units]

        # If we have a difference of only a few bytes, then
        # we don't want to display fractional K/M with a lot
        # of precision
        if diff == 0 or diff > 100:
            # TWEAKABLE: transition points from B => K => M
            if high * mult >= 1024 * 1024:
                mult = mult / (1024. * 1024.)
                suffix = 'M'
                units = 'MiB'
            elif high * mult >= 1024:
                mult = mult / 1024.
                suffix = 'K'
                units = 'KiB'
            else:
                units = 'B'

    elif units in TIME_UNITS:
        mult = TIME_UNITS[units]

        # TWEAKABLE: transition points from us => s => s
        if high * mult >= 0.1:
            units = suffix = 's'
        elif high * mult >= 0.0001:
            units = suffix = 'ms'
            mult *= 1000
        else:
            units = suffix = 'us'
            mult *= 1000000

    high = high * mult
    diff = diff * mult

    # Determine how many digits we need to avoid scientific notation
    if high == 0:
        digits = 1
    else:
        digits = 1 + math.floor(math.log10(high))
        # TWEAKABLE: minimum number of displayed significant digits
        #   before we switch to scientific notation
        digits = max(digits, 3)
        # TWEAKABLE: maximum number of displayed significant digits
        #   before we switch to scientific notation
        digits = min(digits, 6)

        # If we have multiple values, determine how many digits we need
        # to distinguish the values
        if len(values) > 1:
            if diff > 0:
                diff_digits = 1 + math.floor(math.log10(high)) - math.floor(math.log10(diff))
                digits = max(digits, diff_digits)

        digits = int(digits)

    format = '%.*g' + suffix
    result = []
    for v in values:
        if v is None:
            result.append("")
        else:
            result.append(format % (digits, mult * v))

    return result, units

class ReportTable:
    def __init__(self):
        self.reports = []
        self.col_headers = []
        self.__rows = None

    def add_report(self, report, name, link=None):
        self.reports.append(report)
        self.col_headers.append({ 'name': name,
                                  'link': link })

    def __get_data(self):
        if self.__rows != None:
            return

        self.__rows = []
        if len(self.reports) == 0:
            return

        metrics_by_report = {}
        for report in self.reports:
            report_metrics = {}
            for metric in report.metric_set.all():
                report_metrics[metric.name] = metric
            metrics_by_report[report] = report_metrics

        sorted_reports = sorted(self.reports, lambda a, b: cmp(a.date, b.date))
        latest_report = sorted_reports[-1]
        latest_metrics = sorted(metrics_by_report[latest_report].values(), lambda a, b: cmp(a.name, b.name))

        for metric in latest_metrics:
            values = []
            for report in self.reports:
                report_metrics = metrics_by_report[report]
                if metric.name in report_metrics:
                    m = report_metrics[metric.name]
                    values.append(m.value)
                else:
                    values.append(None)

            formatted, units = format_values(values, metric.units)
            self.__rows.append({ 'metric': metric,
                                 'units': units,
                                 'values': formatted })
                
    @property
    def rows(self):
        self.__get_data()
        return self.__rows

# This provides an identical interface to ReportTable, but instead
# of comparing reports, it compares runs in one report
class RunTable:
    def __init__(self, report_json):
        self.json = report_json
        self.reports = []
        self.__col_headers = None
        self.__rows = None

    def __get_data(self):
        if self.__rows != None:
            return

        self.__col_headers = []
        self.__rows = []

        metrics = self.json['metrics']
        metric_names = sorted(metrics.keys())

        if len(metric_names) == 0:
            return

        first_metric = metrics[metric_names[0]]
        self.__col_headers = []
        for i in xrange(0, len(first_metric['values'])):
            self.__col_headers.append({ 'name': "Run %d" % (i + 1),
                                        'link': None })

        for name in metric_names:
            metric = metrics[name]
            # For ReportTable, row.metric is a Metric object, here it's just a dictionary
            # that looks much the same to to the template
            formatted, units = format_values(metric['values'], metric['units'])
            self.__rows.append({ 'metric': { 'name': name,
                                             'description': metric['description'] },
                                 'units': units,
                                 'values': formatted })

    @property
    def col_headers(self):
        self.__get_data()
        return self.__col_headers

    @property
    def rows(self):
        self.__get_data()
        return self.__rows

if __name__ == '__main__':
    def test(values, units, expected):
        results, new_units = format_values(values, units)
        if results != expected:
            raise AssertionError('Formatting %r (%s), expected %r, got %r' %
                                 (values, units, expected, results))

    # 0 length list
    test([], '', [])

    # None values
    test([None], '', [''])
    test([None, 1], '', ['', '1'])

    # Test points at which we give up and use scientific notation
    test([0.00001], '', ['1e-05'])
    test([0.0001], '', ['0.0001'])
    test([100000], '', ['100000'])
    test([1000000], '', ['1e+06'])

    # Check points at which we switch between us/ms/s
    test([90], 'us', ['90us'])
    test([110], 'us', ['0.11ms'])
    test([90], 'ms', ['90ms'])
    test([110], 'ms', ['0.11s'])

    # Check seconds converting to something else
    test([0.09], 's', ['90ms'])

    # Check points at which we switch between B/KB/MB
    test([1023], 'B', ['1023'])
    test([1024], 'B', ['1K'])
    test([1024*1024 - 1], 'B', ['1024K'])
    test([1024*1024], 'B', ['1M'])

    # Check KB => B, MB => KB
    test([0.1], 'KiB', ['102'])
    test([0.1], 'MiB', ['102K'])

    test([1100000,1200000], '', ['1.1e+06', '1.2e+06'])
    test([1000001,1000002], '', ['1000001', '1000002'])
    test([1.10000,1.20000], '', ['1.1', '1.2'])
    test([1.00001,1.00002], '', ['1.00001', '1.00002'])
