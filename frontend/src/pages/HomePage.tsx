import { useNavigate } from "react-router-dom";
import {
  Title1,
  Subtitle1,
  Button,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { RocketRegular } from "@fluentui/react-icons";

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "100vh",
    gap: "16px",
    padding: "32px",
  },
  title: {
    color: tokens.colorBrandForeground1,
  },
});

export default function HomePage() {
  const styles = useStyles();
  const navigate = useNavigate();

  return (
    <div className={styles.container}>
      <Title1 className={styles.title}>OnRamp</Title1>
      <Subtitle1>Azure Landing Zone Architect &amp; Deployer</Subtitle1>
      <Button appearance="primary" icon={<RocketRegular />} size="large" onClick={() => navigate("/wizard")}>
        Start Building Your Landing Zone
      </Button>
    </div>
  );
}
