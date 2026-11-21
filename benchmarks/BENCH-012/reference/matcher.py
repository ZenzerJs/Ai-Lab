"""Segment-aware matching with fail-closed resource validation."""
import re


def valid_resource(resource):
    return (isinstance(resource, str) and bool(resource)
            and all(part not in (".", "..")
                    and re.fullmatch(r"[A-Za-z0-9_.-]+", part)
                    for part in resource.split("/")))


def matches(pattern, resource):
    if not valid_resource(resource) or not isinstance(pattern, str):
        return False
    if pattern == "*":
        return True
    if pattern.endswith("/*"):
        prefix = pattern[:-2]
        return valid_resource(prefix) and resource.startswith(prefix + "/")
    return valid_resource(pattern) and pattern == resource
