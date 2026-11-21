# BENCH-012: RBAC Policy Engine & Audit Trail

Repair models.py, matcher.py, policy_engine.py and audit.py. Stdlib only.

## Public API and invariants
- Frozen dataclasses in models:
  Role(name, parents=()) copies parents to an independent tuple.
  Rule(role, action, resource, effect="allow") accepts only "allow"/"deny" effects,
  otherwise raises ValueError.
  Decision(allowed, reason) records a bool and a reason string.
- matcher.valid_resource(resource) accepts nonempty relative slash-separated paths.
  Each segment contains only ASCII letters, digits, underscore, dot or hyphen, but
  standalone "." and ".." segments are forbidden. Empty segments, leading/trailing
  slash, backslashes, percent encoding, query/fragment strings and wildcards are
  invalid resources. Do not normalize an unsafe path into a safe one.
  matches(pattern, resource) always rejects invalid resources. Supported patterns:
  "*" matches any valid resource; a valid literal path matches exactly; trailing
  "/*" matches descendants of the literal prefix, at a slash boundary, not the
  prefix itself. E.g. "docs/*" matches "docs/a/b" but NOT "docs-secret/x" or "docs".
  All other wildcard forms and malformed patterns fail closed (False).
- audit.AuditLog().record(subject, roles, action, resource, decision) appends a
  deep independent dict containing those fields, except decision is expanded to
  "allowed" and "reason" and roles is stored as a list. entries() returns deep
  copies in decision order. Instances must not share mutable state.
- policy_engine.PolicyEngine(roles, rules, audit=None) accepts iterables of Role
  and Rule; exposes .audit. Duplicate role names raise ValueError.
  resolve_roles(role_names) returns a set containing all known direct and inherited
  roles. Unknown roles/parents are ignored. Cycles must terminate without losing
  any reachable roles or permissions (including deny rules).
  decide(subject, roles, action, resource) returns Decision:
    invalid resource -> (False, "invalid_resource")
    any matching explicit deny -> (False, "explicit_deny")
    otherwise any matching allow -> (True, "allow")
    otherwise -> (False, "no_matching_allow").
  Match the action exactly or via a rule action "*". Evaluate all reachable rules,
  so deny wins regardless of rule order, requested-role order or inheritance depth.
  Subject is an audit label, not a role. Empty or unknown-only roles default deny.
  Every decision, including invalid resources and implicit/explicit denies, MUST
  append exactly one audit entry with its exact reason, subject, roles, action and
  resource. Do not leak audit entries between engine instances.

Visible tests cover only a straightforward direct-role allow.
