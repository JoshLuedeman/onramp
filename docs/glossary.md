# OnRamp Glossary

Domain terms used throughout the OnRamp codebase and documentation.

## Azure & Cloud

| Term | Definition |
|------|-----------|
| **ARM Template** | Azure Resource Manager template — a JSON document that defines Azure infrastructure declaratively. OnRamp generates Bicep (which compiles to ARM) for customer deployments. |
| **Bicep** | A domain-specific language for deploying Azure resources declaratively. Compiles to ARM templates. OnRamp uses Bicep for both its own infrastructure (`infra/`) and customer landing zone templates (`backend/app/templates/bicep/`). |
| **CAF (Cloud Adoption Framework)** | Microsoft's methodology for cloud adoption covering strategy, planning, readiness, migration, governance, and management. OnRamp's questionnaire maps to the 8 CAF design areas. |
| **Entra ID** | Microsoft Entra ID (formerly Azure Active Directory). The identity platform used for authentication and authorization in OnRamp. |
| **Landing Zone** | A pre-configured Azure environment with governance, networking, identity, and security controls aligned to CAF best practices. OnRamp generates and deploys these. |
| **Management Group** | An Azure scope above subscriptions used to organize resources and apply governance (policies, RBAC) across multiple subscriptions in a hierarchy. |
| **NAT Gateway** | An Azure networking resource that provides outbound internet connectivity for resources in a virtual network using static public IP addresses. |
| **NSG (Network Security Group)** | A set of inbound/outbound security rules that filter network traffic to and from Azure resources within a virtual network. |
| **Private Endpoint** | A network interface that connects privately to an Azure service using a private IP address from a virtual network, keeping traffic off the public internet. |
| **Subscription** | An Azure billing and resource management boundary. Landing zones typically span multiple subscriptions (e.g., connectivity, identity, management, workload). |
| **VPN Gateway** | An Azure resource that sends encrypted traffic between an Azure virtual network and on-premises locations or other Azure virtual networks over the public internet. |

## Identity & Security

| Term | Definition |
|------|-----------|
| **Compliance Framework** | A set of security and governance controls against which an architecture is evaluated. OnRamp supports SOC 2, HIPAA, PCI-DSS, FedRAMP, NIST 800-53, and ISO 27001. |
| **MSAL (Microsoft Authentication Library)** | Client-side library for authenticating users with Entra ID. OnRamp uses `msal-browser` and `msal-react` on the frontend, and `msal-python` on the backend. |
| **Policy** | Azure Policy — a service for creating, assigning, and managing rules that enforce organizational standards on Azure resources. Landing zones use policies for governance. |
| **RBAC (Role-Based Access Control)** | A system for managing access to Azure resources based on roles assigned to users. OnRamp itself has three roles: Admin, Architect, and Viewer. |
| **Tenant** | An Entra ID tenant — a dedicated instance of the identity service representing an organization. Each OnRamp deployment is scoped to a single tenant. |

## Architecture & Deployment

| Term | Definition |
|------|-----------|
| **Archetype** | A predefined landing zone pattern sized to an organization (Small, Medium, Enterprise). OnRamp uses archetypes as starting points for AI-generated architectures. |
| **Migration Strategy (6 Rs)** | Six approaches to cloud migration: Rehost (lift-and-shift), Replatform, Refactor, Rearchitect, Rebuild, and Replace. OnRamp's questionnaire captures migration intent to inform architecture recommendations. |
| **Workload** | An application or service that runs in a landing zone subscription. Landing zone design accounts for workload requirements (compute, networking, compliance). |
