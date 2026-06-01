import { Card, Table, Tag, Typography, Input, Space, Tooltip, App as AntdApp } from "antd";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import type { ColumnsType } from "antd/es/table";
import { listAuditLogs } from "@/api/importexport";
import type { AuditLog } from "@/types";

const ACTION_COLOR: Record<string, string> = {
  "skill.create": "blue",
  "skill.update": "gold",
  "skill.delete": "red",
  "skill.file.write": "geekblue",
  "skill.file.upload": "geekblue",
  "skill.file.delete": "volcano",
  "skill.version.publish": "green",
  "skill.version.restore": "cyan",
  "skill.import.zip": "purple",
  "skill.import.md": "purple",
  "skill.repository.bind": "default",
  "skill.repository.create": "default",
  "skill.repository.sync": "default",
  "skill.draft.commit": "geekblue",
  "skill.skill_md.fix": "gold",
  "settings.antcode.test": "default",
  "settings.llm.test": "default",
  "llm.create.submit": "orange",
  "llm.create.apply": "orange",
  "llm.update.submit": "orange",
  "llm.update.apply": "orange",
  "llm.job.cancel": "default",
};

function parseMetadata(json?: string | null): Record<string, unknown> | null {
  if (!json) return null;
  try {
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export default function AuditLogs() {
  const [actionFilter, setActionFilter] = useState("");
  const [skillFilter, setSkillFilter] = useState<string>("");
  const { message } = AntdApp.useApp();

  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", actionFilter, skillFilter],
    queryFn: () =>
      listAuditLogs({
        action: actionFilter || undefined,
        skill_id: skillFilter ? Number(skillFilter) : undefined,
      }),
  });

  const copySha = async (sha: string) => {
    try {
      await navigator.clipboard.writeText(sha);
      message.success("已复制完整 SHA");
    } catch {
      message.error("复制失败");
    }
  };

  const columns: ColumnsType<AuditLog> = [
    {
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 170,
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: "操作",
      dataIndex: "action",
      key: "action",
      width: 220,
      render: (a: string, row) => (
        <Tooltip title={a}>
          <Tag color={ACTION_COLOR[a] ?? "default"}>{row.action_label ?? a}</Tag>
        </Tooltip>
      ),
    },
    {
      title: "Skill",
      dataIndex: "skill_id",
      key: "skill_id",
      width: 180,
      render: (id: number | null, row) =>
        id ? (
          <Link to={`/skills/${id}`}>{row.skill_name ?? `#${id}`}</Link>
        ) : (
          "-"
        ),
    },
    {
      title: "版本",
      dataIndex: "version_id",
      key: "version_id",
      width: 120,
      render: (vid: number | null, row) =>
        vid ? (
          <Link to={`/skills/${row.skill_id}/versions`}>
            {row.version ? `v${row.version}` : `#${vid}`}
          </Link>
        ) : (
          "-"
        ),
    },
    {
      title: "LLM Job",
      dataIndex: "llm_job_id",
      key: "llm_job_id",
      width: 100,
      render: (id?: number | null) =>
        id ? <Link to={`/llm-jobs?id=${id}`}>#{id}</Link> : "-",
    },
    {
      title: "摘要",
      dataIndex: "summary",
      key: "summary",
      ellipsis: { showTitle: false },
      render: (s?: string | null) => (
        <Tooltip title={s ?? ""}>
          <span>{s ?? "-"}</span>
        </Tooltip>
      ),
    },
    {
      title: "Commit",
      dataIndex: "commit_short",
      key: "commit_short",
      width: 130,
      render: (s?: string | null, row?: AuditLog) => {
        if (!s || !row) return "-";
        const meta = parseMetadata(row.metadata_json);
        const commitUrl = meta?.commit_url as string | undefined;
        if (commitUrl) {
          return (
            <Tooltip title="点击打开 AntCode commit 页面">
              <a href={commitUrl} target="_blank" rel="noopener noreferrer">
                <code>{s}</code>
              </a>
            </Tooltip>
          );
        }
        return (
          <Tooltip title="点击复制完整 SHA">
            <code
              className="cursor-pointer"
              onClick={() => row.git_commit_sha && copySha(row.git_commit_sha)}
            >
              {s}
            </code>
          </Tooltip>
        );
      },
    },
    {
      title: "Tag",
      key: "tag",
      width: 100,
      render: (_: unknown, row: AuditLog) => {
        const meta = parseMetadata(row.metadata_json);
        const tag = meta?.git_tag as string | undefined;
        const tagUrl = meta?.tag_url as string | undefined;
        if (!tag) return "-";
        if (tagUrl) {
          return (
            <a href={tagUrl} target="_blank" rel="noopener noreferrer">
              <Tag color="green">{tag}</Tag>
            </a>
          );
        }
        return <Tag color="green">{tag}</Tag>;
      },
    },
    { title: "IP", dataIndex: "ip", key: "ip", width: 140 },
  ];

  return (
    <Card
      title={
        <div className="flex items-center justify-between">
          <Typography.Title level={4} className="!m-0">
            审计日志
          </Typography.Title>
          <Space>
            <Input.Search
              placeholder="按 action 过滤(例如 skill.version.publish)"
              allowClear
              onSearch={setActionFilter}
              style={{ width: 280 }}
            />
            <Input.Search
              placeholder="按 Skill ID 过滤"
              allowClear
              onSearch={setSkillFilter}
              style={{ width: 160 }}
            />
          </Space>
        </div>
      }
    >
      <Table
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={data ?? []}
        pagination={{ pageSize: 20 }}
        scroll={{ x: 1200 }}
      />
    </Card>
  );
}
