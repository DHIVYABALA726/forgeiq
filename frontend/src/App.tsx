import { Suspense, lazy, useCallback, useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import { loadCollections, loadSample, removeSample } from './services/api';
import type { ApiCollections, ScheduleRun, Section } from './types';
import { getSchedule } from './services/api';

const Workspace = lazy(() => import('./pages/Workspace'));
const Scheduling = lazy(() => import('./pages/Scheduling'));
const ManufacturingData = lazy(() => import('./pages/ManufacturingData'));
const Results = lazy(() => import('./pages/Results'));

const empty: ApiCollections = { jobs: [], machines: [], operations: [], schedules: [] };

export default function App() {
  const [data, setData] = useState<ApiCollections>(empty);
  const [run, setRun] = useState<ScheduleRun | null>(null);
  const [section, setSection] = useState<Section>('workspace');
  const [online, setOnline] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState('');
  const [globalError, setGlobalError] = useState('');

  const reload = useCallback(async () => {
    try {
      const next = await loadCollections();
      setData(next); setOnline(true); setGlobalError('');
      if (next.schedules.length) {
        try { setRun(await getSchedule(next.schedules[0].id)); }
        catch { setRun(next.schedules[0]); }
      } else setRun(null);
    } catch (error) {
      setOnline(false); setGlobalError(error instanceof Error ? error.message : 'Could not load the manufacturing workspace.');
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void reload(); }, [reload]);
  useEffect(() => {
    const dataNav = () => setSection('data');
    const schedulingNav = () => setSection('scheduling');
    const refresh = () => { setLoading(true); void reload(); };
    window.addEventListener('forgeiq:navigate-data', dataNav);
    window.addEventListener('forgeiq:navigate-scheduling', schedulingNav);
    window.addEventListener('forgeiq:refresh', refresh);
    return () => { window.removeEventListener('forgeiq:navigate-data', dataNav); window.removeEventListener('forgeiq:navigate-scheduling', schedulingNav); window.removeEventListener('forgeiq:refresh', refresh); };
  }, [reload]);

  const handleSampleLoad = async () => {
    setNotice(''); setGlobalError('');
    try { const response = await loadSample(); setNotice(response.message); await reload(); }
    catch (error) { setGlobalError(error instanceof Error ? error.message : 'Sample dataset could not be loaded.'); }
  };
  const handleSampleRemove = async () => {
    if (!window.confirm('Remove only records labelled as sample data? Manually entered records will be kept.')) return;
    setNotice(''); setGlobalError('');
    try { const response = await removeSample(); setNotice(response.message); await reload(); }
    catch (error) { setGlobalError(error instanceof Error ? error.message : 'Sample dataset could not be removed.'); }
  };
  const onGenerated = (next: ScheduleRun) => { setRun(next); setData(current => ({ ...current, schedules: [next, ...current.schedules.filter(item => item.id !== next.id)] })); };
  const onLoadSchedule = async (id: string) => { try { setRun(await getSchedule(id)); setGlobalError(''); } catch (error) { setGlobalError(error instanceof Error ? error.message : 'The saved schedule could not be loaded.'); } };
  const hasSchedule = Boolean(run || data.schedules.length);
  const staleCount = data.schedules.filter(item => item.is_stale).length;

  return <div className="app-shell">
    <Sidebar active={section} onNavigate={setSection} scheduleAvailable={hasSchedule}/>
    <main className="app-main">
      {notice && <div className="app-toast alert alert-success" role="status">{notice}<button className="toast-close" aria-label="Dismiss message" onClick={() => setNotice('')}>×</button></div>}
      {globalError && <div className="app-toast alert alert-error" role="alert"><span>{globalError}</span><button className="toast-close" aria-label="Dismiss error" onClick={() => setGlobalError('')}>×</button></div>}
      {loading && <div className="loading-screen"><span className="spinner"/> Loading manufacturing data…</div>}
      {!loading && section === 'workspace' && <Suspense fallback={<div className="loading-screen"><span className="spinner"/> Loading workspace…</div>}><Workspace data={data} online={online} staleCount={staleCount} onNavigate={setSection} onLoadSample={handleSampleLoad} onRemoveSample={handleSampleRemove} loading={loading}/></Suspense>}
      {!loading && section === 'data' && <Suspense fallback={<div className="loading-screen"><span className="spinner"/> Loading manufacturing records…</div>}><ManufacturingData data={data} online={online} onChanged={reload} onLoadSample={handleSampleLoad} onRemoveSample={handleSampleRemove}/></Suspense>}
      {!loading && section === 'scheduling' && <Suspense fallback={<div className="loading-screen"><span className="spinner"/> Loading scheduling controls…</div>}><Scheduling data={data} onGenerated={onGenerated} onNavigate={() => setSection('gantt')}/></Suspense>}
      {!loading && ['gantt', 'comparison', 'report'].includes(section) && <Suspense fallback={<div className="loading-screen"><span className="spinner"/> Loading saved results…</div>}><Results key={run?.id || data.schedules[0]?.id || 'no-run'} run={run} allRuns={data.schedules} data={data} initialView={section as 'gantt' | 'comparison' | 'report'} onLoadSchedule={onLoadSchedule}/></Suspense>}
      <footer className="app-footer"><span>ForgeIQ</span><span>Actual schedules · Measured comparisons · Transparent recommendations</span><button onClick={() => void reload()} aria-label="Refresh data">Refresh data</button></footer>
    </main>
  </div>;
}
