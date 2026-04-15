# Screenshots

This directory holds screenshots of the OnRamp application for use in documentation. Screenshots are not checked in yet — this README explains how to capture them.

## How to Capture Screenshots

### 1. Start the Application

```bash
./dev.sh
```

This starts the frontend at `http://localhost:5173` and the backend at `http://localhost:8000`.

### 2. Recommended Settings

- **Resolution:** 1280×720 (browser viewport)
- **Browser:** Microsoft Edge or Google Chrome
- **Theme:** Use the default Fluent UI light theme
- **Data:** Ensure sample data is loaded (the dev environment includes mock data)

### 3. Screenshots Needed

| File | Page / Route | What to Show |
|------|-------------|--------------|
| `home.png` | `/` | Dashboard with the project list showing at least one project |
| `wizard.png` | `/wizard` | Wizard page with a questionnaire question visible and a recommended option highlighted |
| `architecture.png` | `/architecture` | Architecture visualizer with the landing zone diagram rendered |
| `compliance.png` | `/compliance` | Compliance scoring results showing framework scores (e.g., SOC 2, HIPAA) |
| `bicep.png` | `/bicep` | Bicep code preview panel with generated Infrastructure as Code |
| `deploy.png` | `/deploy` | Deployment status page showing deployment progress or completion |

### 4. Capture Steps

1. Navigate to each page listed above
2. Resize the browser viewport to **1280×720**
3. Take a screenshot of the full viewport (no browser chrome)
4. Save the file with the exact name from the table above
5. Place the PNG file in this directory (`docs/screenshots/`)

### 5. When to Update

Screenshots should be updated when:

- The UI layout changes significantly
- New major features are added to a page
- The design system or theme is updated
- Existing screenshots no longer represent the current state of the app
