import { FlaskConical } from 'lucide-react'

export default function DemoBanner() {
  return (
    <div className="bg-amber-500 text-amber-950 px-4 py-1 flex items-center justify-center gap-2 text-xs font-medium flex-shrink-0">
      <FlaskConical size={12} />
      DEMO ENVIRONMENT • SYNTHETIC DATA — Not for clinical use
    </div>
  )
}
