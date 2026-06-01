// 公共类型定义。
export interface Me {
  user_id: string;
  user_name?: string | null;
  user_email?: string | null;
}

export interface ApiError {
  code: string;
  message: string;
}

// ==== Skill ====
export interface Skill {
  id: number;
  user_id: string;
  name: string;
  description: string;
  argument_hint?: string | null;
  disable_model_invocation: boolean;
  user_invocable: boolean;
  status: "draft" | "published" | "archived" | "deleted";
  current_version_id?: number | null;
  current_version?: string | null;
  published_commit_sha?: string | null;
  published_tag?: string | null;
  draft_status?: "none" | "local_only" | "remote";
  git_remote_url?: string | null;
  git_repo_name?: string | null;
  git_project_id?: number | null;
  git_namespace_id?: number | null;
  git_path_with_namespace?: string | null;
  git_http_url?: string | null;
  git_ssh_url?: string | null;
  git_web_url?: string | null;
  default_branch?: string | null;
  draft_branch?: string | null;
  draft_commit_sha?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SkillListItem {
  id: number;
  name: string;
  description: string;
  status: Skill["status"];
  current_version_id?: number | null;
  current_version?: string | null;
  published_tag?: string | null;
  draft_branch?: string | null;
  draft_commit_sha?: string | null;
  draft_status?: "none" | "local_only" | "remote";
  published_commit_sha?: string | null;
  git_bound: boolean;
  git_project_id?: number | null;
  git_web_url?: string | null;
  git_ssh_url?: string | null;
  validation_status: "valid" | "warning" | "error";
  updated_at: string;
  file_count: number;
  last_commit_short?: string | null;
}

export interface SkillCreateBody {
  name: string;
  description: string;
  argument_hint?: string | null;
  disable_model_invocation?: boolean;
  user_invocable?: boolean;
  initial_body?: string | null;
}

export interface SkillUpdateBody {
  description?: string;
  argument_hint?: string | null;
  disable_model_invocation?: boolean;
  user_invocable?: boolean;
  status?: Skill["status"];
}

// ==== File ====
export interface SkillFile {
  path: string;
  content_type: "text" | "binary";
  size: number;
  sha256: string;
  updated_at: string;
}

export interface SkillFileContent {
  path: string;
  content: string;
}

// ==== Version (M3) ====
export interface SkillVersion {
  id: number;
  skill_id: number;
  version: string;
  change_type: "patch" | "minor" | "major";
  summary: string;
  git_commit_sha: string;
  git_tag?: string | null;
  tag_url?: string | null;
  commit_url?: string | null;
  git_pushed?: boolean | null;
  push_error?: string | null;
  author_name?: string | null;
  author_email?: string | null;
  created_at: string;
}

export interface VersionDiffFile {
  path: string;
  change: "added" | "removed" | "modified";
  before: string | null;
  after: string | null;
}

// ==== LLM (M4) ====
export interface LLMJob {
  id: number;
  skill_id?: number | null;
  skill_name?: string | null;
  job_type: "create" | "update" | "review";
  status: "queued" | "running" | "succeeded" | "failed" | "canceled";
  model: string;
  input_summary: string;
  output_summary?: string | null;
  error_message?: string | null;
  applied_at?: string | null;
  patches?: { path: string; change: string; content?: string }[];
  tests?: string[];
  risks?: string[];
  created_at: string;
  updated_at: string;
}

// ==== Validation (PRD2 §2.4) ====
export interface ValidationStatus {
  status: "valid" | "warning" | "error";
  errors: string[];
  warnings: string[];
}

// ==== Workbench stats (PRD2 §2.1) ====
export interface WorkbenchStats {
  skill_total: number;
  skill_draft: number;
  skill_published: number;
  skill_archived: number;
  skill_deleted: number;
  version_total: number;
  llm_total: number;
  llm_running: number;
  recent_skills: {
    id: number;
    name: string;
    status: Skill["status"];
    current_version?: string | null;
    updated_at: string;
  }[];
  recent_versions: {
    id: number;
    skill_id: number;
    skill_name?: string | null;
    version: string;
    git_commit_sha: string;
    created_at: string;
  }[];
  recent_audits: {
    id: number;
    action: string;
    skill_id?: number | null;
    version_id?: number | null;
    summary?: string | null;
    created_at: string;
  }[];
}

// ==== Settings (PRD2 §4.4) ====
export interface AppSettings {
  app_env: string;
  git: {
    antcode_api_base_url: string;
    antcode_group_url: string;
    antcode_namespace_id: number;
    antcode_token_status: "configured" | "missing";
    antcode_token_mask: string;
    default_branch: string;
    draft_branch_prefix: string;
    delete_draft_branch_after_publish: boolean;
    ssh_key_path: string;
    repo_url_template: string;
    auto_create_repository: boolean;
    proxy: { https_proxy: string; http_proxy: string; all_proxy: string };
  };
  llm: {
    provider: string;
    base_url: string;
    model: string;
    timeout_ms: number;
    token_configured: boolean;
    api_style: string;
  };
  limits: {
    max_upload_bytes: number;
    max_file_bytes: number;
    max_asset_file_bytes: number;
    max_files_per_skill: number;
  };
  spec: {
    enabled_rules: string[];
    skill_md_rules: string[];
    path_rules: string[];
  };
}

export interface TestResult {
  ok: boolean;
  message: string;
  detail?: Record<string, unknown> | null;
}

// ==== Audit (PRD2 §2.8) ====
export interface AuditLog {
  id: number;
  user_id: string;
  skill_id?: number | null;
  skill_name?: string | null;
  version_id?: number | null;
  version?: string | null;
  action: string;
  action_label?: string | null;
  summary?: string | null;
  ip?: string | null;
  llm_job_id?: number | null;
  git_commit_sha?: string | null;
  commit_short?: string | null;
  metadata_json?: string | null;
  created_at: string;
}
