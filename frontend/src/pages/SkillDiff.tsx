import {
  Card,
  Select,
  Space,
  Empty,
  Tag,
  Row,
  Col,
  Typography,
  Button,
  Switch,
  Alert,
} from "antd";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { DiffEditor } from "@monaco-editor/react";
import { listVersions, diffVersions } from "@/api/versions";
import { languageOf } from "@/components/MarkdownEditor";

const CHANGE_COLOR: Record<string, string> = {
  added: "green",
  removed: "red",
  modified: "gold",
};

export default function SkillDiff() {
  const { id } = useParams<{ id: string }>();
  const [sp, setSp] = useSearchParams();
  const navigate = useNavigate();
  const skillId = Number(id);

  const fromInit = sp.get("from") ? Number(sp.get("from")) : undefined;
  const toInit = sp.get("to") ? Number(sp.get("to")) : undefined;
  const [from, setFrom] = useState<number | undefined>(fromInit);
  const [to, setTo] = useState<number | undefined>(toInit);
  const [activePath, setActivePath] = useState<string>("");
  const [wordWrap, setWordWrap] = useState(false);

  const { data: versions } = useQuery({
    queryKey: ["skill", skillId, "versions"],
    queryFn: () => listVersions(skillId),
  });

  const { data: diff, error: diffError } = useQuery({
    queryKey: ["skill", skillId, "diff", from, to],
    queryFn: () => diffVersions(skillId, from!, to!),
    enabled: !!from && !!to && from !== to,
    retry: false,
  });

  const versionOptions = useMemo(
    () =>
      (versions ?? []).map((v) => ({
        value: v.id,
        label: `v${v.version}  ·  ${v.git_commit_sha.slice(0, 7)}`,
      })),
    [versions],
  );

  const activeEntry = useMemo(
    () => diff?.files.find((f) => f.path === activePath) ?? diff?.files[0],
    [diff, activePath],
  );

  const counts = useMemo(() => {
    const c = { added: 0, modified: 0, removed: 0 };
    for (const f of diff?.files ?? []) {
      if (f.change in c) c[f.change as keyof typeof c]++;
    }
    return c;
  }, [diff]);

  const fromVersion = (versions ?? []).find((v) => v.id === from);
  const toVersion = (versions ?? []).find((v) => v.id === to);

  return (
    <Card
      title={
        <Space>
          <Typography.Title level={4} className="!m-0">
            版本对比
            {fromVersion && toVersion && (
              <span className="ml-3 text-sm text-gray-500">
                从 v{fromVersion.version} 到 v{toVersion.version}
              </span>
            )}
          </Typography.Title>
          <Button onClick={() => navigate(`/skills/${skillId}/versions`)}>
            返回版本历史
          </Button>
          <Button onClick={() => navigate(`/skills/${skillId}`)}>
            返回 Skill 详情
          </Button>
        </Space>
      }
    >
      <Space className="mb-4" wrap>
        <Select
          placeholder="基准版本 (from)"
          style={{ width: 280 }}
          options={versionOptions}
          value={from}
          onChange={(v) => {
            setFrom(v);
            sp.set("from", String(v));
            setSp(sp);
          }}
        />
        <Select
          placeholder="目标版本 (to)"
          style={{ width: 280 }}
          options={versionOptions}
          value={to}
          onChange={(v) => {
            setTo(v);
            sp.set("to", String(v));
            setSp(sp);
          }}
        />
      </Space>

      {diff && diff.files.length > 0 && (
        <Space className="mb-3">
          <Tag color="green">新增 {counts.added}</Tag>
          <Tag color="gold">修改 {counts.modified}</Tag>
          <Tag color="red">删除 {counts.removed}</Tag>
          <span className="ml-4 text-sm text-gray-500">自动换行</span>
          <Switch size="small" checked={wordWrap} onChange={setWordWrap} />
        </Space>
      )}

      {diffError ? (
        <Alert
          type="error"
          showIcon
          message="版本 diff 失败"
          description={
            (diffError as { response?: { data?: { message?: string } } })
              ?.response?.data?.message ?? String(diffError)
          }
          className="mb-4"
        />
      ) : !from || !to ? (
        <Empty description="请选择两个版本进行对比" />
      ) : diff?.files.length === 0 ? (
        <Empty description="两个版本内容相同" />
      ) : (
        <Row gutter={16}>
          <Col span={6}>
            <div className="border border-gray-200 rounded">
              {(diff?.files ?? []).map((f) => (
                <div
                  key={f.path}
                  onClick={() => setActivePath(f.path)}
                  className={`px-3 py-2 cursor-pointer border-b border-gray-100 ${
                    (activeEntry?.path ?? "") === f.path
                      ? "bg-blue-50"
                      : "hover:bg-gray-50"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Tag color={CHANGE_COLOR[f.change]}>{f.change}</Tag>
                    <span className="text-sm break-all">{f.path}</span>
                  </div>
                </div>
              ))}
            </div>
          </Col>
          <Col span={18}>
            {activeEntry && activeEntry.change === "removed" && (
              <Alert
                type="warning"
                showIcon
                message={`文件已删除: ${activeEntry.path}`}
                description="该文件在目标版本中不存在。左侧为旧版本内容。"
                className="mb-2"
              />
            )}
            {activeEntry && activeEntry.change === "added" && (
              <Alert
                type="success"
                showIcon
                message={`新增文件: ${activeEntry.path}`}
                description="该文件在基准版本中不存在。右侧为新版本内容。"
                className="mb-2"
              />
            )}
            {activeEntry && (
              <DiffEditor
                language={languageOf(activeEntry.path)}
                original={activeEntry.before ?? ""}
                modified={activeEntry.after ?? ""}
                height="60vh"
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  readOnly: true,
                  renderSideBySide: true,
                  wordWrap: wordWrap ? "on" : "off",
                  diffWordWrap: wordWrap ? "on" : "off",
                }}
              />
            )}
          </Col>
        </Row>
      )}
    </Card>
  );
}
