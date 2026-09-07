import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/authStore";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import WorkflowList from "./pages/WorkflowList";
import WorkflowDetail from "./pages/WorkflowDetail";
import ExecutionDetail from "./pages/ExecutionDetail";
import ApiKeys from "./pages/ApiKeys";
import SecurityFindings from "./pages/SecurityFindings";
import Policies from "./pages/Policies";
import AuditLog from "./pages/AuditLog";
import SettingsPage from "./pages/Settings";
import TestPlayground from "./pages/TestPlayground";
import Layout from "./components/Layout";

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuthStore();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login"    element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected — inside sidebar layout */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index                           element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard"                element={<Dashboard />} />
          <Route path="workflows"                element={<WorkflowList />} />
          <Route path="workflows/:workflowId"    element={<WorkflowDetail />} />
          <Route path="executions/:executionId"  element={<ExecutionDetail />} />
          <Route path="security-findings"         element={<SecurityFindings />} />
          <Route path="policies"                  element={<Policies />} />
          <Route path="audit-log"                element={<AuditLog />} />
          <Route path="settings"                 element={<SettingsPage />} />
          <Route path="api-keys"                 element={<ApiKeys />} />
          <Route path="test-playground"          element={<TestPlayground />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
