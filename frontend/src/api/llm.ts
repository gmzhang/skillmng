// LLM API。
import { http } from "./client";
import type { LLMJob } from "@/types";

export interface LLMCreateBody {
  skill_name: string;
  description: string;
  goal: string;
  scenario?: string;
  trigger?: string;
  target_agent?: string;
  extra_materials?: string;
  constraints?: string;
  include_scripts?: boolean;
  include_references?: boolean;
}

export interface LLMUpdateBody {
  skill_id: number;
  goal: string;
  target_version?: string | null;
}

export interface LLMJobDetail extends LLMJob {
  output_payload?: Record<string, unknown> | null;
}

export async function submitCreate(body: LLMCreateBody) {
  const { data } = await http.post<LLMJob>("/llm/skill-drafts", body);
  return data;
}

export async function submitUpdate(body: LLMUpdateBody) {
  const { data } = await http.post<LLMJob>("/llm/skill-updates", body);
  return data;
}

export async function listJobs(skill_id?: number) {
  const { data } = await http.get<LLMJob[]>("/llm/jobs", {
    params: skill_id ? { skill_id } : undefined,
  });
  return data;
}

export async function getJob(id: number) {
  const { data } = await http.get<LLMJobDetail>(`/llm/jobs/${id}`);
  return data;
}

export async function cancelJob(id: number) {
  const { data } = await http.post<LLMJob>(`/llm/jobs/${id}/cancel`);
  return data;
}

export async function applyJob(id: number) {
  const { data } = await http.post<{
    skill_id?: number;
    applied_paths?: string[];
    change_type?: string;
  }>(`/llm/jobs/${id}/apply`);
  return data;
}
