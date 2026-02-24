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
