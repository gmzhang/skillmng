import { Tree, Empty } from "antd";
import { FileOutlined, FileMarkdownOutlined, FolderOutlined } from "@ant-design/icons";
import type { DataNode } from "antd/es/tree";
import type { SkillFile } from "@/types";

interface Props {
  files: SkillFile[];
  selected?: string;
  onSelect: (path: string) => void;
}

function buildTree(files: SkillFile[]): DataNode[] {
  type Node = { key: string; title: string; children: Map<string, Node>; isLeaf: boolean };
  const root = new Map<string, Node>();

  const ensure = (parent: Map<string, Node>, segments: string[], fullPath: string): void => {
    if (segments.length === 0) return;
    const head = segments[0];
    const rest = segments.slice(1);
    const isLeaf = rest.length === 0;
    let node = parent.get(head);
    if (!node) {
      node = {
        key: isLeaf ? fullPath : segments.slice(0, segments.length - rest.length).join("/"),
        title: head,
        children: new Map(),
        isLeaf,
      };
      parent.set(head, node);
    }
    if (!isLeaf) {
      ensure(node.children, rest, fullPath);
    }
  };

  for (const f of files) {
    const parts = f.path.split("/");
    ensure(root, parts, f.path);
  }

  const toData = (m: Map<string, Node>, prefix = ""): DataNode[] =>
    Array.from(m.values())
      .sort((a, b) => {
        // 目录优先,字母序
        if (a.isLeaf !== b.isLeaf) return a.isLeaf ? 1 : -1;
        return a.title.localeCompare(b.title);
      })
      .map<DataNode>((n) => {
        const fullPath = prefix ? `${prefix}/${n.title}` : n.title;
        const isMd = n.title.endsWith(".md");
        return {
          key: n.isLeaf ? fullPath : `dir:${fullPath}`,
          title: n.title,
          isLeaf: n.isLeaf,
          icon: n.isLeaf ? (isMd ? <FileMarkdownOutlined /> : <FileOutlined />) : <FolderOutlined />,
          children: n.isLeaf ? undefined : toData(n.children, fullPath),
        };
      });

  return toData(root);
}

export default function SkillFileTree({ files, selected, onSelect }: Props) {
  if (!files.length) {
    return <Empty description="尚无文件" />;
  }
  return (
    <Tree
      showIcon
      defaultExpandAll
      blockNode
      selectedKeys={selected ? [selected] : []}
      treeData={buildTree(files)}
      onSelect={(_, info) => {
        const node = info.node;
        if (node.isLeaf) {
          onSelect(String(node.key));
        }
      }}
    />
  );
}
