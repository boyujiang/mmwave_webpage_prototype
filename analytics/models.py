from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Permanent Configuration
class DashboardConfig(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    theme = models.CharField(max_length=20, default='light')
    refresh_interval = models.IntegerField(default=5)  # seconds
    widgets = models.JSONField(default=list)
    
# Less Frequent Updates (Daily/Hourly)
class AnalyticsSummary(models.Model):
    PERIOD_CHOICES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ]
    
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start = models.DateTimeField(db_index=True)
    metric_name = models.CharField(max_length=100)
    value = models.FloatField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['period_type', 'period_start', 'metric_name']
        ordering = ['-period_start']

# Real-time Events (also logged to DB for history)
class RealtimeEvent(models.Model):
    event_type = models.CharField(max_length=50, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    data = models.JSONField()
    processed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']


# Resident (Static info stored in DB)
class Resident(models.Model):
    name = models.CharField(max_length=100)
    room_number = models.CharField(max_length=20, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - Room {self.room_number}"


# Resident Vitals (Frequently updated - every few seconds/minutes)
class ResidentVitals(models.Model):
    ACTIVITY_STATUS = [
        ('standing', 'Standing'),
        ('sitting', 'Sitting'),
        ('walking', 'Walking'),
        ('lying_down', 'Lying Down'),
    ]

    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='vitals')
    heart_rate = models.FloatField(null=True, blank=True)  # bpm
    respiration = models.FloatField(null=True, blank=True)  # breaths per minute
    activity_status = models.CharField(max_length=20, choices=ACTIVITY_STATUS, default='lying_down')
    in_bed = models.BooleanField(default=False)
    in_room = models.BooleanField(default=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']


# Resident Events (Bathroom runs, etc - overnight/irregular updates)
class ResidentEvent(models.Model):
    EVENT_TYPES = [
        ('bathroom_run', 'Bathroom Run'),
        ('fall_detected', 'Fall Detected'),
        ('medication_taken', 'Medication Taken'),
        ('exited_room', 'Exited Room'),
        ('returned_room', 'Returned Room'),
    ]

    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ['-timestamp']


# Caregiver Notes for Alerts
class AlertNote(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='alert_notes')
    alert_type = models.CharField(max_length=50)
    note = models.TextField()
    caregiver_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_dismissed = models.BooleanField(default=False)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
