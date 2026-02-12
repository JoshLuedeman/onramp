"""Compliance framework seed data for Azure landing zone evaluation."""

COMPLIANCE_FRAMEWORKS: list[dict] = [
    {
        "name": "SOC 2 Type II",
        "short_name": "SOC2",
        "description": "Service Organization Control 2 — Trust Services Criteria for security, availability, processing integrity, confidentiality, and privacy.",
        "version": "2017",
        "controls": [
            {
                "control_id": "CC1.1",
                "title": "COSO Principle 1: Integrity and Ethical Values",
                "category": "Control Environment",
                "severity": "high",
                "azure_policies": ["audit-log-retention"],
            },
            {
                "control_id": "CC5.1",
                "title": "Logical and Physical Access Controls",
                "category": "Control Activities",
                "severity": "high",
                "azure_policies": ["require-rbac", "require-mfa"],
            },
            {
                "control_id": "CC6.1",
                "title": "Security — Logical Access",
                "category": "Logical and Physical Access",
                "severity": "high",
                "azure_policies": ["require-nsg", "require-firewall"],
            },
            {
                "control_id": "CC6.6",
                "title": "Security — System Boundaries",
                "category": "Logical and Physical Access",
                "severity": "high",
                "azure_policies": ["require-nsg", "deny-public-ip"],
            },
            {
                "control_id": "CC7.1",
                "title": "System Monitoring",
                "category": "System Operations",
                "severity": "medium",
                "azure_policies": ["require-diagnostics", "require-log-analytics"],
            },
            {
                "control_id": "CC7.2",
                "title": "Incident Response",
                "category": "System Operations",
                "severity": "high",
                "azure_policies": ["enable-defender", "enable-sentinel"],
            },
            {
                "control_id": "CC8.1",
                "title": "Change Management",
                "category": "Change Management",
                "severity": "medium",
                "azure_policies": ["require-tags", "audit-changes"],
            },
        ],
    },
    {
        "name": "HIPAA",
        "short_name": "HIPAA",
        "description": "Health Insurance Portability and Accountability Act — safeguards for protecting sensitive patient health information.",
        "version": "2013",
        "controls": [
            {
                "control_id": "164.312(a)(1)",
                "title": "Access Control — Unique User Identification",
                "category": "Technical Safeguards",
                "severity": "high",
                "azure_policies": ["require-rbac", "require-mfa", "require-pim"],
            },
            {
                "control_id": "164.312(a)(2)(iv)",
                "title": "Encryption and Decryption",
                "category": "Technical Safeguards",
                "severity": "high",
                "azure_policies": ["require-encryption-at-rest", "require-tls"],
            },
            {
                "control_id": "164.312(b)",
                "title": "Audit Controls",
                "category": "Technical Safeguards",
                "severity": "high",
                "azure_policies": [
                    "require-diagnostics",
                    "require-log-analytics",
                    "require-audit-logs",
                ],
            },
            {
                "control_id": "164.312(c)(1)",
                "title": "Integrity — Data Integrity Controls",
                "category": "Technical Safeguards",
                "severity": "high",
                "azure_policies": ["require-backup", "require-geo-redundancy"],
            },
            {
                "control_id": "164.312(e)(1)",
                "title": "Transmission Security",
                "category": "Technical Safeguards",
                "severity": "high",
                "azure_policies": ["require-tls", "require-vpn-encryption"],
            },
            {
                "control_id": "164.308(a)(1)",
                "title": "Security Management Process — Risk Analysis",
                "category": "Administrative Safeguards",
                "severity": "high",
                "azure_policies": ["enable-defender", "enable-secure-score"],
            },
        ],
    },
    {
        "name": "PCI DSS v4.0",
        "short_name": "PCI-DSS",
        "description": "Payment Card Industry Data Security Standard — requirements for organizations handling credit card data.",
        "version": "4.0",
        "controls": [
            {
                "control_id": "1.2",
                "title": "Network Security Controls",
                "category": "Build and Maintain a Secure Network",
                "severity": "high",
                "azure_policies": ["require-nsg", "require-firewall", "require-waf"],
            },
            {
                "control_id": "2.2",
                "title": "Secure Configuration Standards",
                "category": "Build and Maintain a Secure Network",
                "severity": "high",
                "azure_policies": ["require-secure-config", "deny-default-passwords"],
            },
            {
                "control_id": "3.5",
                "title": "Protect Stored Account Data — Encryption",
                "category": "Protect Account Data",
                "severity": "high",
                "azure_policies": ["require-encryption-at-rest", "require-key-vault"],
            },
            {
                "control_id": "7.1",
                "title": "Restrict Access by Business Need",
                "category": "Strong Access Control",
                "severity": "high",
                "azure_policies": ["require-rbac", "require-least-privilege"],
            },
            {
                "control_id": "8.3",
                "title": "Strong Authentication",
                "category": "Strong Access Control",
                "severity": "high",
                "azure_policies": ["require-mfa", "require-password-policy"],
            },
            {
                "control_id": "10.2",
                "title": "Audit Logs",
                "category": "Monitor and Test Networks",
                "severity": "high",
                "azure_policies": ["require-diagnostics", "require-log-analytics"],
            },
        ],
    },
    {
        "name": "FedRAMP Moderate",
        "short_name": "FedRAMP",
        "description": "Federal Risk and Authorization Management Program — standardized security assessment for cloud services used by US federal agencies.",
        "version": "Moderate",
        "controls": [
            {
                "control_id": "AC-2",
                "title": "Account Management",
                "category": "Access Control",
                "severity": "high",
                "azure_policies": [
                    "require-rbac",
                    "require-pim",
                    "require-access-reviews",
                ],
            },
            {
                "control_id": "AC-17",
                "title": "Remote Access",
                "category": "Access Control",
                "severity": "high",
                "azure_policies": ["require-vpn", "require-mfa", "deny-public-rdp-ssh"],
            },
            {
                "control_id": "AU-2",
                "title": "Audit Events",
                "category": "Audit and Accountability",
                "severity": "high",
                "azure_policies": ["require-diagnostics", "require-activity-log"],
            },
            {
                "control_id": "CM-7",
                "title": "Least Functionality",
                "category": "Configuration Management",
                "severity": "medium",
                "azure_policies": ["deny-unapproved-services", "require-approved-images"],
            },
            {
                "control_id": "SC-7",
                "title": "Boundary Protection",
                "category": "System and Communications",
                "severity": "high",
                "azure_policies": [
                    "require-nsg",
                    "require-firewall",
                    "deny-public-endpoints",
                ],
            },
            {
                "control_id": "SC-28",
                "title": "Protection of Information at Rest",
                "category": "System and Communications",
                "severity": "high",
                "azure_policies": ["require-encryption-at-rest", "require-cmk"],
            },
        ],
    },
    {
        "name": "NIST SP 800-53 Rev. 5",
        "short_name": "NIST-800-53",
        "description": "Security and Privacy Controls for Information Systems and Organizations.",
        "version": "Rev. 5",
        "controls": [
            {
                "control_id": "AC-2",
                "title": "Account Management",
                "category": "Access Control",
                "severity": "high",
                "azure_policies": ["require-rbac", "require-pim"],
            },
            {
                "control_id": "AU-3",
                "title": "Content of Audit Records",
                "category": "Audit and Accountability",
                "severity": "medium",
                "azure_policies": ["require-diagnostics", "require-log-analytics"],
            },
            {
                "control_id": "IA-2",
                "title": "Identification and Authentication",
                "category": "Identification and Authentication",
                "severity": "high",
                "azure_policies": ["require-mfa", "require-entra-id"],
            },
            {
                "control_id": "IR-4",
                "title": "Incident Handling",
                "category": "Incident Response",
                "severity": "high",
                "azure_policies": ["enable-sentinel", "enable-defender"],
            },
            {
                "control_id": "SC-8",
                "title": "Transmission Confidentiality",
                "category": "System and Communications Protection",
                "severity": "high",
                "azure_policies": ["require-tls", "require-https"],
            },
        ],
    },
    {
        "name": "ISO/IEC 27001:2022",
        "short_name": "ISO-27001",
        "description": "International standard for information security management systems (ISMS).",
        "version": "2022",
        "controls": [
            {
                "control_id": "A.5.15",
                "title": "Access Control",
                "category": "Organizational Controls",
                "severity": "high",
                "azure_policies": ["require-rbac", "require-least-privilege"],
            },
            {
                "control_id": "A.8.1",
                "title": "User Endpoint Devices",
                "category": "Technological Controls",
                "severity": "medium",
                "azure_policies": ["require-compliant-devices", "require-conditional-access"],
            },
            {
                "control_id": "A.8.9",
                "title": "Configuration Management",
                "category": "Technological Controls",
                "severity": "medium",
                "azure_policies": ["require-policy-compliance", "require-tags"],
            },
            {
                "control_id": "A.8.15",
                "title": "Logging",
                "category": "Technological Controls",
                "severity": "high",
                "azure_policies": ["require-diagnostics", "require-log-analytics"],
            },
            {
                "control_id": "A.8.24",
                "title": "Use of Cryptography",
                "category": "Technological Controls",
                "severity": "high",
                "azure_policies": ["require-encryption-at-rest", "require-tls"],
            },
        ],
    },
]


def get_framework_by_short_name(short_name: str) -> dict | None:
    """Get a compliance framework by its short name."""
    for fw in COMPLIANCE_FRAMEWORKS:
        if fw["short_name"].lower() == short_name.lower():
            return fw
    return None


def get_all_frameworks() -> list[dict]:
    """Get all compliance frameworks (summary only, no controls)."""
    return [
        {
            "name": fw["name"],
            "short_name": fw["short_name"],
            "description": fw["description"],
            "version": fw["version"],
            "control_count": len(fw["controls"]),
        }
        for fw in COMPLIANCE_FRAMEWORKS
    ]


def get_controls_for_frameworks(framework_names: list[str]) -> list[dict]:
    """Get all controls for the specified frameworks."""
    controls = []
    for name in framework_names:
        fw = get_framework_by_short_name(name)
        if fw:
            for ctrl in fw["controls"]:
                controls.append({**ctrl, "framework": fw["short_name"]})
    return controls
