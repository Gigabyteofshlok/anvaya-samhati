import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  BedDouble,
  ClipboardList,
  UserCheck,
  HeartPulse,
  UserCog,
  Activity,
  Shield,
  Sparkles,
  Building2,
  FlaskConical,
  Pill,
  ReceiptIndianRupee,
  ShieldCheck,
  LogOut,
} from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { label: 'Command Center', icon: LayoutDashboard, to: '/command-center' },
  { label: 'Patients', icon: Users, to: '/patients' },
  { label: 'Bed Management', icon: BedDouble, to: '/beds' },
  { label: 'Admissions', icon: ClipboardList, to: '/admissions' },
  { divider: true },
  { label: 'Doctor Dashboard', icon: UserCheck, to: '/doctor' },
  { label: 'Nurse Dashboard', icon: HeartPulse, to: '/nurse' },
  { label: 'Reception', icon: UserCog, to: '/reception' },
  { divider: true },
  { label: 'Laboratory', icon: FlaskConical, to: '/laboratory' },
  { label: 'Pharmacy', icon: Pill, to: '/pharmacy' },
  { label: 'Billing', icon: ReceiptIndianRupee, to: '/billing' },
  { label: 'Insurance / TPA', icon: ShieldCheck, to: '/insurance' },
  { label: 'Discharge', icon: LogOut, to: '/discharges' },
  { divider: true },
  { label: 'AI Intelligence', icon: Sparkles, to: '/ai-roadmap' },
  { label: 'Audit & Governance', icon: Shield, to: '/audit' },
]

export default function Sidebar() {
  return (
    <aside className="w-60 bg-slate-900 text-white flex flex-col flex-shrink-0 h-full">
      {/* Brand */}
      <div className="px-5 py-4 border-b border-slate-700">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-blue-600 rounded flex items-center justify-center flex-shrink-0">
            <Building2 size={16} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-white leading-tight">ANVAYA SAṂHATI</p>
            <p className="text-xs text-slate-400 leading-tight">Hospital OS</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {navItems.map((item, idx) => {
          if ('divider' in item && item.divider) {
            return <div key={idx} className="my-2 border-t border-slate-700 mx-2" />
          }
          const Icon = item.icon!
          return (
            <NavLink
              key={item.to}
              to={item.to!}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors mb-0.5',
                  isActive
                    ? 'bg-blue-700 text-white font-medium'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                )
              }
            >
              <Icon size={16} className="flex-shrink-0" />
              {item.label}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-slate-700">
        <div className="flex items-center gap-2">
          <Activity size={12} className="text-green-400" />
          <span className="text-xs text-slate-400">System Operational</span>
        </div>
        <p className="text-xs text-slate-600 mt-1">v1.0.0-alpha</p>
      </div>
    </aside>
  )
}
