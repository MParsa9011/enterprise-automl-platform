/**
 * TypeScript mirrors of the backend API DTOs.
 *
 * Kept in one place so components and hooks share a single source of truth for
 * the shapes returned by the v1 API.
 */

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Role {
  id: string;
  name: string;
  description: string | null;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  roles: Role[];
  created_at: string;
  updated_at: string;
}

export interface RegisterResponse {
  user: User;
  tokens: Tokens;
}

export interface PageMeta {
  page: number;
  size: number;
  total: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface Page<T> {
  items: T[];
  meta: PageMeta;
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  owner_id: string;
  owner: { id: string; email: string; full_name: string | null };
  created_at: string;
  updated_at: string;
}

export interface ColumnSchema {
  name: string;
  dtype: string;
  inferred_type: string;
  n_missing: number;
  missing_pct: number;
  n_unique: number;
}

export interface DatasetVersion {
  id: string;
  version: number;
  original_filename: string;
  file_type: string;
  size_bytes: number;
  checksum: string;
  n_rows: number;
  n_columns: number;
  columns_schema: ColumnSchema[];
  statistics?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Dataset {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  project_id: string;
  latest_version: number;
  versions?: DatasetVersion[];
  created_at: string;
  updated_at: string;
}

export type TaskType = "classification" | "regression" | "clustering";
export type ExperimentStatus =
  | "draft"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";
export type RunStatus = "pending" | "running" | "completed" | "failed";

export interface Run {
  id: string;
  experiment_id: string;
  algorithm: string;
  status: RunStatus;
  primary_score: number | null;
  metrics: Record<string, number>;
  params: Record<string, unknown>;
  duration_seconds: number | null;
  error_message: string | null;
  figures?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Experiment {
  id: string;
  name: string;
  description: string | null;
  project_id: string;
  dataset_id: string;
  dataset_version: number;
  task_type: TaskType;
  target_column: string | null;
  primary_metric: string;
  algorithms: string[];
  status: ExperimentStatus;
  best_run_id: string | null;
  optimize: boolean;
  n_trials: number;
  cv_folds: number;
  test_size: number;
  error_message: string | null;
  runs?: Run[];
  created_at: string;
  updated_at: string;
}

export type ModelStage = "none" | "staging" | "production" | "archived";

export interface Model {
  id: string;
  name: string;
  slug: string;
  version: number;
  description: string | null;
  project_id: string;
  experiment_id: string | null;
  run_id: string;
  stage: ModelStage;
  algorithm: string;
  task_type: TaskType;
  target_column: string | null;
  primary_metric: string;
  primary_score: number | null;
  metrics: Record<string, number>;
  feature_schema: { name: string; dtype: string }[];
  class_names: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface PredictionItem {
  prediction: unknown;
  probabilities: Record<string, number> | null;
}

export interface PredictionResponse {
  model_id: string;
  model_version: number;
  task_type: string;
  predictions: PredictionItem[];
}

export interface Notification {
  id: string;
  type: "info" | "success" | "warning" | "error";
  title: string;
  message: string;
  link: string | null;
  read_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
  request_id?: string;
}
