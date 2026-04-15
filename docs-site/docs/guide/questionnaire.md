# Questionnaire

OnRamp's adaptive questionnaire guides you through all 8 Cloud Adoption Framework (CAF) design areas to gather the information needed for a tailored landing zone architecture.

## CAF Design Areas

The questionnaire covers each of the following design areas:

1. **Azure Billing & Entra Tenant** — Subscription structure, billing accounts, and tenant configuration
2. **Identity & Access Management** — Authentication, authorization, and identity providers
3. **Resource Organization** — Management groups, subscriptions, resource groups, and naming conventions
4. **Network Topology & Connectivity** — Hub-spoke vs. mesh, DNS, ExpressRoute, VPN, and firewall
5. **Security** — Security baselines, encryption, threat protection, and key management
6. **Management & Monitoring** — Logging, diagnostics, alerting, and backup strategies
7. **Governance** — Azure Policy, cost management, tagging, and compliance requirements
8. **Platform Automation & DevOps** — CI/CD pipelines, Infrastructure as Code, and GitOps workflows

## How It Works

### Adaptive Flow

The questionnaire adapts based on your previous answers. For example:

- If you select "Enterprise" for organization size, you'll see additional questions about management group hierarchy and multi-region networking
- If you indicate HIPAA compliance needs, follow-up questions about data residency and encryption appear

### Recommended Options

Many questions include a **recommended** option that represents Microsoft's best-practice guidance for your scenario. These are highlighted in the UI to help you make informed decisions quickly.

### "I'm Not Sure" Fallback

Every question includes an **"I'm not sure"** option. Selecting this tells OnRamp to use the recommended default and flag the decision for later review. This ensures you can complete the questionnaire even if you don't have all the answers up front.

### Progress Tracking

The UI displays your progress through the questionnaire with:

- A progress bar showing overall completion percentage
- Category-level completion indicators
- The ability to navigate back to previously answered questions

## API Endpoints

The questionnaire is powered by these API endpoints:

| Method | Path                          | Description               |
| ------ | ----------------------------- | ------------------------- |
| GET    | `/api/questionnaire/categories` | List question categories |
| GET    | `/api/questionnaire/questions`  | List all questions        |
| POST   | `/api/questionnaire/next`       | Get next unanswered question |
| POST   | `/api/questionnaire/validate`   | Validate an answer        |
| POST   | `/api/questionnaire/progress`   | Get completion progress   |

See the [Questionnaire API Reference](/api/questionnaire) for full details.

## Next Steps

- [Architecture Generation](./architecture) — What happens after you complete the questionnaire
- [Compliance Scoring](./compliance) — How your choices affect compliance scores
