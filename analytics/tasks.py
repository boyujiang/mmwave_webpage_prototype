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
    
    residents = Resident.objects.filter(is_active=True)
    
    for resident in residents:
        # Only generate bathroom runs overnight, max 5 per night
        if is_overnight:
            # Count today's bathroom runs
            today_start = now.replace(hour=22, minute=0, second=0, microsecond=0)
            count_today = ResidentEvent.objects.filter(
                resident=resident,
                event_type='bathroom_run',
                timestamp__gte=today_start
            ).count()
            
            if count_today < 5 and random.random() < 0.7:
                ResidentEvent.objects.create(
                    resident=resident,
                    event_type='bathroom_run',
                    metadata={'auto_generated': True}
                )
        
        # Other events can happen anytime
        if random.random() < 0.1:
            event_type = random.choice([
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


@shared_task
def generate_historical_data(weeks=2):
    """Generate historical data for all residents - several weeks of data for all 7 metrics"""
    from django.utils import timezone
    from datetime import timedelta
    
    residents = Resident.objects.all()
    if not residents.exists():
        return "No residents found. Run create_sample_residents first."
    
    now = timezone.now()
    start_time = now - timedelta(weeks=weeks)
    
    # Generate data points every 30 minutes
    current_time = start_time
    total_records = 0
    
    # Pick first resident to have a fall
    fall_resident = residents.first()
    
    # Base values for vitals
    base_hr = 85  # BPM
    base_rr = 16  # /min
    
    # Batch create for performance
    vitals_batch = []
    events_batch = []
    
    while current_time <= now:
        hour = current_time.hour
        is_overnight = 22 <= hour or hour <= 6
        
        for resident in residents:
            # Heart Rate & Respiration (only when sitting or lying_down)
            # Activity: 40% lying_down, 30% sitting, 20% walking, 10% standing
            activity_weights = ['lying_down'] * 40 + ['sitting'] * 30 + ['walking'] * 20 + ['standing'] * 10
            activity_status = random.choice(activity_weights)
            
            # Show vitals only when sitting or lying_down
            show_vitals = activity_status in ['sitting', 'lying_down']
            
            # In bed: overnight 80%, day 20%
            in_bed_prob = 0.8 if is_overnight else 0.2
            in_bed = random.random() < in_bed_prob
            
            # In room: 85% always
            in_room = random.random() < 0.85
            
            # Generate fall for first resident at a specific time
            is_fall_time = current_time.hour == 23 and current_time.minute == 30
            
            # Heart rate: base 85 ± 10 BPM
            # Respiration: base 16 ± 5
            heart_rate = round(base_hr + random.uniform(-10, 10), 1) if show_vitals else None
            respiration = round(base_rr + random.uniform(-5, 5), 1) if show_vitals else None
            
            vitals = ResidentVitals(
                resident=resident,
                heart_rate=heart_rate,
                respiration=respiration,
                activity_status=activity_status,
                in_bed=in_bed,
                in_room=in_room,
                recorded_at=current_time
            )
            vitals_batch.append(vitals)
            
            # Generate events
            # Bathroom runs: overnight more likely, max 5 per night
            if is_overnight and random.random() < 0.3:
                # Count today's bathroom runs so far
                today_start = current_time.replace(hour=22, minute=0, second=0, microsecond=0)
                if current_time < today_start:
                    today_start = today_start - timedelta(days=1)
                count_today = sum(1 for e in events_batch if e.event_type == 'bathroom_run' and e.resident == resident and e.timestamp >= today_start)
                
                if count_today < 5:
                    events_batch.append(ResidentEvent(
                        resident=resident,
                        event_type='bathroom_run',
                        timestamp=current_time
                    ))
            
            # Fall detected: only for first resident
            if resident == fall_resident and is_fall_time and not in_bed:
                events_batch.append(ResidentEvent(
                    resident=resident,
                    event_type='fall_detected',
                    timestamp=current_time,
                    metadata={'severity': 'high'}
                ))
            
            # Room departure (exited_room)
            if not in_room and random.random() < 0.3:
                events_batch.append(ResidentEvent(
                    resident=resident,
                    event_type='exited_room',
                    timestamp=current_time
                ))
            
            # Wandering - when activity changes frequently
            if activity_status == 'walking' and random.random() < 0.1:
                events_batch.append(ResidentEvent(
                    resident=resident,
                    event_type='wandering',
                    timestamp=current_time
                ))
        
        # Save in batches of 500
        if len(vitals_batch) >= 500:
            ResidentVitals.objects.bulk_create(vitals_batch)
            total_records += len(vitals_batch)
            vitals_batch = []
        
        if len(events_batch) >= 500:
            ResidentEvent.objects.bulk_create(events_batch)
            events_batch = []
        
        # Advance 30 minutes
        current_time += timedelta(minutes=30)
    
    # Save remaining
    if vitals_batch:
        ResidentVitals.objects.bulk_create(vitals_batch)
        total_records += len(vitals_batch)
    
    if events_batch:
        ResidentEvent.objects.bulk_create(events_batch)
    
    return f"Generated {total_records} vitals records for {residents.count()} residents over {weeks} weeks. Fall alert created for {fall_resident.name}."


@shared_task
def check_and_restore_alert(resident_id):
    """Check if resident still has alert after 5 minutes, generate new alert if needed"""
    import time
    from django.utils import timezone
    
    # Wait 5 minutes (300 seconds)
    time.sleep(300)
    
    try:
        resident = Resident.objects.get(id=resident_id, is_active=True)
    except Resident.DoesNotExist:
        return f"Resident {resident_id} not found or inactive"
    
    # Check current status
    latest = resident.vitals.first()
    if latest:
        is_fall = not latest.in_bed and latest.activity_status == 'lying_down'
        is_room_departure = not latest.in_bed and not latest.in_room
        
        if is_fall or is_room_departure:
            return f"Resident {resident.name} still has active alert"
    
    # No alert, generate one to restore it
    # Create vitals that trigger an alert
    ResidentVitals.objects.create(
        resident=resident,
        heart_rate=random.uniform(60, 80),
        respiration=random.uniform(12, 20),
        activity_status='lying_down',
        in_bed=False,  # Not in bed + lying down = fall detected
        in_room=False
    )
    
    return f"Alert restored for resident {resident.name}"


@shared_task
def check_alert_after_dismiss(resident_id, dismissed_at_iso=None):
    """Check if alert conditions are still met 5 minutes after dismiss"""
    from django.utils.dateparse import parse_datetime
    
    try:
        resident = Resident.objects.get(id=resident_id, is_active=True)
    except Resident.DoesNotExist:
        return f"Resident {resident_id} not found or inactive"

    if resident.alert_dismissed_at is None:
        return f"Resident {resident.name} has no dismissed alert"

    if dismissed_at_iso:
        expected_dismissed_at = parse_datetime(dismissed_at_iso)
        if (
            expected_dismissed_at is None
            or resident.alert_dismissed_at != expected_dismissed_at
        ):
            return f"Ignored stale alert check for {resident.name}"
    
    # Check current alert conditions
    latest = resident.vitals.first()
    if latest:
        is_fall = not latest.in_bed and latest.activity_status == 'lying_down'
        is_room_departure = not latest.in_bed and not latest.in_room
        
        # Clear the mute and immediately publish the restored alert state.
        if is_fall or is_room_departure:
            resident.alert_dismissed_at = None
            resident.save(update_fields=['alert_dismissed_at'])
            from .realtime import publish_resident_vitals
            publish_resident_vitals(resident, latest)
            return f"Alert conditions still met for {resident.name} - alert will be shown"
    
    # Clear the mute and publish the stable state to connected frontends.
    resident.alert_dismissed_at = None
    resident.save(update_fields=['alert_dismissed_at'])
    if latest:
        from .realtime import publish_resident_vitals
        publish_resident_vitals(resident, latest)
    return f"Alert conditions no longer met for {resident.name}"
