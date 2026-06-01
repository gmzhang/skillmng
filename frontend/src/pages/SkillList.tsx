import { useState } from "react";
import {
  Table,
  Button,
  Input,
  Space,
  Tag,
  App as AntdApp,
  Typography,
  Card,
  Tooltip,
  Select,
  Dropdown,
  Empty,
} from "antd";
import {
  PlusOutlined,
  ImportOutlined,
  DownloadOutlined,
  EyeOutlined,
  EditOutlined,
  HistoryOutlined,
  DeleteOutlined,
  CheckCircleFilled,
  WarningFilled,
  CloseCircleFilled,
  CloudUploadOutlined,
  LinkOutlined,
  InboxOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnsType } from "antd/es/table";
import { listSkills, deleteSkill } from "@/api/skills";
import { importZip, exportSkillUrl } from "@/api/importexport";
import type { SkillListItem } from "@/types";

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

const VALIDATION_ICON: Record<string, React.ReactNode> = {
  valid: <CheckCircleFilled style={{ color: "#52c41a" }} />,
  warning: <WarningFilled style={{ color: "#faad14" }} />,
  error: <CloseCircleFilled style={{ color: "#ff4d4f" }} />,
};

export default function SkillList() {
  const [q, setQ] = useState("");
  const [pendingQ, setPendingQ] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { message, modal } = AntdApp.useApp();

  const { data, isLoading } = useQuery({
    queryKey: ["skills", q, statusFilter],
    queryFn: () => listSkills({ q: q || undefined, status: statusFilter }),
  });

  const displayed = (data ?? []).filter((s) =>
    statusFilter ? true : s.status !== "deleted",
  );

  const delMut = useMutation({
    mutationFn: (id: number) => deleteSkill(id),
    onSuccess: () => {
      message.success("已删除");
      qc.invalidateQueries({ queryKey: ["skills"] });
    },
  });

  const importMut = useMutation({
    mutationFn: (file: File) => importZip(file),
    onSuccess: (r) => {
      message.success(`已导入 ${r.name},共 ${r.file_count} 个文件`);
      qc.invalidateQueries({ queryKey: ["skills"] });
    },
    onError: (e: { response?: { data?: { message?: string } } }) =>
      message.error(e?.response?.data?.message ?? "导入失败"),
  });

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".zip";
    input.onchange = () => {
      const f = input.files?.[0];
      if (f) importMut.mutate(f);
    };
    input.click();
  };

  const columns: ColumnsType<SkillListItem> = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      width: 220,
      render: (name: string, row) => (
        <Space>
          <Tooltip
            title={
              row.validation_status === "valid"
                ? "校验通过"
                : row.validation_status === "warning"
                ? "有警告"
                : "有错误"
            }
          >
            {VALIDATION_ICON[row.validation_status]}
          </Tooltip>
          <a onClick={() => navigate(`/skills/${row.id}`)}>{name}</a>
        </Space>
      ),
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      ellipsis: { showTitle: false },
      render: (text: string) => (
        <Tooltip title={text}>
          <span>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 96,
      render: (s: string) => <Tag color={STATUS_COLOR[s]}>{STATUS_ZH[s]}</Tag>,
    },
    {
      title: "当前版本",
      dataIndex: "current_version",
      key: "current_version",
      width: 110,
      render: (v?: string | null) => (v ? <Tag color="purple">v{v}</Tag> : "-"),
    },
    {
      title: "Git",
      dataIndex: "git_bound",
      key: "git_bound",
      width: 130,
      render: (_: unknown, row) => (
        <Space size={4} direction="vertical">
          {row.git_bound ? (
            row.git_web_url ? (
              <a href={row.git_web_url} target="_blank" rel="noreferrer">
                <LinkOutlined /> 已绑定
              </a>
            ) : (
              <Tag color="green">已绑定</Tag>
            )
          ) : (
            <Tag>未绑定</Tag>
          )}
          {row.draft_status && row.draft_status !== "none" && !row.published_commit_sha && (
            <Tag color="orange" style={{ fontSize: 11 }}>有草稿</Tag>
          )}
          {row.draft_status && row.draft_status !== "none" && row.published_commit_sha && (
            <Tag color="blue" style={{ fontSize: 11 }}>有未发布草稿</Tag>
          )}
        </Space>
      ),
    },
    { title: "文件数", dataIndex: "file_count", key: "file_count", width: 80 },
    {
      title: "最近更新",
      dataIndex: "updated_at",
      key: "updated_at",
      width: 170,
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: "操作",
      key: "action",
      width: 220,
      fixed: "right",
      render: (_, row) => (
        <Space size="small">
          <Tooltip title="详情">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/skills/${row.id}`)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => navigate(`/skills/${row.id}/edit`)}
            />
          </Tooltip>
          <Tooltip title="版本">
            <Button
              size="small"
              icon={<HistoryOutlined />}
              onClick={() => navigate(`/skills/${row.id}/versions`)}
            />
          </Tooltip>
          <Tooltip title="导出 zip">
            <Button
              size="small"
              icon={<DownloadOutlined />}
              href={exportSkillUrl(row.id)}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              disabled={row.status === "deleted"}
              onClick={() =>
                modal.confirm({
                  title: "确认删除该 Skill?",
                  content: "软删除,Git 历史保留;不可在系统内继续使用。",
                  okText: "删除",
                  okButtonProps: { danger: true },
                  onOk: () => delMut.mutateAsync(row.id),
                })
              }
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <Typography.Title level={4} className="!m-0">
          Skill 列表
        </Typography.Title>
        <Space>
          <Input.Search
            placeholder="按名称/描述搜索"
            value={pendingQ}
            allowClear
            onChange={(e) => setPendingQ(e.target.value)}
            onSearch={(v) => setQ(v)}
            style={{ width: 240 }}
          />
          <Select
            placeholder="状态"
            allowClear
            value={statusFilter}
            onChange={setStatusFilter}
            style={{ width: 120 }}
            options={[
              { value: "draft", label: "草稿" },
              { value: "published", label: "已发布" },
              { value: "archived", label: "已归档" },
              { value: "deleted", label: "已删除" },
            ]}
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate("/skills/new")}
          >
            创建 Skill
          </Button>
          <Dropdown
            menu={{
              items: [
                {
                  key: "zip",
                  icon: <ImportOutlined />,
                  label: "上传 zip 导入",
                  onClick: handleImport,
                },
                {
                  key: "md",
                  icon: <CloudUploadOutlined />,
                  label: "粘贴 SKILL.md (走创建页)",
                  onClick: () => navigate("/skills/new"),
                },
                {
                  key: "git",
                  icon: <LinkOutlined />,
                  label: (
                    <Tooltip title="请先创建或进入某个 Skill 详情后绑定 remote">
                      绑定 Git remote (详情页)
                    </Tooltip>
                  ),
                  disabled: true,
                },
              ],
            }}
          >
            <Button>导入 ▾</Button>
          </Dropdown>
        </Space>
      </div>
      <Typography.Text type="secondary" className="mb-2 block">
        {displayed.length} 个结果
      </Typography.Text>
      {!isLoading && displayed.length === 0 ? (
        <Empty
          image={<InboxOutlined style={{ fontSize: 48, color: "#999" }} />}
          description={
            <Space direction="vertical" size="small">
              <Typography.Text strong>暂无 Skill</Typography.Text>
              <Typography.Text type="secondary">
                当前用户还没有 Skill,数据按 Cookie 用户隔离。
              </Typography.Text>
            </Space>
          }
        >
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate("/skills/new")}
            >
              创建 Skill
            </Button>
            <Button icon={<ImportOutlined />} onClick={handleImport}>
              上传 zip 导入
            </Button>
          </Space>
        </Empty>
      ) : (
        <Table
          rowKey="id"
          loading={isLoading}
          columns={columns}
          dataSource={displayed}
          pagination={{ pageSize: 20 }}
          scroll={{ x: 1200 }}
        />
      )}
    </Card>
  );
}
