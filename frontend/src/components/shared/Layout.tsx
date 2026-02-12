import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  makeStyles,
  tokens,
  Text,
  Tab,
  TabList,
} from "@fluentui/react-components";
import {
  HomeRegular,
  ClipboardRegular,
  BuildingRegular,
  ShieldCheckmarkRegular,
  CodeRegular,
  RocketRegular,
} from "@fluentui/react-icons";
import AuthButton from "./AuthButton";

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
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
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
  const styles = useStyles();
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <Text className={styles.logo} onClick={() => navigate("/")}>
            🚀 OnRamp
          </Text>
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
        <AuthButton />
      </header>
      <main className={styles.content}>{children}</main>
    </div>
  );
}
