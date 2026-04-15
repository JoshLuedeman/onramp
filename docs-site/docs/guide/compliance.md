# Compliance Scoring

OnRamp evaluates your generated architecture against industry compliance frameworks and provides actionable scoring and gap analysis.

## Supported Frameworks

| Framework     | Description                                           |
| ------------- | ----------------------------------------------------- |
| SOC 2         | Service Organization Control 2 — trust services criteria |
| HIPAA         | Health Insurance Portability and Accountability Act    |
| PCI-DSS       | Payment Card Industry Data Security Standard           |
| FedRAMP       | Federal Risk and Authorization Management Program      |
| NIST 800-53   | National Institute of Standards and Technology security controls |
| ISO 27001     | International information security management standard |

## Scoring Methodology

For each selected compliance framework, OnRamp:

1. **Maps controls** — Identifies which framework controls are relevant to your architecture
2. **Evaluates coverage** — Checks whether your architecture addresses each control through Azure services, policies, or configurations
3. **Calculates a score** — Provides a percentage score representing how well your architecture meets the framework requirements
4. **Identifies gaps** — Highlights specific controls that are not fully addressed

## Gap Remediation

For each identified gap, OnRamp provides:

- **Description** of what the control requires
- **Recommendation** for how to address it in your Azure landing zone
- **Azure services** or configurations that can close the gap
- **Impact level** (high, medium, low) indicating how critical the gap is

You can use these recommendations to refine your architecture before generating Bicep templates and deploying.

## API Endpoints

| Method | Path                               | Description                      |
| ------ | ---------------------------------- | -------------------------------- |
| GET    | `/api/compliance/frameworks`       | List compliance frameworks       |
| GET    | `/api/compliance/frameworks/{id}`  | Get framework details            |
| POST   | `/api/compliance/controls`         | Get controls for frameworks      |
| POST   | `/api/scoring/evaluate`            | Score architecture against frameworks |

See the [Compliance API Reference](/api/compliance) for full details.

## Next Steps

- [Bicep Templates](./bicep) — Generate deployable IaC from your architecture
- [Deployment](./deployment) — Deploy your landing zone to Azure
