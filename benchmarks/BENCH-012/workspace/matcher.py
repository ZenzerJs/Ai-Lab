"""Simple resource prefix matching."""
def valid_resource(resource):
    return isinstance(resource, str) and bool(resource)


def matches(pattern, resource):
    return valid_resource(resource) and resource.startswith(pattern.rstrip("*"))
