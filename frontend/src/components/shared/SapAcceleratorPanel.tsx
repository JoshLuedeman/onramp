import { useState } from "react";
import {
  Card,
  CardHeader,
  Text,
  Badge,
  Button,
  Dropdown,
  Option,
  Spinner,
  MessageBar,
  MessageBarBody,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ServerRegular,
  DatabaseRegular,
  CheckmarkCircleRegular,
} from "@fluentui/react-icons";
import type {
  SapQuestion,
  SapCertifiedSku,
  SapBestPractice,
} from "../../services/api";

export interface SapAcceleratorPanelProps {
  questions: SapQuestion[];
  skus: SapCertifiedSku[];
  bestPractices: SapBestPractice[];
  loading?: boolean;
  error?: string | null;
  onProductSelect?: (product: string) => void;
  onDatabaseSelect?: (database: string) => void;
  onGenerateArchitecture?: (answers: Record<string, string>) => void;
  onApply?: (config: SapConfig) => void;
}

export interface SapConfig {
  selectedProduct: string;
  selectedDatabase: string;
  highAvailability: boolean;
  disasterRecovery: boolean;
}

/** SAP product options. */
const SAP_PRODUCTS = [
  { value: "s4hana", label: "SAP S/4HANA" },
  { value: "ecc", label: "SAP ECC" },
  { value: "bw4hana", label: "SAP BW/4HANA" },
  { value: "business_suite", label: "SAP Business Suite" },
  { value: "crm", label: "SAP CRM" },
];

/** SAP database options. */
const SAP_DATABASES = [
  { value: "hana", label: "SAP HANA" },
  { value: "sql_server", label: "Microsoft SQL Server" },
  { value: "oracle", label: "Oracle" },
  { value: "db2", label: "IBM DB2" },
  { value: "maxdb", label: "SAP MaxDB" },
];

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
    padding: tokens.spacingVerticalL,
  },
  header: {
    marginBottom: tokens.spacingVerticalS,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
    gap: tokens.spacingHorizontalM,
  },
  card: {
    cursor: "pointer",
    "&:hover": {
      boxShadow: tokens.shadow8,
    },
  },
  selectedCard: {
    cursor: "pointer",
    borderTopColor: tokens.colorBrandBackground,
    borderRightColor: tokens.colorBrandBackground,
    borderBottomColor: tokens.colorBrandBackground,
    borderLeftColor: tokens.colorBrandBackground,
    borderTopWidth: "2px",
    borderRightWidth: "2px",
    borderBottomWidth: "2px",
    borderLeftWidth: "2px",
    boxShadow: tokens.shadow8,
  },
  section: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
    marginTop: tokens.spacingVerticalM,
  },
  skuTable: {
    width: "100%",
    borderCollapse: "collapse" as const,
    marginTop: tokens.spacingVerticalS,
  },
  practiceItem: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
    padding: tokens.spacingVerticalXS,
  },
  controls: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    alignItems: "flex-end",
    flexWrap: "wrap" as const,
  },
  dropdownField: {
    minWidth: "200px",
  },
});

export default function SapAcceleratorPanel({
  questions,
  skus,
  bestPractices,
  loading = false,
  error = null,
  onProductSelect,
  onDatabaseSelect,
  onGenerateArchitecture,
  onApply,
}: SapAcceleratorPanelProps) {
  const styles = useStyles();
  const [selectedProduct, setSelectedProduct] = useState("");
  const [selectedDatabase, setSelectedDatabase] = useState("");

  if (loading) {
    return (
      <div data-testid="sap-loading" className={styles.container}>
        <Spinner label="Loading SAP accelerator…" />
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="sap-error" className={styles.container}>
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      </div>
    );
  }

  const handleProductChange = (value: string) => {
    setSelectedProduct(value);
    onProductSelect?.(value);
  };

  const handleDatabaseChange = (value: string) => {
    setSelectedDatabase(value);
    onDatabaseSelect?.(value);
  };

  const handleApply = () => {
    onApply?.({
      selectedProduct,
      selectedDatabase,
      highAvailability: true,
      disasterRecovery: false,
    });
  };

  const handleGenerate = () => {
    onGenerateArchitecture?.({
      sap_product: selectedProduct,
      sap_database: selectedDatabase,
    });
  };

  // Filter HANA-tier SKUs for display
  const hanaSkus = skus.filter((s) => s.tier === "hana");
  const appSkus = skus.filter((s) => s.tier === "app");

  return (
    <div className={styles.container} data-testid="sap-panel">
      {/* Header */}
      <Text size={600} weight="semibold" className={styles.header}>
        SAP on Azure Accelerator
      </Text>
      <Text size={300}>
        Configure your SAP workload for Azure with certified VM SKUs, HANA
        sizing, and HA/DR patterns.
      </Text>

      {/* Product & Database Selection */}
      <div className={styles.controls}>
        <div className={styles.dropdownField}>
          <Text size={300} weight="semibold">
            SAP Product
          </Text>
          <Dropdown
            placeholder="Select SAP product"
            data-testid="sap-product-dropdown"
            onOptionSelect={(_ev, data) => {
              if (data.optionValue) handleProductChange(data.optionValue);
            }}
          >
            {SAP_PRODUCTS.map((p) => (
              <Option key={p.value} value={p.value}>
                {p.label}
              </Option>
            ))}
          </Dropdown>
        </div>

        <div className={styles.dropdownField}>
          <Text size={300} weight="semibold">
            Database
          </Text>
          <Dropdown
            placeholder="Select database"
            data-testid="sap-database-dropdown"
            onOptionSelect={(_ev, data) => {
              if (data.optionValue) handleDatabaseChange(data.optionValue);
            }}
          >
            {SAP_DATABASES.map((d) => (
              <Option key={d.value} value={d.value}>
                {d.label}
              </Option>
            ))}
          </Dropdown>
        </div>
      </div>

      {/* Questions Summary */}
      {questions.length > 0 && (
        <div className={styles.section}>
          <Text size={400} weight="semibold">
            Questionnaire ({questions.length} questions)
          </Text>
          <Text size={200}>
            Complete the SAP-specific questionnaire to generate an optimised
            architecture.
          </Text>
        </div>
      )}

      {/* HANA-certified SKUs */}
      {hanaSkus.length > 0 && (
        <div className={styles.section}>
          <Text size={400} weight="semibold">
            <DatabaseRegular /> HANA-Certified VM SKUs
          </Text>
          <div className={styles.grid}>
            {hanaSkus.map((sku) => (
              <Card
                key={sku.name}
                className={styles.card}
                data-testid={`sap-sku-${sku.name}`}
              >
                <CardHeader
                  header={<Text weight="semibold">{sku.name}</Text>}
                  description={sku.description}
                  action={
                    <Badge appearance="outline" color="informative">
                      {sku.series}
                    </Badge>
                  }
                />
                <Text size={200}>
                  {sku.vcpus} vCPUs · {sku.memory_gb} GB ·{" "}
                  {sku.saps_rating.toLocaleString()} SAPS
                </Text>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* App server SKUs */}
      {appSkus.length > 0 && (
        <div className={styles.section}>
          <Text size={400} weight="semibold">
            <ServerRegular /> Application Server SKUs
          </Text>
          <div className={styles.grid}>
            {appSkus.map((sku) => (
              <Card
                key={sku.name}
                className={styles.card}
                data-testid={`sap-sku-${sku.name}`}
              >
                <CardHeader
                  header={<Text weight="semibold">{sku.name}</Text>}
                  description={sku.description}
                />
                <Text size={200}>
                  {sku.vcpus} vCPUs · {sku.memory_gb} GB ·{" "}
                  {sku.saps_rating.toLocaleString()} SAPS
                </Text>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Best Practices */}
      {bestPractices.length > 0 && (
        <div className={styles.section}>
          <Text size={400} weight="semibold">
            Best Practices ({bestPractices.length})
          </Text>
          {bestPractices.slice(0, 5).map((bp) => (
            <div key={bp.id} className={styles.practiceItem}>
              <CheckmarkCircleRegular />
              <div>
                <Text size={300} weight="semibold">
                  {bp.title}
                </Text>
                <br />
                <Text size={200}>{bp.description}</Text>
                <Badge
                  appearance="filled"
                  color={bp.severity === "critical" ? "danger" : "warning"}
                  style={{ marginLeft: 8 }}
                >
                  {bp.severity}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className={styles.controls} style={{ marginTop: 16 }}>
        <Button
          appearance="primary"
          data-testid="sap-generate-button"
          disabled={!selectedProduct || !selectedDatabase}
          onClick={handleGenerate}
        >
          Generate Architecture
        </Button>
        <Button
          appearance="secondary"
          data-testid="sap-apply-button"
          disabled={!selectedProduct}
          onClick={handleApply}
        >
          Apply Configuration
        </Button>
      </div>
    </div>
  );
}
