import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Results from '../src/pages/Results';
import type { ApiCollections, AlgorithmResult, ScheduleRun } from '../src/types';

vi.mock('../src/components/GanttChart', () => ({ default: () => null }));
const empty: ApiCollections = { jobs: [], machines: [], operations: [], schedules: [] };
const result = (name: AlgorithmResult['algorithm_name']): AlgorithmResult => ({ algorithm_name: name, scenario: 'parallel_machine', feasible: true, scheduled_operations: [], metrics: { makespan: 20 }, computation_time_ms: 0.4 });
function makeRun(id: string, recommended: ScheduleRun['recommended_algorithm_name'], selected: ScheduleRun['selected_algorithm_name'] = null, names: AlgorithmResult['algorithm_name'][] = ['FCFS', 'SPT']): ScheduleRun {
  return { id, scenario: 'parallel_machine', objective: 'makespan', secondary_objectives: [], hard_due_dates: false, dataset_version: 1, current_dataset_version: 1, is_stale: false, created_at: '2032-05-11T08:00:00Z', selected_algorithm_name: selected, recommended_algorithm_name: recommended, recommendation_reason: 'Measured comparison', recommendation_details: {}, results: names.map(result), input_snapshot: { jobs: [], machines: [], operations: [] } };
}

describe('saved schedule results', () => {
  it('uses the next saved run selection rather than a stale algorithm selected on the previous run', () => {
    const runA = makeRun('run-a', 'FCFS');
    const runB = makeRun('run-b', 'FCFS', 'EDD', ['FCFS', 'EDD', 'SPT']);
    const props = { run: runA, allRuns: [runA, runB], data: { ...empty, schedules: [runA, runB] }, initialView: 'gantt' as const, onLoadSchedule: vi.fn(async () => {}) };
    const { rerender } = render(<Results {...props}/>);
    const select = screen.getByLabelText('Selected schedule') as HTMLSelectElement;
    expect(select.value).toBe('FCFS');
    fireEvent.change(select, { target: { value: 'SPT' } });
    expect(select.value).toBe('SPT');
    rerender(<Results {...props} run={runB}/>);
    expect((screen.getByLabelText('Selected schedule') as HTMLSelectElement).value).toBe('EDD');
  });
});
