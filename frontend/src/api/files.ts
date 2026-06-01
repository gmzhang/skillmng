// 文件 API。
import { http } from "./client";
import type { SkillFile, SkillFileContent } from "@/types";

export async function listFiles(skillId: number) {
  const { data } = await http.get<SkillFile[]>(`/skills/${skillId}/files`);
  return data;
}

export async function getFileContent(skillId: number, path: string) {
  const { data } = await http.get<SkillFileContent>(
    `/skills/${skillId}/files/content`,
    { params: { path } },
  );
  return data;
}

export async function writeFileContent(
  skillId: number,
  path: string,
  content: string,
) {
  const { data } = await http.put<SkillFile>(
    `/skills/${skillId}/files/content`,
    { path, content },
  );
  return data;
}

export async function deleteFile(skillId: number, path: string) {
  await http.delete(`/skills/${skillId}/files/content`, { params: { path } });
}

export async function uploadFile(skillId: number, path: string, file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const { data } = await http.post<SkillFile>(
    `/skills/${skillId}/files/upload`,
    fd,
    {
      params: { path },
      headers: { "Content-Type": "multipart/form-data" },
    },
  );
  return data;
}
