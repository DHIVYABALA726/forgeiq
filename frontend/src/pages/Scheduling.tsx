import { useState } from 'react';
import { ArrowRight, CircleHelp, Play, ShieldCheck } from 'lucide-react';
import type { AlgorithmName, ApiCollections, Objective, Scenario, ScheduleRun } from '../types';
import { generateSchedules } from '../services/api';

const objectives: { id: Objective; label: string; direction: string }[] = [
  { id: 'makespan', label: 'Minimize makespan', direction: 'Minimize' },
  { id: 'total_tardiness', label: 'Minimize total tardiness', direction: 'Minimize' },
  { id: 'maximum_lateness', label: 'Minimize maximum lateness', direction: 'Minimize' },
  { id: 'tardy_jobs', label: 'Minimize number of tardy jobs', direction: 'Minimize' },
  { id: 'machine_utilization', label: 'Improve machine utilization', direction: 'Maximize' },
  { id: 'average_waiting', label: 'Reduce average job waiting time', direction: 'Minimize' },
];
const dispatchAlgorithms: { id: AlgorithmName; description: string }[] = [
  { id: 'FCFS', description: 'Queue-arrival / release order' }, { id: 'SPT', description: 'Shortest ready operation first' },
  { id: 'EDD', description: 'Earliest due date first' }, { id: 'Priority-Based', description: 'Critical → High → Medium → Low' },
  { id: 'LPT', description: 'Longest ready operation first' },
];
const scenarioLabels: Record<Scenario, string> = { parallel_machine: 'Single-Operation / Parallel-Machine', job_shop: 'Job Shop', permutation_flow_shop: 'Permutation Flow Shop (NEH)' };

export default function Scheduling({ data, onGenerated, onNavigate }: { data: ApiCollections; onGenerated: (run: ScheduleRun) => void; onNavigate: () => void }) {
  const [scenario, setScenario] = useState<Scenario>('job_shop');
  const [algorithms, setAlgorithms] = useState<AlgorithmName[]>(['FCFS', 'SPT', 'EDD', 'Priority-Based', 'LPT']);
  const [objective, setObjective] = useState<Objective>('makespan');
  const [secondary, setSecondary] = useState<Objective[]>([]);
  const [hardDueDates, setHardDueDates] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const usable = data.jobs.length > 0 && data.machines.length > 0 && data.operations.length > 0;
  const jobsReady = data.jobs.every(job => data.operations.some(operation => operation.job_id === job.id));
  const needsParallel = scenario === 'parallel_machine' && data.jobs.some(job => data.operations.filter(operation => operation.job_id === job.id).length !== 1);

  function toggle<T extends string>(values: T[], value: T, setter: (next: T[]) => void) {
    setter(values.includes(value) ? values.filter(x => x !== value) : [...values, value]);
  }
  async function run() {
    setBusy(true); setError(''); setNotice('');
    try {
      const run = await generateSchedules({ scenario, algorithms, objective, secondary_objectives: secondary, hard_due_dates: hardDueDates });
      onGenerated(run);
      const feasible = run.results.filter(result => result.feasible).length;
      setNotice(`${run.results.length} algorithm${run.results.length === 1 ? '' : 's'} evaluated; ${feasible} feasible schedule${feasible === 1 ? '' : 's'} saved.`);
      onNavigate();
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Schedule generation failed. Review the entered constraints and try again.'); }
    finally { setBusy(false); }
  }
  return <div className="page-shell">
    <header className="page-heading"><div><div className="eyebrow">CONFIGURATION</div><h1>Scheduling setup</h1><p className="page-subtitle">Run selected rules against the same validated manufacturing dataset.</p></div><div className="run-meta"><ShieldCheck size={16} /> Results use your current entered inputs</div></header>
    {error && <div className="alert alert-error" role="alert"><strong>Schedule not generated.</strong> {error}</div>}{notice && <div className="alert alert-success" role="status">{notice}</div>}
    {!usable && <div className="alert alert-warning"><strong>Dataset incomplete.</strong> Add at least one job, machine and operation before running a schedule. <button className="inline-link" onClick={() => { window.dispatchEvent(new CustomEvent('forgeiq:navigate-data')); }}>Open manufacturing data</button></div>}
    {!jobsReady && usable && <div className="alert alert-warning"><strong>Operations missing.</strong> Each job needs at least one operation before scheduling.</div>}
    <div className="config-layout">
      <section className="config-panel"><div className="panel-heading"><span className="step-index">01</span><div><h2>Scheduling scenario</h2><p>Scenario selection defines operation and machine constraints.</p></div></div>
        <label className="field-label" htmlFor="scenario">Production flow</label><select id="scenario" className="control" value={scenario} onChange={e => { const next = e.target.value as Scenario; setScenario(next); setAlgorithms(previous => next === 'permutation_flow_shop' ? ['NEH'] : previous.filter(item => item !== 'NEH').length ? previous.filter(item => item !== 'NEH') : dispatchAlgorithms.map(item => item.id)); }}><option value="parallel_machine">Single-Operation / Parallel-Machine</option><option value="job_shop">Job Shop — ordered operations</option><option value="permutation_flow_shop">Permutation Flow Shop — NEH only</option></select>
        <p className="help-text"><CircleHelp size={14} /> {scenario === 'parallel_machine' ? 'Every job must have exactly one operation; each operation can select among eligible parallel machines.' : scenario === 'job_shop' ? 'Each job follows its own ordered operation sequence. Machine eligibility and precedence are respected.' : 'Each job must share the same fixed ordered machine sequence. NEH is a heuristic, not a general job-shop solver.'}</p>
        {needsParallel && <p className="field-error">Current dataset includes a multi-operation job; choose Job Shop instead.</p>}
      </section>
      <section className="config-panel"><div className="panel-heading"><span className="step-index">02</span><div><h2>Algorithms to compare</h2><p>Every selected rule is run on the same data.</p></div></div>
        {scenario === 'permutation_flow_shop' ? <label className="algorithm-option"><input type="checkbox" checked={algorithms.includes('NEH')} onChange={() => toggle(algorithms, 'NEH', setAlgorithms)} /><span className="checkmark"/><span className="algorithm-name">NEH<small>Permutation-flow-shop heuristic only</small></span><span className="algorithm-badge">SPECIALIZED</span></label> : dispatchAlgorithms.map(item => <label className="algorithm-option" key={item.id}><input type="checkbox" checked={algorithms.includes(item.id)} onChange={() => toggle(algorithms, item.id, setAlgorithms)} /><span className="checkmark"/><span className="algorithm-name">{item.id}<small>{item.description}</small></span><span className="algorithm-badge">{scenario === 'job_shop' ? 'JOB SHOP' : 'PARALLEL'}</span></label>)}
        <div className="algorithm-note">{scenario === 'job_shop' ? 'Dispatching heuristics guide precedence-ready operations; they do not prove global optimality.' : scenario === 'parallel_machine' ? 'Rules apply to each job’s single eligible-machine operation.' : 'NEH is intentionally isolated to the permutation-flow-shop scenario.'}</div>
      </section>
      <section className="config-panel objective-panel"><div className="panel-heading"><span className="step-index">03</span><div><h2>Optimization objective</h2><p>Recommendations rank only feasible results.</p></div></div>
        <label className="field-label" htmlFor="objective">Primary objective</label><select className="control" id="objective" value={objective} onChange={e => { const next = e.target.value as Objective; setObjective(next); setSecondary(previous => previous.filter(item => item !== next)); }}>{objectives.map(item => <option value={item.id} key={item.id}>{item.label} · {item.direction}</option>)}</select>
        <div className="secondary-heading"><strong>Secondary objectives</strong><span>Optional · used as tie-breakers</span></div><div className="secondary-grid">{objectives.filter(item => item.id !== objective).map(item => <label className="secondary-option" key={item.id}><input type="checkbox" checked={secondary.includes(item.id)} onChange={() => toggle(secondary, item.id, setSecondary)} />{item.label.replace(/^(Minimize|Improve|Reduce) /, '')}</label>)}</div>
      </section>
      <section className="config-panel constraints-panel"><div className="panel-heading"><span className="step-index">04</span><div><h2>Constraints</h2><p>Due dates are evaluation criteria by default.</p></div></div><label className="toggle-row"><input type="checkbox" checked={hardDueDates} onChange={e => setHardDueDates(e.target.checked)} /><span className="toggle-switch"/><span><strong>Treat due dates as hard constraints</strong><small>Any job finishing late makes that algorithm infeasible.</small></span></label><div className="constraint-footnote">All runs respect release times, machine windows, operation precedence and machine capacity.</div></section>
    </div>
    <footer className="generate-bar"><div><strong>{algorithms.length} algorithm{algorithms.length === 1 ? '' : 's'} selected</strong><span>{scenarioLabels[scenario]} · {objectives.find(x => x.id === objective)?.label}</span></div><button className="button button-primary button-run" onClick={run} disabled={busy || !usable || !jobsReady || algorithms.length === 0 || needsParallel}>{busy ? <><span className="spinner"/> Generating schedules…</> : <><Play size={15} fill="currentColor"/> Generate and Compare Schedules <ArrowRight size={15}/></>}</button></footer>
  </div>;
}
