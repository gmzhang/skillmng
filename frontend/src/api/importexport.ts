// 导入导出与审计 API。
import { http } from "./client";

export interface AuditLog {
  id: number;
  user_id: string;
  skill_id?: number | null;
  version_id?: number | null;
  action: string;
  summary?: string | null;
  ip?: string | null;
  llm_job_id?: number | null;
  git_commit_sha?: string | null;
  created_at: string;
}

export async function listAuditLogs(params?: { action?: string; skill_id?: number }) {
  const { data } = await http.get<AuditLog[]>("/audit-logs", { params });
  return data;
}

export async function importZip(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const { data } = await http.post<{ skill_id: number; name: string; file_count: number }>(
    "/import/zip",
    fd,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return data;
}

export async function importSkillMd(content: string) {
  const { data } = await http.post<{ skill_id: number; name: string; file_count: number }>(
    "/import/skill-md",
    { content },
  );
  return data;
}

export function exportSkillUrl(skillId: number): string {
  return `/api/skills/${skillId}/export.zip`;
}

export function exportSkillVersionUrl(skillId: number, versionId: number): string {
  return `/api/skills/${skillId}/versions/${versionId}/export.zip`;
}
