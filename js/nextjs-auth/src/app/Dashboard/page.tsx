'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getUserProfile, getResidents } from '@/src/lib/api';
import Sidebar from '@/src/components/Sidebar';

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

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [residents, setResidents] = useState<Resident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [userData, residentsData] = await Promise.all([
          getUserProfile(),
          getResidents()
        ]);
        setUser(userData);
        setResidents(residentsData);
        setLoading(false);
      } catch (error) {
        router.push('/login');
      }
    };

    fetchInitialData();
  }, [router]);

  useEffect(() => {
    if (!user) return;

    const fetchResidents = async () => {
      try {
        const data = await getResidents();
        setResidents(data);
      } catch (error) {
        console.error('Failed to fetch residents:', error);
      }
    };

    fetchResidents();
    const interval = setInterval(fetchResidents, 30000);
    return () => clearInterval(interval);
  }, [user]);

  // Calculate stats from real data
  const totalResidents = residents.length;
  const occupiedRooms = residents.filter(r => r.latest_vitals?.heart_rate).length;
  
  // Get fall events from today
  const today = new Date().toISOString().split('T')[0];
  const fallEvents = residents.flatMap(r => 
    r.latest_events?.filter(e => 
      e.event_type === 'fall_detected' && e.timestamp.startsWith(today)
    ) || []
  );
  const residentsRequireAttention = fallEvents.length;
  
  const roomsWithActivity = residents.filter(r => (r.latest_vitals?.activity_level || 0) > 0).length;

  const overviewStats = [
    { label: 'Total Residents', value: totalResidents },
    { label: 'Occupied Rooms', value: occupiedRooms },
    { label: 'Residents Require Attention', value: residentsRequireAttention, alert: residentsRequireAttention > 0 },
    { label: 'Rooms with Activity', value: roomsWithActivity },
  ];

  // Get latest events for alerts
  const recentAlerts = residents.flatMap(r => 
    (r.latest_events || []).slice(0, 3).map(e => ({
      ...e,
      residentName: r.name,
      roomNumber: r.room_number
    }))
  ).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-100">
      <Sidebar user={user} />
      
      <main className="flex-1 p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-500">Welcome back, {user?.first_name || user?.username}</p>
          </div>

          {/* Alert Section */}
          <div className="mb-6">
            <div className={`rounded-lg border p-4 ${recentAlerts.length > 0 ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <span className="text-2xl mr-3">{recentAlerts.length > 0 ? '⚠️' : '✅'}</span>
                  <div>
                    <p className="font-semibold text-gray-900">
                      {recentAlerts.length > 0 ? `${recentAlerts.length} Alert(s) Detected` : 'No Alerts'}
                    </p>
                    <p className="text-sm text-gray-600">
                      {recentAlerts.length > 0 ? 'Recent activity requires attention' : 'All residents are safe'}
                    </p>
                  </div>
                </div>
                {recentAlerts.length > 0 && (
                  <div className="text-right">
                    <p className="text-sm font-medium text-red-700">{recentAlerts[0]?.residentName}</p>
                    <p className="text-xs text-red-600">Room {recentAlerts[0]?.roomNumber}</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Main Content: Overview (Left) + Residents Overview (Right) */}
          <div className="flex gap-6">
            {/* Overview - Left Side */}
            <div className="w-1/2">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="font-semibold text-gray-900 mb-4">Overview</h2>
                <div className="grid grid-cols-2 gap-4">
                  {overviewStats.map((stat, index) => (
                    <div 
                      key={index} 
                      className={`rounded-lg border p-4 ${stat.alert ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-200'}`}
                    >
                      <p className="text-sm text-gray-600 mb-1">{stat.label}</p>
                      <p className={`text-3xl font-bold ${stat.alert ? 'text-red-600' : 'text-gray-900'}`}>
                        {stat.value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Residents Overview - Right Side */}
            <div className="w-1/2">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="font-semibold text-gray-900 mb-4">Residents Overview</h2>
                <div className="space-y-3">
                  {residents.map((resident) => (
                    <div 
                      key={resident.id} 
                      className="bg-gray-50 rounded-lg border border-gray-200 p-4"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-semibold mr-3">
                            {resident.name.charAt(0)}
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{resident.name}</p>
                            <p className="text-sm text-gray-500">Room {resident.room_number}</p>
                          </div>
                        </div>
                        <span className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded-full">
                          Active
                        </span>
                      </div>
                    </div>
                  ))}
                  
                  {residents.length === 0 && (
                    <p className="text-gray-500 text-center py-4">No residents data available</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
