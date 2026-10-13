export type Priority = 'Critical' | 'High' | 'Medium' | 'Low';
export type Scenario = 'parallel_machine' | 'job_shop' | 'permutation_flow_shop';
export type Objective = 'makespan' | 'total_tardiness' | 'maximum_lateness' | 'tardy_jobs' | 'machine_utilization' | 'average_waiting';
export type AlgorithmName = 'FCFS' | 'SPT' | 'EDD' | 'Priority-Based' | 'LPT' | 'NEH';

export interface Job {
  id: string; name: string; product_name: string; quantity: number; priority: Priority;
  release_at: string; due_at: string; notes?: string | null; is_sample: boolean;
}
export interface Machine {
  id: string; name: string; machine_type: string; available_from: string; available_until?: string | null;
  is_available: boolean; setup_time_minutes: number; is_sample: boolean;
}
export interface Operation {
  id: string; job_id: string; name: string; sequence: number; eligible_machine_ids: string[];
  processing_time_minutes: number; setup_time_minutes: number; predecessor_id?: string | null; is_sample: boolean;
}
export interface ScheduledOperation {
  operation_id: string; job_id: string; machine_id: string; operation_name: string; sequence: number;
  start_minute: number; end_minute: number; processing_time_minutes: number; setup_time_minutes: number;
  duration_minutes: number; waiting_time_minutes: number; due_minute: number; due_at: string; start_at: string; end_at: string;
}
export interface Metrics {
  makespan?: number | null; total_completion_time?: number | null; total_tardiness?: number | null;
  maximum_lateness?: number | null; tardy_jobs?: number | null; average_waiting?: number | null;
  machine_utilization?: number | null; job_completion_minutes?: Record<string, number>;
  job_lateness_minutes?: Record<string, number>; horizon_start_minute?: number;
  horizon_end_minute?: number; productive_time_minutes?: number; available_machine_time_minutes?: number;
}
export interface AlgorithmResult {
  algorithm_name: AlgorithmName; scenario: Scenario; feasible: boolean; scheduled_operations: ScheduledOperation[];
  metrics: Metrics; objective_value?: number | null; constraint_violations?: string[]; computation_time_ms: number; error_message?: string | null;
}
export interface ScheduleRun {
  id: string; scenario: Scenario; objective: Objective; secondary_objectives: Objective[]; hard_due_dates: boolean;
  dataset_version: number; current_dataset_version: number; is_stale: boolean; created_at: string;
  selected_algorithm_name?: AlgorithmName | null; recommended_algorithm_name?: AlgorithmName | null;
  recommendation_reason?: string | null; recommendation_details?: { scope?: string; ranking?: string[] };
  results: AlgorithmResult[]; input_snapshot?: { jobs: Job[]; machines: Machine[]; operations: Operation[]; scenario?: Scenario; hard_due_dates?: boolean };
}
export type Section = 'workspace' | 'data' | 'scheduling' | 'gantt' | 'comparison' | 'report';
export interface ApiCollections { jobs: Job[]; machines: Machine[]; operations: Operation[]; schedules: ScheduleRun[]; }
