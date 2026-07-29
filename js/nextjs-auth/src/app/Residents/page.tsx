'use client';

import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getUserProfile, getResidents } from '@/src/lib/api';
import { useVitalsSocket } from '@/src/hooks/useVitalsSocket';
import {
  applyVitalsUpdate,
  type VitalsUpdate,
} from '@/src/lib/realtime';
import type { UserProfile } from '@/src/lib/types';
import Sidebar from '@/src/components/Sidebar';

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
  latest_events: Array<{
    id: number;
    event_type: string;
    event_type_display: string;
    timestamp: string;
  }>;
}

const getActivityLabel = (status: string) => {
  const labels: Record<string, string> = {
    standing: 'Standing',
    sitting: 'Sitting',
    walking: 'Walking',
    lying_down: 'Lying Down',
  };
  return labels[status] || status;
};

function ResidentsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [residents, setResidents] = useState<Resident[]>([]);
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
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
      } catch {
        router.push('/login');
      }
    };

    fetchInitialData();
  }, [router]);

  const handleVitals = useCallback((update: VitalsUpdate) => {
    setResidents((current) =>
      current.map((resident) =>
        applyVitalsUpdate(resident, update)
      )
    );
  }, []);

  useVitalsSocket(handleVitals, Boolean(user));

  const filteredResidents = useMemo(() => {
    const query = searchQuery.toLowerCase();
    if (!query) {
      return residents;
    }

    return residents.filter(
      (resident) =>
        resident.name.toLowerCase().includes(query) ||
        resident.room_number.toLowerCase().includes(query)
    );
  }, [searchQuery, residents]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  const getBorderClass = (status: string) => {
    if (status === 'stable') return 'border-green-500';
    return 'border-red-500';
  };

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
      
      <main className="flex-1 p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold text-gray-900">Residents</h1>
            <div className="relative">
              <input
                type="text"
                placeholder="Search by name or room..."
                value={searchQuery}
                onChange={handleSearch}
                className="w-64 px-4 py-2 pl-10 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <span className="absolute left-3 top-2.5 text-gray-400">🔍</span>
            </div>
          </div>

          {/* Resident Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredResidents.map((resident) => {
              const effectiveStatus = (resident.status !== 'stable' && resident.alert_dismissed_at) ? 'stable' : resident.status;
              return (
                <div
                  key={resident.id}
                  className={`bg-white rounded-xl shadow-sm border-2 overflow-hidden hover:shadow-md transition-shadow ${getBorderClass(effectiveStatus)}`}
                >
                  {/* Header with status dot */}
                  <div className="bg-gradient-to-r from-blue-500 to-blue-600 px-4 py-3 relative">
                    <div className="flex justify-between items-center">
                      <span className="text-white font-semibold">Room {resident.room_number}</span>
                      <div className="flex items-center gap-2">
                        {/* Active/Inactive badge */}
                        <span className={`text-xs px-2 py-0.5 rounded-full ${resident.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-600'}`}>
                          {resident.is_active ? 'Active' : 'Inactive'}
                        </span>
                        {/* Alert status dot */}
                        <span 
                          className={`w-3 h-3 rounded-full ${effectiveStatus === 'stable' ? 'bg-green-500' : 'bg-red-500 animate-pulse'}`}
                          title={effectiveStatus === 'stable' ? 'Stable' : 'Alert'}
                        />
                      </div>
                    </div>
                  </div>

                {/* Content */}
                <div className="p-4">
                  <h3 className="font-semibold text-lg text-gray-900 mb-4">{resident.name}</h3>

                  {/* Vitals Grid */}
                  <div className="grid grid-cols-3 gap-2 mb-4">
                    <div className="text-center p-2 bg-red-50 rounded-lg">
                      <p className="text-xs text-red-600 font-medium">Heart</p>
                      <p className="text-lg font-bold text-red-700">
                        {resident.latest_vitals?.heart_rate || '--'}
                      </p>
                      <p className="text-xs text-red-400">bpm</p>
                    </div>
                    <div className="text-center p-2 bg-blue-50 rounded-lg">
                      <p className="text-xs text-blue-600 font-medium">Resp</p>
                      <p className="text-lg font-bold text-blue-700">
                        {resident.latest_vitals?.respiration || '--'}
                      </p>
                      <p className="text-xs text-blue-400">/min</p>
                    </div>
                    <div className="text-center p-2 bg-purple-50 rounded-lg">
                      <p className="text-xs text-purple-600 font-medium">Activity</p>
                      <p className="text-lg font-bold text-purple-700">
                        {getActivityLabel(resident.latest_vitals?.activity_status || '')}
                      </p>
                    </div>
                  </div>

                  {/* Status Row */}
                  <div className="flex gap-2 mb-4">
                    <div className={`flex-1 text-center py-1 rounded ${resident.latest_vitals?.in_bed ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      <span className="text-xs font-medium">In Bed: {resident.latest_vitals?.in_bed ? 'Yes' : 'No'}</span>
                    </div>
                    <div className={`flex-1 text-center py-1 rounded ${resident.latest_vitals?.in_room ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      <span className="text-xs font-medium">In Room: {resident.latest_vitals?.in_room ? 'Yes' : 'No'}</span>
                    </div>
                  </div>

                  {/* Alert Banner */}
                  {resident.status !== 'stable' && !resident.alert_dismissed_at &&(
                    <div className="mb-4 p-2 bg-red-100 border border-red-400 rounded-lg text-center">
                      <span className="text-red-700 font-semibold text-sm">
                        {resident.status === 'fall_detected' ? '⚠️ Fall Detected!' : '⚠️ Room Departure!'}
                      </span>
                    </div>
                  )}

                  {/* Bathroom Runs */}
                  <div className="flex items-center justify-between py-2 border-t border-gray-100">
                    <span className="text-sm text-gray-600">Bathroom Runs</span>
                    <span className="text-lg font-bold text-orange-600">
                      {resident.today_bathroom_runs}
                    </span>
                  </div>

                  {/* Expand Button */}
                  <button
                    onClick={() => router.push(`/Residents/${resident.id}`)}
                    className="w-full mt-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
                  >
                    View Details
                  </button>
                </div>
              </div>
            )})}
          </div>

          {/* Empty State */}
          {filteredResidents.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500 text-lg">No residents found</p>
              <p className="text-gray-400">Try adjusting your search</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default function ResidentsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-xl">Loading...</div>
        </div>
      }
    >
      <ResidentsContent />
    </Suspense>
  );
}
