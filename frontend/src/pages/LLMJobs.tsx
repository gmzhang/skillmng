import {
  Card,
  Table,
  Tag,
  Typography,
  Button,
  Drawer,
  Descriptions,
  Space,
  Modal,
  App as AntdApp,
  Select,
  Input,
  Tooltip,
} from "antd";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { ColumnsType } from "antd/es/table";
import { DiffEditor } from "@monaco-editor/react";
import { listJobs, getJob, applyJob, cancelJob } from "@/api/llm";
import { getLLMPatchDiff, type DraftDiffEntry } from "@/api/antcode";
import { languageOf } from "@/components/MarkdownEditor";
import type { LLMJob } from "@/types";

const STATUS_COLOR: Record<string, string> = {
  queued: "blue",
  running: "geekblue",
  succeeded: "green",
  failed: "red",
  canceled: "default",
};
const STATUS_ZH: Record<string, string> = {
  queued: "排队中",
  running: "执行中",
  succeeded: "成功",
  failed: "失败",
  canceled: "已取消",
};
const TYPE_ZH: Record<string, string> = {
  create: "创建",
  update: "更新",
  review: "审阅",
};
const CHANGE_COLOR: Record<string, string> = {
  added: "green",
  removed: "red",
  modified: "gold",
};

export default function LLMJobs() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [applyJobId, setApplyJobId] = useState<number | null>(null);
  const [applyActivePath, setApplyActivePath] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [skillFilter, setSkillFilter] = useState<string>("");
  const { message } = AntdApp.useApp();

  const { data, isLoading } = useQuery({
    queryKey: ["llm-jobs", skillFilter],
    queryFn: () => listJobs(skillFilter ? Number(skillFilter) : undefined),
    refetchInterval: 4000,
  });

  const displayed = useMemo(
    () =>
      (data ?? []).filter(
        (j) =>
          (!statusFilter || j.status === statusFilter) &&
          (!typeFilter || j.job_type === typeFilter),
      ),
    [data, statusFilter, typeFilter],
  );

  const { data: detail } = useQuery({
    queryKey: ["llm-job", selectedId],
    queryFn: () => getJob(selectedId!),
    enabled: selectedId !== null,
  });

  const { data: patchDiff } = useQuery({
    queryKey: ["llm-patch-diff", applyJobId],
    queryFn: () => getLLMPatchDiff(applyJobId!),
    enabled: applyJobId !== null,
  });

  const applyMut = useMutation({
    mutationFn: (id: number) => applyJob(id),
    onSuccess: () => {
      message.success("已落地");
      setApplyJobId(null);
      qc.invalidateQueries({ queryKey: ["llm-jobs"] });
    },
    onError: (e: { response?: { data?: { message?: string } } }) =>
      message.error(e?.response?.data?.message ?? "落地失败"),
  });

  const cancelMut = useMutation({
    mutationFn: (id: number) => cancelJob(id),
    onSuccess: () => {
      message.success("已取消");
      qc.invalidateQueries({ queryKey: ["llm-jobs"] });
    },
    onError: (e: { response?: { data?: { message?: string } } }) =>
      message.error(e?.response?.data?.message ?? "取消失败"),
  });

  const activePatch =
    patchDiff?.files.find((f) => f.path === applyActivePath) ?? patchDiff?.files[0];

  const columns: ColumnsType<LLMJob> = [
    { title: "ID", dataIndex: "id", key: "id", width: 70 },
    {
      title: "类型",
      dataIndex: "job_type",
      key: "job_type",
      width: 80,
      render: (t: string) => <Tag>{TYPE_ZH[t] ?? t}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (s: string) => <Tag color={STATUS_COLOR[s]}>{STATUS_ZH[s] ?? s}</Tag>,
    },
    {
      title: "Skill",
      dataIndex: "skill_id",
      key: "skill",
      width: 200,
      render: (id: number | null, row) =>
        id ? (
          <Link to={`/skills/${id}`}>{row.skill_name ?? `#${id}`}</Link>
        ) : (
          "-"
        ),
    },
    { title: "模型", dataIndex: "model", key: "model", width: 120 },
    {
      title: "输入摘要",
      dataIndex: "input_summary",
      key: "input_summary",
      width: 220,
      ellipsis: { showTitle: false },
      render: (s: string) => (
        <Tooltip title={s} placement="topLeft">
          <span>{s}</span>
        </Tooltip>
      ),
    },
    {
      title: "输出摘要",
      dataIndex: "output_summary",
      key: "output_summary",
      width: 200,
      ellipsis: { showTitle: false },
      render: (s?: string | null) => (
        <Tooltip title={s ?? ""} placement="topLeft">
          <span>{s ?? "-"}</span>
        </Tooltip>
      ),
    },
    {
      title: "已落地",
      dataIndex: "applied_at",
      key: "applied_at",
      width: 170,
      render: (v?: string | null) =>
        v ? (
          <Tooltip title={new Date(v).toLocaleString()}>
            <Tag color="green">已落地</Tag>
          </Tooltip>
        ) : (
          <Tag>未落地</Tag>
        ),
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 170,
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: "操作",
      key: "action",
      width: 240,
      render: (_, row) => (
        <Space>
          <Button size="small" onClick={() => setSelectedId(row.id)}>
            详情
          </Button>
          {row.status === "succeeded" && !row.applied_at && (
            <Button
              size="small"
              type="primary"
              onClick={() => setApplyJobId(row.id)}
            >
              落地
            </Button>
          )}
          {row.status === "succeeded" && row.applied_at && (
            <Button size="small" disabled>
              已落地
            </Button>
          )}
          {(row.status === "queued" || row.status === "running") && (
            <Button size="small" danger onClick={() => cancelMut.mutate(row.id)}>
              取消
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={
        <div className="flex items-center justify-between">
          <Typography.Title level={4} className="!m-0">
            LLM 任务
          </Typography.Title>
          <Space>
            <Select
              placeholder="状态"
              allowClear
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 120 }}
              options={Object.entries(STATUS_ZH).map(([v, l]) => ({
                value: v,
                label: l,
              }))}
            />
            <Select
              placeholder="类型"
              allowClear
              value={typeFilter}
              onChange={setTypeFilter}
              style={{ width: 100 }}
              options={Object.entries(TYPE_ZH).map(([v, l]) => ({
                value: v,
                label: l,
              }))}
            />
            <Input.Search
              placeholder="按 Skill ID"
              allowClear
              onSearch={setSkillFilter}
              style={{ width: 140 }}
            />
          </Space>
        </div>
      }
    >
      {!isLoading && displayed.length === 0 ? (
        <div className="py-12 text-center text-gray-500">
          <Typography.Text type="secondary" className="block mb-2">
            暂无 LLM 任务
          </Typography.Text>
          <Typography.Text type="secondary">
            前往 <Link to="/skills/new">创建 Skill → LLM 辅助</Link> 生成新 Skill,
            或在 <Link to="/skills">Skill 详情 → LLM 辅助更新</Link> 对已有 Skill 进行优化。
          </Typography.Text>
        </div>
      ) : (
        <Table
          rowKey="id"
          loading={isLoading}
          columns={columns}
          dataSource={displayed}
          pagination={{ pageSize: 20 }}
          scroll={{ x: 1300 }}
        />
      )}

      <Drawer
        width={760}
        title={selectedId ? `任务 #${selectedId}` : ""}
        open={selectedId !== null}
        onClose={() => setSelectedId(null)}
      >
        {detail && (
          <Space direction="vertical" className="w-full">
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="状态">
                <Tag color={STATUS_COLOR[detail.status]}>
                  {STATUS_ZH[detail.status] ?? detail.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="类型">
                {TYPE_ZH[detail.job_type] ?? detail.job_type}
              </Descriptions.Item>
              <Descriptions.Item label="模型">{detail.model}</Descriptions.Item>
              <Descriptions.Item label="Skill">
                {detail.skill_id ? (
                  <Link to={`/skills/${detail.skill_id}`}>
                    {detail.skill_name ?? `#${detail.skill_id}`}
                  </Link>
                ) : (
                  "-"
                )}
              </Descriptions.Item>
              <Descriptions.Item label="输入">{detail.input_summary}</Descriptions.Item>
              <Descriptions.Item label="输出摘要">
                {detail.output_summary ?? "-"}
              </Descriptions.Item>
              <Descriptions.Item label="是否已落地">
                {detail.applied_at ? (
                  <Tag color="green">{new Date(detail.applied_at).toLocaleString()}</Tag>
                ) : (
                  <Tag>未落地</Tag>
                )}
              </Descriptions.Item>
              {detail.error_message && (
                <Descriptions.Item label="错误">{detail.error_message}</Descriptions.Item>
              )}
            </Descriptions>

            {detail.patches && detail.patches.length > 0 && (
              <Card size="small" title="补丁文件">
                {(detail.patches ?? []).map((p) => (
                  <div key={p.path} className="flex gap-2 py-1">
                    <Tag color={CHANGE_COLOR[p.change] ?? "default"}>{p.change}</Tag>
                    <code className="text-xs">{p.path}</code>
                  </div>
                ))}
              </Card>
            )}

            {detail.tests && detail.tests.length > 0 && (
              <Card size="small" title="测试建议">
                <ul className="pl-5 list-disc text-sm">
                  {detail.tests.map((t, i) => <li key={i}>{t}</li>)}
                </ul>
              </Card>
            )}

            {detail.risks && detail.risks.length > 0 && (
              <Card size="small" title="风险提示">
                <ul className="pl-5 list-disc text-sm">
                  {detail.risks.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </Card>
            )}
          </Space>
        )}
      </Drawer>

      <Modal
        title={`落地 LLM 补丁 #${applyJobId ?? ""} — 请先确认变更`}
        open={applyJobId !== null}
        width={960}
        onCancel={() => setApplyJobId(null)}
        onOk={() => applyJobId && applyMut.mutate(applyJobId)}
        okText="确认落地"
        confirmLoading={applyMut.isPending}
        okButtonProps={{ disabled: patchDiff?.already_applied }}
      >
        {patchDiff?.already_applied && (
          <Tag color="orange" className="mb-2">
            该任务已落地,不可重复落地
          </Tag>
        )}
        {!patchDiff && <Typography.Text>加载中...</Typography.Text>}
        {patchDiff && patchDiff.files.length === 0 && (
          <Typography.Text>没有可应用的补丁。</Typography.Text>
        )}
        {patchDiff && patchDiff.files.length > 0 && (
          <div className="flex gap-3" style={{ height: "60vh" }}>
            <div className="w-64 overflow-auto border rounded">
              {patchDiff.files.map((f: DraftDiffEntry) => (
                <div
                  key={f.path}
                  onClick={() => setApplyActivePath(f.path)}
                  className={`px-3 py-2 cursor-pointer border-b border-gray-100 ${
                    (activePatch?.path ?? "") === f.path ? "bg-blue-50" : "hover:bg-gray-50"
                  }`}
                >
                  <Tag color={CHANGE_COLOR[f.change] ?? "default"}>{f.change}</Tag>
                  <span className="text-xs ml-1 break-all">{f.path}</span>
                </div>
              ))}
            </div>
            <div className="flex-1">
              {activePatch && (
                <DiffEditor
                  language={languageOf(activePatch.path)}
                  original={activePatch.before ?? ""}
                  modified={activePatch.after ?? ""}
                  height="60vh"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    readOnly: true,
                    renderSideBySide: true,
                  }}
                />
              )}
            </div>
          </div>
        )}
      </Modal>
    </Card>
  );
}
