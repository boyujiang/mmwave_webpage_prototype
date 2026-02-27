'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getUserProfile, getDashboardConfig, getResidents } from '@/src/lib/api';
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
  const [config, setConfig] = useState<any>({});
  const [residents, setResidents] = useState<Resident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [userData, configData, residentsData] = await Promise.all([
          getUserProfile(),
          getDashboardConfig(),
          getResidents()
        ]);
        setUser(userData);
        setConfig(configData);
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

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar user={user} />
      
      <main className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">
            Dashboard
          </h1>
          
          {/* Residents Section */}
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-700">Residents</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {residents.map((resident) => (
                <div key={resident.id} className="bg-white p-4 rounded-lg shadow">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-semibold text-lg text-gray-900">{resident.name}</h3>
                      <p className="text-sm text-gray-500">Room {resident.room_number}</p>
                    </div>
                    <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
                      Active
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-2 mb-3">
                    <div className="text-center">
                      <p className="text-xs text-gray-500">Heart Rate</p>
                      <p className="font-semibold text-red-600">
                        {resident.latest_vitals?.heart_rate || '--'} bpm
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-gray-500">Respiration</p>
                      <p className="font-semibold text-blue-600">
                        {resident.latest_vitals?.respiration || '--'} /min
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-gray-500">Activity</p>
                      <p className="font-semibold text-purple-600">
                        {resident.latest_vitals?.activity_level?.toFixed(0) || '--'}%
                      </p>
                    </div>
                  </div>
                  
                  <div className="border-t pt-3">
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Bathroom runs today:</span>{' '}
                      <span className="text-orange-600 font-semibold">{resident.today_bathroom_runs}</span>
                    </p>
                  </div>
                </div>
              ))}
              
              {residents.length === 0 && (
                <div className="col-span-full text-center py-8 text-gray-500">
                  No residents found. Run create_sample_residents task to add sample data.
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Welcome, {user?.first_name || user?.username}!</h2>
            <p className="text-gray-600">
              Refresh interval: {config.refresh_interval || 5} seconds • Theme: {config.theme || 'light'}
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
