"""
Self-healing adapter builder:
  LLM → Parse YAML → Validate → Error? → Feed error back → Retry (up to 3x)
"""
import yaml
import json
import re
from llm_provider import llm
from core.adapter import save_adapter_files

MAX_RETRIES = 3

SCHEMA_EXAMPLE = """
# schema.yaml
domain_name: "Example Domain"
primary_entity: "Account"
entities:
  - id: account
    label: Account
    primary: true
  - id: contact
    label: Contact
relationships:
  - from: account
    to: contact
    type: has_contact

# intents.yaml
intents:
  - id: churn_risk
    label: Churn Risk
    keywords: [churn, cancel, leaving, competitor]
    description: Customer showing signs of leaving

# actions.yaml
actions:
  - id: schedule_review
    intents: [churn_risk]
    keywords: [usage, drop, health]
    action: "Schedule Executive Business Review within 5 days"
    owner: "Senior CSM"
    action_type: meeting
    priority: critical
    base_confidence: 0.88
    estimated_hours: 2
fallback:
  action: "Review account and schedule check-in"
  owner: "CSM"
  priority: medium
  base_confidence: 0.60

# rules.yaml
severity_keywords:
  critical: [urgent, cancel, rejected]
  high: [concern, dropping, declining]
  medium: [question, wondering]
  low: [update, fyi]
deadline_warning_hours: 48
rejection_count_critical: 3

# knowledge.yaml
playbooks:
  - id: protocol_1
    title: "Escalation Protocol"
    keywords: [health, drop, executive]
    excerpt: "When health score drops below 60%, initiate review within 5 business days."

# ui.yaml
domain_label: "Example Domain"
entity_label: "Account"
interaction_placeholder: "Paste meeting notes or CRM updates here..."
demo_interaction:
  entity_name: "Sample Corp"
  text: "Sample Corp usage dropped 40% last month. Renewal in 28 days."
sample_scenarios:
  - label: "Risk Signal"
    entity_name: "Demo Corp"
    text: "Demo Corp is evaluating competitors."
value_metric:
  label: "ARR Protected"
  per_approved_nba: 50000
"""

SYSTEM_PROMPT = """You are a business analyst configuring a B2B decision intelligence platform.
Given a company description, generate EXACT YAML configuration files.
Output ONLY valid YAML — no markdown fences, no explanation, no comments.
Use EXACTLY this structure and field names as shown in the example."""


def _build_generation_prompt(inputs: dict, previous_error: str = None, attempt: int = 0) -> str:
    error_section = ""
    if previous_error:
        error_section = f"""
CRITICAL: Your previous attempt had these validation errors. You MUST fix them:
{previous_error}

"""
    strictness = ""
    if attempt >= 2:
        strictness = "\nBe EXTREMELY precise. Follow the schema example exactly. Every field is required.\n"

    return f"""{error_section}{strictness}
Company: {inputs.get('company_name', 'Unknown')}
Industry: {inputs.get('industry', 'B2B')}
They manage: {inputs.get('what_they_manage', '')}
Decisions they make: {inputs.get('decisions', '')}
Primary entity: {inputs.get('primary_entity', 'Account')}

Their SOPs and Playbooks:
{inputs.get('sops_text', 'No SOPs provided.')}

Their business rules:
{inputs.get('rules_text', 'No rules provided.')}

Actions available to their team:
{inputs.get('actions_text', 'No actions provided.')}

SCHEMA EXAMPLE (follow this structure exactly):
{SCHEMA_EXAMPLE}

Generate ALL 6 files in this exact order, separated by "---FILENAME: <name>---":
---FILENAME: schema.yaml---
[schema content]
---FILENAME: intents.yaml---
[intents content]
---FILENAME: actions.yaml---
[actions content]
---FILENAME: rules.yaml---
[rules content]
---FILENAME: knowledge.yaml---
[knowledge content]
---FILENAME: ui.yaml---
[ui content]

Generate 4-6 intents and 4-6 actions specific to their business.
"""


def _parse_llm_output(raw: str) -> dict[str, str]:
    """Split LLM output into individual YAML file strings."""
    files = {}
    pattern = r"---FILENAME:\s*(\S+)---\s*(.*?)(?=---FILENAME:|$)"
    matches = re.findall(pattern, raw, re.DOTALL)
    for filename, content in matches:
        # Strip markdown fences if LLM adds them
        content = re.sub(r"```ya?ml\s*", "", content)
        content = re.sub(r"```\s*", "", content)
        files[filename.strip()] = content.strip()
    return files


def _validate_config(files: dict[str, str]) -> list[str]:
    """Return list of validation errors. Empty = valid."""
    errors = []
    required_files = ["schema.yaml", "intents.yaml", "actions.yaml", "rules.yaml", "knowledge.yaml", "ui.yaml"]

    for f in required_files:
        if f not in files:
            errors.append(f"Missing file: {f}")
            continue
        try:
            parsed = yaml.safe_load(files[f])
            if not parsed:
                errors.append(f"{f}: empty or null content")
                continue

            # File-specific validation
            if f == "intents.yaml":
                intents = parsed.get("intents", [])
                if len(intents) < 2:
                    errors.append("intents.yaml: must have at least 2 intents")
                for i, intent in enumerate(intents):
                    for field in ["id", "label", "keywords"]:
                        if field not in intent:
                            errors.append(f"intents.yaml[{i}]: missing field '{field}'")

            elif f == "actions.yaml":
                actions = parsed.get("actions", [])
                if len(actions) < 1:
                    errors.append("actions.yaml: must have at least 1 action")
                for i, action in enumerate(actions):
                    for field in ["id", "action", "owner", "base_confidence"]:
                        if field not in action:
                            errors.append(f"actions.yaml[{i}]: missing field '{field}'")
                    if "base_confidence" in action:
                        bc = action["base_confidence"]
                        if not (0.5 <= bc <= 0.99):
                            errors.append(f"actions.yaml[{i}]: base_confidence must be 0.5-0.99, got {bc}")

            elif f == "schema.yaml":
                if "primary_entity" not in parsed:
                    errors.append("schema.yaml: missing 'primary_entity'")
                if "entities" not in parsed or len(parsed.get("entities", [])) < 1:
                    errors.append("schema.yaml: must have at least 1 entity")

        except yaml.YAMLError as e:
            errors.append(f"{f}: YAML parse error — {str(e)[:200]}")

    return errors


def generate_adapter(inputs: dict) -> dict:
    """
    Self-healing generation loop:
    Generate → Validate → Error? → Feed back → Retry (max 3x)
    Returns: { "files": {filename: content}, "preview": {...}, "slug": str }
    """
    slug = inputs.get("company_name", "unknown").lower().replace(" ", "_").replace("-", "_")
    slug = re.sub(r"[^a-z0-9_]", "", slug)[:30]

    previous_error = None

    for attempt in range(MAX_RETRIES):
        print(f"[Builder] Generation attempt {attempt + 1}/{MAX_RETRIES}")
        prompt = _build_generation_prompt(inputs, previous_error, attempt)

        try:
            raw_output = llm.generate(prompt, SYSTEM_PROMPT)
            files = _parse_llm_output(raw_output)

            if not files:
                previous_error = "Could not parse any YAML files from the output. Use '---FILENAME: schema.yaml---' separators."
                print(f"[Builder] Parse failed on attempt {attempt + 1}")
                continue

            errors = _validate_config(files)

            if not errors:
                print(f"[Builder] Validation passed on attempt {attempt + 1}")
                preview = _build_preview(files)
                return {"files": files, "preview": preview, "slug": slug, "attempts": attempt + 1}

            previous_error = "Fix these specific errors:\n" + "\n".join(f"  - {e}" for e in errors)
            print(f"[Builder] Validation failed on attempt {attempt + 1}: {errors}")

        except Exception as e:
            previous_error = f"LLM call failed: {str(e)}"
            print(f"[Builder] LLM error on attempt {attempt + 1}: {e}")

    # All retries exhausted — return best partial result with error flag
    raise ValueError(
        f"Failed to generate valid adapter after {MAX_RETRIES} attempts. "
        f"Last error: {previous_error}"
    )


def _build_preview(files: dict[str, str]) -> dict:
    """Build the preview object shown in the Blueprint Canvas."""
    preview = {"intents": [], "actions": [], "rules": {}, "knowledge_sources": [], "entities": []}

    try:
        intents_data = yaml.safe_load(files.get("intents.yaml", "")) or {}
        preview["intents"] = intents_data.get("intents", [])
    except Exception:
        pass

    try:
        actions_data = yaml.safe_load(files.get("actions.yaml", "")) or {}
        preview["actions"] = actions_data.get("actions", [])
    except Exception:
        pass

    try:
        rules_data = yaml.safe_load(files.get("rules.yaml", "")) or {}
        preview["rules"] = {
            "deadline_warning_hours": rules_data.get("deadline_warning_hours", 48),
            "severity_keywords": rules_data.get("severity_keywords", {}),
        }
    except Exception:
        pass

    try:
        knowledge_data = yaml.safe_load(files.get("knowledge.yaml", "")) or {}
        preview["knowledge_sources"] = knowledge_data.get("playbooks", [])
    except Exception:
        pass

    try:
        schema_data = yaml.safe_load(files.get("schema.yaml", "")) or {}
        preview["entities"] = schema_data.get("entities", [])
    except Exception:
        pass

    return preview


def deploy_adapter(slug: str, files: dict[str, str]):
    """Save adapter files to disk and hot-reload."""
    save_adapter_files(slug, files)
