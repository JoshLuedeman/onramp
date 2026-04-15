# Security Policy

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

If you discover a security vulnerability in OnRamp, please report it responsibly:

1. **Email:** Send a detailed report to the repository maintainers via
   [GitHub Security Advisories](https://github.com/JoshLuedeman/onramp/security/advisories/new).
2. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Response Timeline

| Action | Timeline |
|--------|----------|
| Acknowledgment of report | Within 48 hours |
| Initial assessment | Within 5 business days |
| Fix development | Based on severity |
| Public disclosure | After fix is released |

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest release on `main` | ✅ |
| Older releases | ❌ |

Only the latest version on the `main` branch receives security updates.

## Scope

The following are in scope for security reports:

- Authentication and authorization bypass
- SQL injection or other injection attacks
- Cross-site scripting (XSS)
- Sensitive data exposure (credentials, tokens, PII)
- Server-side request forgery (SSRF)
- Insecure deserialization
- Misconfigured Azure resources in generated Bicep templates

## Out of Scope

- Issues in third-party dependencies (report upstream, but let us know)
- Denial of service via rate limiting (we have rate limiting middleware)
- Social engineering attacks
- Issues requiring physical access

## Security Best Practices

When contributing to OnRamp:

- Never commit secrets, credentials, or API keys
- Use environment variables for all sensitive configuration
- Validate all user input through Pydantic schemas
- Follow the principle of least privilege for Azure RBAC
- Keep dependencies updated and review security advisories

## Recognition

We appreciate responsible disclosure and will acknowledge security researchers
in our release notes (with permission).
