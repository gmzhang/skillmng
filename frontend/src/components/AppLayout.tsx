import { Layout, Menu, Typography, Space, Avatar, Alert, Breadcrumb, Tooltip } from "antd";
import {
  AppstoreOutlined,
  PlusOutlined,
  RobotOutlined,
  SettingOutlined,
  AuditOutlined,
  HomeOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Outlet, useLocation, useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchMe } from "@/api/client";
import { getSkill } from "@/api/skills";
import type { Me } from "@/types";

const { Header, Sider, Content } = Layout;

const NAV_ITEMS = [
  { key: "/", icon: <HomeOutlined />, label: "工作台" },
  { key: "/skills", icon: <AppstoreOutlined />, label: "Skill 列表" },
  { key: "/skills/new", icon: <PlusOutlined />, label: "创建 Skill" },
  { key: "/llm-jobs", icon: <RobotOutlined />, label: "LLM 任务" },
  { key: "/audit-logs", icon: <AuditOutlined />, label: "审计日志" },
  { key: "/settings", icon: <SettingOutlined />, label: "设置" },
];

function pickSelectedKey(pathname: string): string {
  if (pathname === "/") return "/";
  // /skills/new 优先匹配创建,避免被 /skills 抢
  if (pathname.startsWith("/skills/new")) return "/skills/new";
  if (pathname.startsWith("/skills")) return "/skills";
  for (const item of NAV_ITEMS) {
    if (item.key === "/") continue;
    if (pathname === item.key || pathname.startsWith(item.key + "/")) return item.key;
  }
  return "/";
}

function buildBreadcrumb(pathname: string, skillName?: string): { title: React.ReactNode; key: string }[] {
  const crumbs: { title: React.ReactNode; key: string }[] = [
    { title: <Link to="/">工作台</Link>, key: "home" },
  ];
  if (pathname === "/") return crumbs;
  if (pathname.startsWith("/skills/new")) {
    crumbs.push({ title: <Link to="/skills">Skill 列表</Link>, key: "list" });
    crumbs.push({ title: "创建 Skill", key: "new" });
    return crumbs;
  }
  if (pathname.startsWith("/skills/")) {
    crumbs.push({ title: <Link to="/skills">Skill 列表</Link>, key: "list" });
    const m = pathname.match(/^\/skills\/(\d+)(?:\/(\w+))?/);
    if (m) {
      const id = m[1];
      const sub = m[2];
      const label = skillName || `#${id}`;
      const subZh: Record<string, string> = {
        edit: "编辑",
        versions: "版本历史",
        diff: "版本对比",
      };
      if (sub) {
        crumbs.push({
          title: <Link to={`/skills/${id}`}>{label}</Link>,
          key: "detail",
        });
        crumbs.push({ title: subZh[sub] ?? sub, key: "sub" });
      } else {
        crumbs.push({ title: label, key: "detail" });
      }
    }
    return crumbs;
  }
  if (pathname.startsWith("/skills")) {
    crumbs.push({ title: "Skill 列表", key: "list" });
    return crumbs;
  }
  const map: Record<string, string> = {
    "/llm-jobs": "LLM 任务",
    "/audit-logs": "审计日志",
    "/settings": "设置",
  };
  for (const [path, zh] of Object.entries(map)) {
    if (pathname === path || pathname.startsWith(path + "/")) {
      crumbs.push({ title: zh, key: path });
      break;
    }
  }
  return crumbs;
}

function useSkillIdFromPath(pathname: string): number | undefined {
  const m = pathname.match(/^\/skills\/(\d+)/);
  return m ? Number(m[1]) : undefined;
}

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { data, isError, error } = useQuery<Me>({
    queryKey: ["me"],
    queryFn: fetchMe,
    retry: false,
  });

  const skillId = useSkillIdFromPath(location.pathname);
  const { data: skillData } = useQuery({
    queryKey: ["skill", skillId],
    queryFn: () => getSkill(skillId!),
    enabled: skillId !== undefined,
    staleTime: 30_000,
  });

  const selectedKey = pickSelectedKey(location.pathname);
  const items = NAV_ITEMS.map((i) => ({
    key: i.key,
    icon: <Tooltip title={i.label}>{i.icon}</Tooltip>,
    label: i.label,
  }));

  return (
    <Layout className="min-h-screen">
      <Header className="flex items-center justify-between px-6 bg-white border-b border-gray-200">
        <Typography.Title level={4} className="!m-0 !text-gray-800">
          Skill 管理系统
        </Typography.Title>
        <Space>
          <Avatar icon={<UserOutlined />} />
          <span className="text-gray-700">
            {data?.user_name ?? data?.user_id ?? "未登录"}
          </span>
        </Space>
      </Header>
      <Layout>
        <Sider width={220} theme="light" className="border-r border-gray-200">
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            items={items}
            onClick={({ key }) => navigate(key as string)}
            className="h-full pt-2"
          />
        </Sider>
        <Content className="p-6 bg-gray-50">
          <Breadcrumb className="mb-3" items={buildBreadcrumb(location.pathname, skillData?.name)} />
          {isError && (() => {
            const e = error as {
              response?: { status?: number; data?: { message?: string } };
            };
            const status = e?.response?.status;
            const serverMessage = e?.response?.data?.message;
            if (status === 401) {
              return (
                <Alert
                  type="warning"
                  showIcon
                  message="无法识别登录用户"
                  description={
                    serverMessage ??
                    "请确认浏览器 Cookie 中含有 user_id;开发期可在 DevTools Application → Cookies 中手动添加。"
                  }
                  className="mb-4"
                />
              );
            }
            return (
              <Alert
                type="error"
                showIcon
                message={`后端 ${status ?? "网络"} 错误`}
                description={serverMessage ?? "请查看后端日志,或确认服务运行中。"}
                className="mb-4"
              />
            );
          })()}
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
