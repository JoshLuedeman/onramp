# Introduction

**OnRamp** is an AI-powered web application that guides Azure customers through designing and deploying Cloud Adoption Framework (CAF) aligned landing zones. Answer questions about your organization, get an AI-generated architecture recommendation, review it visually, and deploy it to Azure with a single click.

## Core Workflow

OnRamp follows a five-step process to take you from requirements to a fully deployed Azure landing zone:

1. **Questionnaire** — An adaptive wizard walks you through all 8 CAF design areas, asking questions about your organization's size, compliance needs, networking requirements, and more.

2. **Architecture Generation** — Based on your answers, OnRamp uses Azure AI Foundry to generate a tailored landing zone architecture, complete with management group hierarchy, subscription layout, and resource recommendations.

3. **Compliance Scoring** — Your architecture is evaluated against industry frameworks (SOC 2, HIPAA, PCI-DSS, FedRAMP, NIST 800-53, ISO 27001) to identify gaps and provide a compliance score.

4. **Bicep Generation** — OnRamp auto-generates deployable Bicep templates (Infrastructure as Code) that implement your architecture.

5. **Deployment** — Deploy your landing zone directly to Azure subscriptions with real-time progress tracking, audit logging, and rollback support.

## Key Features

- **🧭 Guided Questionnaire** — Adaptive wizard covering all 8 CAF design areas
- **🤖 AI Architecture Generation** — Azure AI Foundry powered recommendations
- **🏗️ Interactive Visualizer** — Explore your landing zone hierarchy and network topology
- **📋 Compliance Scoring** — Evaluate against six industry compliance frameworks
- **📝 Bicep Generation** — Auto-generated, deployable Infrastructure as Code
- **🚀 One-Click Deploy** — Deploy your entire landing zone to Azure subscriptions
- **📊 Deployment Tracking** — Real-time progress, audit logging, and rollback support

## Prerequisites

### For Local Development

- **Docker Desktop** — The recommended way to run OnRamp locally. A single `./dev.sh` command starts everything in containers.

### For Production Deployment

- **Azure Subscription** — With permissions to create resources
- **Microsoft Entra ID** — App registration for authentication
- **Azure AI Foundry** — Endpoint for AI-powered architecture generation

## What's Next?

- [Quick Start](./quick-start) — Get OnRamp running locally in minutes
- [Deploy to Azure](./deploy-to-azure) — Deploy OnRamp to your Azure subscription
- [Questionnaire Guide](./questionnaire) — Learn how the adaptive questionnaire works
