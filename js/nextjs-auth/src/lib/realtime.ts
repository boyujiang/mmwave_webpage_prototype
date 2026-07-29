export type ResidentStatus =
  | 'stable'
  | 'fall_detected'
  | 'room_departure';

export interface VitalsData {
  heart_rate: number;
  respiration: number;
  activity_status: string;
  in_bed: boolean;
  in_room: boolean;
  recorded_at: string;
}

export interface VitalsUpdate extends VitalsData {
  resident_id: number;
  room_number: string;
  status: ResidentStatus;
  alert_dismissed_at: string | null;
}

export interface RealtimeResident {
  id: number;
  latest_vitals: VitalsData | null;
  status: ResidentStatus;
  alert_dismissed_at: string | null;
}

export function applyVitalsUpdate<T extends RealtimeResident>(
  resident: T,
  update: VitalsUpdate,
): T {
  if (resident.id !== update.resident_id) {
    return resident;
  }

  return {
    ...resident,
    latest_vitals: {
      heart_rate: update.heart_rate,
      respiration: update.respiration,
      activity_status: update.activity_status,
      in_bed: update.in_bed,
      in_room: update.in_room,
      recorded_at: update.recorded_at,
    },
    status: update.status,
    alert_dismissed_at: update.alert_dismissed_at,
  };
}
