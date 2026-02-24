from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Schedule tasks
app.conf.beat_schedule = {
    'update-realtime-every-5-seconds': {
        'task': 'analytics.tasks.update_realtime_metrics',
        'schedule': 5.0,  # Every 5 seconds
    },
    'generate-daily-summary': {
        'task': 'analytics.tasks.generate_daily_summary',
        'schedule': crontab(hour=0, minute=1),  # Daily at 00:01
    },
}
