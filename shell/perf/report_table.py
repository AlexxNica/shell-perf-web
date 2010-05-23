from models import Metric
import sys

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

            self.__rows.append({ 'metric': metric,
                                 'values': values })
                
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
            self.__rows.append({ 'metric': { 'name': name,
                                             'description': metric['description'],
                                             'units': metric['units'] },
                                 'values': metric['values'] })

    @property
    def col_headers(self):
        self.__get_data()
        return self.__col_headers

    @property
    def rows(self):
        self.__get_data()
        return self.__rows
