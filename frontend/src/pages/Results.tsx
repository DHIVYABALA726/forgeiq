import { useEffect, useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Download, Printer, Save, TriangleAlert } from 'lucide-react';
import type { AlgorithmName, ApiCollections, Objective, ScheduleRun } from '../types';
import { selectSchedule } from '../services/api';
import GanttChart from '../components/GanttChart';

const metricRows: { key: keyof NonNullable<ScheduleRun['results'][number]['metrics']>; label: string; unit: string }[] = [
  { key: 'makespan', label: 'Makespan', unit: 'min' }, { key: 'total_completion_time', label: 'Total completion time', unit: 'min' },
  { key: 'total_tardiness', label: 'Total tardiness', unit: 'min' }, { key: 'maximum_lateness', label: 'Maximum lateness', unit: 'min' },
  { key: 'tardy_jobs', label: 'Tardy jobs', unit: 'jobs' }, { key: 'average_waiting', label: 'Average waiting', unit: 'min / operation' },
  { key: 'machine_utilization', label: 'Machine utilization', unit: '%' },
];
const objectiveLabel: Record<Objective, string> = { makespan: 'Makespan', total_tardiness: 'Total tardiness', maximum_lateness: 'Maximum lateness', tardy_jobs: 'Tardy jobs', machine_utilization: 'Machine utilization', average_waiting: 'Average waiting' };
const number = (value: number | null | undefined, unit: string) => value == null || !Number.isFinite(value) ? 'N/A' : `${Number(value.toFixed(2)).toLocaleString()}${unit === '%' ? '%' : unit === 'jobs' ? '' : ` ${unit}`}`;

function downloadCsv(filename: string, rows: (string | number | null | undefined)[][]) {
  const escape = (value: unknown) => `"${String(value ?? '').replaceAll('"', '""')}"`;
  const csv = rows.map(row => row.map(escape).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' }));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
}

export default function Results({ run, allRuns, data, initialView, onLoadSchedule }: { run?: ScheduleRun | null; allRuns: ScheduleRun[]; data: ApiCollections; initialView: 'gantt' | 'comparison' | 'report'; onLoadSchedule: (id: string) => Promise<void> }) {
  const [algorithmByRun, setAlgorithmByRun] = useState<Record<string, AlgorithmName>>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [saveError, setSaveError] = useState('');
  const [tab, setTab] = useState(initialView);
  useEffect(() => setTab(initialView), [initialView]);
  const current = run ?? allRuns[0];
  const feasible = current?.results.filter(x => x.feasible) ?? [];
  const selected = feasible.find(x => x.algorithm_name === (current ? algorithmByRun[current.id] : null)) ?? feasible.find(x => x.algorithm_name === current?.selected_algorithm_name) ?? feasible.find(x => x.algorithm_name === current?.recommended_algorithm_name) ?? feasible[0];
  const objective = current?.objective ?? 'makespan';
  const objectiveMetric = objective as keyof NonNullable<ScheduleRun['results'][number]['metrics']>;
  const chartData = useMemo(() => (current?.results ?? []).map(result => ({ name: result.algorithm_name, feasible: result.feasible, value: result.feasible ? Number(result.metrics[objectiveMetric] ?? 0) : null, fill: result.feasible ? '#2563eb' : '#cbd5e1' })), [current, objectiveMetric]);
  const jobs = current?.input_snapshot?.jobs ?? data.jobs;
  const machines = current?.input_snapshot?.machines ?? data.machines;
  if (!current) return <div className="page-shell"><header className="page-heading"><div><div className="eyebrow">SCHEDULE RESULTS</div><h1>{initialView === 'gantt' ? 'Gantt chart' : initialView === 'comparison' ? 'Algorithm comparison' : 'Scheduling report'}</h1><p className="page-subtitle">Generated schedules and metrics appear here after a successful run.</p></div></header><div className="chart-empty"><div className="empty-icon"><TriangleAlert size={21}/></div><h3>No schedule results yet</h3><p>Enter manufacturing data, choose a scenario and generate a schedule to see calculated results.</p><button className="button button-primary" onClick={() => window.dispatchEvent(new CustomEvent('forgeiq:navigate-scheduling'))}>Configure scheduling</button></div></div>;
  async function saveSelected() {
    if (!selected) return;
    setSaving(true); setMessage(''); setSaveError('');
    try { await selectSchedule(current.id, selected.algorithm_name); current.selected_algorithm_name = selected.algorithm_name; setMessage(`${selected.algorithm_name} saved as the selected schedule.`); }
    catch (error) { setSaveError(error instanceof Error ? error.message : 'Could not save this schedule.'); }
    finally { setSaving(false); }
  }
  function exportSchedule() {
    const header = ['Algorithm', 'Feasible', 'Hard due dates', 'Operation ID', 'Job ID', 'Operation', 'Machine ID', 'Start', 'Finish', 'Duration (min)', 'Processing (min)', 'Setup (min)', 'Waiting (min)', 'Due'];
    const rows = current.results.filter(result => result.feasible).flatMap(result => result.scheduled_operations.map(op => [result.algorithm_name, 'Yes', current.hard_due_dates ? 'Yes' : 'No', op.operation_id, op.job_id, op.operation_name, op.machine_id, op.start_at, op.end_at, op.duration_minutes, op.processing_time_minutes, op.setup_time_minutes, op.waiting_time_minutes, op.due_at]));
    downloadCsv(`forgeiq-schedule-${current.id.slice(0, 8)}.csv`, [header, ...rows]);
  }
  function exportComparison() {
    const header = ['Algorithm', 'Feasible', 'Hard due dates', ...metricRows.map(row => row.label), 'Computation time (ms)', 'Reason if infeasible'];
    const rows = current.results.map(result => [result.algorithm_name, result.feasible ? 'Yes' : 'No', current.hard_due_dates ? 'Yes' : 'No', ...metricRows.map(row => result.feasible ? result.metrics[row.key] as string | number | null : 'N/A'), result.computation_time_ms, result.error_message]);
    downloadCsv(`forgeiq-comparison-${current.id.slice(0, 8)}.csv`, [header, ...rows]);
  }
  return <div className="page-shell results-page">
    <header className="page-heading"><div><div className="eyebrow">RESULTS · {current.scenario.replaceAll('_', ' ').toUpperCase()}</div><h1>{initialView === 'gantt' ? 'Gantt chart' : initialView === 'comparison' ? 'Algorithm comparison' : 'Scheduling report'}</h1><p className="page-subtitle">Run {current.id.slice(0, 8)} · {new Date(current.created_at).toLocaleString()} · Objective: {objectiveLabel[objective]} · Due dates: {current.hard_due_dates ? 'hard constraint' : 'soft evaluation'}</p></div><div className="top-actions"><label className="history-select"><span>Saved run</span><select className="control control-sm" aria-label="Load a saved schedule" value={current.id} onChange={event => void onLoadSchedule(event.target.value)}>{allRuns.map(item => <option key={item.id} value={item.id}>{new Date(item.created_at).toLocaleString()} · {item.objective}{item.hard_due_dates ? ' · hard deadlines' : ''}{item.is_stale ? ' · outdated' : ''}</option>)}</select></label><button className="button button-outline" onClick={exportSchedule}><Download size={15}/> Export schedule CSV</button><button className="button button-outline" onClick={exportComparison}><Download size={15}/> Export comparison CSV</button><button className="button button-quiet print-action" onClick={() => window.print()}><Printer size={15}/> Print</button></div></header>
    {current.is_stale && <div className="alert alert-warning" role="status"><strong>Outdated schedule.</strong> Inputs changed after this run. Results below are the saved snapshot, not the current dataset.</div>}
    {message && <div className="alert alert-success" role="status">{message}</div>}{saveError && <div className="alert alert-error" role="alert">{saveError}</div>}
    <section className="recommendation-banner"><div className="recommendation-mark"><span>IQ</span></div><div className="recommendation-copy"><div className="eyebrow">MEASURED ALGORITHM RECOMMENDATION</div><h2>Recommended algorithm: <span>{current.recommended_algorithm_name || 'None available'}</span></h2><p><strong>Reason:</strong> {current.recommendation_reason || 'No feasible result was produced. Review machine eligibility, availability, release times and operation precedence.'}</p><div className="recommendation-meta"><span><strong>Objective:</strong> {objectiveLabel[objective]}</span><span><strong>Scope:</strong> Best among the feasible algorithms evaluated for this dataset. This is not a guarantee of global optimality.</span></div></div></section>
    <div className="results-toolbar"><div className="view-tabs" role="tablist" aria-label="Result views">{(['gantt', 'comparison', 'report'] as const).map(view => <button key={view} role="tab" aria-selected={tab === view} className={tab === view ? 'selected' : ''} onClick={() => setTab(view)}>{view === 'gantt' ? 'Gantt chart' : view === 'comparison' ? 'Comparison' : 'Report'}</button>)}</div><div className="save-control"><label htmlFor="save-algorithm">Selected schedule</label><select id="save-algorithm" className="control control-sm" value={selected?.algorithm_name ?? ''} onChange={e => setAlgorithmByRun(state => ({ ...state, [current.id]: e.target.value as AlgorithmName }))}>{feasible.map(result => <option key={result.algorithm_name} value={result.algorithm_name}>{result.algorithm_name}</option>)}</select><button className="button button-primary button-sm" onClick={saveSelected} disabled={!selected || saving || current.is_stale}><Save size={14}/>{saving ? 'Saving…' : 'Save selection'}</button></div></div>
    {tab === 'gantt' && <GanttChart results={current.results} machines={machines} jobs={jobs} initialAlgorithm={selected?.algorithm_name ?? current.recommended_algorithm_name} />}
    {(tab === 'comparison' || tab === 'report') && <>
      <section className="metrics-panel"><div className="section-title-row"><div><div className="eyebrow">CALCULATED FROM SCHEDULE OUTPUT</div><h2>Performance comparison</h2></div><span className="metric-definition-note">Times are minutes from the run's scheduling-horizon origin unless otherwise labelled.</span></div>
        <div className="table-wrap"><table className="comparison-table"><thead><tr><th>Algorithm</th><th>Feasible</th>{metricRows.map(row => <th key={row.key}>{row.label}<small>{row.unit}</small></th>)}<th>Compute time<small>ms</small></th></tr></thead><tbody>{current.results.map(result => <tr key={result.algorithm_name} className={result.algorithm_name === current.recommended_algorithm_name ? 'winner-row' : ''}><th>{result.algorithm_name}{result.algorithm_name === current.recommended_algorithm_name && <span className="winner-tag">BEST</span>}{!result.feasible && result.error_message && <small className="row-error">{result.error_message}</small>}</th><td><span className={`feasible-pill ${result.feasible ? 'yes' : 'no'}`}>{result.feasible ? 'Yes' : 'No'}</span></td>{metricRows.map(row => <td key={row.key}>{number(result.feasible ? result.metrics[row.key] as number | null | undefined : null, row.unit)}</td>)}<td>{result.computation_time_ms.toFixed(2)}</td></tr>)}</tbody></table></div>
      </section>
      <section className="chart-panel"><div className="section-title-row"><div><div className="eyebrow">OBJECTIVE: {objectiveLabel[objective].toUpperCase()}</div><h2>Objective comparison</h2></div><span className="chart-unit">{objective === 'machine_utilization' ? 'Higher is better · %' : 'Lower is better · minutes / jobs'}</span></div><div className="objective-chart"><ResponsiveContainer width="100%" height={260}><BarChart data={chartData} margin={{ top: 12, right: 22, left: 12, bottom: 10 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e9eef4"/><XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 12 }}/><YAxis tick={{ fill: '#64748b', fontSize: 11 }}/><Tooltip formatter={(value) => [number(Number(value), objective === 'machine_utilization' ? '%' : objective === 'tardy_jobs' ? 'jobs' : 'min'), objectiveLabel[objective]]}/><Bar dataKey="value" radius={[5, 5, 0, 0]} maxBarSize={64}>{chartData.map(entry => <Cell key={entry.name} fill={entry.fill} fillOpacity={entry.feasible ? 1 : .45}/>)}</Bar></BarChart></ResponsiveContainer></div></section>
      <section className="definitions-panel"><div className="eyebrow">METRIC DEFINITIONS</div><div className="definitions-grid"><p><strong>Makespan</strong><span>Last operation completion minus horizon start.</span></p><p><strong>Total completion time</strong><span>Sum of job completions, measured from horizon start.</span></p><p><strong>Tardiness / lateness</strong><span>Positive completion − due time; maximum lateness retains negative values.</span></p><p><strong>Average waiting</strong><span>Mean of operation queue intervals before start; excludes machine idle.</span></p><p><strong>Machine utilization</strong><span>Processing minutes ÷ available machine minutes; unavailable time and setup are excluded from productive processing.</span></p><p><strong>Computation time</strong><span>Elapsed backend algorithm time, measured for each run.</span></p></div></section>
    </>}
    <div className="print-footer">ForgeIQ · Scheduling report · Dataset snapshot version {current.dataset_version} · Run {current.id}</div>
  </div>;
}
