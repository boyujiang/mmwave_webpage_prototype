# analytics/tasks.py
from celery import shared_task
from .models import Resident, ResidentVitals, ResidentEvent
import random


@shared_task
def update_resident_vitals():
    """Update resident vitals (heart_rate, respiration, activity) - every 30 seconds"""
    residents = Resident.objects.filter(is_active=True)
    
    for resident in residents:
        base_heart_rate = random.uniform(60, 80)
        base_respiration = random.uniform(12, 20)
        
        ResidentVitals.objects.create(
            resident=resident,
            heart_rate=round(base_heart_rate + random.uniform(-5, 5), 1),
            respiration=round(base_respiration + random.uniform(-2, 2), 1),
            activity_level=round(random.uniform(0, 100), 1)
        )
    
    return f"Updated vitals for {residents.count()} residents"


@shared_task
def generate_resident_events():
    """Generate random resident events like bathroom runs - runs hourly, mostly overnight"""
    from django.utils import timezone
    
    now = timezone.now()
    hour = now.hour
    
    is_overnight = 22 <= hour or hour <= 6
    probability = 0.7 if is_overnight else 0.1
    
    residents = Resident.objects.filter(is_active=True)
    
    for resident in residents:
        if random.random() < probability:
            event_type = random.choice([
                'bathroom_run',
                'bathroom_run',
                'bathroom_run',
                'exited_room',
                'returned_room',
            ])
            
            ResidentEvent.objects.create(
                resident=resident,
                event_type=event_type,
                metadata={'auto_generated': True}
            )
    
    return f"Generated events for overnight period"


@shared_task
def create_sample_residents():
    """Create sample residents for testing"""
    sample_residents = [
        {'name': 'John Smith', 'room_number': '101'},
        {'name': 'Mary Johnson', 'room_number': '102'},
        {'name': 'Robert Williams', 'room_number': '103'},
        {'name': 'Patricia Brown', 'room_number': '104'},
    ]
    
    created = []
    for data in sample_residents:
        resident, created_flag = Resident.objects.get_or_create(
            room_number=data['room_number'],
            defaults={'name': data['name']}
        )
        if created_flag:
            created.append(resident.name)
    
    return f"Created sample residents: {created}" if created else "Residents already exist"
