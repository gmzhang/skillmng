// axios 客户端 — 必须 withCredentials 才能携带 Cookie。
import axios, { AxiosError } from "axios";
import type { ApiError } from "@/types";

export const http = axios.create({
  baseURL: "/api",
  withCredentials: true,
  timeout: 30_000,
});

http.interceptors.response.use(
  (resp) => resp,
  (error: AxiosError<ApiError>) => {
    // 让上层 catch 仍能拿到原 error,只是规范一下消息。
    return Promise.reject(error);
  },
);

export async function fetchMe() {
  const { data } = await http.get("/me");
  return data;
}
