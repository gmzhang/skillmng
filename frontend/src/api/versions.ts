// 版本与 diff API。
import { http } from "./client";
import type { SkillVersion, VersionDiffFile } from "@/types";

export async function listVersions(skillId: number) {
  const { data } = await http.get<SkillVersion[]>(
    `/skills/${skillId}/versions`,
  );
  return data;
}

export async function publishVersion(
  skillId: number,
  body: { version: string; summary: string; change_type: "patch" | "minor" | "major"; create_tag?: boolean },
) {
  const { data } = await http.post<SkillVersion>(
    `/skills/${skillId}/versions`,
    body,
  );
  return data;
}

export async function restoreVersion(
  skillId: number,
  versionId: number,
  body: { new_version: string; summary?: string },
) {
  const { data } = await http.post<SkillVersion>(
    `/skills/${skillId}/versions/${versionId}/restore`,
    body,
  );
  return data;
}

export async function listVersionFiles(skillId: number, versionId: number) {
  const { data } = await http.get<{ path: string }[]>(
    `/skills/${skillId}/versions/${versionId}/files`,
  );
  return data;
}

export async function diffVersions(
  skillId: number,
  fromVersionId: number,
  toVersionId: number,
) {
  const { data } = await http.get<{
    from_version_id: number;
    to_version_id: number;
    files: VersionDiffFile[];
  }>(`/skills/${skillId}/diff`, {
    params: { from_version_id: fromVersionId, to_version_id: toVersionId },
  });
  return data;
}
