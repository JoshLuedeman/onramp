import { useCallback, useEffect, useState } from "react";
import {
  Badge,
  Body1,
  Button,
  Card,
  CardHeader,
  Dropdown,
  Input,
  Option,
  Spinner,
  Subtitle2,
  Title1,
  Title2,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ArrowDownloadRegular,
  SearchRegular,
  ThumbDislikeRegular,
  ThumbLikeRegular,
} from "@fluentui/react-icons";
import { api } from "../services/api";

const INDUSTRIES = [
  "All",
  "Healthcare",
  "Financial Services",
  "Government",
  "Retail",
  "Startup",
];

const VISIBILITIES = ["All", "curated", "public", "private"];

interface TemplateItem {
  id: string;
  name: string;
  description: string | null;
  industry: string;
  tags: string[];
  architecture_json: string | null;
  visibility: string;
  download_count: number;
  rating_up: number;
  rating_down: number;
  created_at: string;
  updated_at: string;
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXXL,
    padding: tokens.spacingHorizontalXXL,
    maxWidth: "1200px",
    marginLeft: "auto",
    marginRight: "auto",
    width: "100%",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: tokens.spacingVerticalM,
  },
  filters: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    flexWrap: "wrap",
    alignItems: "center",
  },
  searchInput: {
    minWidth: "250px",
  },
  dropdown: {
    minWidth: "160px",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
    gap: tokens.spacingHorizontalL,
  },
  card: {
    minHeight: "220px",
    display: "flex",
    flexDirection: "column",
  },
  cardBody: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
    padding: tokens.spacingHorizontalM,
  },
  tags: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
    flexWrap: "wrap",
  },
  cardFooter: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: tokens.spacingHorizontalM,
    paddingTop: 0,
  },
  stats: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    alignItems: "center",
    color: tokens.colorNeutralForeground3,
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: tokens.spacingVerticalXXXL,
    gap: tokens.spacingVerticalM,
    color: tokens.colorNeutralForeground3,
  },
  loadingState: {
    display: "flex",
    justifyContent: "center",
    padding: tokens.spacingVerticalXXXL,
  },
  ratingButtons: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
  },
});

export default function MarketplacePage() {
  const styles = useStyles();
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [industry, setIndustry] = useState("All");
  const [visibility, setVisibility] = useState("All");
  const [usingTemplate, setUsingTemplate] = useState<string | null>(null);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (industry !== "All") params.industry = industry;
      if (visibility !== "All") params.visibility = visibility;
      const data = await api.templates.list(params);
      setTemplates(data.templates || []);
    } catch {
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  }, [industry, visibility]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleUseTemplate = async (templateId: string) => {
    setUsingTemplate(templateId);
    try {
      await api.templates.use(templateId, "default-project");
      await fetchTemplates();
    } catch {
      // Error handled silently — user sees count update
    } finally {
      setUsingTemplate(null);
    }
  };

  const handleRate = async (
    templateId: string,
    rating: "up" | "down",
  ) => {
    try {
      await api.templates.rate(templateId, rating);
      await fetchTemplates();
    } catch {
      // Silent — optimistic UI would be better but simple for now
    }
  };

  const filtered = templates.filter((t) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      t.name.toLowerCase().includes(q) ||
      (t.description ?? "").toLowerCase().includes(q) ||
      t.tags.some((tag) => tag.toLowerCase().includes(q))
    );
  });

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <Title1>Template Marketplace</Title1>
          <Body1>
            Browse and use curated architecture templates for your
            industry
          </Body1>
        </div>
      </div>

      <div className={styles.filters}>
        <Input
          className={styles.searchInput}
          placeholder="Search templates..."
          contentBefore={<SearchRegular />}
          value={search}
          onChange={(_e, data) => setSearch(data.value)}
          aria-label="Search templates"
        />
        <Dropdown
          className={styles.dropdown}
          placeholder="Industry"
          value={industry}
          selectedOptions={[industry]}
          onOptionSelect={(_e, data) =>
            setIndustry(data.optionValue ?? "All")
          }
          aria-label="Filter by industry"
        >
          {INDUSTRIES.map((ind) => (
            <Option key={ind} value={ind}>
              {ind}
            </Option>
          ))}
        </Dropdown>
        <Dropdown
          className={styles.dropdown}
          placeholder="Visibility"
          value={visibility}
          selectedOptions={[visibility]}
          onOptionSelect={(_e, data) =>
            setVisibility(data.optionValue ?? "All")
          }
          aria-label="Filter by visibility"
        >
          {VISIBILITIES.map((vis) => (
            <Option key={vis} value={vis}>
              {vis}
            </Option>
          ))}
        </Dropdown>
      </div>

      {loading && (
        <div className={styles.loadingState}>
          <Spinner label="Loading templates..." />
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className={styles.emptyState}>
          <Title2>No templates found</Title2>
          <Body1>
            Try adjusting your search or filters
          </Body1>
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div className={styles.grid}>
          {filtered.map((tpl) => (
            <Card key={tpl.id} className={styles.card}>
              <CardHeader
                header={<Subtitle2>{tpl.name}</Subtitle2>}
                description={
                  <Badge appearance="outline" color="informative">
                    {tpl.industry}
                  </Badge>
                }
              />
              <div className={styles.cardBody}>
                <Body1>{tpl.description}</Body1>
                <div className={styles.tags}>
                  {tpl.tags.slice(0, 4).map((tag) => (
                    <Badge
                      key={tag}
                      appearance="tint"
                      size="small"
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className={styles.cardFooter}>
                <div className={styles.stats}>
                  <span>
                    <ArrowDownloadRegular /> {tpl.download_count}
                  </span>
                  <span>
                    <ThumbLikeRegular /> {tpl.rating_up}
                  </span>
                  <span>
                    <ThumbDislikeRegular /> {tpl.rating_down}
                  </span>
                </div>
                <div className={styles.ratingButtons}>
                  <Button
                    size="small"
                    icon={<ThumbLikeRegular />}
                    onClick={() => handleRate(tpl.id, "up")}
                    aria-label={`Rate ${tpl.name} up`}
                  />
                  <Button
                    size="small"
                    icon={<ThumbDislikeRegular />}
                    onClick={() => handleRate(tpl.id, "down")}
                    aria-label={`Rate ${tpl.name} down`}
                  />
                  <Button
                    appearance="primary"
                    size="small"
                    onClick={() => handleUseTemplate(tpl.id)}
                    disabled={usingTemplate === tpl.id}
                  >
                    {usingTemplate === tpl.id
                      ? "Applying..."
                      : "Use Template"}
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
