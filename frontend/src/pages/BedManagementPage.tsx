import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { BedDouble, RefreshCcw, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
  AVAILABLE:    { label: 'Available',    bg: 'bg-green-50',  text: 'text-green-800',  border: 'border-green-300' },
  OCCUPIED:     { label: 'Occupied',     bg: 'bg-red-50',    text: 'text-red-800',    border: 'border-red-400' },
  RESERVED:     { label: 'Reserved',     bg: 'bg-blue-50',   text: 'text-blue-800',   border: 'border-blue-300' },
  CLEANING:     { label: 'Cleaning',     bg: 'bg-yellow-50', text: 'text-yellow-800', border: 'border-yellow-400' },
  MAINTENANCE:  { label: 'Maintenance',  bg: 'bg-purple-50', text: 'text-purple-800', border: 'border-purple-300' },
  ISOLATION:    { label: 'Isolation',    bg: 'bg-orange-50', text: 'text-orange-800', border: 'border-orange-400' },
}

function BedCell({ bed }: { bed: any }) {
  const cfg = STATUS_CONFIG[bed.status] ?? STATUS_CONFIG.AVAILABLE
  return (
    <div className={clsx('border rounded p-2 text-xs cursor-pointer hover:shadow-sm transition-shadow', cfg.bg, cfg.border)}>
      <p className={clsx('font-bold leading-tight', cfg.text)}>{bed.bed_number}</p>
      <p className="text-gray-500 mt-0.5 truncate">{cfg.label}</p>
      {bed.current_patient_name && (
        <p className="text-gray-600 truncate mt-0.5 text-xs">{bed.current_patient_name}</p>
      )}
    </div>
  )
}

export default function BedManagementPage() {
  const { data: bedsRaw, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['beds-all'],
    queryFn: () => api.get('/beds', { params: { limit: 200 } }).then(r => r.data),
    refetchInterval: 30_000,
  })

  const { data: stats } = useQuery({
    queryKey: ['bed-stats'],
    queryFn: () => api.get('/beds/stats').then(r => r.data),
  })
  const { data: priorities = [] } = useQuery({
    queryKey: ['bed-action-priorities'],
    queryFn: () => api.get('/beds/action-priorities').then(r => r.data),
    refetchInterval: 30_000,
  })

  const beds: any[] = Array.isArray(bedsRaw) ? bedsRaw : (bedsRaw?.items ?? [])

  // Group by ward
  const byWard: Record<string, any[]> = {}
  beds.forEach(b => {
    const ward = b.ward_name ?? b.ward ?? 'Unknown Ward'
    if (!byWard[ward]) byWard[ward] = []
    byWard[ward].push(b)
  })

  const statusTotals = stats ?? {}

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Bed Management</h1>
          <p className="text-sm text-gray-500">Real-time bed status across all wards</p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50"
        >
          <RefreshCcw size={14} className={clsx(isFetching && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Legend + Stats */}
      <div className="card p-4 flex items-center gap-6 flex-wrap">
        {Object.entries(STATUS_CONFIG).map(([status, cfg]) => (
          <div key={status} className="flex items-center gap-1.5">
            <div className={clsx('w-3 h-3 rounded border', cfg.bg, cfg.border)} />
            <span className="text-xs text-gray-600">
              {cfg.label}
              {statusTotals[status.toLowerCase()] !== undefined && (
                <span className="font-semibold ml-1">({statusTotals[status.toLowerCase()]})</span>
              )}
            </span>
          </div>
        ))}
        {error && (
          <div className="flex items-center gap-1 text-amber-600 text-xs ml-auto">
            <AlertTriangle size={12} />
            Backend offline
          </div>
        )}
      </div>

      {/* Ward Grids */}
      <section className="card overflow-hidden">
        <div className="px-4 py-3 border-b"><h2 className="text-sm font-semibold">Bed action priority</h2><p className="text-xs text-gray-500 mt-0.5">A transparent queue calculated from persisted bed state and discharge timing. It never assigns beds automatically.</p></div>
        <div className="divide-y">{priorities.map((item: any) => <div key={item.bed_id} className="px-4 py-3 flex flex-wrap gap-3 items-center"><span className="font-mono font-semibold text-blue-700">{item.bed_number}</span><span className={clsx('badge', STATUS_CONFIG[item.status]?.text || 'badge-gray')}>{item.status}</span><span className="text-sm font-medium">{item.recommended_action}</span><span className="text-xs text-gray-600 flex-1">{item.reason}</span></div>)}{!priorities.length && <p className="p-4 text-sm text-gray-500">No bed priorities available.</p>}</div>
      </section>
      {isLoading ? (
        <div className="card p-8 text-center text-gray-500">Loading beds…</div>
      ) : beds.length === 0 ? (
        <div className="card p-8 text-center">
          <BedDouble size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500">No beds found. Is the backend running and seeded?</p>
        </div>
      ) : (
        Object.entries(byWard).map(([ward, wardBeds]) => {
          const occupied = wardBeds.filter(b => b.status === 'OCCUPIED').length
          const total = wardBeds.length
          const pct = Math.round((occupied / total) * 100)
          return (
            <div key={ward} className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <h3 className="text-sm font-semibold text-gray-800">{ward}</h3>
                  <span className={clsx('badge',
                    pct >= 90 ? 'badge-danger' : pct >= 70 ? 'badge-warning' : 'badge-success'
                  )}>
                    {occupied}/{total} Occupied ({pct}%)
                  </span>
                </div>
                {/* Mini occupancy bar */}
                <div className="w-32 h-2 bg-gray-200 rounded overflow-hidden">
                  <div
                    className={clsx('h-full rounded transition-all', pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-yellow-400' : 'bg-green-500')}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
              <div className="grid grid-cols-5 sm:grid-cols-8 md:grid-cols-10 lg:grid-cols-12 gap-2">
                {wardBeds.map(b => <BedCell key={b.id} bed={b} />)}
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}
