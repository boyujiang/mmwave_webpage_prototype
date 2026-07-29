from abc import ABC, abstractmethod
from datetime import timedelta

from django.db.models import Avg, Count
from django.db.models.functions import TruncDate, TruncHour, TruncWeek

from .models import ResidentEvent, ResidentVitals


class VitalsHistoryMetric(ABC):
    """Polymorphic interface for a resident-history metric."""

    supports_hourly = True

    @abstractmethod
    def get_history(self, resident, start_time, range_param):
        """Return the existing history response payload for this metric."""


class AveragedVitalMetric(VitalsHistoryMetric):
    field_name = None
    baseline = 0

    def get_history(self, resident, start_time, range_param):
        vitals = ResidentVitals.objects.filter(
            resident=resident,
            recorded_at__gte=start_time,
        ).order_by('recorded_at')

        truncation = {
            'hour': TruncHour,
            'day': TruncDate,
        }.get(range_param, TruncWeek)
        grouped = (
            vitals.annotate(period=truncation('recorded_at'))
            .values('period')
            .annotate(avg_val=Avg(self.field_name))
            .order_by('period')
        )
        data = [
            {
                'timestamp': group['period'].isoformat(),
                'value': round(group['avg_val'], 1),
            }
            for group in grouped
            if group['avg_val']
        ]
        average = (
            sum(item['value'] for item in data) / max(len(data), 1)
            if data
            else self.baseline
        )

        return {
            'data_avgs': data,
            'baseline': self.baseline,
            'average': round(average, 1),
        }


class HeartRateMetric(AveragedVitalMetric):
    field_name = 'heart_rate'
    baseline = 72


class RespirationMetric(AveragedVitalMetric):
    field_name = 'respiration'
    baseline = 16


class ActivityMetric(VitalsHistoryMetric):
    activity_values = {
        'lying_down': 1,
        'sitting': 2,
        'standing': 3,
        'walking': 4,
    }

    def get_history(self, resident, start_time, range_param):
        vitals = ResidentVitals.objects.filter(
            resident=resident,
            recorded_at__gte=start_time,
        ).order_by('recorded_at')

        if range_param == 'hour':
            grouped = vitals.annotate(
                period=TruncHour('recorded_at')
            ).values('period')
        elif range_param == 'day':
            grouped = vitals.annotate(
                period=TruncDate('recorded_at')
            ).values('period')
        else:
            grouped = vitals.annotate(
                period=TruncWeek('recorded_at')
            ).values('period')

        data = []
        for group in grouped:
            period = group['period']
            period_vitals = self._period_vitals(
                resident,
                period,
                range_param,
            )
            activities = [
                self.activity_values.get(vital.activity_status, 1)
                for vital in period_vitals
            ]
            if activities:
                data.append({
                    'timestamp': period.isoformat(),
                    'value': round(sum(activities) / len(activities), 1),
                })

        return {
            'data_avgs': data,
            'baseline': 1,
            'average': (
                len(data) > 0
                and sum(item['value'] for item in data) / len(data)
                or 1
            ),
        }

    def _period_vitals(self, resident, period, range_param):
        if range_param == 'hour':
            return ResidentVitals.objects.filter(
                resident=resident,
                recorded_at__hour=period.hour,
                recorded_at__date=period.date(),
            )
        if range_param == 'day':
            return ResidentVitals.objects.filter(
                resident=resident,
                recorded_at__date=period,
            )
        return ResidentVitals.objects.filter(
            resident=resident,
            recorded_at__gte=period,
            recorded_at__lt=period + timedelta(days=7),
        )


class EventCountMetric(VitalsHistoryMetric):
    supports_hourly = False
    event_type = None

    def get_history(self, resident, start_time, range_param):
        events = ResidentEvent.objects.filter(
            resident=resident,
            event_type=self.event_type,
            timestamp__gte=start_time,
        ).order_by('timestamp')

        truncation = TruncDate if range_param == 'day' else TruncWeek
        grouped = (
            events.annotate(period=truncation('timestamp'))
            .values('period')
            .annotate(count=Count('id'))
            .order_by('period')
        )
        data = [
            {
                'timestamp': group['period'].isoformat(),
                'value': group['count'],
            }
            for group in grouped
        ]

        return {
            'data_avgs': data,
            'baseline': 0,
            'average': (
                sum(item['value'] for item in data) / max(len(data), 1)
            ),
        }


class BathroomRunMetric(EventCountMetric):
    event_type = 'bathroom_run'


class FallMetric(EventCountMetric):
    event_type = 'fall_detected'


class EmptyMetric(VitalsHistoryMetric):
    def get_history(self, resident, start_time, range_param):
        return {
            'data_avgs': [],
            'baseline': 0,
            'average': 0,
        }


class EmptyNonHourlyMetric(EmptyMetric):
    supports_hourly = False


METRICS = {
    'hr': HeartRateMetric(),
    'rr': RespirationMetric(),
    'activity': ActivityMetric(),
    'br': BathroomRunMetric(),
    'f': FallMetric(),
    # These metrics historically return the non-hourly warning even though
    # they do not otherwise have a history implementation.
    'rd': EmptyNonHourlyMetric(),
    'w': EmptyNonHourlyMetric(),
    'ibt': EmptyNonHourlyMetric(),
}
DEFAULT_METRIC = EmptyMetric()

