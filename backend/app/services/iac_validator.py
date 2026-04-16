"""Infrastructure-as-Code syntax validation service.

Validates generated Bicep, Terraform, ARM, and Pulumi code for syntax
correctness using local pattern-based and structural checks — no external
tools required.
"""

import ast
import json
import logging
import re

from app.schemas.iac_validation import (
    IaCFormat,
    IaCValidationError,
    IaCValidationResult,
    IaCValidationWarning,
)

logger = logging.getLogger(__name__)

# Maximum file size we'll validate (512 KB).
_MAX_CODE_SIZE = 512 * 1024


class IaCValidator:
    """Validates IaC code for syntax correctness.

    Each public ``validate_*`` method returns an ``IaCValidationResult``
    containing errors, warnings, and an overall ``is_valid`` flag.
    """

    # ------------------------------------------------------------------
    # Public dispatch
    # ------------------------------------------------------------------

    def validate(
        self,
        code: str,
        fmt: IaCFormat,
        *,
        file_name: str | None = None,
    ) -> IaCValidationResult:
        """Validate *code* written in the given IaC *fmt*.

        Delegates to the format-specific validator and performs common
        pre-checks (empty file, oversized file).
        """
        errors: list[IaCValidationError] = []
        warnings: list[IaCValidationWarning] = []

        # --- common pre-checks ---
        if not code or not code.strip():
            errors.append(IaCValidationError(message="File is empty"))
            return IaCValidationResult(
                is_valid=False,
                format=fmt,
                errors=errors,
                warnings=warnings,
                file_name=file_name,
            )

        if len(code) > _MAX_CODE_SIZE:
            warnings.append(
                IaCValidationWarning(
                    message=f"File exceeds {_MAX_CODE_SIZE // 1024} KB; validation may be incomplete",
                )
            )

        # --- format dispatch ---
        handler = {
            IaCFormat.bicep: self._validate_bicep,
            IaCFormat.terraform: self._validate_terraform,
            IaCFormat.arm: self._validate_arm,
            IaCFormat.pulumi_ts: self._validate_pulumi_ts,
            IaCFormat.pulumi_py: self._validate_pulumi_py,
        }.get(fmt)

        if handler is None:
            errors.append(IaCValidationError(message=f"Unsupported format: {fmt}"))
            return IaCValidationResult(
                is_valid=False,
                format=fmt,
                errors=errors,
                warnings=warnings,
                file_name=file_name,
            )

        fmt_errors, fmt_warnings = handler(code)
        errors.extend(fmt_errors)
        warnings.extend(fmt_warnings)

        return IaCValidationResult(
            is_valid=len(errors) == 0,
            format=fmt,
            errors=errors,
            warnings=warnings,
            file_name=file_name,
        )

    # ------------------------------------------------------------------
    # Bicep
    # ------------------------------------------------------------------

    def _validate_bicep(
        self, code: str
    ) -> tuple[list[IaCValidationError], list[IaCValidationWarning]]:
        """Validate Bicep syntax."""
        errors: list[IaCValidationError] = []
        warnings: list[IaCValidationWarning] = []

        # Balanced braces
        brace_errors = self._check_balanced_braces(code)
        errors.extend(brace_errors)

        # Required keywords
        known_keywords = {"param", "var", "resource", "module", "output", "targetScope"}
        found = set()
        for line_num, line in enumerate(code.splitlines(), start=1):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue
            for kw in known_keywords:
                if re.match(rf"^{kw}\s", stripped):
                    found.add(kw)

        structural_keywords = {"param", "resource", "module", "output"}
        if not found & structural_keywords:
            warnings.append(
                IaCValidationWarning(
                    message=(
                        "No Bicep structural keywords found "
                        "(expected at least one of: param, resource, module, output)"
                    ),
                )
            )

        # String quoting — detect unmatched single quotes (Bicep uses single quotes)
        for line_num, line in enumerate(code.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            single_quotes = stripped.count("'")
            if single_quotes % 2 != 0:
                errors.append(
                    IaCValidationError(
                        line=line_num,
                        message="Unmatched single quote",
                    )
                )

        # Double-quote warning (Bicep uses single quotes, not double)
        for line_num, line in enumerate(code.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            if '"' in stripped and "'" not in stripped:
                warnings.append(
                    IaCValidationWarning(
                        line=line_num,
                        message="Bicep uses single quotes for strings, not double quotes",
                    )
                )

        return errors, warnings

    # ------------------------------------------------------------------
    # Terraform / HCL
    # ------------------------------------------------------------------

    def _validate_terraform(
        self, code: str
    ) -> tuple[list[IaCValidationError], list[IaCValidationWarning]]:
        """Validate Terraform HCL syntax."""
        errors: list[IaCValidationError] = []
        warnings: list[IaCValidationWarning] = []

        # Balanced braces
        errors.extend(self._check_balanced_braces(code))

        # Block structure: look for top-level blocks
        top_blocks: set[str] = set()
        block_pattern = re.compile(
            r'^(terraform|provider|resource|data|variable|output|locals|module)\s',
        )
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            m = block_pattern.match(stripped)
            if m:
                top_blocks.add(m.group(1))

        if not top_blocks:
            warnings.append(
                IaCValidationWarning(
                    message=(
                        "No Terraform top-level blocks found "
                        "(expected terraform, provider, resource, variable, output, etc.)"
                    ),
                )
            )

        # Check for = inside blocks without leading keyword (common typo)
        for line_num, line in enumerate(code.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            # Detect double-quoted HCL strings with unmatched quotes
            dq = stripped.count('"')
            if dq % 2 != 0:
                errors.append(
                    IaCValidationError(
                        line=line_num,
                        message="Unmatched double quote",
                    )
                )

        # Warn if no resource or data blocks
        if "resource" not in top_blocks and "data" not in top_blocks and "module" not in top_blocks:
            warnings.append(
                IaCValidationWarning(
                    message="No resource, data, or module blocks found",
                )
            )

        return errors, warnings

    # ------------------------------------------------------------------
    # ARM Template (JSON)
    # ------------------------------------------------------------------

    def _validate_arm(
        self, code: str
    ) -> tuple[list[IaCValidationError], list[IaCValidationWarning]]:
        """Validate ARM template JSON structure."""
        errors: list[IaCValidationError] = []
        warnings: list[IaCValidationWarning] = []

        # Parse JSON
        try:
            template = json.loads(code)
        except json.JSONDecodeError as exc:
            errors.append(
                IaCValidationError(
                    line=exc.lineno,
                    column=exc.colno,
                    message=f"Invalid JSON: {exc.msg}",
                )
            )
            return errors, warnings

        if not isinstance(template, dict):
            errors.append(IaCValidationError(message="ARM template must be a JSON object"))
            return errors, warnings

        # Required fields
        if "$schema" not in template:
            errors.append(IaCValidationError(message="Missing required field: $schema"))
        elif not isinstance(template["$schema"], str):
            errors.append(IaCValidationError(message="$schema must be a string"))
        elif "deploymentTemplate" not in template["$schema"].lower() and \
             "subscriptiondeploymenttemplate" not in template["$schema"].lower():
            warnings.append(
                IaCValidationWarning(
                    message="$schema does not reference a known ARM deployment template schema",
                )
            )

        if "contentVersion" not in template:
            errors.append(IaCValidationError(message="Missing required field: contentVersion"))
        elif not isinstance(template["contentVersion"], str):
            errors.append(IaCValidationError(message="contentVersion must be a string"))

        if "resources" not in template:
            errors.append(IaCValidationError(message="Missing required field: resources"))
        elif not isinstance(template["resources"], list):
            errors.append(IaCValidationError(message="resources must be an array"))
        else:
            # Validate individual resources
            for i, resource in enumerate(template["resources"]):
                if not isinstance(resource, dict):
                    errors.append(
                        IaCValidationError(
                            message=f"resources[{i}] must be an object",
                        )
                    )
                    continue
                if "type" not in resource:
                    errors.append(
                        IaCValidationError(
                            message=f"resources[{i}] is missing required field: type",
                        )
                    )
                if "apiVersion" not in resource:
                    errors.append(
                        IaCValidationError(
                            message=f"resources[{i}] is missing required field: apiVersion",
                        )
                    )
                if "name" not in resource:
                    warnings.append(
                        IaCValidationWarning(
                            message=f"resources[{i}] is missing field: name",
                        )
                    )

        # Optional top-level sections — warn if unknown keys present
        known_keys = {
            "$schema", "contentVersion", "apiProfile", "parameters",
            "variables", "functions", "resources", "outputs",
            "metadata", "languageVersion",
        }
        for key in template:
            if key not in known_keys:
                warnings.append(
                    IaCValidationWarning(
                        message=f"Unknown top-level field: {key}",
                    )
                )

        return errors, warnings

    # ------------------------------------------------------------------
    # Pulumi TypeScript
    # ------------------------------------------------------------------

    def _validate_pulumi_ts(
        self, code: str
    ) -> tuple[list[IaCValidationError], list[IaCValidationWarning]]:
        """Validate Pulumi TypeScript syntax."""
        errors: list[IaCValidationError] = []
        warnings: list[IaCValidationWarning] = []

        # Balanced braces and parentheses
        errors.extend(self._check_balanced_braces(code))
        errors.extend(self._check_balanced_parens(code))

        # Import statements
        has_import = False
        has_pulumi_import = False
        for line_num, line in enumerate(code.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("import{"):
                has_import = True
                if "@pulumi/" in stripped or '"@pulumi' in stripped or "'@pulumi" in stripped:
                    has_pulumi_import = True

        if not has_import:
            warnings.append(
                IaCValidationWarning(message="No import statements found"),
            )
        elif not has_pulumi_import:
            warnings.append(
                IaCValidationWarning(message="No @pulumi/* imports found"),
            )

        # Export pattern — Pulumi programs typically export values
        has_export = any(
            line.strip().startswith("export ")
            for line in code.splitlines()
        )
        if not has_export:
            warnings.append(
                IaCValidationWarning(message="No export statements found"),
            )

        # Basic string quoting (unmatched template literals)
        for line_num, line in enumerate(code.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            backticks = stripped.count("`")
            if backticks % 2 != 0:
                errors.append(
                    IaCValidationError(
                        line=line_num,
                        message="Unmatched backtick in template literal",
                    )
                )

        # Semicolons after closing braces (not required in TS but detect obvious issues)
        for line_num, line in enumerate(code.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            # Detect arrow-function-like patterns missing closing
            if stripped.endswith("=>") and line_num < len(code.splitlines()):
                next_line = code.splitlines()[line_num].strip() if line_num < len(code.splitlines()) else ""
                if not next_line:
                    warnings.append(
                        IaCValidationWarning(
                            line=line_num,
                            message="Arrow function followed by empty line — possible incomplete expression",
                        )
                    )

        return errors, warnings

    # ------------------------------------------------------------------
    # Pulumi Python
    # ------------------------------------------------------------------

    def _validate_pulumi_py(
        self, code: str
    ) -> tuple[list[IaCValidationError], list[IaCValidationWarning]]:
        """Validate Pulumi Python syntax."""
        errors: list[IaCValidationError] = []
        warnings: list[IaCValidationWarning] = []

        # Python ast.parse — catches real syntax errors
        try:
            ast.parse(code)
        except SyntaxError as exc:
            errors.append(
                IaCValidationError(
                    line=exc.lineno,
                    column=exc.offset,
                    message=f"Python syntax error: {exc.msg}",
                )
            )
            return errors, warnings

        # Import checks
        has_import = False
        has_pulumi_import = False
        for line_num, line in enumerate(code.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                has_import = True
                if "pulumi" in stripped:
                    has_pulumi_import = True

        if not has_import:
            warnings.append(
                IaCValidationWarning(message="No import statements found"),
            )
        elif not has_pulumi_import:
            warnings.append(
                IaCValidationWarning(message="No pulumi imports found"),
            )

        # Indentation consistency — detect mixed tabs and spaces
        has_tabs = False
        has_spaces = False
        for line_num, line in enumerate(code.splitlines(), start=1):
            if not line or line.isspace():
                continue
            leading = line[: len(line) - len(line.lstrip())]
            if "\t" in leading:
                has_tabs = True
            if " " in leading and leading != "":
                # At least one space used for indentation
                if line != line.lstrip():
                    has_spaces = True

        if has_tabs and has_spaces:
            warnings.append(
                IaCValidationWarning(
                    message="Mixed tabs and spaces detected in indentation",
                )
            )

        # Pulumi export pattern
        has_export = any(
            re.match(r"^pulumi\.export\(", line.strip())
            for line in code.splitlines()
        )
        if not has_export:
            warnings.append(
                IaCValidationWarning(message="No pulumi.export() calls found"),
            )

        return errors, warnings

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_balanced_braces(
        code: str,
    ) -> list[IaCValidationError]:
        """Check that ``{`` and ``}`` are balanced, ignoring strings and comments."""
        errors: list[IaCValidationError] = []
        depth = 0
        in_block_comment = False
        in_string: str | None = None  # quote character if inside a string

        lines = code.splitlines()
        for line_num, line in enumerate(lines, start=1):
            i = 0
            while i < len(line):
                ch = line[i]
                next_ch = line[i + 1] if i + 1 < len(line) else ""

                # Block comment handling
                if in_block_comment:
                    if ch == "*" and next_ch == "/":
                        in_block_comment = False
                        i += 2
                        continue
                    i += 1
                    continue

                # String handling
                if in_string:
                    if ch == "\\" and i + 1 < len(line):
                        i += 2  # skip escaped char
                        continue
                    if ch == in_string:
                        in_string = None
                    i += 1
                    continue

                # Start of comments
                if ch == "/" and next_ch == "/":
                    break
                if ch == "/" and next_ch == "*":
                    in_block_comment = True
                    i += 2
                    continue
                if ch == "#" and not in_string:
                    # HCL/Python single-line comment
                    break

                # Start of string
                if ch in ("'", '"', "`"):
                    in_string = ch
                    i += 1
                    continue

                # Braces
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth < 0:
                        errors.append(
                            IaCValidationError(
                                line=line_num,
                                message="Unexpected closing brace '}'",
                            )
                        )
                        depth = 0

                i += 1

        if depth > 0:
            errors.append(
                IaCValidationError(
                    message=f"Unclosed brace(s): {depth} opening '{{' without matching '}}'",
                )
            )

        return errors

    @staticmethod
    def _check_balanced_parens(
        code: str,
    ) -> list[IaCValidationError]:
        """Check that ``(`` and ``)`` are balanced, ignoring strings and comments."""
        errors: list[IaCValidationError] = []
        depth = 0
        in_block_comment = False
        in_string: str | None = None

        lines = code.splitlines()
        for line_num, line in enumerate(lines, start=1):
            i = 0
            while i < len(line):
                ch = line[i]
                next_ch = line[i + 1] if i + 1 < len(line) else ""

                if in_block_comment:
                    if ch == "*" and next_ch == "/":
                        in_block_comment = False
                        i += 2
                        continue
                    i += 1
                    continue

                if in_string:
                    if ch == "\\" and i + 1 < len(line):
                        i += 2
                        continue
                    if ch == in_string:
                        in_string = None
                    i += 1
                    continue

                if ch == "/" and next_ch == "/":
                    break
                if ch == "/" and next_ch == "*":
                    in_block_comment = True
                    i += 2
                    continue

                if ch in ("'", '"', "`"):
                    in_string = ch
                    i += 1
                    continue

                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth < 0:
                        errors.append(
                            IaCValidationError(
                                line=line_num,
                                message="Unexpected closing parenthesis ')'",
                            )
                        )
                        depth = 0

                i += 1

        if depth > 0:
            errors.append(
                IaCValidationError(
                    message=f"Unclosed parenthesis: {depth} opening '(' without matching ')'",
                )
            )

        return errors


# Module-level singleton
iac_validator = IaCValidator()
