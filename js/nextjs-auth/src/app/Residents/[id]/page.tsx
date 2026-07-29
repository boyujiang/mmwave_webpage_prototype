'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { getUserProfile, getResident, getResidentVitalsHistory, getAlertNotes, createAlertNote, dismissAlert, toggleResidentActive } from '@/src/lib/api';
import { useVitalsSocket } from '@/src/hooks/useVitalsSocket';
import {
  applyVitalsUpdate,
  type VitalsUpdate,
} from '@/src/lib/realtime';
import type { UserProfile } from '@/src/lib/types';
import Sidebar from '@/src/components/Sidebar';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  type ChartData,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface Resident {
  id: number;
  name: string;
  room_number: string;
  is_active: boolean;
  alert_dismissed_at: string | null;
  latest_vitals: {
    heart_rate: number;
    respiration: number;
    activity_status: string;
    in_bed: boolean;
    in_room: boolean;
    recorded_at: string;
  } | null;
  today_bathroom_runs: number;
  status: 'stable' | 'fall_detected' | 'room_departure';
}

interface AlertNote {
  id: string;
  alert_type: string;
  note: string;
  caregiver_name: string;
  created_at: string;
  is_dismissed: boolean;
  dismissed_at: string | null;
}

interface HistoryPoint {
  timestamp: string;
  value: number;
}

const metrics = [
  { id: 'hr', label: 'Heart Rate', unit: 'BPM' },
  { id: 'rr', label: 'Respiration', unit: '/min' },
  { id: 'br', label: 'Bathroom Runs', unit: 'times' },
  { id: 'f', label: 'Falls', unit: 'times' },
  { id: 'rd', label: 'Room Departures', unit: 'times' },
  { id: 'w', label: 'Wandering', unit: 'times' },
  { id: 'ibt', label: 'In Bed Time', unit: 'hours' },
];

const metricUnits: Record<string, string> = {
  hr: 'BPM',
  rr: '/min',
  br: 'times',
  f: 'times',
  rd: 'times',
  w: 'times',
  ibt: 'hours',
};

const acceptableHrRange = [60, 100];
const acceptableRrRange = [12, 20];

const getActivityLabel = (status: string) => {
  const labels: Record<string, string> = {
    standing: 'Standing',
    sitting: 'Sitting',
    walking: 'Walking',
    lying_down: 'Lying Down',
  };
  return labels[status] || status;
};

const canShowVitals = (status: string) => {
  return status === 'sitting' || status === 'lying_down';
};

const formatTimestamp = (timestamp: string, range: string) => {
  const date = new Date(timestamp);
  if (range === 'hour') {
    return date.toLocaleTimeString('en-CA', {
      hour12: false,
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  return date.toLocaleDateString('en-CA', {
    month: 'short',
    day: 'numeric',
  });
};

export default function ResidentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const residentId = params.id as string;

  const [user, setUser] = useState<UserProfile | null>(null);
  const [resident, setResident] = useState<Resident | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState('hr');
  const [selectedRange, setSelectedRange] = useState('day');
  const [chartData, setChartData] = useState<ChartData<'line'>>({
    labels: [],
    datasets: [],
  });
  const [alertNotes, setAlertNotes] = useState<AlertNote[]>([]);
  const [newNote, setNewNote] = useState('');
  const [selectedNote, setSelectedNote] = useState<AlertNote | null>(null);
  const [dismissedLocally, setDismissedLocally] = useState(false);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [userData, residentData, notesData] = await Promise.all([
          getUserProfile(),
          getResident(residentId),
          getAlertNotes(residentId)
        ]);
        setUser(userData);
        setAlertNotes(notesData);
        setResident(residentData);
        setDismissedLocally(false);
        setLoading(false);
      } catch {
        router.push('/login');
      }
    };
    fetchInitialData();
  }, [router, residentId]);

  const hasResident = resident !== null;

  useEffect(() => {
    if (!hasResident) return;
    const fetchHistory = async () => {
      try {
        const data = await getResidentVitalsHistory(residentId, selectedMetric, selectedRange);
        const labels = data.data_avgs.map((point: HistoryPoint) =>
          formatTimestamp(point.timestamp, selectedRange)
        );
        const values = data.data_avgs.map(
          (point: HistoryPoint) => point.value
        );
        const unit = metricUnits[selectedMetric] || '';
        setChartData({
          labels,
          datasets: [
            { label: `${metrics.find(m => m.id === selectedMetric)?.label || selectedMetric} (${unit})`, data: values, borderColor: '#000', backgroundColor: '#000', fill: false },
          ],
        });
      } catch (error) {
        console.error('Failed to fetch history:', error);
      }
    };
    fetchHistory();
  }, [hasResident, selectedMetric, selectedRange, residentId]);

  const handleVitals = useCallback((update: VitalsUpdate) => {
    setResident((current) =>
      current ? applyVitalsUpdate(current, update) : current
    );
    setDismissedLocally(Boolean(update.alert_dismissed_at));
  }, []);

  useVitalsSocket(handleVitals, Boolean(user), residentId);

  const handleSubmitNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim()) return;
    try {
      await createAlertNote(residentId, newNote, resident?.status || 'general');
      setNewNote('');
      const notes = await getAlertNotes(residentId);
      setAlertNotes(notes);
    } catch (error) {
      console.error('Failed to submit note:', error);
    }
  };

  const handleDismissAlert = async () => {
    try {
      await dismissAlert(residentId);
      setDismissedLocally(true);
    } catch (error) {
      console.error('Failed to dismiss alert:', error);
    }
  };

  const handleToggleActive = async () => {
    try {
      const result = await toggleResidentActive(residentId);
      setResident((prev: Resident | null) => prev ? { ...prev, is_active: result.is_active } : null);
    } catch (error) {
      console.error('Failed to toggle active:', error);
    }
  };

  const isAbnormalHR = () => {
    const hr = resident?.latest_vitals?.heart_rate;
    return hr != null && (hr < acceptableHrRange[0] || hr > acceptableHrRange[1]);
  };

  const isAbnormalRR = () => {
    const rr = resident?.latest_vitals?.respiration;
    return rr != null && (rr < acceptableRrRange[0] || rr > acceptableRrRange[1]);
  };

  const isAlertDismissed =
    dismissedLocally || Boolean(resident?.alert_dismissed_at);

  if (loading || !resident) {
    return <div className="min-h-screen flex items-center justify-center"><div className="text-xl">Loading...</div></div>;
  }

  return (
    <div className="flex min-h-screen" style={{ backgroundColor: '#f5f0f0' }}>
      <Sidebar user={user} />
      <main className="flex-1">
        {/* Header */}
        <div style={{ backgroundColor: '#f5f0f0', borderBottom: '1px solid #d8d8db', padding: '20px', fontSize: '26px', fontWeight: 600 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div>{resident.name}</div>
                <button
                  onClick={handleToggleActive}
                  style={{
                    padding: '4px 12px',
                    fontSize: '12px',
                    borderRadius: '12px',
                    border: 'none',
                    cursor: 'pointer',
                    backgroundColor: resident.is_active ? '#dcfce7' : '#f3f4f6',
                    color: resident.is_active ? '#166534' : '#6b7280',
                  }}
                >
                  {resident.is_active ? 'Active' : 'Inactive'}
                </button>
              </div>
              <div style={{ fontSize: '20px', fontWeight: 400, color: '#666' }}>Room: {resident.room_number}</div>
            </div>
          </div>
        </div>

        {/* Alert Banner */}
        {resident.is_active && resident.status !== 'stable' && !isAlertDismissed && (
          <div style={{ padding: '12px', backgroundColor: '#fee2e2', borderBottom: '1px solid #fca5a5' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 600, color: '#991b1b' }}>
                ⚠️ {resident.status === 'fall_detected' ? 'Fall Detected!' : 'Room Departure!'}
              </span>
              <button onClick={handleDismissAlert} style={{ padding: '6px 12px', border: '1px solid #dc2626', borderRadius: '4px', backgroundColor: 'white', color: '#dc2626', cursor: 'pointer' }}>
                Dismiss Alert
              </button>
            </div>
          </div>
        )}

        {/* Main Content - Two Columns */}
        <div style={{ display: 'flex', minHeight: 'calc(100vh - 150px)' }}>
          {/* Left Sidebar - Vitals */}
          <div style={{ width: '33%', borderRight: '1px solid #d8d8db', padding: '16px', overflowY: 'auto' }}>
            {/* Abnormal Alerts */}
            {resident.is_active && canShowVitals(resident.latest_vitals?.activity_status || '') && isAbnormalHR() && (
              <div style={{ margin: '16px 8px 0 8px', padding: '12px', backgroundColor: '#fee2e2', border: '1px solid #fca5a5', borderRadius: '4px', color: '#dc2626', fontSize: '14px' }}>
                Abnormal heart rate: {resident.latest_vitals?.heart_rate} BPM
              </div>
            )}
            {resident.is_active && canShowVitals(resident.latest_vitals?.activity_status || '') && isAbnormalRR() && (
              <div style={{ margin: '16px 8px 0 8px', padding: '12px', backgroundColor: '#fee2e2', border: '1px solid #fca5a5', borderRadius: '4px', color: '#dc2626', fontSize: '14px' }}>
                Abnormal respiration: {resident.latest_vitals?.respiration} /min
              </div>
            )}

            {/* Vital Cards */}
            <div style={{ padding: '16px 8px', display: 'flex', gap: '8px' }}>
              <div style={{ flex: 1, padding: '12px', backgroundColor: '#fef2f2', borderRadius: '1rem', border: '1px solid #d8d8db', textAlign: 'center' }}>
                <div style={{ fontSize: '12px', color: '#dc2626', fontWeight: 500 }}>Heart Rate</div>
                <div style={{ fontSize: '34px', fontWeight: 'bold', color: '#fc3737' }}>
                  {!resident.is_active || !canShowVitals(resident.latest_vitals?.activity_status || '') ? 'N/A' : (resident.latest_vitals?.heart_rate || '--')}
                </div>
                <div style={{ fontSize: '12px', color: '#fca5a5' }}>BPM</div>
              </div>
              <div style={{ flex: 1, padding: '12px', backgroundColor: '#eff6ff', borderRadius: '1rem', border: '1px solid #d8d8db', textAlign: 'center' }}>
                <div style={{ fontSize: '12px', color: '#2563eb', fontWeight: 500 }}>Respiration</div>
                <div style={{ fontSize: '34px', fontWeight: 'bold', color: '#488bff' }}>
                  {!resident.is_active || !canShowVitals(resident.latest_vitals?.activity_status || '') ? 'N/A' : (resident.latest_vitals?.respiration || '--')}
                </div>
                <div style={{ fontSize: '12px', color: '#93c5fd' }}>/min</div>
              </div>
            </div>

            {/* Status */}
            <div style={{ padding: '0 20px', fontSize: '18px' }}>
              <p>Bathroom Runs (10pm-8am): {resident.today_bathroom_runs}</p>
              <p>Activity: {getActivityLabel(resident.latest_vitals?.activity_status || '')}</p>
            </div>

            {/* Location */}
            <div style={{ marginTop: '20px', padding: '20px', backgroundColor: '#f7f9eb', fontSize: '18px', fontWeight: 600 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Not In Bed</span>
                <span>In Room</span>
              </div>
            </div>
          </div>

          {/* Right - Chart and Notes */}
          <div style={{ flex: 1, padding: '16px' }}>
            {/* Metric Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '16px' }}>
              {metrics.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setSelectedMetric(m.id)}
                  style={{
                    padding: '8px',
                    border: selectedMetric === m.id ? '2px solid #930c0c' : '1px solid #2d2d2d',
                    borderRadius: '4px',
                    backgroundColor: selectedMetric === m.id ? '#ffefef' : 'white',
                    color: selectedMetric === m.id ? '#930c0c' : '#2d2d2d',
                    cursor: 'pointer',
                    fontWeight: selectedMetric === m.id ? 600 : 400,
                  }}
                >
                  {m.label}
                </button>
              ))}
            </div>

            {/* Range Buttons */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginBottom: '16px' }}>
              {['hour', 'day', 'week'].map((r) => (
                <button
                  key={r}
                  onClick={() => setSelectedRange(r)}
                  style={{
                    padding: '6px 12px',
                    border: '1px solid #2d2d2d',
                    borderRadius: '4px',
                    backgroundColor: selectedRange === r ? '#2d2d2d' : 'white',
                    color: selectedRange === r ? 'white' : '#2d2d2d',
                    cursor: 'pointer',
                    textTransform: 'capitalize',
                  }}
                >
                  {r}
                </button>
              ))}
            </div>

            {/* Chart */}
            <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '16px', border: '1px solid #d8d8db' }}>
              <div style={{ height: '200px' }}>
                <Line data={chartData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { enabled: false } }, scales: { y: { title: { display: true, text: metricUnits[selectedMetric] || '' } } } }} />
              </div>
            </div>

            {/* Notes Section */}
            <div style={{ marginTop: '24px', backgroundColor: 'white', borderRadius: '8px', padding: '16px', border: '1px solid #d8d8db' }}>
              <h3 style={{ fontWeight: 600, marginBottom: '12px' }}>Caregiver Notes</h3>
              
              <div style={{ display: 'flex', gap: '16px' }}>
                {/* File List */}
                <div style={{ width: '30%', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '8px', maxHeight: '200px', overflowY: 'auto' }}>
                  {alertNotes.length > 0 ? (
                    alertNotes.map((note) => (
                      <div
                        key={note.id}
                        onDoubleClick={() => setSelectedNote(note)}
                        style={{
                          padding: '8px',
                          cursor: 'pointer',
                          borderRadius: '4px',
                          marginBottom: '4px',
                          backgroundColor: selectedNote?.id === note.id ? '#dbeafe' : 'transparent',
                          border: selectedNote?.id === note.id ? '1px solid #3b82f6' : '1px solid transparent',
                        }}
                      >
                        <span style={{ color: '#374151', fontSize: '14px' }}>{note.id}</span>
                      </div>
                    ))
                  ) : (
                    <p style={{ color: '#9ca3af', textAlign: 'center', padding: '20px' }}>No notes</p>
                  )}
                </div>

                {/* Note Content */}
                <div style={{ flex: 1, border: '1px solid #e5e7eb', borderRadius: '8px', padding: '12px' }}>
                  {selectedNote ? (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ fontWeight: 500 }}>{selectedNote.caregiver_name}</span>
                        <span style={{ fontSize: '14px', color: '#6b7280' }}>{new Date(selectedNote.created_at).toLocaleString()}</span>
                      </div>
                      <p style={{ color: '#374151' }}>{selectedNote.note}</p>
                      {selectedNote.is_dismissed && <span style={{ fontSize: '12px', color: '#9ca3af' }}>Dismissed</span>}
                    </div>
                  ) : (
                    <p style={{ color: '#9ca3af', textAlign: 'center', padding: '20px' }}>Double-click a file to view</p>
                  )}
                </div>
              </div>

              {/* Create Note */}
              <form onSubmit={handleSubmitNote} style={{ marginTop: '16px', display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                  placeholder="Create new note..."
                  style={{ flex: 1, padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px' }}
                />
                <button
                  type="submit"
                  disabled={!newNote.trim()}
                  style={{ padding: '8px 16px', backgroundColor: '#3b82f6', color: 'white', borderRadius: '6px', opacity: newNote.trim() ? 1 : 0.5, cursor: newNote.trim() ? 'pointer' : 'not-allowed' }}
                >
                  Create
                </button>
              </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
