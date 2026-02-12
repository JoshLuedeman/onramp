import { FluentProvider, webLightTheme } from "@fluentui/react-components";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./auth";
import Layout from "./components/shared/Layout";
import HomePage from "./pages/HomePage";
import WizardPage from "./pages/WizardPage";
import ArchitecturePage from "./pages/ArchitecturePage";
import DeployPage from "./pages/DeployPage";

function App() {
  return (
    <AuthProvider>
      <FluentProvider theme={webLightTheme}>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/wizard" element={<WizardPage />} />
              <Route path="/architecture" element={<ArchitecturePage />} />
              <Route path="/deploy" element={<DeployPage />} />
            </Routes>
          </Layout>
        </BrowserRouter>
      </FluentProvider>
    </AuthProvider>
  );
}

export default App;
