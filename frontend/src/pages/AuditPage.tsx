import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { Shield, Filter, ChevronLeft, ChevronRight, RefreshCcw } from 'lucide-react'
import clsx from 'clsx'

const ACTION_COLORS: Record<string, string> = {
  CREATE: 'badge-success',
  UPDATE: 'badge-info',
  DELETE: 'badge-danger',
  LOGIN: 'badge-purple',
  LOGOUT: 'badge-gray',
  TRANSITION: 'badge-warning',
  ACCESS: 'badge-gray',
}

const FILTER_ACTIONS = ['', 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'TRANSITION']

export default function AuditPage() {
  const [page, setPage] = useState(1)
  const [action, setAction] = useState('')
  const [resource, setResource] = useState('')
  const pageSize = 25

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['audit-logs', page, action, resource],
    queryFn: () =>
      api.get('/audit-logs', {
        params: {
          offset: (page - 1) * pageSize,
          limit: pageSize,
          action: action || undefined,
          entity_type: resource || undefined,
        },
      }).then(r => r.data),
    placeholderData: (prev) => prev,
  })

  const logs = Array.isArray(data) ? data : (data?.items ?? [])
  const total = data?.total ?? logs.length

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Shield size={20} className="text-blue-700" />
            Audit & Governance
          </h1>
          <p className="text-sm text-gray-500">All system events logged with actor, timestamp, and affected resource</p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50"
        >
          <RefreshCcw size={14} className={clsx(isFetching && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="card px-4 py-3 flex items-center gap-3 flex-wrap">
        <Filter size={14} className="text-gray-400" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Action:</span>
          {FILTER_ACTIONS.map(a => (
            <button
              key={a}
              onClick={() => { setAction(a); setPage(1) }}
              className={clsx('px-2.5 py-1 text-xs rounded border transition-colors',
                action === a ? 'bg-blue-700 text-white border-blue-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'
              )}
            >
              {a === '' ? 'All' : a}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 ml-4">
          <span className="text-xs text-gray-500">Resource:</span>
          <input
            className="input text-xs w-36 py-1"
            placeholder="e.g. Bed, Patient"
            value={resource}
            onChange={e => { setResource(e.target.value); setPage(1) }}
          />
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading audit logs…</div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">Failed to load audit logs.</div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="table-th">Timestamp</th>
                <th className="table-th">Actor</th>
                <th className="table-th">Action</th>
                <th className="table-th">Resource</th>
                <th className="table-th">Resource ID</th>
                <th className="table-th">Details</th>
                <th className="table-th">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map((log: any) => (
                <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                  <td className="table-td text-xs text-gray-500 whitespace-nowrap">
                    {new Date(log.created_at ?? log.timestamp).toLocaleString('en-IN')}
                  </td>
                  <td className="table-td">
                    <p className="font-medium text-sm">{log.actor_name ?? `User #${log.actor_id}`}</p>
                    <p className="text-xs text-gray-400">{log.actor_email}</p>
                  </td>
                  <td className="table-td">
                    <span className={clsx('badge', ACTION_COLORS[log.action] ?? 'badge-gray')}>
                      {log.action}
                    </span>
                  </td>
                  <td className="table-td text-sm font-medium">{log.entity_type}</td>
                  <td className="table-td font-mono text-xs text-gray-600">{log.entity_id ?? '—'}</td>
                  <td className="table-td text-xs text-gray-600 max-w-xs truncate">{log.notes ?? '—'}</td>
                  <td className="table-td font-mono text-xs text-gray-400">{log.ip_address ?? '—'}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr>
                  <td colSpan={7} className="table-td text-center text-gray-400 py-10">
                    No audit events found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}

        {!isLoading && !error && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
            <p className="text-xs text-gray-500">Showing {Math.min(logs.length, pageSize)} of {total} events</p>
            <div className="flex items-center gap-1">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="p-1 rounded hover:bg-gray-100 disabled:opacity-40">
                <ChevronLeft size={16} />
              </button>
              <span className="text-sm px-2">Page {page}</span>
              <button onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= total} className="p-1 rounded hover:bg-gray-100 disabled:opacity-40">
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
