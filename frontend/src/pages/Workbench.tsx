import {
  Card,
  Typography,
  Empty,
  Space,
  Button,
  Row,
  Col,
  Statistic,
  Tag,
  List,
  Skeleton,
} from "antd";
import {
  PlusOutlined,
  ImportOutlined,
  AppstoreOutlined,
  RocketOutlined,
  RobotOutlined,
  AuditOutlined,
} from "@ant-design/icons";
import { useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchMe } from "@/api/client";
import { fetchWorkbenchStats, fetchSettings } from "@/api/settings";
import type { Me } from "@/types";

const STATUS_ZH: Record<string, string> = {
  draft: "草稿",
  published: "已发布",
  archived: "已归档",
  deleted: "已删除",
};
const STATUS_COLOR: Record<string, string> = {
  draft: "blue",
  published: "green",
  archived: "default",
  deleted: "red",
};

export default function Workbench() {
  const navigate = useNavigate();
  const { data: me } = useQuery<Me>({
    queryKey: ["me"],
    queryFn: fetchMe,
    retry: false,
  });
  const { data: stats, isLoading } = useQuery({
    queryKey: ["workbench-stats"],
    queryFn: fetchWorkbenchStats,
  });
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: fetchSettings,
  });

  const isEmpty = !isLoading && stats && stats.skill_total === 0;

  return (
    <Space direction="vertical" size="large" className="w-full">
      <Card>
        <Typography.Title level={3} className="!m-0">
          欢迎,{me?.user_name ?? me?.user_id ?? "..."}
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="!mt-2 !mb-0">
          这里是 Skill 工作台。所有 Skill、版本、LLM 任务都按当前 Cookie 用户隔离。
        </Typography.Paragraph>
        <Space className="mt-3">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate("/skills/new")}
          >
            创建 Skill
          </Button>
          <Button icon={<ImportOutlined />} onClick={() => navigate("/skills")}>
            导入 / 导出
          </Button>
        </Space>
      </Card>

      {settings && (
        <Card title="环境健康" size="small">
          <Space wrap>
            <Tag>用户: {me?.user_id ?? "..."}</Tag>
            <Tag color={settings.llm.provider === "mock" ? "default" : "blue"}>
              LLM: {settings.llm.provider} / {settings.llm.model}
            </Tag>
            <Tag color={settings.git.antcode_token_status === "configured" ? "green" : "red"}>
              AntCode Token: {settings.git.antcode_token_status === "configured" ? "已配置" : "未配置"}
            </Tag>
            <Tag color={settings.llm.token_configured ? "green" : "red"}>
              LLM Token: {settings.llm.token_configured ? "已配置" : "未配置"}
            </Tag>
            {!settings.git.proxy.https_proxy && !settings.git.proxy.http_proxy && (
              <Tag color="orange">代理: 未配置</Tag>
            )}
            {(settings.git.proxy.https_proxy || settings.git.proxy.http_proxy) && (
              <Tag color="blue">代理: 已配置</Tag>
            )}
            {stats && (
              <Tag color={stats.skill_total > 0 ? "green" : "default"}>
                数据库: {stats.skill_total > 0 ? `${stats.skill_total} 个 Skill` : "空"}
              </Tag>
            )}
          </Space>
        </Card>
      )}

      {isLoading && <Skeleton active />}

      {isEmpty ? (
        <Card title="开始使用">
          <Empty
            description={
              <Space direction="vertical" size="small" className="text-center">
                <span>还没有 Skill,选择一种方式开始:</span>
                <Typography.Text type="secondary" className="text-xs">
                  保存草稿先进入 draft branch,发布后合并到 master 并打 tag。
                </Typography.Text>
              </Space>
            }
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Space>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate("/skills/new")}
              >
                手动创建 Skill
              </Button>
              <Button
                icon={<RobotOutlined />}
                onClick={() => navigate("/skills/new?tab=llm")}
              >
                LLM 辅助创建
              </Button>
              <Button
                icon={<ImportOutlined />}
                onClick={() => navigate("/skills")}
              >
                从 zip / Git 导入
              </Button>
            </Space>
          </Empty>
        </Card>
      ) : (
        stats && (
          <>
            <Row gutter={16}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="Skill 总数"
                    value={stats.skill_total}
                    prefix={<AppstoreOutlined />}
                  />
                  <div className="mt-2 text-xs text-gray-500">
                    草稿 {stats.skill_draft} · 已发布 {stats.skill_published} · 归档 {stats.skill_archived}
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="版本总数"
                    value={stats.version_total}
                    prefix={<RocketOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="LLM 任务总数"
                    value={stats.llm_total}
                    prefix={<RobotOutlined />}
                  />
                  <div className="mt-2 text-xs text-gray-500">
                    进行中 {stats.llm_running}
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="近期审计"
                    value={stats.recent_audits.length}
                    prefix={<AuditOutlined />}
                  />
                  <div className="mt-2 text-xs text-gray-500">
                    最近 8 条
                  </div>
                </Card>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={8}>
                <Card title="最近更新的 Skill" size="small">
                  <List
                    size="small"
                    dataSource={stats.recent_skills}
                    locale={{ emptyText: "暂无" }}
                    renderItem={(s) => (
                      <List.Item
                        actions={[
                          <Link key="view" to={`/skills/${s.id}`}>查看</Link>,
                        ]}
                      >
                        <Space>
                          <Tag color={STATUS_COLOR[s.status]}>{STATUS_ZH[s.status]}</Tag>
                          <span>{s.name}</span>
                          {s.current_version && (
                            <Tag color="purple">v{s.current_version}</Tag>
                          )}
                        </Space>
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card title="最近发布版本" size="small">
                  <List
                    size="small"
                    dataSource={stats.recent_versions}
                    locale={{ emptyText: "暂无" }}
                    renderItem={(v) => (
                      <List.Item
                        actions={[
                          <Link
                            key="view"
                            to={`/skills/${v.skill_id}/versions`}
                          >
                            版本
                          </Link>,
                        ]}
                      >
                        <Space>
                          <Tag color="purple">v{v.version}</Tag>
                          <span>{v.skill_name ?? `#${v.skill_id}`}</span>
                          <code className="text-xs text-gray-500">
                            {v.git_commit_sha.slice(0, 9)}
                          </code>
                        </Space>
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card title="最近动态" size="small">
                  <List
                    size="small"
                    dataSource={stats.recent_audits}
                    locale={{ emptyText: "暂无" }}
                    renderItem={(a) => (
                      <List.Item>
                        <div className="flex flex-col w-full">
                          <span className="text-xs text-gray-500">
                            {new Date(a.created_at).toLocaleString()}
                          </span>
                          <span>
                            <Tag>{a.action}</Tag>
                            {a.summary}
                          </span>
                        </div>
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
            </Row>
          </>
        )
      )}
    </Space>
  );
}
