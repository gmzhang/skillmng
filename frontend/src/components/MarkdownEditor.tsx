import Editor from "@monaco-editor/react";
import { Spin } from "antd";

interface Props {
  value: string;
  onChange?: (v: string) => void;
  language?: string;
  readOnly?: boolean;
  height?: number | string;
}

const LANG_BY_EXT: Record<string, string> = {
  md: "markdown",
  ts: "typescript",
  tsx: "typescript",
  js: "javascript",
  json: "json",
  yml: "yaml",
  yaml: "yaml",
  py: "python",
  sh: "shell",
};

export function languageOf(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  return LANG_BY_EXT[ext] ?? "plaintext";
}

export default function MarkdownEditor({
  value,
  onChange,
  language = "markdown",
  readOnly = false,
  height = "60vh",
}: Props) {
  return (
    <Editor
      value={value}
      language={language}
      height={height}
      loading={<Spin />}
      onChange={(v) => onChange?.(v ?? "")}
      options={{
        minimap: { enabled: false },
        fontSize: 13,
        wordWrap: "on",
        readOnly,
        scrollBeyondLastLine: false,
      }}
    />
  );
}
