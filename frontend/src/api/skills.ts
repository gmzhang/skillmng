// Skill 相关 API。
import { http } from "./client";
import type {
  Skill,
  SkillListItem,
  SkillCreateBody,
  SkillUpdateBody,
} from "@/types";

export async function listSkills(params?: { q?: string; status?: string }) {
  const { data } = await http.get<SkillListItem[]>("/skills", { params });
  return data;
}

export async function createSkill(body: SkillCreateBody) {
  const { data } = await http.post<Skill>("/skills", body);
  return data;
}

export async function getSkill(id: number) {
  const { data } = await http.get<Skill>(`/skills/${id}`);
  return data;
}

export async function updateSkill(id: number, body: SkillUpdateBody) {
  const { data } = await http.patch<Skill>(`/skills/${id}`, body);
  return data;
}

export async function deleteSkill(id: number) {
  await http.delete(`/skills/${id}`);
}

export async function bindRepository(id: number, git_remote_url: string) {
  const { data } = await http.patch<Skill>(`/skills/${id}/repository`, {
    git_remote_url,
  });
  return data;
}

export async function createRepository(id: number) {
  const { data } = await http.post<Skill>(`/skills/${id}/repository`);
  return data;
}
