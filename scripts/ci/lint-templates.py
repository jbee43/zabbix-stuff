#!/usr/bin/env python3
"""Lint Zabbix template JSON files against repo conventions.

Checks:
- Valid JSON and required top-level structure (zabbix_export.version, templates)
- Template has name, description, groups, tags (including class: and target:)
- All items, prototypes, triggers, macros, discovery rules have descriptions/tags
- Master items (history=0, trends=0) have a nodata trigger
- Preprocessing step types are valid Zabbix 7.2 constants
  (item vs. LLD subsets; error_handler values)
- All UUIDs are valid UUIDv4 (Zabbix rejects any other variant on import)
- No duplicate UUIDs across the repo
- Password/secret/token macros are SECRET_TEXT (no plaintext values)
- Templates with active-agent items have a matching userparameters/<base>.conf
  (unless every active key uses Zabbix built-in namespaces)
"""

import json
import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEMPLATES_DIR = os.path.join(REPO_ROOT, "templates")
USERPARAMS_DIR = os.path.join(REPO_ROOT, "userparameters")

# Zabbix 7.2 preprocessing type constants (items and item prototypes)
# Source: ui/include/classes/import/validators/C72XmlValidator.php
VALID_ITEM_PREPROC = {
    "MULTIPLIER",
    "RTRIM", "LTRIM", "TRIM",
    "REGEX",
    "BOOL_TO_DECIMAL", "OCTAL_TO_DECIMAL", "HEX_TO_DECIMAL",
    "SIMPLE_CHANGE", "CHANGE_PER_SECOND",
    "XMLPATH", "JSONPATH",
    "IN_RANGE", "MATCHES_REGEX", "NOT_MATCHES_REGEX",
    "CHECK_JSON_ERROR", "CHECK_XML_ERROR", "CHECK_REGEX_ERROR",
    "CHECK_NOT_SUPPORTED",
    "DISCARD_UNCHANGED", "DISCARD_UNCHANGED_HEARTBEAT",
    "JAVASCRIPT",
    "PROMETHEUS_PATTERN", "PROMETHEUS_TO_JSON",
    "CSV_TO_JSON", "XML_TO_JSON",
    "STR_REPLACE",
    "SNMP_WALK_VALUE", "SNMP_WALK_TO_JSON", "SNMP_GET_VALUE",
}

# Restricted subset accepted inside discovery_rules[].preprocessing[]
VALID_LLD_PREPROC = {
    "REGEX", "XMLPATH", "JSONPATH",
    "MATCHES_REGEX", "NOT_MATCHES_REGEX",
    "CHECK_JSON_ERROR", "CHECK_XML_ERROR", "CHECK_NOT_SUPPORTED",
    "DISCARD_UNCHANGED_HEARTBEAT",
    "JAVASCRIPT",
    "PROMETHEUS_TO_JSON", "CSV_TO_JSON", "XML_TO_JSON",
    "STR_REPLACE",
    "SNMP_WALK_TO_JSON",
}

VALID_ERROR_HANDLERS = {
    "ORIGINAL_ERROR", "DISCARD_VALUE", "CUSTOM_VALUE", "CUSTOM_ERROR",
}

# Zabbix agent built-in key namespaces — active items using only these keys
# do not require a UserParameter config file.
BUILTIN_KEY_PREFIXES = (
    "agent.", "system.", "vfs.", "vm.", "net.", "proc.", "kernel.",
    "sensor[", "web.", "zabbix[", "zabbix.stats[",
    "log[", "log.count[", "logrt[", "logrt.count[",
    "eventlog[", "perf_counter[", "perf_counter_en[",
    "perf_instance[", "perf_instance_en[", "wmi.",
    "systemd.",
)

SECRET_NAME_PATTERN = re.compile(r"(PASSWORD|SECRET|TOKEN|APIKEY)", re.IGNORECASE)

# 32 hex chars, version nibble 4, variant nibble in {8,9,a,b} (RFC 4122 UUIDv4).
UUID4_PATTERN = re.compile(r"^[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$")

errors: list[str] = []
warnings: list[str] = []
uuid_locations: dict[str, list[str]] = {}


def err(file: str, msg: str) -> None:
    errors.append(f"  ERROR: {file}: {msg}")


def warn(file: str, msg: str) -> None:
    warnings.append(f"  WARN:  {file}: {msg}")


def record_uuid(uuid: str, file: str, context: str) -> None:
    if not uuid:
        return
    if not UUID4_PATTERN.match(uuid):
        err(file, f"{context}: UUID '{uuid}' is not a valid UUIDv4")
    uuid_locations.setdefault(uuid, []).append(f"{file} ({context})")


def check_tags_have(tags, prefix, file, context):
    if not tags:
        err(file, f"{context} has no tags")
        return
    prefixes = [t.get("tag", "") for t in tags]
    if prefix not in prefixes:
        warn(file, f"{context} missing '{prefix}' tag")


def check_preprocessing(steps, file, context, valid_types):
    for idx, step in enumerate(steps, start=1):
        ptype = step.get("type", "")
        if ptype not in valid_types:
            err(file, f"{context} preprocessing step {idx}: invalid type '{ptype}'")
        handler = step.get("error_handler")
        if handler and handler not in VALID_ERROR_HANDLERS:
            err(file, f"{context} preprocessing step {idx}: invalid error_handler '{handler}'")


def check_item(item, file, context, is_prototype=False):
    name = item.get("name", "(unnamed)")
    ctx = f"{context} item '{name}'"
    record_uuid(item.get("uuid", ""), file, ctx)
    if not item.get("description"):
        warn(file, f"{ctx} has no description")
    if not item.get("tags"):
        warn(file, f"{ctx} has no tags")
    check_preprocessing(item.get("preprocessing", []), file, ctx, VALID_ITEM_PREPROC)
    for trigger in item.get("triggers", []):
        check_trigger(trigger, file, ctx)


def check_trigger(trigger, file, context):
    name = trigger.get("name", "(unnamed)")
    ctx = f"{context} trigger '{name}'"
    record_uuid(trigger.get("uuid", ""), file, ctx)
    if not trigger.get("description"):
        warn(file, f"{ctx} has no description")


def check_macro(macro, file):
    name = macro.get("macro", "(unnamed)")
    if not macro.get("description"):
        err(file, f"macro {name} has no description")
    if SECRET_NAME_PATTERN.search(name) and macro.get("value") and macro.get("type") != "SECRET_TEXT":
        err(file, f"macro {name} looks like a credential but is not SECRET_TEXT and has a plaintext value")


def has_nodata_trigger(items):
    for item in items:
        for trigger in item.get("triggers", []):
            if "nodata(" in trigger.get("expression", ""):
                return True
    return False


def check_discovery_rule(rule, file):
    name = rule.get("name", "(unnamed)")
    ctx = f"discovery '{name}'"
    record_uuid(rule.get("uuid", ""), file, ctx)
    if not rule.get("description"):
        warn(file, f"{ctx} has no description")
    check_preprocessing(rule.get("preprocessing", []), file, ctx, VALID_LLD_PREPROC)
    for proto in rule.get("item_prototypes", []):
        check_item(proto, file, ctx, is_prototype=True)
    for proto in rule.get("trigger_prototypes", []):
        check_trigger(proto, file, ctx)


def check_active_agent_userparameters(template, basename_noext, file):
    """If any ZABBIX_ACTIVE item uses a non-builtin key, require a userparameters file."""
    active_keys: list[str] = []
    for item in template.get("items", []):
        if item.get("type") == "ZABBIX_ACTIVE":
            active_keys.append(item.get("key", ""))
    for rule in template.get("discovery_rules", []):
        if rule.get("type") == "ZABBIX_ACTIVE":
            active_keys.append(rule.get("key", ""))

    if not active_keys:
        return

    custom_keys = [k for k in active_keys if not k.startswith(BUILTIN_KEY_PREFIXES)]
    if not custom_keys:
        return

    candidates = [
        os.path.join(USERPARAMS_DIR, f"{basename_noext}.conf"),
        os.path.join(USERPARAMS_DIR, f"{basename_noext}-win.conf"),
    ]
    if not any(os.path.isfile(c) for c in candidates):
        err(file, f"has active-agent items with custom keys but no userparameters/{basename_noext}.conf")


def check_template(template, file):
    basename = os.path.basename(file)
    record_uuid(template.get("uuid", ""), basename, f"template '{template.get('name', '(unnamed)')}'")

    if not template.get("name"):
        err(basename, "template has no name")
    if not template.get("description"):
        err(basename, "template has no description")
    if not template.get("groups"):
        err(basename, "template has no groups")

    tags = template.get("tags", [])
    if not tags:
        err(basename, "template has no tags")
    else:
        check_tags_have(tags, "class", basename, "template")
        check_tags_have(tags, "target", basename, "template")

    for macro in template.get("macros", []):
        check_macro(macro, basename)

    items = template.get("items", [])
    master_items = []
    for item in items:
        check_item(item, basename, "template")
        if str(item.get("history", "")) == "0" and str(item.get("trends", "")) == "0":
            master_items.append(item)

    if master_items and not has_nodata_trigger(items):
        err(basename, "has master item(s) but no nodata trigger")

    for rule in template.get("discovery_rules", []):
        check_discovery_rule(rule, basename)

    for valuemap in template.get("valuemaps", []):
        record_uuid(valuemap.get("uuid", ""), basename, f"valuemap '{valuemap.get('name', '')}'")

    base_noext = os.path.splitext(basename)[0]
    check_active_agent_userparameters(template, base_noext, basename)


def lint_file(filepath):
    basename = os.path.basename(filepath)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        err(basename, f"invalid JSON: {e}")
        return

    export = data.get("zabbix_export")
    if not export:
        err(basename, "missing zabbix_export top-level key")
        return

    version = export.get("version")
    if not version:
        err(basename, "missing zabbix_export.version")
    elif version != "7.2":
        warn(basename, f"version is {version}, expected 7.2")

    templates = export.get("templates", [])
    if not templates:
        err(basename, "no templates found in export")
        return

    for template in templates:
        check_template(template, filepath)

    for graph in export.get("graphs", []):
        record_uuid(graph.get("uuid", ""), basename, f"graph '{graph.get('name', '')}'")


def main():
    if not os.path.isdir(TEMPLATES_DIR):
        print(f"Templates directory not found: {TEMPLATES_DIR}", file=sys.stderr)
        sys.exit(1)

    files = sorted(f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".json"))
    if not files:
        print("No template JSON files found", file=sys.stderr)
        sys.exit(1)

    print(f"Linting {len(files)} template(s)...")
    for f in files:
        lint_file(os.path.join(TEMPLATES_DIR, f))

    for uuid, locations in uuid_locations.items():
        if len(locations) > 1:
            err("(repo)", f"duplicate UUID {uuid} used in: {'; '.join(locations)}")

    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(w)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)
        sys.exit(1)

    print(f"\nAll {len(files)} templates passed.")


if __name__ == "__main__":
    main()
