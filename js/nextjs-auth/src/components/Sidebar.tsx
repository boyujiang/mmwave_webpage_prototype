'use client';

import { useRouter } from 'next/navigation';

interface SidebarProps {
  user: any;
}

export default function Sidebar({ user }: SidebarProps) {
  const router = useRouter();

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    router.push('/login');
  };

  const menuItems = [
    { name: 'Dashboard', icon: '📊', active: true },
    { name: 'Analytics', icon: '📈', active: false },
    { name: 'Users', icon: '👥', active: false },
    { name: 'Settings', icon: '⚙️', active: false },
  ];

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen p-4">
      <div className="mb-8">
        <h2 className="text-2xl font-bold">MyApp</h2>
      </div>

      <div className="mb-8 p-4 bg-gray-800 rounded-lg">
        <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center text-xl font-bold mb-2">
          {user?.username?.charAt(0).toUpperCase()}
        </div>
        <p className="font-medium">{user?.username}</p>
        <p className="text-sm text-gray-400">{user?.email}</p>
      </div>

      <nav className="space-y-2">
        {menuItems.map((item) => (
          <button
            key={item.name}
            className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
              item.active
                ? 'bg-blue-600 text-white'
                : 'hover:bg-gray-800 text-gray-300'
            }`}
          >
            <span className="mr-3">{item.icon}</span>
            {item.name}
          </button>
        ))}
      </nav>

      <button
        onClick={handleLogout}
        className="w-full mt-8 px-4 py-3 bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
      >
        🚪 Logout
      </button>
    </aside>
  );
}