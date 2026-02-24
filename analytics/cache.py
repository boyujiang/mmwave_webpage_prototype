from django.core.cache import cache
import json

class RealtimeCache:
    @staticmethod
    def set_metric(metric_name, value, ttl=10):
        """Store real-time metric (expires in 10 seconds)"""
        cache.set(f'realtime:{metric_name}', value, timeout=ttl)
    
    @staticmethod
    def get_metric(metric_name):
        """Get real-time metric"""
        return cache.get(f'realtime:{metric_name}')
    
    @staticmethod
    def set_dashboard_data(user_id, data, ttl=30):
        """Cache dashboard data for specific user"""
        cache.set(f'dashboard:{user_id}', json.dumps(data), timeout=ttl)
    
    @staticmethod
    def get_dashboard_data(user_id):
        """Get cached dashboard data"""
        data = cache.get(f'dashboard:{user_id}')
        return json.loads(data) if data else None
