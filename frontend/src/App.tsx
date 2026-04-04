import { Routes, Route, Navigate } from "react-router";
import { LoginPage } from "./pages/LoginPage";
import { TemplateListPage } from "./pages/TemplateListPage";
import { DesignerPage } from "./pages/DesignerPage";
import { QueryPage } from "./pages/QueryPage";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { AppShell } from "./components/layout/AppShell";

export default function App() {
  return (
    <Routes>
      {/* Public route */}
      <Route path="/login" element={<LoginPage />} />

      {/* Redirect root to templates */}
      <Route path="/" element={<Navigate to="/templates" replace />} />

      {/* Protected routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/templates" element={<TemplateListPage />} />
          <Route
            path="/templates/:id/edit"
            element={<DesignerPage />}
          />
          <Route path="/query" element={<QueryPage />} />
        </Route>
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/templates" replace />} />
    </Routes>
  );
}
