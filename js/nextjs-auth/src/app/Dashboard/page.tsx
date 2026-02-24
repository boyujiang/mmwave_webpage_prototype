'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getUserProfile, getRealtimeData, getDailySummary, getDashboardConfig } from '@/src/lib/api';
import Sidebar from '@/src/components/Sidebar';

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [realtimeData, setRealtimeData] = useState<any>({});
  const [dailyData, setDailyData] = useState<any>({});
  const [config, setConfig] = useState<any>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [userData, configData, dailyDataResult] = await Promise.all([
          getUserProfile(),
          getDashboardConfig(),
          getDailySummary()
        ]);
        setUser(userData);
        setConfig(configData);
        setDailyData(dailyDataResult);
        setLoading(false);
      } catch (error) {
        router.push('/login');
      }
    };

    fetchInitialData();
  }, [router]);

  // Poll for real-time data
  useEffect(() => {
    if (!user) return;

    const fetchRealtime = async () => {
      try {
        const data = await getRealtimeData();
        setRealtimeData(data);
      } catch (error) {
        console.error('Failed to fetch realtime data:', error);
      }
    };

    // Initial fetch
    fetchRealtime();

    // Poll every 5 seconds (or use config.refresh_interval)
    const interval = setInterval(fetchRealtime, (config.refresh_interval || 5) * 1000);

    return () => clearInterval(interval);
  }, [user, config.refresh_interval]);

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
          
          {/* Real-time Metrics */}
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-700">Real-time Metrics</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-lg shadow border-l-4 border-blue-500">
                <h3 className="text-gray-500 text-sm font-medium">Active Users</h3>
                <p className="text-2xl font-bold text-blue-600 mt-1">
                  {realtimeData.active_users || 0}
                </p>
                <p className="text-xs text-gray-400 mt-1">Live</p>
              </div>
              
              <div className="bg-white p-4 rounded-lg shadow border-l-4 border-green-500">
                <h3 className="text-gray-500 text-sm font-medium">CPU Usage</h3>
                <p className="text-2xl font-bold text-green-600 mt-1">
                  {realtimeData.cpu_usage?.toFixed(1) || 0}%
                </p>
                <p className="text-xs text-gray-400 mt-1">Live</p>
              </div>
              
              <div className="bg-white p-4 rounded-lg shadow border-l-4 border-yellow-500">
                <h3 className="text-gray-500 text-sm font-medium">Memory</h3>
                <p className="text-2xl font-bold text-yellow-600 mt-1">
                  {realtimeData.memory_usage?.toFixed(1) || 0}%
                </p>
                <p className="text-xs text-gray-400 mt-1">Live</p>
              </div>
              
              <div className="bg-white p-4 rounded-lg shadow border-l-4 border-purple-500">
                <h3 className="text-gray-500 text-sm font-medium">Requests/sec</h3>
                <p className="text-2xl font-bold text-purple-600 mt-1">
                  {realtimeData.requests_per_second || 0}
                </p>
                <p className="text-xs text-gray-400 mt-1">Live</p>
              </div>
            </div>
          </div>

          {/* Daily Summary */}
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-700">Today's Summary</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-gray-500 text-sm font-medium">Total Transactions</h3>
                <p className="text-3xl font-bold text-blue-600 mt-2">
                  {dailyData.total_transactions?.toLocaleString() || 0}
                </p>
                <p className="text-xs text-gray-400 mt-1">Updated daily</p>
              </div>
              
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-gray-500 text-sm font-medium">Revenue</h3>
                <p className="text-3xl font-bold text-green-600 mt-2">
                  ${dailyData.total_revenue?.toLocaleString() || 0}
                </p>
                <p className="text-xs text-gray-400 mt-1">Updated daily</p>
              </div>
              
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-gray-500 text-sm font-medium">Active Projects</h3>
                <p className="text-3xl font-bold text-purple-600 mt-2">23</p>
                <p className="text-xs text-gray-400 mt-1">Static</p>
              </div>
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