from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Schedule tasks
app.conf.beat_schedule = {
    'generate-resident-events-hourly': {
        'task': 'analytics.tasks.generate_resident_events',
        'schedule': crontab(minute=0),
    },
}
