# analytics/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .cache import RealtimeCache
from .models import AnalyticsSummary, DashboardConfig
from datetime import datetime, timedelta

class RealtimeDataView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get real-time data from Redis"""
        metrics = {
            'active_users': RealtimeCache.get_metric('active_users') or 0,
            'cpu_usage': RealtimeCache.get_metric('cpu_usage') or 0,
            'memory_usage': RealtimeCache.get_metric('memory_usage') or 0,
            'requests_per_second': RealtimeCache.get_metric('rps') or 0,
        }
        return Response(metrics)

class DailySummaryView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get daily summary (cached for 1 hour)"""
        cache_key = f'daily_summary:{datetime.now().date()}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        # Query from database
        today = datetime.now().date()
        summaries = AnalyticsSummary.objects.filter(
            period_type='daily',
            period_start__date=today
        )
        
        data = {
            summary.metric_name: summary.value 
            for summary in summaries
        }
        
        # Cache for 1 hour
        cache.set(cache_key, data, timeout=3600)
        
        return Response(data)

class ConfigView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user configuration (rarely changes)"""
        config, _ = DashboardConfig.objects.get_or_create(
            user=request.user
        )
        return Response({
            'theme': config.theme,
            'refresh_interval': config.refresh_interval,
            'widgets': config.widgets,
        })
    
    def post(self, request):
        """Update configuration"""
        config, _ = DashboardConfig.objects.get_or_create(
            user=request.user
        )
        config.theme = request.data.get('theme', config.theme)
        config.refresh_interval = request.data.get('refresh_interval', config.refresh_interval)
        config.widgets = request.data.get('widgets', config.widgets)
        config.save()
        
        return Response({'status': 'updated'})
