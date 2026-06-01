import { useState, useCallback } from "react";
import {
  Card,
  Form,
  Input,
  Button,
  Switch,
  Space,
  Tabs,
  App as AntdApp,
  Alert,
  Steps,
  Tag,
  Descriptions,
  Typography,
} from "antd";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { createSkill } from "@/api/skills";
import { submitCreate, getJob, applyJob } from "@/api/llm";
import { fetchSettings } from "@/api/settings";
import type { SkillCreateBody } from "@/types";

const FRONT_MATTER_RE = /^---\s*\n[\s\S]*?\n---/;

function SkillMdPreview({ form }: { form: ReturnType<typeof Form.useForm<SkillCreateBody>>[0] }) {
  const values = Form.useWatch([], form);
  if (!values?.name && !values?.description) return null;

  const fmLines = ["---"];
  if (values?.name) fmLines.push(`name: ${values.name}`);
  if (values?.description) fmLines.push(`description: ${values.description}`);
  if (values?.argument_hint) fmLines.push(`argument-hint: ${values.argument_hint}`);
  if (values?.disable_model_invocation) fmLines.push("disable-model-invocation: true");
  if (values?.user_invocable === false) fmLines.push("user-invocable: false");
  fmLines.push("---");
  const body = values?.initial_body?.trim() || `# ${values?.name || "my-skill"}\n\n(正文待填写)`;
  const preview = fmLines.join("\n") + "\n\n" + body;

  return (
    <Card title="SKILL.md 预览" size="small" className="mt-4">
      <pre className="text-xs whitespace-pre-wrap bg-gray-50 p-3 rounded max-h-64 overflow-auto">
        {preview}
      </pre>
    </Card>
  );
}

function ManualForm() {
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const [form] = Form.useForm<SkillCreateBody>();
  const [fmWarning, setFmWarning] = useState(false);

  const checkFrontMatter = useCallback((value: string) => {
    setFmWarning(FRONT_MATTER_RE.test(value ?? ""));
  }, []);

  const handleSplitFrontMatter = useCallback(() => {
    const body = form.getFieldValue("initial_body") as string;
    const match = body.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$/);
    if (!match) return;
    const yamlContent = match[1];
    const mdBody = match[2];
    const nameMatch = yamlContent.match(/^name:\s*(.+)$/m);
    const descMatch = yamlContent.match(/^description:\s*(.+)$/m);
    if (nameMatch && !form.getFieldValue("name")) {
      form.setFieldValue("name", nameMatch[1].trim());
    }
    if (descMatch && !form.getFieldValue("description")) {
      form.setFieldValue("description", descMatch[1].trim());
    }
    form.setFieldValue("initial_body", mdBody.trim());
    setFmWarning(false);
    message.success("已拆分 front matter 到元数据字段");
  }, [form, message]);

  const mut = useMutation({
    mutationFn: createSkill,
    onSuccess: (skill) => {
      message.success(`Skill ${skill.name} 已创建`);
      navigate(`/skills/${skill.id}`);
    },
    onError: (e: { response?: { data?: { message?: string } } }) => {
      message.error(e?.response?.data?.message ?? "创建失败");
    },
  });

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={(v) => mut.mutate(v)}
      initialValues={{ user_invocable: true, disable_model_invocation: false }}
    >
      <Form.Item
        label="名称"
        name="name"
        rules={[
          { required: true, message: "必填" },
          { pattern: /^[a-z0-9-]{3,64}$/, message: "仅 [a-z0-9-],长度 3-64" },
        ]}
        extra="作为 /skill-name 的调用命令,也是 Git 仓库后缀"
      >
        <Input placeholder="my-skill" />
      </Form.Item>

      <Form.Item
        label="描述 (description)"
        name="description"
        rules={[{ required: true, message: "必填" }, { min: 10, message: "至少 10 字符" }]}
        extra="按公司规范:功能说明 + 使用场景 + 关键词。AI 选择 Skill 主要靠这一项。"
      >
        <Input.TextArea rows={4} />
      </Form.Item>

      <Form.Item label="argument-hint" name="argument_hint" extra="例如 [filename]">
        <Input placeholder="[filename]" />
      </Form.Item>

      <Form.Item
        label="禁止 AI 自动调用"
        name="disable_model_invocation"
        valuePropName="checked"
      >
        <Switch />
      </Form.Item>

      <Form.Item
        label="在 / 菜单中显示"
        name="user_invocable"
        valuePropName="checked"
      >
        <Switch />
      </Form.Item>

      <Form.Item label="初始正文 (可选)" name="initial_body">
        <Input.TextArea
          rows={5}
          placeholder="# my-skill\n\n说明..."
          onChange={(e) => checkFrontMatter(e.target.value)}
        />
      </Form.Item>
      {fmWarning && (
        <Alert
          type="warning"
          showIcon
          message="检测到 front matter"
          description="正文中包含 YAML front matter (---...---)。系统会自动生成唯一 front matter，直接粘贴可能产生重复。"
          action={
            <Button size="small" type="primary" onClick={handleSplitFrontMatter}>
              拆分为元数据 + 正文
            </Button>
          }
          className="mb-4"
        />
      )}

      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={mut.isPending}>
            保存本地草稿
          </Button>
          <Button onClick={() => navigate("/skills")}>取消</Button>
        </Space>
      </Form.Item>

      <SkillMdPreview form={form} />
    </Form>
  );
}

interface LLMCreatePayload {
  skill_name: string;
  description: string;
  goal: string;
  scenario?: string;
  trigger?: string;
  target_agent?: string;
  extra_materials?: string;
  constraints?: string;
  include_scripts?: boolean;
  include_references?: boolean;
}

function LLMForm() {
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const [form] = Form.useForm<LLMCreatePayload>();
  const [jobId, setJobId] = useState<number | null>(null);

  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: fetchSettings,
    staleTime: 60_000,
  });

  const isMock = settings?.llm.provider === "mock";

  const submitMut = useMutation({
    mutationFn: submitCreate,
    onSuccess: (job) => {
      setJobId(job.id);
      message.success(`任务 #${job.id} 已提交,正在生成...`);
    },
    onError: (e: { response?: { data?: { message?: string } } }) => {
      message.error(e?.response?.data?.message ?? "提交失败");
    },
  });

  const { data: job } = useQuery({
    queryKey: ["llm-job", jobId],
    queryFn: () => getJob(jobId!),
    enabled: jobId !== null,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s && ["succeeded", "failed", "canceled"].includes(s) ? false : 1500;
    },
  });

  const applyMut = useMutation({
    mutationFn: () => applyJob(jobId!),
    onSuccess: (result) => {
      message.success("已落地为 Skill 草稿");
      if (result.skill_id) navigate(`/skills/${result.skill_id}`);
    },
    onError: (e: { response?: { data?: { message?: string } } }) => {
      message.error(e?.response?.data?.message ?? "落地失败");
    },
  });

  const statusToStep = (s?: string) => {
    if (!s) return 0;
    if (s === "queued") return 0;
    if (s === "running") return 1;
    if (s === "succeeded") return 2;
    return 3;
  };

  return (
    <Space direction="vertical" size="large" className="w-full">
      {settings && (
        <Descriptions size="small" column={4} bordered className="mb-4">
          <Descriptions.Item label="Provider">
            <Tag color={isMock ? "default" : "blue"}>{settings.llm.provider}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Model">{settings.llm.model}</Descriptions.Item>
          <Descriptions.Item label="API Style">{settings.llm.api_style}</Descriptions.Item>
          <Descriptions.Item label="Token">
            <Tag color={settings.llm.token_configured ? "green" : "red"}>
              {settings.llm.token_configured ? "已配置" : "未配置"}
            </Tag>
          </Descriptions.Item>
        </Descriptions>
      )}
      {isMock && (
        <Alert
          type="info"
          showIcon
          message="当前 LLM_PROVIDER=mock"
          description="Mock 客户端会基于输入按模板生成 Skill 草稿。切到真实 LLM 需在 .env 中配置 ANTHROPIC_AUTH_TOKEN 与 LLM_PROVIDER=anthropic。"
        />
      )}
      {!isMock && !settings?.llm.token_configured && (
        <Alert
          type="error"
          showIcon
          message="LLM Token 未配置"
          description="真实 LLM 当前不可用,提交任务将失败。请在 .env 中配置 ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN。"
          className="mb-2"
        />
      )}
      <Form
        form={form}
        layout="vertical"
        onFinish={(v) => submitMut.mutate(v)}
        initialValues={{ include_scripts: true, include_references: true }}
      >
        <Form.Item
          label="Skill 名称"
          name="skill_name"
          rules={[
            { required: true, message: "必填" },
            { pattern: /^[a-z0-9-]{3,64}$/, message: "仅 [a-z0-9-],长度 3-64" },
          ]}
        >
          <Input placeholder="my-llm-skill" />
        </Form.Item>
        <Form.Item
          label="描述 (description)"
          name="description"
          rules={[{ required: true, message: "必填" }, { min: 10, message: "至少 10 字符" }]}
        >
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item
          label="目标"
          name="goal"
          rules={[{ required: true, message: "必填" }]}
          extra="这个 Skill 要完成什么任务"
        >
          <Input.TextArea rows={2} placeholder="例如:把一段日志摘要为关键事件" />
        </Form.Item>
        <Form.Item label="使用场景" name="scenario">
          <Input placeholder="什么情境下使用" />
        </Form.Item>
        <Form.Item label="触发关键词" name="trigger">
          <Input placeholder="逗号分隔" />
        </Form.Item>
        <Form.Item label="目标 Agent" name="target_agent">
          <Input placeholder="例如:代码审查 Agent" />
        </Form.Item>
        <Form.Item label="参考材料" name="extra_materials">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item label="约束条件" name="constraints">
          <Input.TextArea rows={2} />
        </Form.Item>
        <Space>
          <Form.Item name="include_scripts" valuePropName="checked" noStyle>
            <Switch />
          </Form.Item>
          <span>生成 scripts/ 示例</span>
          <Form.Item name="include_references" valuePropName="checked" noStyle>
            <Switch />
          </Form.Item>
          <span>生成 references/ 占位</span>
        </Space>
        <div className="mt-4">
          <Button type="primary" htmlType="submit" loading={submitMut.isPending}>
            提交 LLM 任务
          </Button>
        </div>
      </Form>

      {jobId && (
        <Card title={`LLM 任务 #${jobId}`}>
          <Steps
            current={statusToStep(job?.status)}
            status={job?.status === "failed" ? "error" : undefined}
            items={[
              { title: "排队" },
              { title: "运行" },
              { title: "成功" },
            ]}
          />
          <Descriptions column={1} size="small" className="mt-4">
            <Descriptions.Item label="状态">
              <Tag>{job?.status ?? "..."}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="输入摘要">
              {job?.input_summary}
            </Descriptions.Item>
            <Descriptions.Item label="输出摘要">
              {job?.output_summary ?? "-"}
            </Descriptions.Item>
            {job?.error_message && (
              <Descriptions.Item label="错误">
                {job.error_message}
              </Descriptions.Item>
            )}
          </Descriptions>
          {job?.status === "succeeded" && (
            <>
              {job.patches && job.patches.length > 0 && (
                <Card size="small" title="生成文件列表" className="mt-3">
                  {job.patches.map((p) => (
                    <Tag key={p.path} color={p.change === "add" ? "green" : p.change === "remove" ? "red" : "blue"}>
                      {p.change}: {p.path}
                    </Tag>
                  ))}
                  {job.patches.find((p) => p.path === "SKILL.md" && p.content) && (
                    <div className="mt-2">
                      <Typography.Text strong className="block mb-1">SKILL.md 预览:</Typography.Text>
                      <pre className="text-xs whitespace-pre-wrap bg-gray-50 p-3 rounded max-h-48 overflow-auto">
                        {job.patches.find((p) => p.path === "SKILL.md")?.content}
                      </pre>
                    </div>
                  )}
                </Card>
              )}
              {job.tests && job.tests.length > 0 && (
                <Card size="small" title="测试建议" className="mt-2">
                  <ul className="pl-5 list-disc text-sm">
                    {job.tests.map((t, i) => <li key={i}>{t}</li>)}
                  </ul>
                </Card>
              )}
              {job.risks && job.risks.length > 0 && (
                <Card size="small" title="风险提示" className="mt-2">
                  <ul className="pl-5 list-disc text-sm text-orange-600">
                    {job.risks.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </Card>
              )}
              <Button
                type="primary"
                loading={applyMut.isPending}
                onClick={() => applyMut.mutate()}
                className="mt-3"
              >
                确认落地为 Skill 草稿
              </Button>
            </>
          )}
        </Card>
      )}
    </Space>
  );
}

export default function SkillNew() {
  const [searchParams] = useSearchParams();
  const defaultTab = searchParams.get("tab") === "llm" ? "llm" : "manual";

  return (
    <Card title="创建 Skill">
      <Tabs
        defaultActiveKey={defaultTab}
        items={[
          { key: "manual", label: "手动创建", children: <ManualForm /> },
          { key: "llm", label: "LLM 辅助", children: <LLMForm /> },
        ]}
      />
    </Card>
  );
}
