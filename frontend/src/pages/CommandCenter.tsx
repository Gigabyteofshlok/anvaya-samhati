import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import {
  ActivitySquare, AlertTriangle, BedDouble, ClipboardList, Clock,
  RefreshCcw, Users,
} from 'lucide-react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import clsx from 'clsx'

const STATUS_COLORS: Record<string, string> = {
  Available: '#00875A', Occupied: '#DE350B', Reserved: '#0052CC',
  Cleaning: '#FF991F', Maintenance: '#6554C0', Isolation: '#7A4EAB',
}

function StatCard({ label, value, icon: Icon, color, note, loading }: {
  label: string
  value: string | number
  icon: typeof BedDouble
  color: string
  note: string
  loading?: boolean
}) {
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
          {loading ? <div className="h-8 w-16 bg-gray-200 animate-pulse rounded mt-1" /> :
            <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>}
          <p className="mt-1 text-xs text-gray-500">{note}</p>
        </div>
        <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center', color)}>
          <Icon size={20} className="text-white" />
        </div>
      </div>
    </div>
  )
}

function eventTone(eventType: string) {
  if (eventType.includes('DISCHARG')) return 'badge-success'
  if (eventType.includes('VITAL') || eventType.includes('ADMIT')) return 'badge-info'
  if (eventType.includes('BED')) return 'badge-warning'
  return 'badge-gray'
}

export default function CommandCenter() {
  const [branchId, setBranchId] = useState('')
  const { data: summary, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['dashboard-summary', branchId],
    queryFn: () => api.get('/dashboard/summary', { params: branchId ? { branch_id: branchId } : {} }).then(r => r.data),
    refetchInterval: 60_000,
  })

  const bedStatus = summary ? [
    ['Available', summary.available_beds], ['Occupied', summary.occupied_beds],
    ['Reserved', summary.reserved_beds], ['Cleaning', summary.cleaning_beds],
    ['Maintenance', summary.maintenance_beds], ['Isolation', summary.isolation_beds],
  ].filter(([, value]) => value > 0).map(([name, value]) => ({
    name, value, color: STATUS_COLORS[name as string],
  })) : []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Hospital Command Center</h1>
          <p className="text-sm text-gray-500 mt-0.5">Live operational overview from the ANVAYA database</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={branchId} onChange={(event) => setBranchId(event.target.value)} className="input text-sm py-1.5">
            <option value="">All branches</option>
            {(summary?.branches ?? []).map((branch: any) => <option key={branch.branch_id} value={branch.branch_id}>{branch.branch_name}</option>)}
          </select>
          <button onClick={() => refetch()} disabled={isFetching} className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded hover:bg-gray-50">
            <RefreshCcw size={14} className={clsx(isFetching && 'animate-spin')} /> Refresh
          </button>
          <span className="flex items-center gap-1.5 text-xs text-gray-400"><Clock size={12} /> Updates every minute</span>
        </div>
      </div>

      {error && <div className="flex items-center gap-2 rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        <AlertTriangle size={16} /> Operational data could not be loaded. Refresh to retry.
      </div>}

      <div className="grid grid-cols-2 xl:grid-cols-3 gap-4">
        <StatCard label="Total Beds" icon={BedDouble} value={summary?.total_beds ?? '—'} color="bg-blue-700" note={`${summary?.occupancy_rate_pct ?? 0}% occupied`} loading={isLoading} />
        <StatCard label="Occupied Beds" icon={ActivitySquare} value={summary?.occupied_beds ?? '—'} color="bg-red-600" note={`${summary?.active_admissions ?? 0} active admissions`} loading={isLoading} />
        <StatCard label="Available Beds" icon={BedDouble} value={summary?.available_beds ?? '—'} color="bg-green-600" note={`${summary?.cleaning_beds ?? 0} cleaning · ${summary?.maintenance_beds ?? 0} maintenance`} loading={isLoading} />
        <StatCard label="Registered Patients" icon={Users} value={summary?.total_patients ?? '—'} color="bg-purple-600" note={`${summary?.today_registrations ?? 0} registered today`} loading={isLoading} />
        <StatCard label="Admissions Today" icon={ClipboardList} value={summary?.today_admissions ?? '—'} color="bg-cyan-700" note={`${summary?.today_discharges ?? 0} discharges today`} loading={isLoading} />
        <StatCard label="Reserved / Isolation" icon={AlertTriangle} value={`${summary?.reserved_beds ?? 0} / ${summary?.isolation_beds ?? 0}`} color="bg-amber-600" note="Current bed state" loading={isLoading} />
        <StatCard label="Active Encounters" icon={ActivitySquare} value={summary?.active_encounters ?? '—'} color="bg-indigo-600" note={`${summary?.pending_lab_orders ?? 0} lab orders pending`} loading={isLoading} />
        <StatCard label="Pharmacy Alerts" icon={AlertTriangle} value={summary?.low_stock_items ?? '—'} color="bg-orange-600" note={`${summary?.pending_prescriptions ?? 0} prescriptions pending`} loading={isLoading} />
        <StatCard label="Outstanding Billing" icon={ClipboardList} value={`₹${summary?.outstanding_amount ?? 0}`} color="bg-rose-600" note={`${summary?.bills ?? 0} bills · ${summary?.payments ?? 0} payments`} loading={isLoading} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <section className="xl:col-span-2 card p-5">
          <div className="flex items-center justify-between mb-4"><div><h2 className="text-sm font-semibold text-gray-900">Admissions vs Discharges</h2><p className="text-xs text-gray-500 mt-0.5">Past 7 days</p></div><ClipboardList size={16} className="text-gray-400" /></div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={summary?.admission_trend ?? []}><CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" /><XAxis dataKey="label" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} tick={{ fontSize: 11 }} /><Tooltip /><Area type="monotone" dataKey="admissions" stroke="#0052CC" fill="#E6F0FF" strokeWidth={2} name="Admissions" /><Area type="monotone" dataKey="discharges" stroke="#00875A" fill="#E3FCEF" strokeWidth={2} name="Discharges" /></AreaChart>
          </ResponsiveContainer>
        </section>
        <section className="card p-5">
          <div className="flex items-center justify-between mb-4"><h2 className="text-sm font-semibold text-gray-900">Bed Status Distribution</h2><BedDouble size={16} className="text-gray-400" /></div>
          <ResponsiveContainer width="100%" height={190}>
            <PieChart><Pie data={bedStatus} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={3} dataKey="value">{bedStatus.map((entry) => <Cell key={entry.name} fill={entry.color} />)}</Pie><Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} /></PieChart>
          </ResponsiveContainer>
        </section>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <section className="xl:col-span-2 card p-5">
          <h2 className="text-sm font-semibold text-gray-900">Ward Occupancy Rate</h2><p className="text-xs text-gray-500 mt-0.5 mb-4">Current occupancy by ward</p>
          <ResponsiveContainer width="100%" height={Math.max(180, (summary?.wards?.length ?? 0) * 34)}>
            <BarChart data={summary?.wards ?? []} layout="vertical" margin={{ left: 24 }}><CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} /><XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" /><YAxis type="category" dataKey="ward_name" tick={{ fontSize: 11 }} width={110} /><Tooltip /><Bar dataKey="occupancy_pct" fill="#0052CC" radius={[0, 4, 4, 0]} name="Occupancy (%)" /></BarChart>
          </ResponsiveContainer>
        </section>
        <section className="card p-5"><div className="flex items-center justify-between mb-4"><h2 className="text-sm font-semibold text-gray-900">Recent Patient Events</h2><span className="badge badge-info">LIVE</span></div><div className="space-y-3">{(summary?.recent_events ?? []).map((event: any) => <div key={event.id} className="flex items-start gap-2.5"><span className="text-xs text-gray-400 w-12 flex-shrink-0 pt-0.5">{new Date(event.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</span><div><span className={clsx('badge text-xs mb-0.5', eventTone(event.event_type))}>{event.event_type.replaceAll('_', ' ')}</span><p className="text-xs text-gray-700 leading-snug">{event.title}{event.patient_name ? ` — ${event.patient_name}` : ''}</p></div></div>)}{!isLoading && !summary?.recent_events?.length && <p className="text-sm text-gray-500">No recent events.</p>}</div></section>
      </div>
    </div>
  )
}
