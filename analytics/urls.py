from django.urls import path
from .views import RealtimeDataView, DailySummaryView, ConfigView

urlpatterns = [
    path('realtime/', RealtimeDataView.as_view(), name='realtime'),
    path('daily/', DailySummaryView.as_view(), name='daily_summary'),
    path('config/', ConfigView.as_view(), name='config'),
]

