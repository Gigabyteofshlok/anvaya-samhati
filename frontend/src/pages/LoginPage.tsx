import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import api from '../lib/api'
import { Building2, Eye, EyeOff, AlertCircle } from 'lucide-react'

const DEMO_ACCOUNTS = [
  { username: 'superadmin', label: 'System Admin', role: 'Super Administrator' },
  { username: 'drsharma', label: 'Dr. Rajesh Sharma', role: 'Doctor' },
  { username: 'nursepriya', label: 'Priya Nair', role: 'Nurse' },
  { username: 'reception', label: 'Ramesh Patil', role: 'Reception' },
]

export default function LoginPage() {
  const [username, setUsername] = useState('superadmin')
  const [password, setPassword] = useState('DemoPassword123!')
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const form = new URLSearchParams()
      form.append('username', username)
      form.append('password', password)
      const { data } = await api.post('/auth/token', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      const me = await api.get('/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` },
      })
      setAuth(data.access_token, me.data)
      navigate('/command-center')
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Login failed. Check credentials.')
    } finally {
      setLoading(false)
    }
  }

  const quickFill = (u: string) => {
    setUsername(u)
    setPassword('DemoPassword123!')
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-5"
        style={{backgroundImage:'radial-gradient(circle at 25px 25px, white 2px, transparent 0)',backgroundSize:'50px 50px'}} />

      <div className="relative z-10 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4 shadow-lg">
            <Building2 size={32} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-1">ANVAYA SAṂHATI</h1>
          <p className="text-slate-400 text-sm">Hospital Operating System</p>
          <p className="text-slate-500 text-xs mt-1">Connecting every part of a hospital into one intelligent system</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Sign in to your account</h2>

          {error && (
            <div className="mb-4 flex items-center gap-2 bg-red-50 border border-red-200 rounded px-3 py-2 text-red-700 text-sm">
              <AlertCircle size={15} className="flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
              <input
                className="input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="username"
                autoFocus
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <div className="relative">
                <input
                  className="input pr-10"
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••"
                  required
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  onClick={() => setShowPass(!showPass)}
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <button className="btn-primary w-full py-2.5 mt-2" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>

          {/* Demo accounts */}
          <div className="mt-6 pt-5 border-t border-gray-100">
            <p className="text-xs text-gray-500 font-medium mb-3">DEMO ACCOUNTS — all use DemoPassword123!</p>
            <div className="grid grid-cols-2 gap-2">
              {DEMO_ACCOUNTS.map((a) => (
                <button
                  key={a.username}
                  onClick={() => quickFill(a.username)}
                  className="text-left px-2.5 py-2 border border-gray-200 rounded hover:border-blue-400 hover:bg-blue-50 transition-colors"
                >
                  <p className="text-xs font-medium text-gray-800">{a.label}</p>
                  <p className="text-xs text-gray-500">{a.role}</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-slate-600 text-xs mt-4">
          DEMO ENVIRONMENT • SYNTHETIC DATA • Not for clinical use
        </p>
      </div>
    </div>
  )
}
