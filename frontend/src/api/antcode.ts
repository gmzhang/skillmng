// AntCode 工作流 API (PRD2 §4.5)。
import { http } from "./client";
import type { Skill, SkillVersion } from "@/types";

export interface DraftCommitOut {
  branch: string;
  commit_sha: string | null;
  changed: boolean;
}

export interface DraftDiffEntry {
  path: string;
  change: "added" | "modified" | "removed";
  before: string | null;
  after: string | null;
}

export interface DraftDiffOut {
  draft_branch: string | null;
  files: DraftDiffEntry[];
}

export interface PatchDiffOut {
  job_id: number;
  files: DraftDiffEntry[];
  already_applied: boolean;
}

export async function createRepository(skillId: number) {
  const { data } = await http.post<Skill>(`/skills/${skillId}/repository/create`);
  return data;
}

export async function commitDraft(skillId: number, summary?: string) {
  const { data } = await http.post<DraftCommitOut>(
    `/skills/${skillId}/drafts/commit`,
    { summary: summary ?? "save draft" },
  );
  return data;
}

export async function getDraftDiff(skillId: number) {
  const { data } = await http.get<DraftDiffOut>(`/skills/${skillId}/drafts/diff`);
  return data;
}

export async function publishToMaster(
  skillId: number,
  body: { version: string; summary: string; change_type: "patch" | "minor" | "major"; create_tag?: boolean },
) {
  const { data } = await http.post<SkillVersion>(
    `/skills/${skillId}/publish`,
    body,
  );
  return data;
}

export async function syncRepository(skillId: number) {
  const { data } = await http.post(`/skills/${skillId}/repository/sync`);
  return data;
}

export async function getLLMPatchDiff(jobId: number) {
  const { data } = await http.get<PatchDiffOut>(`/llm/jobs/${jobId}/patch-diff`);
  return data;
}
