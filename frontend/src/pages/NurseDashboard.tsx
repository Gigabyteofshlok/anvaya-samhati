import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { useAuthStore } from '../store/authStore'
import { Activity, AlertTriangle, BedDouble, ClipboardList } from 'lucide-react'
import clsx from 'clsx'

function statusClass(status: string) {
  if (status === 'OCCUPIED') return 'badge-danger'
  if (status === 'AVAILABLE') return 'badge-success'
  if (status === 'CLEANING') return 'badge-warning'
  return 'badge-gray'
}

export default function NurseDashboard() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const { data: station, isLoading, error } = useQuery({
    queryKey: ['nurse-station'],
    queryFn: () => api.get('/clinical/nursing').then(response => response.data),
  })

  const beds = station?.beds ?? []
  const tasks = station?.shift_tasks ?? []
  const cards = [
    { label: 'Station Beds', value: station?.total_station_beds ?? 0, icon: BedDouble, color: 'bg-blue-600' },
    { label: 'Occupied Beds', value: station?.occupied_count ?? 0, icon: Activity, color: 'bg-red-500' },
    { label: 'Vitals Due', value: station?.pending_vitals_count ?? 0, icon: ClipboardList, color: 'bg-amber-600' },
    { label: 'Vital Alerts', value: station?.critical_alert_count ?? 0, icon: AlertTriangle, color: 'bg-purple-600' },
  ]

  return (
    <div className="space-y-6">
      <div><h1 className="text-xl font-bold text-gray-900">Nursing Station</h1><p className="text-sm text-gray-500">Welcome, {user?.full_name ?? 'Nurse'} — branch-based live patient activity</p></div>
      {error && <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">Unable to load nursing data. Refresh to retry.</div>}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">{cards.map(card => <div key={card.label} className="stat-card flex items-center gap-4"><div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0', card.color)}><card.icon size={18} className="text-white" /></div><div><p className="text-xs text-gray-500 font-medium">{card.label}</p><p className="text-xl font-bold text-gray-900">{isLoading ? '—' : card.value}</p></div></div>)}</div>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <section className="xl:col-span-2 card"><div className="px-5 py-4 border-b border-gray-100"><h2 className="text-sm font-semibold text-gray-800">Beds and Patients</h2></div>{isLoading ? <div className="p-6 text-center text-gray-500">Loading station data…</div> : <table className="w-full"><thead className="bg-gray-50"><tr><th className="table-th">Bed</th><th className="table-th">Patient</th><th className="table-th">Status</th><th className="table-th">Latest Vitals</th><th className="table-th"></th></tr></thead><tbody className="divide-y divide-gray-100">{beds.map((bed: any) => <tr key={bed.bed_id} className="hover:bg-blue-50"><td className="table-td"><p className="font-medium">{bed.bed_number}</p><p className="text-xs text-gray-400">{bed.ward_name}</p></td><td className="table-td">{bed.patient_name ?? <span className="text-gray-400">Empty</span>}</td><td className="table-td"><span className={clsx('badge', statusClass(bed.status))}>{bed.status}</span></td><td className="table-td text-xs">{bed.latest_vitals ? new Date(bed.latest_vitals.recorded_at).toLocaleString('en-IN') : 'Not recorded'}</td><td className="table-td">{bed.patient_id && <button onClick={() => navigate('/patients/' + bed.patient_id)} className="text-xs text-blue-600 hover:underline">Open patient →</button>}</td></tr>)}</tbody></table>}</section>
        <section className="card"><div className="px-5 py-4 border-b border-gray-100"><h2 className="text-sm font-semibold text-gray-800">Shift Tasks</h2><p className="text-xs text-gray-500 mt-0.5">Derived from live bed and vital state</p></div><div className="p-4 space-y-3">{tasks.map((task: any, index: number) => <div key={index} className="border-l-2 border-amber-500 pl-3"><p className="text-xs font-medium text-amber-700">{task.type.replaceAll('_', ' ')}</p><p className="text-sm text-gray-700">{task.description}</p></div>)}{!isLoading && tasks.length === 0 && <p className="text-sm text-gray-500">No operational tasks are currently due.</p>}</div></section>
      </div>
    </div>
  )
}
