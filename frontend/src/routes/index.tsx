import { createBrowserRouter, Navigate } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import Workbench from "@/pages/Workbench";
import SkillList from "@/pages/SkillList";
import SkillNew from "@/pages/SkillNew";
import SkillDetail from "@/pages/SkillDetail";
import SkillEdit from "@/pages/SkillEdit";
import SkillVersions from "@/pages/SkillVersions";
import SkillDiff from "@/pages/SkillDiff";
import LLMJobs from "@/pages/LLMJobs";
import AuditLogs from "@/pages/AuditLogs";
import Settings from "@/pages/Settings";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Workbench /> },
      { path: "skills", element: <SkillList /> },
      { path: "skills/new", element: <SkillNew /> },
      { path: "skills/:id", element: <SkillDetail /> },
      { path: "skills/:id/edit", element: <SkillEdit /> },
      { path: "skills/:id/versions", element: <SkillVersions /> },
      { path: "skills/:id/diff", element: <SkillDiff /> },
      { path: "llm-jobs", element: <LLMJobs /> },
      { path: "settings", element: <Settings /> },
      { path: "audit-logs", element: <AuditLogs /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
