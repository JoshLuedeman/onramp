import { Suspense, lazy } from "react";
import { FluentProvider, webLightTheme } from "@fluentui/react-components";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./auth";
import Layout from "./components/shared/Layout";
import ErrorBoundary from "./components/shared/ErrorBoundary";
import PageSkeleton from "./components/shared/PageSkeleton";
import { ProjectProvider } from "./contexts/ProjectContext";
import DashboardPage from "./pages/DashboardPage";

const WizardPage = lazy(() => import("./pages/WizardPage"));
const ArchitecturePage = lazy(() => import("./pages/ArchitecturePage"));
const CompliancePage = lazy(() => import("./pages/CompliancePage"));
const BicepPage = lazy(() => import("./pages/BicepPage"));
const DeployPage = lazy(() => import("./pages/DeployPage"));
const ProjectDetailPage = lazy(() => import("./pages/ProjectDetailPage"));
const GapAnalysisPage = lazy(() => import("./pages/GapAnalysisPage"));

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
                    <ProjectProvider><ProjectDetailPage /></ProjectProvider>
                  } />
                  <Route path="/projects/:projectId/wizard" element={
                    <ProjectProvider><WizardPage /></ProjectProvider>
                  } />
                  <Route path="/projects/:projectId/architecture" element={
                    <ProjectProvider><ArchitecturePage /></ProjectProvider>
                  } />
                  <Route path="/projects/:projectId/compliance" element={
                    <ProjectProvider><CompliancePage /></ProjectProvider>
                  } />
                  <Route path="/projects/:projectId/bicep" element={
                    <ProjectProvider><BicepPage /></ProjectProvider>
                  } />
                  <Route path="/projects/:projectId/deploy" element={
                    <ProjectProvider><DeployPage /></ProjectProvider>
                  } />

                  {/* Legacy routes (backward compatibility) */}
                  <Route path="/wizard" element={<WizardPage />} />
                  <Route path="/architecture" element={<ArchitecturePage />} />
                  <Route path="/compliance" element={<CompliancePage />} />
                  <Route path="/bicep" element={<BicepPage />} />
                  <Route path="/deploy" element={<DeployPage />} />

                  {/* Gap analysis */}
                  <Route path="/gap-analysis/:scanId" element={<GapAnalysisPage />} />
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
