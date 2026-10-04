import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { useAuthStore } from '../store/authStore'
import { Activity, ClipboardList, Stethoscope, UserCheck } from 'lucide-react'
import clsx from 'clsx'

export default function DoctorDashboard() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const { data: overview, isLoading, error } = useQuery({
    queryKey: ['doctor-overview'],
    queryFn: () => api.get('/clinical/overview').then(response => response.data),
  })

  const patients = overview?.patients ?? []
  const stats = overview?.stats ?? {}
  const cards = [
    { label: 'My Active Admissions', value: stats.active_admissions ?? 0, icon: UserCheck, color: 'bg-blue-600' },
    { label: "Today's Encounters", value: stats.today_encounters ?? 0, icon: ClipboardList, color: 'bg-green-600' },
    { label: 'Patients With Vitals', value: stats.patients_with_recent_vitals ?? 0, icon: Activity, color: 'bg-purple-600' },
    { label: 'Clinical Reviews', value: patients.length, icon: Stethoscope, color: 'bg-amber-600' },
  ]

  return (
    <div className="space-y-6">
      <div><h1 className="text-xl font-bold text-gray-900">Doctor Dashboard</h1><p className="text-sm text-gray-500">Welcome, {user?.full_name ?? 'Doctor'} — live clinical workspace</p></div>
      {error && <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">Unable to load clinical data. Refresh to retry.</div>}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">{cards.map(card => <div key={card.label} className="stat-card flex items-center gap-4"><div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0', card.color)}><card.icon size={18} className="text-white" /></div><div><p className="text-xs text-gray-500 font-medium">{card.label}</p><p className="text-xl font-bold text-gray-900">{isLoading ? '—' : card.value}</p></div></div>)}</div>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <section className="xl:col-span-2 card"><div className="px-5 py-4 border-b border-gray-100"><h2 className="text-sm font-semibold text-gray-800">My Active Patients</h2></div>{isLoading ? <div className="p-6 text-center text-gray-500">Loading clinical workspace…</div> : patients.length === 0 ? <div className="p-6 text-center text-gray-400">No active admissions assigned.</div> : <table className="w-full"><thead className="bg-gray-50"><tr><th className="table-th">Patient</th><th className="table-th">Location</th><th className="table-th">Reason</th><th className="table-th">Latest Vitals</th><th className="table-th"></th></tr></thead><tbody className="divide-y divide-gray-100">{patients.map((patient: any) => <tr key={patient.admission_id} className="hover:bg-blue-50"><td className="table-td"><p className="font-medium">{patient.patient_name}</p><p className="text-xs text-gray-400 font-mono">{patient.patient_code}</p></td><td className="table-td">{patient.ward_name} · {patient.bed_number}</td><td className="table-td text-xs">{patient.reason}</td><td className="table-td text-xs">{patient.latest_vitals ? <>{patient.latest_vitals.bp ?? 'BP —'} · SpO₂ {patient.latest_vitals.spo2 ?? '—'}%</> : 'Not recorded'}</td><td className="table-td"><button onClick={() => navigate('/patients/' + patient.patient_id)} className="text-xs text-blue-600 hover:underline">Open patient →</button></td></tr>)}</tbody></table>}</section>
        <section className="card"><div className="px-5 py-4 border-b border-gray-100"><h2 className="text-sm font-semibold text-gray-800">Clinical Activity</h2><p className="text-xs text-gray-500 mt-0.5">Admissions assigned to you</p></div><div className="p-4 space-y-3">{patients.slice(0, 6).map((patient: any) => <div key={patient.admission_id} className="border-l-2 border-blue-500 pl-3"><p className="text-sm font-medium text-gray-800">{patient.patient_name}</p><p className="text-xs text-gray-500">{patient.admission_type} · admitted {new Date(patient.admitted_at).toLocaleDateString('en-IN')}</p></div>)}{!isLoading && patients.length === 0 && <p className="text-sm text-gray-500">No active clinical activity.</p>}</div></section>
      </div>
    </div>
  )
}
