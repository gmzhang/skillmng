import { Result } from "antd";

export default function Placeholder({ title, milestone }: { title: string; milestone: string }) {
  return (
    <Result
      status="info"
      title={title}
      subTitle={`此页面将在 ${milestone} 中实现`}
    />
  );
}
