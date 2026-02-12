import { Suspense, lazy } from "react";
import { FluentProvider, webLightTheme, Spinner } from "@fluentui/react-components";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./auth";
import Layout from "./components/shared/Layout";
import HomePage from "./pages/HomePage";

const WizardPage = lazy(() => import("./pages/WizardPage"));
const ArchitecturePage = lazy(() => import("./pages/ArchitecturePage"));
const DeployPage = lazy(() => import("./pages/DeployPage"));

function App() {
  return (
    <AuthProvider>
      <FluentProvider theme={webLightTheme}>
        <BrowserRouter>
          <Layout>
            <Suspense fallback={<Spinner label="Loading..." style={{ margin: "40px auto" }} />}>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/wizard" element={<WizardPage />} />
                <Route path="/architecture" element={<ArchitecturePage />} />
                <Route path="/deploy" element={<DeployPage />} />
              </Routes>
            </Suspense>
          </Layout>
        </BrowserRouter>
      </FluentProvider>
    </AuthProvider>
  );
}

export default App;
