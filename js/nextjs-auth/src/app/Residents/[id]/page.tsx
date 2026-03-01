'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { getUserProfile, getResidents, getResidentVitalsHistory } from '@/src/lib/api';
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
  latest_vitals: {
    heart_rate: number;
    respiration: number;
    activity_level: number;
    recorded_at: string;
  } | null;
  today_bathroom_runs: number;
  latest_events: Array<{
    id: number;
    event_type: string;
    event_type_display: string;
    timestamp: string;
  }>;
}

const metrics = [
  { id: 'hr', label: 'Heart Rate' },
  { id: 'rr', label: 'Respiration' },
  { id: 'br', label: 'Bathroom Runs' },
  { id: 'f', label: 'Falls' },
  { id: 'rd', label: 'Room Departures' },
  { id: 'w', label: 'Wandering' },
  { id: 'ibt', label: 'In Bed Time' },
];

const acceptableHrRange = [60, 100];
const acceptableRrRange = [12, 20];

export default function ResidentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const residentId = params.id as string;
  
  const [user, setUser] = useState<any>(null);
  const [resident, setResident] = useState<Resident | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState('hr');
  const [selectedRange, setSelectedRange] = useState('day');
  const [chartData, setChartData] = useState<any>({ labels: [], datasets: [] });
  const [average, setAverage] = useState<number | null>(null);
  const [baseline, setBaseline] = useState<number | null>(null);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [userData, residentsData] = await Promise.all([
          getUserProfile(),
          getResidents()
        ]);
        setUser(userData);
        const found = residentsData.find((r: Resident) => r.id === parseInt(residentId));
        setResident(found || null);
        setLoading(false);
      } catch (error) {
        router.push('/login');
      }
    };

    fetchInitialData();
  }, [router, residentId]);

  useEffect(() => {
    if (!resident) return;

    const fetchHistory = async () => {
      try {
        const data = await getResidentVitalsHistory(residentId, selectedMetric, selectedRange);
        
        const labels = data.data_avgs.map((d: any) => formatTimestamp(d.timestamp, selectedRange));
        const values = data.data_avgs.map((d: any) => d.value);
        
        setBaseline(data.baseline);
        
        if (values.length > 0) {
          const avg = values.reduce((a: number, b: number) => a + b, 0) / values.length;
          setAverage(avg);
        }

        setChartData({
          labels,
          datasets: [
            {
              label: metrics.find(m => m.id === selectedMetric)?.label || selectedMetric,
              data: values,
              borderColor: '#000',
              backgroundColor: '#000',
              fill: false,
            },
            {
              label: 'Baseline',
              data: labels.map(() => data.baseline),
              borderColor: '#488bff',
              borderDash: [2, 4],
              pointStyle: false,
            },
          ],
        });
      } catch (error) {
        console.error('Failed to fetch history:', error);
      }
    };

    fetchHistory();
  }, [resident, selectedMetric, selectedRange, residentId]);

  useEffect(() => {
    if (!user) return;

    const fetchResidents = async () => {
      try {
        const data = await getResidents();
        const found = data.find((r: Resident) => r.id === parseInt(residentId));
        setResident(found || null);
      } catch (error) {
        console.error('Failed to fetch resident:', error);
      }
    };

    fetchResidents();
    const interval = setInterval(fetchResidents, 30000);
    return () => clearInterval(interval);
  }, [user, residentId]);

  const formatTimestamp = (timestamp: string, range: string) => {
    const date = new Date(timestamp);
    if (range === 'hour' || range === 'day') {
      return date.toLocaleTimeString('en-CA', {
        hour12: false,
        hour: 'numeric',
        minute: '2-digit',
      });
    } else {
      return date.toLocaleDateString('en-CA', {
        weekday: 'short',
        day: 'numeric',
      });
    }
  };

  const getAverageDisplay = () => {
    if (average === null) return '';
    const label = selectedRange === 'hour' ? 'Hourly' : selectedRange === 'day' ? 'Daily' : 'Weekly';
    return `${label} Avg: ${average.toFixed(0)} BPM`;
  };

  const getBaselineDisplay = () => {
    if (average === null || baseline === null) return '';
    const percentDiff = ((average - baseline) / baseline) * 100;
    if (percentDiff >= 10) return `↑ ${percentDiff.toFixed(1)}% vs. baseline`;
    if (percentDiff <= -10) return `↓ ${Math.abs(percentDiff).toFixed(1)}% vs. baseline`;
    return '';
  };

  const getActivityStatus = () => {
    const activity = resident?.latest_vitals?.activity_level || 0;
    if (activity > 70) return 'Walking';
    if (activity > 30) return 'Sitting';
    return 'Lying Down';
  };

  const isAbnormalHR = () => {
    const hr = resident?.latest_vitals?.heart_rate;
    return hr !== null && (hr < acceptableHrRange[0] || hr > acceptableHrRange[1]);
  };

  const isAbnormalRR = () => {
    const rr = resident?.latest_vitals?.respiration;
    return rr !== null && (rr < acceptableRrRange[0] || rr > acceptableRrRange[1]);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  if (!resident) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Resident not found</div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen" style={{ backgroundColor: '#f5f0f0' }}>
      <Sidebar user={user} />
      
      <main className="flex-1">
        {/* Header */}
        <div className="patient-header">
          <div className="d-flex justify-content-between align-items-center">
            <div className="patient-name">{resident.name}</div>
            <div className="room-number">Room: {resident.room_number}</div>
          </div>
        </div>

        <div className="container-fluid">
          <div className="row">
            {/* Sidebar - Desktop */}
            <div className="col-12 col-lg-4 desktop-sidebar">
              <div className="current-metrics-container">
                {/* Alerts */}
                {isAbnormalHR() && (
                  <div className="alert alert-danger alert-dismissible" style={{ margin: '16px 8px 0px 8px' }}>
                    Abnormal heart rate detected: {resident.latest_vitals?.heart_rate} BPM
                  </div>
                )}
                {isAbnormalRR() && (
                  <div className="alert alert-danger alert-dismissible" style={{ margin: '16px 8px 0px 8px' }}>
                    Abnormal respiration rate detected: {resident.latest_vitals?.respiration} breaths/min
                  </div>
                )}

                {/* Vital Cards */}
                <div className="row vital-cards" style={{ padding: '16px 8px' }}>
                  <div className="col-6">
                    <div className="card vital-card" style={{ borderRadius: '1rem' }}>
                      <div className="card-body">
                        <p className="card-title" style={{ padding: '0px 2px', margin: '0px', fontSize: '19px', fontWeight: 600 }}>Heart Rate</p>
                        <p className="card-text" style={{ padding: '0px 2px', fontSize: '34px', fontWeight: 'bold', color: '#fc3737' }}>
                          {resident.latest_vitals?.heart_rate || '--'} <span style={{ fontSize: '20px' }}>BPM</span>
                        </p> 
                      </div>
                    </div>
                  </div>
                  <div className="col-6">
                    <div className="card vital-card" style={{ borderRadius: '1rem' }}>
                      <div className="card-body">
                        <p className="card-title" style={{ padding: '0px 2px', margin: '0px', fontSize: '19px', fontWeight: 600 }}>Respiration</p>
                        <p className="card-text" style={{ padding: '0px 5px', fontSize: '34px', fontWeight: 'bold', color: '#488bff' }}>
                          {resident.latest_vitals?.respiration || '--'} <span style={{ fontSize: '20px' }}>BPM</span>
                        </p> 
                      </div>
                    </div>
                  </div>
                </div>

                {/* Text statuses */}
                <div className="text-statuses" style={{ padding: '0px 20px', fontSize: '18px' }}>
                  <p>Bathroom Runs: {resident.today_bathroom_runs}</p>
                  <p>Activity: {getActivityStatus()}</p>
                </div>

                {/* Location status */}
                <div className="location-status" style={{ backgroundColor: '#f7f9eb', padding: '20px', fontSize: '18px', fontWeight: 600 }}>
                  <div className="d-flex justify-content-between align-items-center">
                    <div className="text">Not In Bed</div>
                    <div className="text">In Room</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Main Content */}
            <div className="col-12 col-lg-8 desktop-main-content">
              <div className="historical-metrics-container p-2">
                {/* Measurement selection buttons */}
                <div className="measurement-buttons mb-3">
                  <div className="d-none d-lg-grid metric-grid gap-2" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', width: '100%' }}>
                    {metrics.map((m) => (
                      <button
                        key={m.id}
                        onClick={() => setSelectedMetric(m.id)}
                        className={`btn ${selectedMetric === m.id ? 'btn-primary' : 'btn-outline-primary'}`}
                        style={{
                          borderColor: '#2d2d2d',
                          color: selectedMetric === m.id ? '#930c0c' : '#2d2d2d',
                          backgroundColor: selectedMetric === m.id ? '#ffefef' : '#fff',
                          flex: '1 0 0',
                          fontWeight: selectedMetric === m.id ? 600 : 400,
                        }}
                      >
                        {m.label}
                      </button>
                    ))}
                  </div>
                  
                  {/* Mobile dropdown */}
                  <div className="dropdown d-lg-none">
                    <button className="btn dropdown-toggle" type="button" data-bs-toggle="dropdown" style={{ backgroundColor: '#fff', borderColor: '#d8d8db' }}>
                      {metrics.find(m => m.id === selectedMetric)?.label}
                    </button>
                    <ul className="dropdown-menu">
                      {metrics.map((m) => (
                        <li key={m.id}>
                          <a
                            className="dropdown-item"
                            href="#"
                            onClick={() => setSelectedMetric(m.id)}
                          >
                            {m.label}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="card p-2">
                  {/* Chart header with range buttons */}
                  <div className="chart-header d-flex justify-content-between align-items-center m-2">
                    <div>
                      <div className="text" id="average-display">{getAverageDisplay()}</div>
                      <div className="text" id="baseline-display" style={{ fontSize: '14px', color: '#488bff' }}>{getBaselineDisplay()}</div>
                    </div>
                    
                    <div className="btn-group" role="group">
                      <input
                        type="radio"
                        className="btn-check"
                        name="btn-range"
                        id="btn-hour"
                        autoComplete="off"
                        checked={selectedRange === 'hour'}
                        onChange={() => setSelectedRange('hour')}
                      />
                      <label className="btn btn-outline-primary" htmlFor="btn-hour" style={{ borderColor: '#2d2d2d', color: '#2d2d2d' }}>Hour</label>

                      <input
                        type="radio"
                        className="btn-check"
                        name="btn-range"
                        id="btn-day"
                        autoComplete="off"
                        checked={selectedRange === 'day'}
                        onChange={() => setSelectedRange('day')}
                      />
                      <label className="btn btn-outline-primary" htmlFor="btn-day" style={{ borderColor: '#2d2d2d', color: '#2d2d2d' }}>Day</label>

                      <input
                        type="radio"
                        className="btn-check"
                        name="btn-range"
                        id="btn-week"
                        autoComplete="off"
                        checked={selectedRange === 'week'}
                        onChange={() => setSelectedRange('week')}
                      />
                      <label className="btn btn-outline-primary" htmlFor="btn-week" style={{ borderColor: '#2d2d2d', color: '#2d2d2d' }}>Week</label>
                    </div>
                  </div>

                  {/* Chart */}
                  <div className="chart-container mb-3" style={{ position: 'relative', width: '100%', height: '200px' }}>
                    <Line
                      data={chartData}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: { display: false },
                          tooltip: { enabled: false },
                        },
                        scales: {
                          y: {
                            title: { display: true, text: 'BPM' },
                          },
                        },
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <style jsx global>{`
        .patient-header {
          background-color: #f5f0f0;
          border-bottom: 1px solid #d8d8db;
          padding: 20px;
          font-size: 26px;
          font-weight: 600;
        }
        
        @media (min-width: 1130px) {
          .desktop-sidebar {
            border-right: 1px solid #d8d8db;
            width: 33%;
            height: 100vh;
          }
          .desktop-main-content {
            width: 67%;
          }
        }
        
        .vital-card {
          border: 1px solid #d8d8db;
        }
      `}</style>
    </div>
  );
}
