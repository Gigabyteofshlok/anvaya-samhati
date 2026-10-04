import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { Plus, Search, ChevronLeft, ChevronRight, X, AlertCircle } from 'lucide-react'
import clsx from 'clsx'
import { RegistrationModal } from './PatientsPage'

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: 'badge-success',
  DISCHARGED: 'badge-info',
  TRANSFERRED: 'badge-warning',
  CANCELLED: 'badge-danger',
}

export default function AdmissionsPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const pageSize = 15

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admissions', page, search],
    queryFn: () =>
      api.get('/admissions', { params: { q: search || undefined, offset: (page - 1) * pageSize, limit: pageSize } }).then(r => r.data),
    placeholderData: (prev) => prev,
  })

  const admissions = Array.isArray(data) ? data : (data?.items ?? [])
  const total = data?.total ?? admissions.length

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Admissions</h1>
          <p className="text-sm text-gray-500">{total} total admissions</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowModal(true)}>
          <Plus size={15} />
          New Admission
        </button>
      </div>

      {/* Search */}
      <div className="card px-4 py-3 flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            className="input pl-8"
            placeholder="Search by ADM-ID or patient name…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading admissions…</div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">Failed to load admissions.</div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="table-th">ADM No.</th>
                <th className="table-th">Patient</th>
                <th className="table-th">Bed</th>
                <th className="table-th">Ward</th>
                <th className="table-th">Admitted</th>
                <th className="table-th">Attending Doctor</th>
                <th className="table-th">Status</th>
                <th className="table-th">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {admissions.map((a: any) => (
                <tr key={a.id} className="hover:bg-blue-50 transition-colors">
                  <td className="table-td font-mono text-blue-700 font-medium text-xs">{a.admission_number}</td>
                  <td className="table-td">
                    <p className="font-medium">{a.patient_name ?? `Patient #${a.patient_id}`}</p>
                    <p className="text-xs text-gray-400">{a.patient_code}</p>
                  </td>
                  <td className="table-td">{a.bed_number ?? 'Unassigned'}</td>
                  <td className="table-td text-gray-600">{a.ward_name ?? '—'}</td>
                  <td className="table-td text-xs text-gray-500">
                    {a.admitted_at ? new Date(a.admitted_at).toLocaleString('en-IN') : '—'}
                  </td>
                  <td className="table-td">{a.doctor_name ?? '—'}</td>
                  <td className="table-td">
                    <span className={clsx('badge', STATUS_COLORS[a.status] ?? 'badge-gray')}>{a.status}</span>
                  </td>
                  <td className="table-td">
                    {a.status === 'ACTIVE' && <span className="text-xs text-gray-400">Active</span>}
                  </td>
                </tr>
              ))}
              {admissions.length === 0 && (
                <tr><td colSpan={8} className="table-td text-center text-gray-400 py-8">No admissions found.</td></tr>
              )}
            </tbody>
          </table>
        )}

        {!isLoading && !error && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
            <p className="text-xs text-gray-500">Showing {Math.min(admissions.length, pageSize)} of {total}</p>
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

      {/* New Admission Modal */}
      {showModal && <NewAdmissionModal onClose={() => { setShowModal(false); refetch() }} />}
    </div>
  )
}

function NewAdmissionModal({ onClose }: { onClose: () => void }) {
  const [patientId, setPatientId] = useState('')
  const [bedId, setBedId] = useState('')
  const [doctorId, setDoctorId] = useState('')
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [registering, setRegistering] = useState(false)

  const { data: patientsData } = useQuery({
    queryKey: ['patients-select'],
    queryFn: () => api.get('/patients', { params: { limit: 100 } }).then(r => r.data),
  })
  const { data: bedsData } = useQuery({
    queryKey: ['beds-available'],
    queryFn: () => api.get('/beds', { params: { status: 'AVAILABLE' } }).then(r => r.data),
  })
  const { data: doctorsData } = useQuery({
    queryKey: ['doctors-select'],
    queryFn: () => api.get('/users', { params: { role: 'DOCTOR' } }).then(r => r.data),
  })

  const patients = Array.isArray(patientsData) ? patientsData : (patientsData?.items ?? [])
  const beds = Array.isArray(bedsData) ? bedsData : (bedsData?.items ?? [])
  const doctors = Array.isArray(doctorsData) ? doctorsData : []
  const selectedBed = beds.find((bed: any) => bed.id === bedId)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await api.post('/admissions', {
        patient_id: patientId,
        branch_id: selectedBed.branch_id,
        assigned_bed_id: bedId,
        attending_doctor_id: doctorId,
        admission_type: 'EMERGENCY',
        reason,
      })
      onClose()
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Failed to create admission.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">New Admission</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded px-3 py-2 text-red-700 text-sm">
              <AlertCircle size={14} />
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Attending Doctor</label>
            <select className="input" value={doctorId} onChange={e => setDoctorId(e.target.value)} required>
              <option value="">Select doctor…</option>
              {doctors.map((doctor: any) => <option key={doctor.id} value={doctor.id}>{doctor.full_name}{doctor.specialization ? ` — ${doctor.specialization}` : ''}</option>)}
            </select>
          </div>
          <div>
            <div className="flex items-center justify-between mb-1"><label className="block text-sm font-medium text-gray-700">Patient</label><button type="button" onClick={() => setRegistering(true)} className="text-xs text-blue-700 hover:underline">Register new patient</button></div>
            <select className="input" value={patientId} onChange={e => setPatientId(e.target.value)} required>
              <option value="">Select patient…</option>
              {patients.map((p: any) => (
                <option key={p.id} value={p.id}>{p.first_name} {p.last_name} ({p.patient_id})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Bed (Available)</label>
            <select className="input" value={bedId} onChange={e => setBedId(e.target.value)} required>
              <option value="">Select bed…</option>
              {beds.map((b: any) => (
                <option key={b.id} value={b.id}>{b.bed_number} — {b.ward_name ?? b.ward}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Chief Complaint / Reason</label>
            <textarea
              className="input"
              rows={3}
              placeholder="Chief complaint or reason for admission…"
              value={reason}
              onChange={e => setReason(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Admitting…' : 'Admit Patient'}
            </button>
          </div>
        </form>
      </div>
      {registering && <RegistrationModal onClose={() => setRegistering(false)} onCreated={(id) => { setPatientId(id); setRegistering(false) }} />}
    </div>
  )
}
