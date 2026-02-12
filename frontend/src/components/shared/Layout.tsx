import type { ReactNode } from "react";
import { makeStyles, tokens, Text } from "@fluentui/react-components";
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
  logo: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase500,
    color: tokens.colorBrandForeground1,
  },
  content: {
    flex: 1,
  },
});

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const styles = useStyles();

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <Text className={styles.logo}>OnRamp</Text>
        <AuthButton />
      </header>
      <main className={styles.content}>{children}</main>
    </div>
  );
}
