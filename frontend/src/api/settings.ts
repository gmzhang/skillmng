// Settings / 工作台统计 / 校验状态 API。
import { http } from "./client";
import type {
  AppSettings,
  TestResult,
  WorkbenchStats,
  ValidationStatus,
} from "@/types";

export async function fetchSettings() {
  const { data } = await http.get<AppSettings>("/settings");
  return data;
}

export async function testGit() {
  const { data } = await http.post<TestResult>("/settings/test-git");
  return data;
}

export async function testSSH() {
  const { data } = await http.post<TestResult>("/settings/test-ssh");
  return data;
}

export async function testLLM() {
  const { data } = await http.post<TestResult>("/settings/test-llm");
  return data;
}

export async function reloadSettings() {
  const { data } = await http.post<TestResult>("/settings/reload");
  return data;
}

export async function fetchWorkbenchStats() {
  const { data } = await http.get<WorkbenchStats>("/workbench/stats");
  return data;
}

export async function fetchValidation(skillId: number) {
  const { data } = await http.get<ValidationStatus>(
    `/skills/${skillId}/validation`,
  );
  return data;
}

export async function fixSkillMd(skillId: number) {
  const { data } = await http.post<{
    fixed: boolean;
    before: string;
    after: string;
  }>(`/skills/${skillId}/skill-md/fix`);
  return data;
}
