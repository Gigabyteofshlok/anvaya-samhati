import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import AppShell from './components/layout/AppShell'
import LoginPage from './pages/LoginPage'
import CommandCenter from './pages/CommandCenter'
import PatientsPage from './pages/PatientsPage'
import Patient360Page from './pages/Patient360Page'
import BedManagementPage from './pages/BedManagementPage'
import AdmissionsPage from './pages/AdmissionsPage'
import DoctorDashboard from './pages/DoctorDashboard'
import NurseDashboard from './pages/NurseDashboard'
import ReceptionDashboard from './pages/ReceptionDashboard'
import AIRoadmapPage from './pages/AIRoadmapPage'
import AuditPage from './pages/AuditPage'
import LaboratoryPage from './pages/LaboratoryPage'
import PharmacyPage from './pages/PharmacyPage'
import BillingPage from './pages/BillingPage'
import InsurancePage from './pages/InsurancePage'
import DischargePage from './pages/DischargePage'
import PatientPortalPage from './pages/PatientPortalPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/command-center" replace />} />
        <Route path="command-center" element={<CommandCenter />} />
        <Route path="patients" element={<PatientsPage />} />
        <Route path="patients/:patientId" element={<Patient360Page />} />
        <Route path="beds" element={<BedManagementPage />} />
        <Route path="admissions" element={<AdmissionsPage />} />
        <Route path="doctor" element={<DoctorDashboard />} />
        <Route path="nurse" element={<NurseDashboard />} />
        <Route path="reception" element={<ReceptionDashboard />} />
        <Route path="ai-roadmap" element={<AIRoadmapPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="laboratory" element={<LaboratoryPage />} />
        <Route path="lab-orders" element={<LaboratoryPage />} />
        <Route path="lab-history" element={<LaboratoryPage />} />
        <Route path="lab-catalog" element={<LaboratoryPage />} />
        <Route path="pharmacy" element={<PharmacyPage />} />
        <Route path="billing" element={<BillingPage />} />
        <Route path="insurance" element={<InsurancePage />} />
        <Route path="discharges" element={<DischargePage />} />
        <Route path="portal" element={<PatientPortalPage />} />
      </Route>
    </Routes>
  )
}
