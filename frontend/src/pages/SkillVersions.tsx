import { useState } from "react";
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Form,
  Input,
  Select,
  App as AntdApp,
  Typography,
  Modal,
  Descriptions,
} from "antd";
import { useParams, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnsType } from "antd/es/table";
import { commitDraft, getDraftDiff, publishToMaster } from "@/api/antcode";
import type { DraftDiffOut } from "@/api/antcode";
import { listVersions, restoreVersion } from "@/api/versions";
import { getSkill } from "@/api/skills";
import type { SkillVersion } from "@/types";

export default function SkillVersions() {
  const { id } = useParams<{ id: string }>();
  const skillId = Number(id);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { message, modal } = AntdApp.useApp();
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishStep, setPublishStep] = useState<"form" | "preview">("form");
  const [draftDiff, setDraftDiff] = useState<DraftDiffOut | null>(null);
  const [draftCommitSha, setDraftCommitSha] = useState<string | null>(null);
  const [pubForm] = Form.useForm<{
    version: string;
    summary: string;
    change_type: "patch" | "minor" | "major";
  }>();
  const [selected, setSelected] = useState<number[]>([]);

  const { data: skill } = useQuery({
    queryKey: ["skill", skillId],
    queryFn: () => getSkill(skillId),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["skill", skillId, "versions"],
    queryFn: () => listVersions(skillId),
  });

  const prepareMut = useMutation({
    mutationFn: async (v: { version: string; summary: string; change_type: "patch" | "minor" | "major" }) => {
      const commitRes = await commitDraft(skillId, v.summary || `release v${v.version}`);
      const diff = await getDraftDiff(skillId);
      return { commitRes, diff };
    },
    onSuccess: ({ commitRes, diff }) => {
      setDraftCommitSha(commitRes.commit_sha);
      setDraftDiff(diff);
      setPublishStep("preview");
    },
    onError: (e: { response?: { data?: { message?: string } } }) => {
      message.error(e?.response?.data?.message ?? "准备发布失败");
    },
  });

  const pubMut = useMutation({
    mutationFn: async (v: { version: string; summary: string; change_type: "patch" | "minor" | "major" }) => {
      return publishToMaster(skillId, v);
    },
    onSuccess: (v) => {
      message.success(`已发布 v${v.version}，已推送到 AntCode`);
      setPublishOpen(false);
      setPublishStep("form");
      setDraftDiff(null);
      setDraftCommitSha(null);
      pubForm.resetFields();
      qc.invalidateQueries({ queryKey: ["skill", skillId, "versions"] });
      qc.invalidateQueries({ queryKey: ["skill", skillId] });
    },
    onError: (e: { response?: { data?: { message?: string } } }) => {
      message.error(e?.response?.data?.message ?? "发布失败");
    },
  });

  const restoreMut = useMutation({
    mutationFn: (payload: { versionId: number; new_version: string }) =>
      restoreVersion(skillId, payload.versionId, { new_version: payload.new_version }),
    onSuccess: (v) => {
      if (v.git_pushed === true) {
        message.success(`已恢复并发布 v${v.version}，已推送到远端仓库`);
      } else if (v.git_pushed === false) {
        message.warning(`v${v.version} 本地恢复成功，但推送远端失败：${v.push_error || "未知错误"}`, 8);
      } else {
        message.success(`已恢复并发布 v${v.version}`);
      }
      qc.invalidateQueries({ queryKey: ["skill", skillId, "versions"] });
    },
    onError: (e: { response?: { data?: { message?: string } } }) => {
      message.error(e?.response?.data?.message ?? "恢复失败");
    },
  });

  const columns: ColumnsType<SkillVersion> = [
    { title: "版本", dataIndex: "version", key: "version", width: 100 },
    {
      title: "类型",
      dataIndex: "change_type",
      key: "change_type",
      width: 80,
      render: (t: string) => <Tag>{t}</Tag>,
    },
    { title: "摘要", dataIndex: "summary", key: "summary", ellipsis: true },
    {
      title: "Commit",
      dataIndex: "git_commit_sha",
      key: "sha",
      width: 110,
      render: (sha: string, row: SkillVersion) =>
        row.commit_url ? (
          <a href={row.commit_url} target="_blank" rel="noopener noreferrer">
            <code>{sha.slice(0, 9)}</code>
          </a>
        ) : (
          <code>{sha.slice(0, 9)}</code>
        ),
    },
    {
      title: "Tag",
      dataIndex: "git_tag",
      key: "tag",
      width: 100,
      render: (t: string | null | undefined, row: SkillVersion) => {
        if (!t) return "-";
        return row.tag_url ? (
          <a href={row.tag_url} target="_blank" rel="noopener noreferrer">
            <Tag color="green">{t}</Tag>
          </a>
        ) : (
          <Tag color="green">{t}</Tag>
        );
      },
    },
    {
      title: "作者",
      dataIndex: "author_name",
      key: "author",
      width: 120,
    },
    {
      title: "发布时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: "操作",
      key: "action",
      width: 120,
      render: (_, row) => (
        <Button
          size="small"
          onClick={() => {
            let nv = "";
            modal.confirm({
              title: `基于 v${row.version} 恢复并创建新版本`,
              content: (
                <Form layout="vertical">
                  <Form.Item>
                    <Typography.Text type="secondary">
                      将以 v{row.version} 的内容创建新版本。已有版本不会被删除或修改。
                    </Typography.Text>
                  </Form.Item>
                  <Form.Item label="新版本号" required>
                    <Input
                      onChange={(e) => (nv = e.target.value)}
                      placeholder="例如 0.1.2"
                    />
                  </Form.Item>
                </Form>
              ),
              onOk: () => {
                if (!nv) {
                  message.error("请填新版本号");
                  return Promise.reject(new Error("empty"));
                }
                return restoreMut.mutateAsync({ versionId: row.id, new_version: nv });
              },
            });
          }}
        >
          恢复
        </Button>
      ),
    },
  ];

  return (
    <Card
      title={
        <div className="flex items-center justify-between">
          <Typography.Title level={4} className="!m-0">
            {skill?.name} · 版本历史
          </Typography.Title>
          <Space>
            <Button
              disabled={selected.length !== 2}
              onClick={() => {
                // 默认旧 → 新方向 (PRD2 §2.5)
                const ids = [...selected].sort((a, b) => a - b);
                navigate(
                  `/skills/${skillId}/diff?from=${ids[0]}&to=${ids[1]}`,
                );
              }}
            >
              {selected.length === 2
                ? (() => {
                    const sortedIds = [...selected].sort((a, b) => a - b);
                    const a = (data ?? []).find((v) => v.id === sortedIds[0]);
                    const b = (data ?? []).find((v) => v.id === sortedIds[1]);
                    return a && b ? `对比 v${a.version} → v${b.version}` : "对比选中两个";
                  })()
                : "对比选中两个"}
            </Button>
            <Button
              type="primary"
              onClick={() => {
                // 推荐下一个 patch 版本
                const latest = (data ?? [])[0];
                if (latest) {
                  const m = latest.version.match(/^(\d+)\.(\d+)\.(\d+)$/);
                  if (m) {
                    pubForm.setFieldValue(
                      "version",
                      `${m[1]}.${m[2]}.${Number(m[3]) + 1}`,
                    );
                  }
                }
                setPublishOpen(true);
              }}
            >
              发布新版本
            </Button>
          </Space>
        </div>
      }
    >
      <Table
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={data ?? []}
        rowSelection={{
          selectedRowKeys: selected,
          onChange: (keys) => setSelected(keys.slice(0, 2).map(Number)),
          type: "checkbox",
        }}
      />

      <Modal
        title={publishStep === "form" ? "发布新版本" : "确认发布"}
        open={publishOpen}
        width={publishStep === "preview" ? 720 : undefined}
        onCancel={() => {
          setPublishOpen(false);
          setPublishStep("form");
          setDraftDiff(null);
          setDraftCommitSha(null);
        }}
        onOk={async () => {
          if (publishStep === "form") {
            const v = await pubForm.validateFields();
            prepareMut.mutate(v);
          } else {
            const v = pubForm.getFieldsValue(true);
            pubMut.mutate(v);
          }
        }}
        okText={publishStep === "form" ? "预览变更" : "确认发布"}
        confirmLoading={prepareMut.isPending || pubMut.isPending}
      >
        {publishStep === "form" ? (
          <Form
            form={pubForm}
            layout="vertical"
            preserve
            initialValues={{ change_type: "patch", summary: "" }}
          >
            <Form.Item
              label="版本号"
              name="version"
              rules={[
                { required: true, message: "必填" },
                { pattern: /^\d+\.\d+\.\d+$/, message: "需为 MAJOR.MINOR.PATCH" },
              ]}
            >
              <Input placeholder="0.1.0" />
            </Form.Item>
            <Form.Item label="变更类型" name="change_type">
              <Select
                options={[
                  { value: "patch", label: "patch:修复 / 小调整" },
                  { value: "minor", label: "minor:新增功能 / 文档" },
                  { value: "major", label: "major:重构 / 不兼容" },
                ]}
              />
            </Form.Item>
            <Form.Item label="更新摘要" name="summary">
              <Input.TextArea rows={3} />
            </Form.Item>
          </Form>
        ) : (
          <Space direction="vertical" className="w-full" size="middle">
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="目标仓库">
                {skill?.git_web_url ? (
                  <a href={skill.git_web_url} target="_blank" rel="noreferrer">
                    {skill.git_path_with_namespace}
                  </a>
                ) : (
                  skill?.git_path_with_namespace ?? "-"
                )}
              </Descriptions.Item>
              <Descriptions.Item label="主分支">
                <code>{skill?.default_branch ?? "master"}</code>
              </Descriptions.Item>
              <Descriptions.Item label="草稿分支">
                <code>{draftDiff?.draft_branch ?? skill?.draft_branch ?? "-"}</code>
              </Descriptions.Item>
              <Descriptions.Item label="草稿 SHA">
                <code>{draftCommitSha?.slice(0, 9) ?? "-"}</code>
              </Descriptions.Item>
              <Descriptions.Item label="发布版本">
                <Tag color="blue">v{pubForm.getFieldValue("version")}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="预计 Tag">
                <Tag color="green">v{pubForm.getFieldValue("version")}</Tag>
              </Descriptions.Item>
            </Descriptions>
            <Typography.Text strong>
              变更文件 ({draftDiff?.files.length ?? 0})
            </Typography.Text>
            {draftDiff && draftDiff.files.length > 0 ? (
              <div style={{ maxHeight: 300, overflow: "auto" }}>
                {draftDiff.files.map((f) => (
                  <div key={f.path} className="py-1 border-b border-gray-100">
                    <Tag
                      color={f.change === "added" ? "green" : f.change === "removed" ? "red" : "blue"}
                    >
                      {f.change}
                    </Tag>
                    <code className="text-sm">{f.path}</code>
                  </div>
                ))}
              </div>
            ) : (
              <Typography.Text type="secondary">无变更文件</Typography.Text>
            )}
            <Button
              size="small"
              onClick={() => setPublishStep("form")}
            >
              返回修改
            </Button>
          </Space>
        )}
      </Modal>
    </Card>
  );
}
