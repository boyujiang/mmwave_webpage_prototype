# analytics/tasks.py
from celery import shared_task
from .models import Resident, ResidentVitals, ResidentEvent
import random


@shared_task
def update_resident_vitals():
    """Update resident vitals - every 30 seconds"""
    from django.utils import timezone
    
    residents = Resident.objects.filter(is_active=True)
    now = timezone.now()
    is_overnight = 22 <= now.hour or now.hour <= 6
    
    for resident in residents:
        base_heart_rate = random.uniform(60, 80)
        base_respiration = random.uniform(12, 20)
        
        # Activity status: standing, sitting, walking, lying_down
        activity_status = random.choice(['standing', 'sitting', 'walking', 'lying_down'])
        
        # Simulate in_bed and in_room states
        # Most residents are in bed during overnight, else random
        if is_overnight:
            in_bed = random.random() < 0.8  # 80% in bed overnight
        else:
            in_bed = random.random() < 0.3  # 30% in bed during day
        
        in_room = random.random() < 0.85  # 85% in room
        
        # Occasionally simulate fall (not in bed + lying down)
        if not in_bed and activity_status == 'lying_down' and random.random() < 0.05:
            # This creates a potential fall scenario
            pass
        
        ResidentVitals.objects.create(
            resident=resident,
            heart_rate=round(base_heart_rate + random.uniform(-5, 5), 1),
            respiration=round(base_respiration + random.uniform(-2, 2), 1),
            activity_status=activity_status,
            in_bed=in_bed,
            in_room=in_room
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
