export type Role = 'user' | 'admin' | 'data_scientist'
export type Source = 'knn' | 'baseline' | 'popular'

export type User = { id: number; username: string; role: Role; n_ratings: number }
export type TokenOut = { access_token: string; token_type: string; user: User }

export type Movie = {
  id: number
  title: string
  year: number | null
  genres: string[]
  avg_rating_train?: number | null
  n_ratings_train?: number
  my_rating?: number | null
  popularity_score?: number
  release_date?: string | null
  imdb_url?: string | null
}
export type Page<T> = { items: T[]; total: number; page: number; page_size: number }

export type Breakdown = { mu: number; b_user: number; b_item: number; neighbor_term: number; clipped: boolean }
export type Neighbor = { label: string; similarity: number; rating: number; common_items: number }
export type RecItem = {
  movie: Movie
  predicted_rating: number
  source: Source
  n_neighbors: number
  breakdown: Breakdown | null
  neighbors: Neighbor[]
}
export type Recommendations = {
  model_version: string
  profile_size: number
  n_candidates: number
  source_summary: Record<Source, number>
  min_item_ratings: number
  latency_ms: number
  cached: boolean
  items: RecItem[]
  message: string | null
  ml_user_id?: number
}
export type Prediction = Omit<Recommendations, 'items'> & { item: RecItem | null }

export type HistoryItem = { rating: number; updated_at: string; movie: Movie }

export type AdminStatus = {
  users: { app: number; movielens: number }
  movies: { total: number; hidden: number }
  ratings: { app: number; movielens: number }
  model: { loaded: boolean; version: string | null; active_in_db: string | null; loaded_at: string | null; min_item_ratings: number | null }
  recommendations: { requests: number; p50_ms: number | null; p95_ms: number | null; fallback_rate: number | null }
  training_running: boolean
}
export type AdminUser = { id: number; username: string; role: Role; is_active: boolean; created_at: string }
export type AdminMovie = Movie & { is_hidden: boolean }

export type Check = { name: string; passed: boolean; severity: string; detail: unknown }
export type DataReport = {
  ok: boolean
  checks: Check[]
  cleaning: { duplicate_rows_dropped: number; rows_after_cleaning: number }
  generated_at: string
  source: { name: string; url: string; zip_sha256: string; checksum_verified: boolean }
  stats: {
    n_users: number
    n_items_catalog: number
    n_ratings: number
    sparsity: number
    rating_mean: number
    rating_distribution: Record<string, number>
    ratings_per_user: Record<string, number>
    ratings_per_item: Record<string, number>
    items_with_lt_5_ratings: number
    genre_counts: Record<string, number>
    timestamp_range_utc: string[]
  }
}
export type SplitManifest = {
  seed: number
  strategy: string
  fractions: Record<string, number>
  rounding: string
  split_hash: string
  summary: Record<string, unknown> & { rows: Record<string, number> }
}

export type TrainConfig = {
  k: number
  min_k: number
  reg_u: number
  reg_i: number
  n_epochs: number
  shrinkage: number
  min_support: number
  min_item_ratings: number
}
export type TrainingJob = {
  id: number
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  config: { knn: { k: number; min_k: number }; baseline: { reg_u: number; reg_i: number; n_epochs: number }; similarity: { shrinkage: number; min_support: number }; serving: { min_item_ratings: number } }
  model_version_id: number | null
  started_at: string
  finished_at: string | null
  log?: string
}
export type ModelVersion = {
  id: number
  version: string
  algorithm: string
  is_active: boolean
  includes_app_ratings: boolean
  created_at: string
  data_hash: string | null
  split_hash: string | null
  config: { params: Record<string, number | string>; serving: Record<string, number> }
  metrics_val: Record<string, number> | null
  has_test_metrics: boolean
}

export type CompareRow = { model: string; label: string; split: 'validation' | 'test'; min_item_ratings: number } & Record<string, number | string>
export type Comparison = { config_hash: string; split_hash: string; config: { serving: { min_item_ratings: number } }; rows: CompareRow[] }
export type GroupRow = { group: string; n: number } & Record<string, number | string>
export type ErrorAnalysis = {
  by_user_activity: GroupRow[]
  by_item_popularity: GroupRow[]
  by_true_rating: GroupRow[]
  by_n_neighbors: GroupRow[]
  worst_10: { user_id: number; movie: string; rating: number; est: number; source: string; n_neighbors: number; user_train_n: number; item_train_n: number }[]
}
export type TuningRow = Record<string, number | null>
