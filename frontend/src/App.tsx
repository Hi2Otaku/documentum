import { Routes, Route, Navigate } from "react-router";
import { LoginPage } from "./pages/LoginPage";
import { TemplateListPage } from "./pages/TemplateListPage";
import { DesignerPage } from "./pages/DesignerPage";
import { DashboardPage } from "./pages/DashboardPage";
import { QueryPage } from "./pages/QueryPage";
import { InboxPage } from "./pages/InboxPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { WorkflowsPage } from "./pages/WorkflowsPage";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { AppShell } from "./components/layout/AppShell";
import { AdminRoute } from "./components/layout/AdminRoute";

export default function App() {
  return (
    <Routes>
      {/* Public route */}
      <Route path="/login" element={<LoginPage />} />

      {/* Redirect root to inbox */}
      <Route path="/" element={<Navigate to="/inbox" replace />} />

      {/* Protected routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/templates" element={<TemplateListPage />} />
          <Route path="/templates/:id/edit" element={<DesignerPage />} />
          <Route path="/inbox" element={<InboxPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/workflows" element={<WorkflowsPage />} />

          {/* Admin-only routes */}
          <Route element={<AdminRoute />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/query" element={<QueryPage />} />
          </Route>
        </Route>
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/inbox" replace />} />
    </Routes>
  );
}
