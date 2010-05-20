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
