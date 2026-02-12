import {
  Menu,
  MenuTrigger,
  MenuPopover,
  MenuList,
  MenuItem,
  Button,
} from "@fluentui/react-components";
import {
  ArrowDownloadRegular,
  DocumentRegular,
  ImageRegular,
  CodeRegular,
} from "@fluentui/react-icons";

interface ExportMenuProps {
  architecture: Record<string, any>;
}

export default function ExportMenu({ architecture }: ExportMenuProps) {
  const exportAsJson = () => {
    const blob = new Blob([JSON.stringify(architecture, null, 2)], {
      type: "application/json",
    });
    downloadBlob(blob, "onramp-architecture.json");
  };

  const exportAsSvg = () => {
    const items = Object.entries(architecture).map(
      ([key, _], i) =>
        `<text x="20" y="${40 + i * 24}" font-family="Segoe UI" font-size="14">${key}</text>`
    );
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="${60 + items.length * 24}">
      <rect width="600" height="${60 + items.length * 24}" fill="white" stroke="#ccc"/>
      <text x="20" y="24" font-family="Segoe UI" font-size="16" font-weight="bold">OnRamp Architecture</text>
      ${items.join("\n")}
    </svg>`;
    const blob = new Blob([svg], { type: "image/svg+xml" });
    downloadBlob(blob, "onramp-architecture.svg");
  };

  const exportAsMarkdown = () => {
    const lines = ["# OnRamp Architecture\n"];
    const renderSection = (key: string, value: any, depth = 2) => {
      lines.push(`${"#".repeat(depth)} ${key}\n`);
      if (typeof value === "object" && value !== null) {
        if (Array.isArray(value)) {
          value.forEach((item) => {
            if (typeof item === "object") {
              lines.push(`- ${item.name || item.display_name || JSON.stringify(item)}`);
            } else {
              lines.push(`- ${item}`);
            }
          });
        } else {
          Object.entries(value).forEach(([k, v]) => {
            if (typeof v === "object") {
              renderSection(k, v, Math.min(depth + 1, 6));
            } else {
              lines.push(`- **${k}**: ${v}`);
            }
          });
        }
      } else {
        lines.push(`${value}`);
      }
      lines.push("");
    };
    Object.entries(architecture).forEach(([key, value]) =>
      renderSection(key, value)
    );
    const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
    downloadBlob(blob, "onramp-architecture.md");
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Menu>
      <MenuTrigger disableButtonEnhancement>
        <Button icon={<ArrowDownloadRegular />} appearance="subtle">
          Export
        </Button>
      </MenuTrigger>
      <MenuPopover>
        <MenuList>
          <MenuItem icon={<CodeRegular />} onClick={exportAsJson}>
            Export as JSON
          </MenuItem>
          <MenuItem icon={<ImageRegular />} onClick={exportAsSvg}>
            Export as SVG
          </MenuItem>
          <MenuItem icon={<DocumentRegular />} onClick={exportAsMarkdown}>
            Export as Markdown
          </MenuItem>
        </MenuList>
      </MenuPopover>
    </Menu>
  );
}
