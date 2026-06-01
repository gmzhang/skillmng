import { useState, useMemo, useEffect } from "react";
import {
  Card,
  Row,
  Col,
  Space,
  Button,
  Descriptions,
  Tag,
  Empty,
  App as AntdApp,
  Input,
  Form,
  Typography,
  Modal,
  Select,
  Steps,
  Tooltip,
} from "antd";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  EditOutlined,
  RocketOutlined,
  RobotOutlined,
  CheckCircleFilled,
  WarningFilled,
  CloseCircleFilled,
  CloudUploadOutlined,
  CloudSyncOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import { getSkill, bindRepository } from "@/api/skills";
import { fetchValidation, fixSkillMd } from "@/api/settings";
import { commitDraft, createRepository, getDraftDiff, getLLMPatchDiff, publishToMaster, syncRepository } from "@/api/antcode";
import type { DraftDiffOut, PatchDiffOut } from "@/api/antcode";
import {
  listFiles,
  getFileContent,
  writeFileContent,
  deleteFile,
} from "@/api/files";
import { submitUpdate, getJob, applyJob } from "@/api/llm";
import { DiffEditor } from "@monaco-editor/react";
import SkillFileTree from "@/components/SkillFileTree";
import MarkdownEditor, { languageOf } from "@/components/MarkdownEditor";

interface Props {
  /** edit 模式:打开页面即进入编辑;view 模式:默认只读,可点击切换 */
  mode?: "view" | "edit";
}

const STATUS_TO_STEP = (s?: string): number => {
  if (!s || s === "queued") return 0;
  if (s === "running") return 1;
  if (s === "succeeded") return 2;
  return 3;
};

export default function SkillDetail({ mode = "view" }: Props) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const skillId = Number(id);
  const qc = useQueryClient();
  const { message, modal } = AntdApp.useApp();

  const [selectedPath, setSelectedPath] = useState<string>("SKILL.md");
  const [editing, setEditing] = useState<boolean>(mode === "edit");
  const [draft, setDraft] = useState<string>("");
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishStep, setPublishStep] = useState<"form" | "preview">("form");
  const [draftDiff, setDraftDiff] = useState<DraftDiffOut | null>(null);
  const [draftCommitSha, setDraftCommitSha] = useState<string | null>(null);
  const [llmOpen, setLlmOpen] = useState(false);
  const [llmJobId, setLlmJobId] = useState<number | null>(null);
  const [llmPatchDiff, setLlmPatchDiff] = useState<PatchDiffOut | null>(null);
  const [llmApplied, setLlmApplied] = useState(false);
  const [pubForm] = Form.useForm<{
    version: string;
    summary: string;
    change_type: "patch" | "minor" | "major";
  }>();
  const [llmForm] = Form.useForm<{ goal: string }>();

  const { data: skill } = useQuery({
    queryKey: ["skill", skillId],
    queryFn: () => getSkill(skillId),
    enabled: !Number.isNaN(skillId),
  });

  const { data: files } = useQuery({
    queryKey: ["skill", skillId, "files"],
    queryFn: () => listFiles(skillId),
    enabled: !Number.isNaN(skillId),
  });

  const { data: fileContent } = useQuery({
    queryKey: ["skill", skillId, "file", selectedPath],
    queryFn: () => getFileContent(skillId, selectedPath),
    enabled: !!selectedPath && !Number.isNaN(skillId),
  });

  const { data: validation } = useQuery({
    queryKey: ["skill", skillId, "validation"],
    queryFn: () => fetchValidation(skillId),
    enabled: !Number.isNaN(skillId),
  });

  useEffect(() => {
    setDraft(fileContent?.content ?? "");
  }, [fileContent?.path, fileContent?.content]);

  const writeMut = useMutation({
    mutationFn: (payload: { path: string; content: string }) =>
      writeFileContent(skillId, payload.path, payload.content),
    onSuccess: () => {
      message.success("已保存");
      qc.invalidateQueries({ queryKey: ["skill", skillId] });
    },
    onError: (e: { response?: { data?: { message?: string } } }) => {
      message.error(e?.response?.data?.message ?? "保存失败");
    },
  });

  const deleteFileMut = useMutation({
    mutationFn: (path: string) => deleteFile(skillId, path),
    onSuccess: () => {
      message.success("已删除");
      setSelectedPath("SKILL.md");
      qc.invalidateQueries({ queryKey: ["skill", skillId, "files"] });
    },
  });

  const bindMut = useMutation({
    mutationFn: (url: string) => bindRepository(skillId, url),
    onSuccess: () => {
      message.success("已绑定");
      qc.invalidateQueries({ queryKey: ["skill", skillId] });
    },
  });

  const createRepoMut = useMutation({
    mutationFn: () => createRepository(skillId),
    onSuccess: () => {
      message.success("AntCode 仓库已就绪");
      qc.invalidateQueries({ queryKey: ["skill", skillId] });
    },
    onError: (e: { response?: { data?: { message?: string } } }) =>
      message.error(e?.response?.data?.message ?? "创建 AntCode 仓库失败"),
  });

  const syncRepoMut = useMutation({
    mutationFn: () => syncRepository(skillId),
    onSuccess: () => {
      message.success("已同步");
      qc.invalidateQueries({ queryKey: ["skill", skillId] });
    },
    onError: (e: { response?: { data?: { message?: string } } }) =>
      message.error(e?.response?.data?.message ?? "同步失败"),
  });

  const fixMut = useMutation({
    mutationFn: () => fixSkillMd(skillId),
    onSuccess: (r) => {
      if (r.fixed) message.success("已自动拆分双 front matter");
      else message.info("当前 SKILL.md 无需修复");
      qc.invalidateQueries({ queryKey: ["skill", skillId, "file", "SKILL.md"] });
      qc.invalidateQueries({ queryKey: ["skill", skillId, "validation"] });
    },
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

  const publishMut = useMutation({
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
      qc.invalidateQueries({ queryKey: ["skill", skillId] });
      qc.invalidateQueries({ queryKey: ["skill", skillId, "versions"] });
    },
    onError: (e: { response?: { data?: { message?: string } } }) => {
      message.error(e?.response?.data?.message ?? "发布失败");
    },
  });

  const submitLlmMut = useMutation({
    mutationFn: (goal: string) => submitUpdate({ skill_id: skillId, goal }),
    onSuccess: (job) => {
      setLlmJobId(job.id);
      message.success(`LLM 任务 #${job.id} 已提交`);
    },
  });

  const { data: llmJob } = useQuery({
    queryKey: ["llm-job", llmJobId],
    queryFn: () => getJob(llmJobId!),
    enabled: llmJobId !== null,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s && ["succeeded", "failed", "canceled"].includes(s) ? false : 1500;
    },
  });

  const fetchPatchDiffMut = useMutation({
    mutationFn: (jobId: number) => getLLMPatchDiff(jobId),
    onSuccess: (data) => setLlmPatchDiff(data),
    onError: (e: { response?: { data?: { message?: string } } }) =>
      message.error(e?.response?.data?.message ?? "获取 patch diff 失败"),
  });

  const applyLlmMut = useMutation({
    mutationFn: () => applyJob(llmJobId!),
    onSuccess: () => {
      message.success("已写回当前 Skill");
      setLlmApplied(true);
      qc.invalidateQueries({ queryKey: ["skill", skillId] });
      qc.invalidateQueries({ queryKey: ["skill", skillId, "files"] });
      qc.invalidateQueries({ queryKey: ["skill", skillId, "file", selectedPath] });
    },
    onError: (e: { response?: { data?: { message?: string } } }) =>
      message.error(e?.response?.data?.message ?? "落地失败"),
  });

  const language = useMemo(() => languageOf(selectedPath), [selectedPath]);
  const isBinaryView = !fileContent && (files ?? []).find((f) => f.path === selectedPath)?.content_type === "binary";

  const handleSave = () => {
    if (!selectedPath) return;
    writeMut.mutate({ path: selectedPath, content: draft });
  };

  const handleNewFile = () => {
    let value = "";
    modal.confirm({
      title: "新建文件",
      content: (
        <Form layout="vertical">
          <Form.Item label="路径" extra="例如 scripts/run.sh、references/notes.md" required>
            <Input onChange={(e) => (value = e.target.value)} placeholder="path" />
          </Form.Item>
        </Form>
      ),
      onOk: async () => {
        if (!value.trim()) {
          message.error("请输入路径");
          throw new Error("empty path");
        }
        await writeMut.mutateAsync({ path: value.trim(), content: "" });
        setSelectedPath(value.trim());
      },
    });
  };

  const handleDeleteFile = (path: string) => {
    if (path === "SKILL.md") {
      message.warning("SKILL.md 不能删除");
      return;
    }
    modal.confirm({
      title: `删除文件 ${path}?`,
      okButtonProps: { danger: true },
      onOk: () => deleteFileMut.mutateAsync(path),
    });
  };

  const handleBind = () => {
    let value = skill?.git_remote_url ?? "";
    modal.confirm({
      title: "绑定 Git 仓库 remote URL",
      content: (
        <Form layout="vertical">
          <Form.Item label="remote URL" required>
            <Input
              defaultValue={value}
              onChange={(e) => (value = e.target.value)}
              placeholder="git@code.example.com:group/repo.git"
            />
          </Form.Item>
        </Form>
      ),
      onOk: () => bindMut.mutateAsync(value),
    });
  };

  if (!skill) return <Empty />;

  return (
    <Space direction="vertical" size="large" className="w-full">
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <Typography.Title level={4} className="!m-0">
              {skill.name}
            </Typography.Title>
            <Typography.Paragraph type="secondary" className="!mt-1 !mb-0">
              {skill.description}
            </Typography.Paragraph>
          </div>
          <Space>
            <Tag>{skill.status}</Tag>
            <Link to={`/skills/${skill.id}/versions`}>
              <Button>版本历史</Button>
            </Link>
            <Button icon={<RobotOutlined />} onClick={() => setLlmOpen(true)}>
              LLM 辅助更新
            </Button>
            <Button
              type="primary"
              icon={<RocketOutlined />}
              onClick={() => setPublishOpen(true)}
            >
              发布版本
            </Button>
          </Space>
        </div>
        <Descriptions column={3} size="small" className="mt-4">
          <Descriptions.Item label="argument-hint">
            {skill.argument_hint ?? "-"}
          </Descriptions.Item>
          <Descriptions.Item label="禁止 AI 自动调用">
            {skill.disable_model_invocation ? "是" : "否"}
          </Descriptions.Item>
          <Descriptions.Item label="/ 菜单显示">
            {skill.user_invocable ? "是" : "否"}
          </Descriptions.Item>
          <Descriptions.Item label="校验状态">
            {validation ? (
              validation.status === "valid" ? (
                <Tag color="green" icon={<CheckCircleFilled />}>通过</Tag>
              ) : validation.status === "warning" ? (
                <Tag color="orange" icon={<WarningFilled />}>
                  警告 ({validation.warnings.length})
                </Tag>
              ) : (
                <Tag color="red" icon={<CloseCircleFilled />}>
                  错误 ({validation.errors.length})
                </Tag>
              )
            ) : (
              "..."
            )}
          </Descriptions.Item>
          <Descriptions.Item label="AntCode 仓库">
            {skill.git_web_url ? (
              <a href={skill.git_web_url} target="_blank" rel="noreferrer">
                {skill.git_path_with_namespace ?? skill.git_web_url}
              </a>
            ) : skill.git_remote_url ? (
              <code className="text-xs">{skill.git_remote_url}</code>
            ) : (
              <Tag>未绑定</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="当前版本">
            {skill.current_version ? (
              <Tag color="purple">v{skill.current_version}</Tag>
            ) : (
              "-"
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Git tag">
            {skill.published_tag ? (
              <Tag color="cyan">{skill.published_tag}</Tag>
            ) : (
              "-"
            )}
          </Descriptions.Item>
          <Descriptions.Item label="主分支">
            <code>{skill.default_branch ?? "master"}</code>
          </Descriptions.Item>
          <Descriptions.Item label="草稿分支">
            {skill.draft_branch ? (
              <Space size={4}>
                <code>{skill.draft_branch}</code>
                {skill.draft_commit_sha && (
                  <Tooltip title={`点击复制: ${skill.draft_commit_sha}`}>
                    <code
                      className="cursor-pointer text-blue-600"
                      onClick={() => {
                        navigator.clipboard.writeText(skill.draft_commit_sha!);
                        message.success("已复制草稿 commit SHA");
                      }}
                    >
                      {skill.draft_commit_sha.slice(0, 9)}
                    </code>
                  </Tooltip>
                )}
              </Space>
            ) : (
              "-"
            )}
          </Descriptions.Item>
          <Descriptions.Item label="最新发布 commit">
            {skill.published_commit_sha ? (
              <Tooltip title={`点击复制: ${skill.published_commit_sha}`}>
                <code
                  className="cursor-pointer text-green-600"
                  onClick={() => {
                    navigator.clipboard.writeText(skill.published_commit_sha!);
                    message.success("已复制发布 commit SHA");
                  }}
                >
                  {skill.published_commit_sha.slice(0, 9)}
                </code>
              </Tooltip>
            ) : (
              "-"
            )}
          </Descriptions.Item>
        </Descriptions>

        {validation && validation.status !== "valid" && (
          <div className="mt-3">
            {validation.errors.length > 0 && (
              <div className="text-red-600 text-sm">
                ⚠ {validation.errors.join("; ")}
              </div>
            )}
            {validation.warnings.length > 0 && (
              <div className="text-orange-600 text-sm">
                ! {validation.warnings.join("; ")}
              </div>
            )}
          </div>
        )}

        <Space className="mt-2" wrap>
          <Button
            type="primary"
            icon={<CloudUploadOutlined />}
            onClick={() => createRepoMut.mutate()}
            loading={createRepoMut.isPending}
          >
            {skill.git_project_id ? "已创建仓库 (重新读取)" : "在 AntCode 创建仓库"}
          </Button>
          <Button
            icon={<CloudSyncOutlined />}
            onClick={() => syncRepoMut.mutate()}
            loading={syncRepoMut.isPending}
            disabled={!skill.git_project_id}
          >
            从远端同步
          </Button>
          <Button onClick={handleBind}>手动绑定 remote</Button>
          <Button
            icon={<ToolOutlined />}
            onClick={() => fixMut.mutate()}
            loading={fixMut.isPending}
            disabled={validation?.status !== "error"}
          >
            修复 SKILL.md
          </Button>
          <Button onClick={() => navigate(`/skills/${skill.id}/versions`)}>
            查看版本
          </Button>
        </Space>
      </Card>

      <Row gutter={16}>
        <Col span={7}>
          <Card
            title="文件树"
            extra={
              <Space>
                <Button size="small" icon={<PlusOutlined />} onClick={handleNewFile}>
                  新建
                </Button>
              </Space>
            }
          >
            <SkillFileTree
              files={files ?? []}
              selected={selectedPath}
              onSelect={setSelectedPath}
            />
          </Card>
        </Col>
        <Col span={17}>
          <Card
            title={selectedPath || "SKILL.md"}
            extra={
              <Space>
                {!editing && (
                  <Button
                    icon={<EditOutlined />}
                    onClick={() => setEditing(true)}
                    type="primary"
                  >
                    编辑
                  </Button>
                )}
                {editing && (
                  <>
                    <Button
                      icon={<SaveOutlined />}
                      type="primary"
                      onClick={handleSave}
                      loading={writeMut.isPending}
                    >
                      保存
                    </Button>
                    <Button onClick={() => setEditing(false)}>退出编辑</Button>
                  </>
                )}
                {selectedPath && selectedPath !== "SKILL.md" && (
                  <Button
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleDeleteFile(selectedPath)}
                  >
                    删除
                  </Button>
                )}
              </Space>
            }
          >
            {isBinaryView ? (
              <Empty description="二进制文件不支持在线编辑" />
            ) : (
              <MarkdownEditor
                value={editing ? draft : fileContent?.content ?? ""}
                onChange={setDraft}
                language={language}
                readOnly={!editing}
              />
            )}
          </Card>
        </Col>
      </Row>

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
            publishMut.mutate(v);
          }
        }}
        okText={publishStep === "form" ? "预览变更" : "确认发布"}
        confirmLoading={prepareMut.isPending || publishMut.isPending}
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
                {skill.git_web_url ? (
                  <a href={skill.git_web_url} target="_blank" rel="noreferrer">
                    {skill.git_path_with_namespace}
                  </a>
                ) : (
                  skill.git_path_with_namespace ?? "-"
                )}
              </Descriptions.Item>
              <Descriptions.Item label="主分支">
                <code>{skill.default_branch ?? "master"}</code>
              </Descriptions.Item>
              <Descriptions.Item label="草稿分支">
                <code>{draftDiff?.draft_branch ?? skill.draft_branch ?? "-"}</code>
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
            {!skill.published_commit_sha && (!draftDiff || draftDiff.files.length === 0) ? (
              <Typography.Text type="secondary">
                首次发布：将创建 master 分支并发布当前 Skill 全部内容为正式版本。
              </Typography.Text>
            ) : (
              <>
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
              </>
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

      <Modal
        title="LLM 辅助更新"
        open={llmOpen}
        onCancel={() => {
          setLlmOpen(false);
          setLlmJobId(null);
          setLlmPatchDiff(null);
          setLlmApplied(false);
          llmForm.resetFields();
        }}
        footer={null}
        width={680}
      >
        <Space direction="vertical" className="w-full">
          <Form
            form={llmForm}
            layout="vertical"
            onFinish={(v) => submitLlmMut.mutate(v.goal)}
          >
            <Form.Item
              label="更新目标"
              name="goal"
              rules={[{ required: true, message: "必填" }]}
              extra="例如:补充输入校验小节、在 SKILL.md 中增加触发关键词"
            >
              <Input.TextArea rows={3} />
            </Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={submitLlmMut.isPending}
              disabled={llmJobId !== null && llmJob?.status === "running"}
            >
              提交 LLM 任务
            </Button>
          </Form>

          {llmJobId && (
            <Card size="small" title={`任务 #${llmJobId}`}>
              <Steps
                size="small"
                current={STATUS_TO_STEP(llmJob?.status)}
                status={llmJob?.status === "failed" ? "error" : undefined}
                items={[
                  { title: "排队" },
                  { title: "运行" },
                  { title: "成功" },
                ]}
              />
              <Descriptions column={1} size="small" className="mt-3">
                <Descriptions.Item label="状态">
                  <Tag>{llmJob?.status ?? "..."}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="输出摘要">
                  {llmJob?.output_summary ?? "-"}
                </Descriptions.Item>
              </Descriptions>
              {llmJob?.status === "succeeded" && !llmPatchDiff && !llmApplied && (
                <Button
                  type="default"
                  className="mt-2"
                  loading={fetchPatchDiffMut.isPending}
                  onClick={() => fetchPatchDiffMut.mutate(llmJobId!)}
                >
                  查看变更 diff
                </Button>
              )}
              {llmPatchDiff && !llmApplied && (
                <div className="mt-3">
                  <Typography.Text strong>
                    变更文件 ({llmPatchDiff.files.length})
                  </Typography.Text>
                  <div className="mt-2 mb-2" style={{ maxHeight: "60vh", overflow: "auto" }}>
                    {llmPatchDiff.files.map((f) => (
                      <div key={f.path} className="mb-3">
                        <div className="py-1 mb-1">
                          <Tag
                            color={f.change === "added" ? "green" : f.change === "removed" ? "red" : "blue"}
                          >
                            {f.change}
                          </Tag>
                          <code className="text-sm">{f.path}</code>
                        </div>
                        <DiffEditor
                          language={languageOf(f.path)}
                          original={f.before ?? ""}
                          modified={f.after ?? ""}
                          height={Math.min(300, Math.max(100, ((f.after ?? f.before ?? "").split("\n").length + 2) * 19))}
                          options={{
                            minimap: { enabled: false },
                            fontSize: 12,
                            readOnly: true,
                            renderSideBySide: true,
                            scrollBeyondLastLine: false,
                          }}
                        />
                      </div>
                    ))}
                  </div>
                  {llmPatchDiff.already_applied ? (
                    <Tag color="default">已落地</Tag>
                  ) : (
                    <Button
                      type="primary"
                      loading={applyLlmMut.isPending}
                      onClick={() => applyLlmMut.mutate()}
                    >
                      确认写回
                    </Button>
                  )}
                </div>
              )}
              {llmApplied && (
                <Tag color="green" className="mt-2">已落地</Tag>
              )}
            </Card>
          )}
        </Space>
      </Modal>
    </Space>
  );
}
