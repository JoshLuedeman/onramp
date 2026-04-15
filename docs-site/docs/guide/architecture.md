# Architecture Generation

After completing the questionnaire, OnRamp generates a tailored Azure landing zone architecture based on your answers.

## Generation Approaches

### Archetype-Based

OnRamp includes three predefined landing zone archetypes that serve as starting points:

| Archetype   | Org Size         | Subscriptions | Management Groups       |
| ----------- | ---------------- | ------------- | ----------------------- |
| Small       | 1–50 employees   | 2–3           | Simplified hierarchy    |
| Medium      | 51–500 employees | 4–6           | Standard CAF hierarchy  |
| Enterprise  | 500+ employees   | 8+            | Full enterprise-scale   |

Your questionnaire answers determine which archetype is selected, and the architecture is then customized based on your specific requirements.

### AI-Generated

When Azure AI Foundry is configured, OnRamp uses AI to generate a fully customized architecture that goes beyond the base archetype. The AI considers:

- Your specific compliance requirements
- Network topology preferences
- Identity and access management needs
- Organization size and growth projections

In development mode (without AI credentials), OnRamp returns a mock architecture response so you can still explore the full workflow.

## Interactive Visualizer

The generated architecture is displayed in an interactive visualizer that lets you explore:

- **Management group hierarchy** — See how subscriptions and resource groups are organized
- **Network topology** — View hub-spoke layouts, connectivity, and firewall placement
- **Resource relationships** — Understand dependencies between Azure resources

## Cost Estimation

OnRamp provides estimated monthly costs for the generated architecture, broken down by:

- Compute resources
- Networking components
- Storage and databases
- Security and monitoring services

## Chat-Based Refinement

After the initial architecture is generated, you can use the chat interface to refine it:

- Ask questions about specific design decisions
- Request changes to networking, security, or organization structure
- Get explanations for why certain resources were recommended

The AI will update the architecture in real-time based on your feedback.

## API Endpoints

| Method | Path                            | Description                        |
| ------ | ------------------------------- | ---------------------------------- |
| GET    | `/api/architecture/archetypes`  | List landing zone archetypes       |
| POST   | `/api/architecture/generate`    | Generate architecture from answers |
| POST   | `/api/architecture/recommend`   | Get AI recommendations             |

See the [Architecture API Reference](/api/architecture) for full details.

## Next Steps

- [Compliance Scoring](./compliance) — Evaluate your architecture against compliance frameworks
- [Bicep Templates](./bicep) — Generate Infrastructure as Code from your architecture
