# Authentication Strategy

- **Status:** accepted
- **Date:** 2024-10-01
- **Deciders:** OnRamp founding team

## Context and Problem Statement

OnRamp needs an authentication strategy for a web application whose target audience is Azure customers. Users already have Microsoft Entra ID (Azure AD) tenants and expect single sign-on (SSO) with their existing Microsoft identities. The solution must support multi-tenant access, role-based authorization, and a frictionless developer experience for local development without cloud dependencies.

## Decision Drivers

- Target users are Azure customers with existing Entra ID tenants
- SSO with Microsoft 365 and Azure Portal identities
- Multi-tenant support (each customer organization is a tenant)
- Role-based access control (Admin, Architect, Viewer)
- Local development must work without Entra ID configuration
- Token-based authentication for the SPA frontend

## Considered Options

1. Microsoft Entra ID (Azure AD) via MSAL
2. Auth0 / Okta (third-party identity provider)
3. Custom JWT authentication with local user database

## Decision Outcome

**Chosen option:** "Microsoft Entra ID via MSAL", because the target audience already has Entra ID tenants and expects seamless SSO with their Azure identities.

### Positive Consequences

- **Zero friction for Azure customers** — users log in with their existing Microsoft account.
- **MSAL.js** on the frontend handles token acquisition, refresh, and caching automatically.
- **PyJWT + JWKS** on the backend provides lightweight, stateless token validation without a session store.
- **Multi-tenant support** is built into Entra ID — each customer's tenant is isolated automatically.
- **Conditional Access and MFA** are handled by Entra ID, not by our application.
- **Role mapping** from Entra ID app roles to application permissions (Admin, Architect, Viewer) is straightforward.

### Negative Consequences

- **Development mode requires mock authentication** — developers without an Entra ID tenant configured need a mock user injected by the backend. This adds a code path that only exists in development.
- **Dependency on the Microsoft identity platform** — any Entra ID outage affects all authenticated operations.
- **App registration management** — each deployment environment (dev, staging, prod) needs its own app registration with correct redirect URIs.
- **Token validation complexity** — JWKS key rotation, issuer validation for multi-tenant apps, and audience verification require careful implementation.

## Pros and Cons of the Options

### Microsoft Entra ID via MSAL

- ✅ Good, because users already have Microsoft accounts.
- ✅ Good, because MSAL handles token lifecycle (acquire, refresh, cache).
- ✅ Good, because Entra ID provides MFA, Conditional Access, and audit logs for free.
- ✅ Good, because multi-tenant is a first-class Entra ID feature.
- ❌ Bad, because local development needs mock auth to avoid cloud dependency.
- ❌ Bad, because app registration setup is a manual step per environment.

### Auth0 / Okta

- ✅ Good, because provider-agnostic — supports Google, GitHub, and other identity providers.
- ✅ Good, because hosted login page reduces frontend complexity.
- ❌ Bad, because adds a third-party dependency and cost.
- ❌ Bad, because Azure customers would need to configure federation with their Entra ID tenant, adding friction.
- ❌ Bad, because token validation requires integrating with a non-Microsoft JWKS endpoint.

### Custom JWT Authentication

- ✅ Good, because full control over the authentication flow.
- ✅ Good, because no external identity provider dependency.
- ❌ Bad, because we must build and maintain password storage, MFA, session management, and token refresh — all solved problems in Entra ID.
- ❌ Bad, because Azure customers cannot SSO with their existing accounts.
- ❌ Bad, because significant security liability in managing credentials.

## Links

- [MSAL.js documentation](https://learn.microsoft.com/entra/msal/overview)
- [Entra ID app registration](https://learn.microsoft.com/entra/identity-platform/quickstart-register-app)
- [backend/app/auth/](../../backend/app/auth/) — token validation implementation
- [docs/architecture.md](../architecture.md)
