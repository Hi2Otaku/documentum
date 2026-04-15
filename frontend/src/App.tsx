import { Routes, Route, Navigate } from "react-router";
import { LoginPage } from "./pages/LoginPage";
import { TemplateListPage } from "./pages/TemplateListPage";
import { DesignerPage } from "./pages/DesignerPage";
import { DashboardPage } from "./pages/DashboardPage";
import { QueryPage } from "./pages/QueryPage";
import { InboxPage } from "./pages/InboxPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { SearchPage } from "./pages/SearchPage";
import { WorkflowsPage } from "./pages/WorkflowsPage";
import { BrowsePage } from "./pages/BrowsePage";
import { DocumentTypesPage } from "./pages/DocumentTypesPage";
import { FoldersPage } from "./pages/FoldersPage";
import { RetentionPage } from "./pages/RetentionPage";
import { QueueAdminPage } from "./pages/QueueAdminPage";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { AppShell } from "./components/layout/AppShell";
import { AdminRoute } from "./components/layout/AdminRoute";
import { NotificationPreferencesPage } from "./pages/NotificationPreferencesPage";
import { AuditVerificationPage } from "./pages/AuditVerificationPage";
import { SSOSettingsPage } from "./pages/SSOSettingsPage";
import { BulkJobsPage } from "./pages/BulkJobsPage";
import ImportExportPage from "./pages/ImportExportPage";
import { MonitoringPage } from "./pages/MonitoringPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";

export default function App() {
  return (
    <Routes>
      {/* Public route */}
      <Route path="/login" element={<LoginPage />} />

      {/* Redirect root to browse */}
      <Route path="/" element={<Navigate to="/browse" replace />} />

      {/* Protected routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/browse" element={<BrowsePage />} />
          <Route path="/templates" element={<TemplateListPage />} />
          <Route path="/templates/:id/edit" element={<DesignerPage />} />
          <Route path="/inbox" element={<InboxPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/workflows" element={<WorkflowsPage />} />
          <Route path="/settings/notifications" element={<NotificationPreferencesPage />} />
          <Route path="/bulk-jobs" element={<BulkJobsPage />} />

          {/* Admin-only routes */}
          <Route element={<AdminRoute />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/query" element={<QueryPage />} />
            <Route path="/admin/types" element={<DocumentTypesPage />} />
            <Route path="/admin/folders" element={<FoldersPage />} />
            <Route path="/admin/retention" element={<RetentionPage />} />
            <Route path="/admin/queues" element={<QueueAdminPage />} />
            <Route path="/admin/audit-verification" element={<AuditVerificationPage />} />
            <Route path="/admin/sso" element={<SSOSettingsPage />} />
            <Route path="/admin/import-export" element={<ImportExportPage />} />
            <Route path="/admin/monitoring" element={<MonitoringPage />} />
            <Route path="/admin/analytics" element={<AnalyticsPage />} />
          </Route>
        </Route>
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/browse" replace />} />
    </Routes>
  );
}
