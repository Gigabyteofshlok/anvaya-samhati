import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { BedDouble, ClipboardList, Search, UserPlus, Users } from 'lucide-react'

export default function ReceptionDashboard() {
  const [search, setSearch] = useState('')
  const navigate = useNavigate()
  const { data: overview, isLoading: overviewLoading, error: overviewError } = useQuery({
    queryKey: ['reception-overview'],
    queryFn: () => api.get('/clinical/reception').then(response => response.data),
  })
  const { data: patientsData, isLoading: searchLoading } = useQuery({
    queryKey: ['reception-patients', search],
    queryFn: () => api.get('/patients', { params: { q: search, limit: 20 } }).then(response => response.data),
    enabled: search.trim().length >= 2,
  })
  const patients = Array.isArray(patientsData) ? patientsData : []
  const cards = [
    { label: 'Registrations Today', value: overview?.today_registrations ?? 0, icon: UserPlus, color: 'bg-blue-600' },
    { label: 'Admissions Today', value: overview?.today_admissions_count ?? 0, icon: ClipboardList, color: 'bg-red-600' },
    { label: 'Active Admissions', value: overview?.active_admissions_count ?? 0, icon: Users, color: 'bg-purple-600' },
    { label: 'Available Beds', value: overview?.available_beds_count ?? 0, icon: BedDouble, color: 'bg-green-600' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between"><div><h1 className="text-xl font-bold text-gray-900">Reception</h1><p className="text-sm text-gray-500">Patient registration, search, and live admission queue</p></div><button onClick={() => navigate('/patients')} className="btn-primary flex items-center gap-2"><UserPlus size={15} /> Register New Patient</button></div>
      {overviewError && <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">Unable to load reception operations. Refresh to retry.</div>}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">{cards.map(card => <div key={card.label} className="stat-card flex items-center gap-4"><div className={'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ' + card.color}><card.icon size={18} className="text-white" /></div><div><p className="text-xs text-gray-500 font-medium">{card.label}</p><p className="text-xl font-bold text-gray-900">{overviewLoading ? '—' : card.value}</p></div></div>)}</div>
      <section className="card p-5"><h2 className="text-sm font-semibold text-gray-700 mb-3">Patient Search</h2><div className="relative max-w-lg"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" /><input className="input pl-9" placeholder="Search by name, ANV ID, or mobile number…" value={search} onChange={(event) => setSearch(event.target.value)} autoFocus /></div>{search.trim().length >= 2 && <div className="mt-3">{searchLoading ? <p className="text-sm text-gray-500">Searching…</p> : patients.length === 0 ? <p className="text-sm text-gray-500">No patients found.</p> : <div className="border border-gray-200 rounded divide-y divide-gray-100">{patients.map((patient: any) => <button key={patient.id} onClick={() => navigate('/patients/' + patient.patient_id)} className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-blue-50"><span><span className="block font-medium text-gray-900">{patient.full_name}</span><span className="text-xs text-gray-500 font-mono">{patient.patient_id} · {patient.mobile}</span></span><span className="text-xs text-blue-600">Open patient →</span></button>)}</div>}</div>}</section>
      <section className="card"><div className="px-5 py-4 border-b border-gray-100"><h2 className="text-sm font-semibold text-gray-800 flex items-center gap-2"><ClipboardList size={15} /> Today's Admissions</h2></div>{overviewLoading ? <div className="p-6 text-center text-gray-500">Loading admission queue…</div> : !(overview?.today_admissions ?? []).length ? <div className="p-6 text-center text-gray-500">No admissions have been created today.</div> : <table className="w-full"><thead className="bg-gray-50"><tr><th className="table-th">Time</th><th className="table-th">Patient</th><th className="table-th">Location</th><th className="table-th">Reason</th><th className="table-th">Status</th></tr></thead><tbody className="divide-y divide-gray-100">{overview.today_admissions.map((admission: any) => <tr key={admission.id} className="hover:bg-blue-50"><td className="table-td text-xs text-gray-500">{new Date(admission.admitted_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</td><td className="table-td"><p className="font-medium">{admission.patient_name}</p><p className="font-mono text-xs text-blue-700">{admission.patient_code}</p></td><td className="table-td text-sm">{admission.ward_name} · {admission.bed_number}</td><td className="table-td text-sm text-gray-600">{admission.reason}</td><td className="table-td"><span className="badge badge-danger">{admission.status}</span></td></tr>)}</tbody></table>}</section>
    </div>
  )
}
