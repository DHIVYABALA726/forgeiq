import { Activity, BarChart3, Factory, FileText, Gauge, Settings2 } from 'lucide-react';
import type { Section } from '../types';

const items: { id: Section; label: string; icon: typeof Activity }[] = [
  { id: 'workspace', label: 'Workspace', icon: Gauge },
  { id: 'data', label: 'Manufacturing data', icon: Factory },
  { id: 'scheduling', label: 'Scheduling', icon: Settings2 },
  { id: 'gantt', label: 'Gantt chart', icon: Activity },
  { id: 'comparison', label: 'Algorithm comparison', icon: BarChart3 },
  { id: 'report', label: 'Scheduling report', icon: FileText },
];

export default function Sidebar({ active, onNavigate, scheduleAvailable }: { active: Section; onNavigate: (section: Section) => void; scheduleAvailable: boolean }) {
  return <aside className="sidebar">
    <div className="brand"><div className="brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M6 8h9v7h11v9h-9v-7H6z" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinejoin="round"/><path d="M6 8h6m14 16h-6" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"/></svg></div><div><strong>Forge<span>IQ</span></strong><small>Production scheduler</small></div></div>
    <div className="nav-label">WORKSPACE</div>
    <nav aria-label="Main navigation">{items.map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${active === id ? 'active' : ''}`} onClick={() => onNavigate(id)} aria-current={active === id ? 'page' : undefined}>
      <Icon size={17} strokeWidth={1.9} /><span>{label}</span>{id !== 'workspace' && !scheduleAvailable && ['gantt', 'comparison', 'report'].includes(id) && <span className="nav-dot" aria-label="No schedule yet" />}
    </button>)}</nav>
    <div className="sidebar-foot"><div className="status-pulse" /><span>Scheduling engine ready</span><small>Deterministic · Constraint-aware</small></div>
  </aside>;
}
