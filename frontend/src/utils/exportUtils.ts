// Export architecture as JSON
export function exportArchitectureJson(architecture: Record<string, unknown>): void {
  const blob = new Blob([JSON.stringify(architecture, null, 2)], { type: "application/json" });
  downloadBlob(blob, "onramp-architecture.json");
}

// Export compliance report as HTML (self-contained, printable)
export function exportComplianceReport(scoringResult: Record<string, unknown>): void {
  const html = buildComplianceHtml(scoringResult);
  const blob = new Blob([html], { type: "text/html" });
  downloadBlob(blob, "onramp-compliance-report.html");
}

// Export full landing zone design document as HTML
export function exportDesignDocument(
  architecture: Record<string, unknown>,
  complianceResult?: Record<string, unknown>
): void {
  const html = buildDesignDocumentHtml(architecture, complianceResult);
  const blob = new Blob([html], { type: "text/html" });
  downloadBlob(blob, "onramp-landing-zone-design.html");
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function escapeHtml(text: unknown): string {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function scoreColor(score: number): string {
  if (score >= 80) return "#107c10";
  if (score >= 50) return "#ca5010";
  return "#d13438";
}

function buildComplianceHtml(result: Record<string, unknown>): string {
  const overall = Number(result.overall_score ?? 0);
  const frameworks = (result.frameworks ?? []) as Array<Record<string, unknown>>;
  const date = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  let gapsRows = "";
  for (const fw of frameworks) {
    const gaps = (fw.gaps ?? []) as Array<Record<string, unknown>>;
    for (const gap of gaps) {
      gapsRows += `<tr>
        <td>${escapeHtml(gap.control)}</td>
        <td>${escapeHtml(fw.name)}</td>
        <td>${escapeHtml(gap.description)}</td>
        <td>${escapeHtml(gap.remediation)}</td>
      </tr>`;
    }
  }

  let frameworkBars = "";
  for (const fw of frameworks) {
    const score = Number(fw.score ?? 0);
    frameworkBars += `
      <div class="fw-row">
        <span class="fw-name">${escapeHtml(fw.name)}</span>
        <div class="bar-track">
          <div class="bar-fill" style="width:${Math.round(score)}%;background:${scoreColor(score)}"></div>
        </div>
        <span class="fw-score" style="color:${scoreColor(score)}">${Math.round(score)}%</span>
      </div>`;
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>OnRamp Compliance Report</title>
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:40px;color:#242424;background:#fff}
  h1{color:#0078d4;margin-bottom:4px}
  .date{color:#616161;margin-bottom:32px}
  .overall{text-align:center;margin:32px 0;padding:24px;border-radius:8px;background:#f5f5f5}
  .overall-score{font-size:64px;font-weight:700}
  .overall-label{font-size:18px;color:#616161}
  .fw-row{display:flex;align-items:center;gap:12px;margin:8px 0}
  .fw-name{width:140px;font-weight:600;flex-shrink:0}
  .bar-track{flex:1;height:20px;background:#e0e0e0;border-radius:4px;overflow:hidden}
  .bar-fill{height:100%;border-radius:4px;transition:width .3s}
  .fw-score{width:50px;text-align:right;font-weight:700}
  table{width:100%;border-collapse:collapse;margin-top:16px}
  th,td{text-align:left;padding:8px 12px;border-bottom:1px solid #e0e0e0}
  th{background:#f5f5f5;font-weight:600}
  h2{margin-top:40px;color:#242424;border-bottom:2px solid #0078d4;padding-bottom:8px}
  @media print{body{padding:20px}h1{color:#000}.bar-fill{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
</style>
</head>
<body>
<h1>OnRamp Compliance Report</h1>
<p class="date">Generated on ${escapeHtml(date)}</p>

<div class="overall">
  <div class="overall-score" style="color:${scoreColor(overall)}">${Math.round(overall)}%</div>
  <div class="overall-label">Overall Compliance Score</div>
</div>

<h2>Framework Scores</h2>
${frameworkBars}

${gapsRows ? `<h2>Compliance Gaps</h2>
<table>
<thead><tr><th>Control ID</th><th>Framework</th><th>Description</th><th>Remediation</th></tr></thead>
<tbody>${gapsRows}</tbody>
</table>` : "<p>No compliance gaps identified.</p>"}

</body>
</html>`;
}

function renderMgHierarchy(mg: Record<string, unknown>): string {
  const name = escapeHtml(mg.name ?? mg.display_name ?? "Unknown");
  const children = (mg.children ?? []) as Array<Record<string, unknown>>;
  let html = `<li>${name}`;
  if (children.length > 0) {
    html += "<ul>";
    for (const child of children) {
      html += renderMgHierarchy(child);
    }
    html += "</ul>";
  }
  html += "</li>";
  return html;
}

function buildDesignDocumentHtml(
  architecture: Record<string, unknown>,
  complianceResult?: Record<string, unknown>
): string {
  const date = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const subs = (architecture.subscriptions ?? []) as Array<Record<string, unknown>>;
  const network = (architecture.network_topology ?? {}) as Record<string, unknown>;
  const identity = (architecture.identity ?? {}) as Record<string, unknown>;
  const security = (architecture.security ?? {}) as Record<string, unknown>;
  const governance = (architecture.governance ?? {}) as Record<string, unknown>;
  const mgGroups = architecture.management_groups as Record<string, unknown> | undefined;

  let mgHtml = "<p>Not configured.</p>";
  if (mgGroups) {
    mgHtml = `<ul class="mg-tree">${renderMgHierarchy(mgGroups)}</ul>`;
  }

  let subsRows = "";
  for (const sub of subs) {
    subsRows += `<tr>
      <td>${escapeHtml(sub.name)}</td>
      <td>${escapeHtml(sub.purpose)}</td>
    </tr>`;
  }

  let complianceSection = "";
  if (complianceResult) {
    const overall = Number(complianceResult.overall_score ?? 0);
    const frameworks = (complianceResult.frameworks ?? []) as Array<Record<string, unknown>>;
    let fwRows = "";
    for (const fw of frameworks) {
      const score = Number(fw.score ?? 0);
      fwRows += `<tr>
        <td>${escapeHtml(fw.name)}</td>
        <td style="color:${scoreColor(score)};font-weight:700">${Math.round(score)}%</td>
        <td>${escapeHtml(fw.controls_met)}/${Number(fw.controls_met ?? 0) + Number(fw.controls_partial ?? 0) + Number(fw.controls_gap ?? 0)}</td>
      </tr>`;
    }
    complianceSection = `
    <h2>Compliance Scores</h2>
    <p>Overall Score: <strong style="color:${scoreColor(overall)}">${Math.round(overall)}%</strong></p>
    <table>
      <thead><tr><th>Framework</th><th>Score</th><th>Controls Met</th></tr></thead>
      <tbody>${fwRows}</tbody>
    </table>`;
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Azure Landing Zone Design</title>
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:40px;color:#242424;background:#fff}
  h1{color:#0078d4;margin-bottom:4px}
  .date{color:#616161;margin-bottom:32px}
  h2{margin-top:36px;color:#242424;border-bottom:2px solid #0078d4;padding-bottom:8px}
  table{width:100%;border-collapse:collapse;margin-top:12px}
  th,td{text-align:left;padding:8px 12px;border-bottom:1px solid #e0e0e0}
  th{background:#f5f5f5;font-weight:600}
  .mg-tree{list-style:none;padding-left:0}
  .mg-tree ul{list-style:none;padding-left:24px;border-left:2px solid #0078d4}
  .mg-tree li{padding:4px 0}
  .config-grid{display:grid;grid-template-columns:160px 1fr;gap:4px 16px;margin-top:8px}
  .config-label{font-weight:600;color:#616161}
  @media print{body{padding:20px}.mg-tree ul{border-left-color:#000}}
</style>
</head>
<body>
<h1>Azure Landing Zone Design</h1>
<p class="date">Generated on ${escapeHtml(date)}</p>
<p>Organization Size: <strong>${escapeHtml(architecture.organization_size)}</strong></p>

<h2>Management Group Hierarchy</h2>
${mgHtml}

<h2>Subscriptions</h2>
${subs.length > 0 ? `<table>
<thead><tr><th>Name</th><th>Purpose</th></tr></thead>
<tbody>${subsRows}</tbody>
</table>` : "<p>No subscriptions configured.</p>"}

<h2>Network Topology</h2>
<div class="config-grid">
  <span class="config-label">Topology Type</span><span>${escapeHtml(network.type ?? "hub-spoke")}</span>
  <span class="config-label">Primary Region</span><span>${escapeHtml(network.primary_region ?? "eastus2")}</span>
</div>

<h2>Identity &amp; Security</h2>
<div class="config-grid">
  <span class="config-label">Identity Provider</span><span>${escapeHtml(identity.provider ?? "Entra ID")}</span>
  <span class="config-label">PIM Enabled</span><span>${escapeHtml(identity.pim_enabled ?? false)}</span>
  <span class="config-label">MFA Policy</span><span>${escapeHtml(identity.mfa_policy ?? "all_users")}</span>
  <span class="config-label">Defender for Cloud</span><span>${escapeHtml(security.defender_for_cloud ?? true)}</span>
  <span class="config-label">Sentinel</span><span>${escapeHtml(security.sentinel ?? false)}</span>
  <span class="config-label">Azure Firewall</span><span>${escapeHtml(security.azure_firewall ?? true)}</span>
</div>

<h2>Governance</h2>
<div class="config-grid">
  <span class="config-label">Naming Convention</span><span>${escapeHtml(governance.naming_convention ?? "CAF")}</span>
</div>

${complianceSection}

</body>
</html>`;
}
