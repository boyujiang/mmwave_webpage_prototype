import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from analytics.models import Resident
from django.utils import timezone
from datetime import timedelta

print("Clearing alert_dismissed_at for residents with timestamps older than 5 minutes...")

threshold = timezone.now() - timedelta(minutes=5)
result = Resident.objects.filter(alert_dismissed_at__lt=threshold).update(alert_dismissed_at=None)

print(f"Done! Cleared {result} residents.")

# Show current status
print("\nCurrent alert_dismissed_at status:")
for r in Resident.objects.all():
    print(f"  {r.name}: {r.alert_dismissed_at}")