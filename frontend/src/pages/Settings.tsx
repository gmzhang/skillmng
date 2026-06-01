import { Card, Descriptions, Tag, Button, Space, Typography, App as AntdApp, Alert, Result } from "antd";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { fetchSettings, testGit, testSSH, testLLM, reloadSettings } from "@/api/settings";
import type { TestResult } from "@/types";

const fmtBytes = (n: number): string => {
  if (n >= 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${n} B`;
};

function TestResultPanel({ title, result }: { title: string; result: TestResult | null }) {
  if (!result) return null;
  const d = result.detail || {};
  const s = (key: string) => (d[key] != null ? String(d[key]) : "");
  return (
    <Card
      size="small"
      title={title}
      className="mt-4"
      extra={
        <Tag color={result.ok ? "green" : "red"}>
          {result.ok ? "成功" : "失败"}
        </Tag>
      }
    >
      <Result
        status={result.ok ? "success" : "error"}
        title={result.message}
        className="!py-2"
      />
      {Object.keys(d).length > 0 && (
        <Descriptions column={2} size="small" bordered className="mt-2">
          {d.tested_at != null && (
            <Descriptions.Item label="测试时间">{s("tested_at")}</Descriptions.Item>
          )}
          {d.provider != null && (
            <Descriptions.Item label="Provider">{s("provider")}</Descriptions.Item>
          )}
          {d.model != null && (
            <Descriptions.Item label="Model">{s("model")}</Descriptions.Item>
          )}
          {d.api_style != null && (
            <Descriptions.Item label="API Style">{s("api_style")}</Descriptions.Item>
          )}
          {d.base_url != null && (
            <Descriptions.Item label="Base URL">{s("base_url")}</Descriptions.Item>
          )}
          {d.request_url != null && (
            <Descriptions.Item label="请求路径">{s("request_url")}</Descriptions.Item>
          )}
          {d.status_code != null && (
            <Descriptions.Item label="HTTP Status">
              <Tag color={d.status_code === 200 ? "green" : "red"}>{s("status_code")}</Tag>
            </Descriptions.Item>
          )}
          {d.proxy_enabled != null && (
            <Descriptions.Item label="代理">
              <Tag color={d.proxy_enabled ? "blue" : "default"}>
                {d.proxy_enabled ? "已启用" : "未启用"}
              </Tag>
            </Descriptions.Item>
          )}
          {d.host != null && (
            <Descriptions.Item label="Host">{s("host")}</Descriptions.Item>
          )}
          {d.key_path != null && (
            <Descriptions.Item label="Key Path">{s("key_path")}</Descriptions.Item>
          )}
          {d.exit_code != null && (
            <Descriptions.Item label="Exit Code">
              <Tag color={Number(d.exit_code) <= 1 ? "green" : "red"}>{s("exit_code")}</Tag>
            </Descriptions.Item>
          )}
          {d.username != null && (
            <Descriptions.Item label="用户名">{s("username")}</Descriptions.Item>
          )}
          {d.group_path != null && (
            <Descriptions.Item label="Group Path">{s("group_path")}</Descriptions.Item>
          )}
          {d.api_message != null && (
            <Descriptions.Item label="错误详情" span={2}>
              <Typography.Text type="danger">{s("api_message")}</Typography.Text>
            </Descriptions.Item>
          )}
          {d.error_type != null && (
            <Descriptions.Item label="错误类型">
              <Typography.Text type="danger">{s("error_type")}</Typography.Text>
            </Descriptions.Item>
          )}
        </Descriptions>
      )}
    </Card>
  );
}

export default function Settings() {
  const { message } = AntdApp.useApp();
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["settings"],
    queryFn: fetchSettings,
  });

  const [gitResult, setGitResult] = useState<TestResult | null>(null);
  const [sshResult, setSshResult] = useState<TestResult | null>(null);
  const [llmResult, setLlmResult] = useState<TestResult | null>(null);

  const gitMut = useMutation({
    mutationFn: testGit,
    onSuccess: (r) => {
      setGitResult(r);
      r.ok ? message.success(r.message) : message.error(r.message);
    },
  });
  const sshMut = useMutation({
    mutationFn: testSSH,
    onSuccess: (r) => {
      setSshResult(r);
      r.ok ? message.success(r.message) : message.error(r.message);
    },
  });
  const llmMut = useMutation({
    mutationFn: testLLM,
    onSuccess: (r) => {
      setLlmResult(r);
      r.ok ? message.success(r.message) : message.error(r.message);
    },
  });
  const reloadMut = useMutation({
    mutationFn: reloadSettings,
    onSuccess: (r) => {
      message.success(r.message);
      refetch();
    },
  });

  if (isLoading || !data) {
    return <Card loading title="设置" />;
  }

  const noProxy = !data.git.proxy.https_proxy && !data.git.proxy.http_proxy && !data.git.proxy.all_proxy;

  return (
    <Space direction="vertical" size="large" className="w-full">
      <Card
        title={
          <div className="flex items-center justify-between">
            <Typography.Title level={4} className="!m-0">
              设置 (只读)
            </Typography.Title>
            <Space>
              <Button onClick={() => gitMut.mutate()} loading={gitMut.isPending}>
                测试 AntCode API
              </Button>
              <Button onClick={() => sshMut.mutate()} loading={sshMut.isPending}>
                测试 SSH 连接
              </Button>
              <Button onClick={() => llmMut.mutate()} loading={llmMut.isPending}>
                测试 LLM 连接
              </Button>
              <Button onClick={() => reloadMut.mutate()} loading={reloadMut.isPending}>
                刷新配置
              </Button>
            </Space>
          </div>
        }
      >
        <Alert
          type="info"
          showIcon
          message={`运行环境:${data.app_env}`}
          description="第一阶段所有配置只读。如需修改,请编辑 .env / .env.local 后点击 刷新配置。"
        />
        {noProxy && (
          <Alert
            type="warning"
            showIcon
            className="mt-3"
            message="代理未配置"
            description="当前后端进程没有代理配置 (https_proxy / http_proxy / all_proxy 均为空),内网接口可能失败。"
          />
        )}
      </Card>

      {(gitResult || sshResult || llmResult) && (
        <Card title="最近一次连接测试结果">
          <TestResultPanel title="AntCode API 测试" result={gitResult} />
          <TestResultPanel title="SSH 连接测试" result={sshResult} />
          <TestResultPanel title="LLM 连接测试" result={llmResult} />
        </Card>
      )}

      <Card title="Git 设置 (AntCode)">
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="API base URL">{data.git.antcode_api_base_url}</Descriptions.Item>
          <Descriptions.Item label="Group URL">
            <a href={data.git.antcode_group_url} target="_blank" rel="noreferrer">
              {data.git.antcode_group_url}
            </a>
          </Descriptions.Item>
          <Descriptions.Item label="Namespace ID">{data.git.antcode_namespace_id}</Descriptions.Item>
          <Descriptions.Item label="PRIVATE-TOKEN">
            <Tag color={data.git.antcode_token_status === "configured" ? "green" : "red"}>
              {data.git.antcode_token_status === "configured" ? "已配置" : "未配置"}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="默认主分支">{data.git.default_branch}</Descriptions.Item>
          <Descriptions.Item label="草稿分支前缀">{data.git.draft_branch_prefix}</Descriptions.Item>
          <Descriptions.Item label="发布后删除草稿分支">
            <Tag color={data.git.delete_draft_branch_after_publish ? "orange" : "default"}>
              {data.git.delete_draft_branch_after_publish ? "是" : "否"}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="SSH key">{data.git.ssh_key_path || "(未配置)"}</Descriptions.Item>
          <Descriptions.Item label="Repo URL template" span={2}>
            <code>{data.git.repo_url_template || "(未配置)"}</code>
          </Descriptions.Item>
          <Descriptions.Item label="自动创建仓库">
            <Tag color={data.git.auto_create_repository ? "green" : "default"}>
              {data.git.auto_create_repository ? "是 (PRIVATE-TOKEN 可用)" : "否"}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="代理">
            <div className="text-xs">
              <div>https: {data.git.proxy.https_proxy || "(无)"}</div>
              <div>http: {data.git.proxy.http_proxy || "(无)"}</div>
              <div>all: {data.git.proxy.all_proxy || "(无)"}</div>
            </div>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="LLM 设置">
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Provider">
            <Tag color={data.llm.provider === "mock" ? "default" : "blue"}>{data.llm.provider}</Tag>
            {data.llm.provider === "mock" && (
              <Typography.Text type="secondary" className="ml-2">
                (Mock 客户端,不会真正调用外部 API)
              </Typography.Text>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="API Style">
            <Tag color="blue">{data.llm.api_style}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Base URL">{data.llm.base_url || "(未配置)"}</Descriptions.Item>
          <Descriptions.Item label="Model">{data.llm.model}</Descriptions.Item>
          <Descriptions.Item label="Timeout">{data.llm.timeout_ms} ms</Descriptions.Item>
          <Descriptions.Item label="Token">
            <Tag color={data.llm.token_configured ? "green" : "red"}>
              {data.llm.token_configured ? "已配置" : "未配置"}
            </Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="系统限制">
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="单文件上限">{fmtBytes(data.limits.max_file_bytes)}</Descriptions.Item>
          <Descriptions.Item label="assets 上限">{fmtBytes(data.limits.max_asset_file_bytes)}</Descriptions.Item>
          <Descriptions.Item label="zip 上传上限">{fmtBytes(data.limits.max_upload_bytes)}</Descriptions.Item>
          <Descriptions.Item label="单 Skill 文件数上限">{data.limits.max_files_per_skill}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="规范校验">
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="启用规则">
            {data.spec.enabled_rules.map((r) => (
              <Tag key={r}>{r}</Tag>
            ))}
          </Descriptions.Item>
          <Descriptions.Item label="SKILL.md 规则">
            <ul className="pl-5 list-disc">
              {data.spec.skill_md_rules.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </Descriptions.Item>
          <Descriptions.Item label="路径规则">
            <ul className="pl-5 list-disc">
              {data.spec.path_rules.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  );
}
