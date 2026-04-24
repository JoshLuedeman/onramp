import { type ReactNode, useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  makeStyles,
  tokens,
  Text,
  Tab,
  TabList,
  Dropdown,
  Option,
  Button,
  Tooltip,
} from "@fluentui/react-components";
import {
  HomeRegular,
  ClipboardRegular,
  BuildingRegular,
  ShieldCheckmarkRegular,
  CodeRegular,
  RocketRegular,
  FolderRegular,
  QuestionCircleRegular,
} from "@fluentui/react-icons";
import AuthButton from "./AuthButton";
import TutorialOverlay from "./TutorialOverlay";
import { TutorialProvider, useTutorialContext } from "../../contexts/TutorialContext";
import { api } from "../../services/api";
import type { Project } from "../../types/project";

const useStyles = makeStyles({
  root: {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "8px 24px",
    borderBottom: `1px solid ${tokens.colorNeutralStroke1}`,
    backgroundColor: tokens.colorNeutralBackground1,
    "@media (max-width: 768px)": {
      flexDirection: "column",
      gap: "8px",
      padding: "8px 12px",
    },
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
    "@media (max-width: 768px)": {
      width: "100%",
      justifyContent: "space-between",
    },
  },
  tabListWrapper: {
    "@media (max-width: 768px)": {
      width: "100%",
      overflowX: "auto",
      WebkitOverflowScrolling: "touch",
      "::-webkit-scrollbar": { display: "none" },
    },
  },
  logo: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase500,
    color: tokens.colorBrandForeground1,
    cursor: "pointer",
  },
  content: {
    flex: 1,
  },
  projectSwitcher: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
});

const NAV_ITEMS = [
  { path: "/", label: "Home", icon: <HomeRegular /> },
  { path: "/wizard", label: "Wizard", icon: <ClipboardRegular /> },
  { path: "/architecture", label: "Architecture", icon: <BuildingRegular /> },
  { path: "/compliance", label: "Compliance", icon: <ShieldCheckmarkRegular /> },
  { path: "/bicep", label: "Bicep", icon: <CodeRegular /> },
  { path: "/deploy", label: "Deploy", icon: <RocketRegular /> },
];

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <TutorialProvider currentPath={location.pathname}>
      <LayoutInner>{children}</LayoutInner>
    </TutorialProvider>
  );
}

function LayoutInner({ children }: LayoutProps) {
  const styles = useStyles();
  const location = useLocation();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const tutorial = useTutorialContext();

  useEffect(() => {
    api.projects.list().then((res) => setProjects(res.projects)).catch(() => {});
  }, []);

  // Extract projectId from URL if on a project-scoped route
  const projectMatch = location.pathname.match(/^\/projects\/([^/]+)/);
  const activeProjectId = projectMatch ? projectMatch[1] : undefined;

  const handleProjectSelect = (_: unknown, data: { optionValue?: string }) => {
    if (data.optionValue) {
      navigate(`/projects/${data.optionValue}`);
    }
  };

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <Text className={styles.logo} onClick={() => navigate("/")}>
            🚀 OnRamp
          </Text>
          <div className={styles.tabListWrapper}>
            <TabList
              selectedValue={location.pathname}
              onTabSelect={(_, data) => navigate(data.value as string)}
              size="small"
            >
              {NAV_ITEMS.map((item) => (
                <Tab key={item.path} value={item.path} icon={item.icon}>
                  {item.label}
                </Tab>
              ))}
            </TabList>
          </div>
        </div>
        <div className={styles.projectSwitcher}>
          {projects.length > 0 && (
            <Dropdown
              placeholder="Switch project..."
              selectedOptions={activeProjectId ? [activeProjectId] : []}
              value={projects.find((p) => p.id === activeProjectId)?.name ?? ""}
              onOptionSelect={handleProjectSelect}
              size="small"
              aria-label="Switch project"
            >
              {projects.map((p) => (
                <Option key={p.id} value={p.id} text={p.name}>
                  <FolderRegular /> {p.name}
                </Option>
              ))}
            </Dropdown>
          )}
          <Tooltip content="Start tutorial" relationship="label">
            <Button
              appearance="subtle"
              icon={<QuestionCircleRegular />}
              onClick={tutorial.startTutorial}
              aria-label="Start tutorial"
              size="small"
            />
          </Tooltip>
          <AuthButton />
        </div>
      </header>
      <main className={styles.content}>{children}</main>
      <TutorialOverlay />
    </div>
  );
}
