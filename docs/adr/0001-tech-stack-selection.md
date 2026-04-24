# Tech Stack Selection

- **Status:** accepted
- **Date:** 2024-10-01
- **Deciders:** OnRamp founding team

## Context and Problem Statement

OnRamp needs a technology stack that supports rapid iteration on a complex web application while maintaining strong type safety, Azure-native deployment, and a productive developer experience. The application has a rich interactive frontend (questionnaire wizard, architecture visualization, Bicep preview) and a backend that orchestrates AI services, database operations, and Azure deployments.

## Decision Drivers

- Fast iteration with a small team
- Strong typing to catch errors early in both frontend and backend
- Azure-native deployment (Container Apps, Azure SQL, AI Foundry)
- Rich interactive UI with Microsoft design language
- Async I/O for concurrent AI and Azure API calls
- Familiarity and hiring pool for the chosen languages

## Considered Options

1. React + TypeScript frontend, FastAPI (Python) backend, Bicep IaC
2. Next.js full-stack (TypeScript everywhere), Bicep IaC
3. Angular + C# (.NET) backend, ARM templates

## Decision Outcome

**Chosen option:** "React + TypeScript frontend, FastAPI (Python) backend, Bicep IaC", because it balances developer productivity, type safety, and Azure-native tooling.

### Positive Consequences

- **React 19 + TypeScript + Vite** provides fast builds, HMR, and a mature ecosystem for complex UI.
- **Fluent UI React v9** gives us Microsoft-standard components out of the box, ensuring visual consistency with Azure Portal.
- **FastAPI** offers automatic OpenAPI generation, async support, and Pydantic validation — reducing boilerplate for a large API surface.
- **Python** is the dominant language for AI/ML integrations, making Azure AI Foundry integration straightforward.
- **SQLAlchemy 2.0 async** provides a mature ORM with support for both SQLite (dev) and Azure SQL (prod).
- **Bicep** is the first-class Azure IaC language, with better Azure RM integration than Terraform for Azure-only deployments.

### Negative Consequences

- The team must maintain expertise in both **Python and TypeScript** — two distinct language ecosystems.
- **Python's runtime performance** is lower than Go or C# for CPU-bound operations, though this is mitigated by the I/O-bound nature of the workload.
- **Two separate build/deploy pipelines** are needed for frontend and backend containers.

## Pros and Cons of the Options

### React + TypeScript + FastAPI + Bicep

- ✅ Good, because FastAPI auto-generates OpenAPI docs from type annotations.
- ✅ Good, because Python has the best AI/ML library ecosystem.
- ✅ Good, because Bicep is purpose-built for Azure Resource Manager.
- ✅ Good, because React has the largest frontend ecosystem and hiring pool.
- ❌ Bad, because two languages increase onboarding time.
- ❌ Bad, because Python packaging is more complex than Node.js.

### Next.js Full-Stack

- ✅ Good, because one language (TypeScript) for the entire stack.
- ✅ Good, because SSR and API routes in a single framework.
- ❌ Bad, because Node.js AI/ML libraries are less mature than Python's.
- ❌ Bad, because server-side rendering adds complexity for a SPA-style wizard UI.
- ❌ Bad, because Fluent UI v9 is React-only, so no benefit from Next.js-specific features.

### Angular + .NET + ARM Templates

- ✅ Good, because .NET has excellent Azure SDK support.
- ✅ Good, because Angular provides strong opinions and structure.
- ❌ Bad, because ARM templates are verbose and harder to maintain than Bicep.
- ❌ Bad, because Angular has a steeper learning curve and smaller hiring pool than React.
- ❌ Bad, because C# AI Foundry integration requires more boilerplate than Python.

## Links

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Fluent UI React v9](https://react.fluentui.dev/)
- [Bicep documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [docs/architecture.md](../architecture.md)
