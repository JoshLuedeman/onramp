import { Suspense, lazy } from "react";
import { FluentProvider, webLightTheme } from "@fluentui/react-components";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./auth";
import Layout from "./components/shared/Layout";
import ErrorBoundary from "./components/shared/ErrorBoundary";
import PageSkeleton from "./components/shared/PageSkeleton";
import ProtectedRoute from "./components/shared/ProtectedRoute";
import { ProjectProvider } from "./contexts/ProjectContext";
import DashboardPage from "./pages/DashboardPage";

const WizardPage = lazy(() => import("./pages/WizardPage"));
const ArchitecturePage = lazy(() => import("./pages/ArchitecturePage"));
const CompliancePage = lazy(() => import("./pages/CompliancePage"));
const BicepPage = lazy(() => import("./pages/BicepPage"));
const DeployPage = lazy(() => import("./pages/DeployPage"));
const ProjectDetailPage = lazy(() => import("./pages/ProjectDetailPage"));
const GapAnalysisPage = lazy(() => import("./pages/GapAnalysisPage"));
const WorkloadsPage = lazy(() => import("./pages/WorkloadsPage"));
const MigrationPage = lazy(() => import("./pages/MigrationPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const GovernancePage = lazy(() => import("./pages/GovernancePage"));
const ChatPage = lazy(() => import("./pages/ChatPage"));
const OutputPage = lazy(() => import("./pages/OutputPage"));
const MSPDashboardPage = lazy(() => import("./pages/MSPDashboardPage"));
const MarketplacePage = lazy(() => import("./pages/MarketplacePage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));

function App() {
  return (
    <AuthProvider>
      <FluentProvider theme={webLightTheme}>
        <BrowserRouter>
          <Layout>
            <ErrorBoundary>
              <Suspense fallback={<PageSkeleton />}>
                <Routes>
                  <Route path="/" element={<DashboardPage />} />

                  {/* Project-scoped routes */}
                  <Route path="/projects/:projectId" element={
                    <ProtectedRoute><ProjectProvider><ProjectDetailPage /></ProjectProvider></ProtectedRoute>
                  } />
                  <Route path="/projects/:projectId/wizard" element={
                    <ProtectedRoute><ProjectProvider><WizardPage /></ProjectProvider></ProtectedRoute>
                  } />
                  <Route path="/projects/:projectId/architecture" element={
                    <ProtectedRoute><ProjectProvider><ArchitecturePage /></ProjectProvider></ProtectedRoute>
                  } />
                  <Route path="/projects/:projectId/compliance" element={
                    <ProtectedRoute><ProjectProvider><CompliancePage /></ProjectProvider></ProtectedRoute>
                  } />
                  <Route path="/projects/:projectId/bicep" element={
                    <ProtectedRoute><ProjectProvider><BicepPage /></ProjectProvider></ProtectedRoute>
                  } />
                  <Route path="/projects/:projectId/deploy" element={
                    <ProtectedRoute><ProjectProvider><DeployPage /></ProjectProvider></ProtectedRoute>
                  } />

                  {/* Legacy routes — redirect to dashboard */}
                  <Route path="/wizard" element={<Navigate to="/" replace />} />
                  <Route path="/architecture" element={<Navigate to="/" replace />} />
                  <Route path="/compliance" element={<Navigate to="/" replace />} />
                  <Route path="/bicep" element={<Navigate to="/" replace />} />
                  <Route path="/deploy" element={<Navigate to="/" replace />} />

                  {/* Gap analysis */}
                  <Route path="/gap-analysis/:scanId" element={
                    <ProtectedRoute><GapAnalysisPage /></ProtectedRoute>
                  } />

                  {/* Workloads */}
                  <Route path="/workloads" element={<Navigate to="/projects" replace />} />
                  <Route path="/projects/:projectId/workloads" element={
                    <ProtectedRoute><ProjectProvider><WorkloadsPage /></ProjectProvider></ProtectedRoute>
                  } />
                  <Route path="/projects/:projectId/migration" element={
                    <ProtectedRoute><ProjectProvider><MigrationPage /></ProjectProvider></ProtectedRoute>
                  } />

                  {/* Admin */}
                  <Route path="/admin/plugins" element={
                    <ProtectedRoute><AdminPage /></ProtectedRoute>
                  } />

                  {/* Governance */}
                  <Route path="/governance" element={
                    <ProtectedRoute><GovernancePage /></ProtectedRoute>
                  } />
                  <Route path="/projects/:projectId/governance" element={
                    <ProtectedRoute><ProjectProvider><GovernancePage /></ProjectProvider></ProtectedRoute>
                  } />

                  {/* Chat */}
                  <Route path="/chat" element={
                    <ProtectedRoute><ChatPage /></ProtectedRoute>
                  } />
                  <Route path="/projects/:projectId/chat" element={
                    <ProtectedRoute><ProjectProvider><ChatPage /></ProjectProvider></ProtectedRoute>
                  } />

                  {/* Multi-format output */}
                  <Route path="/output" element={
                    <ProtectedRoute><OutputPage /></ProtectedRoute>
                  } />
                  <Route path="/projects/:projectId/output" element={
                    <ProtectedRoute><ProjectProvider><OutputPage /></ProjectProvider></ProtectedRoute>
                  } />

                  {/* MSP Dashboard */}
                  <Route path="/msp" element={
                    <ProtectedRoute><MSPDashboardPage /></ProtectedRoute>
                  } />
                  <Route path="/msp/tenants/:tenantId" element={
                    <ProtectedRoute><MSPDashboardPage /></ProtectedRoute>
                  } />

                  {/* Template Marketplace */}
                  <Route path="/marketplace" element={<MarketplacePage />} />

                  {/* 404 catch-all */}
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </Suspense>
            </ErrorBoundary>
          </Layout>
        </BrowserRouter>
      </FluentProvider>
    </AuthProvider>
  );
}

export default App;
