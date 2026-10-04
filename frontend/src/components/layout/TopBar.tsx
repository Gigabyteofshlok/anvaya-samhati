import { Bell, Search, LogOut, ChevronDown } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useNavigate } from 'react-router-dom'
import api from '../../lib/api'
import { useState } from 'react'

export default function TopBar() {
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()
  const [searching, setSearching] = useState('')

  const handleLogout = async () => {
    try { await api.post('/auth/logout') } catch (_) {}
    clearAuth()
    navigate('/login')
  }

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
      {/* Search */}
      <div className="relative w-80">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          className="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Search patients, beds, encounters…"
          value={searching}
          onChange={(e) => setSearching(e.target.value)}
        />
      </div>

      {/* Right */}
      <div className="flex items-center gap-4">
        <button className="relative p-1.5 text-gray-500 hover:text-gray-700">
          <Bell size={18} />
          <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full" />
        </button>
        <div className="flex items-center gap-2 text-sm">
          <div className="w-8 h-8 bg-blue-700 text-white rounded-full flex items-center justify-center font-semibold text-xs">
            {user?.full_name?.charAt(0) ?? 'A'}
          </div>
          <div className="hidden sm:block">
            <p className="font-medium text-gray-800 leading-tight">{user?.full_name ?? 'Admin'}</p>
            <p className="text-xs text-gray-500">{user?.roles?.[0] ?? 'administrator'}</p>
          </div>
          <ChevronDown size={14} className="text-gray-400" />
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-red-600 transition-colors"
        >
          <LogOut size={16} />
        </button>
      </div>
    </header>
  )
}
