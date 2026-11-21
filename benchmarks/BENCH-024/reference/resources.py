"""Resource pools with atomic all-or-nothing acquisition."""
from models import ResourceCapacityError


class ResourcePool:
    def __init__(self, capacities):
        if not isinstance(capacities, dict) or not capacities:
            raise ResourceCapacityError("capacities must be a nonempty dict")
        for name, cap in capacities.items():
            if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
                raise ResourceCapacityError(
                    f"capacity for {name!r} must be a positive int")
        self.capacities = dict(capacities)
        self._in_use = {name: 0 for name in capacities}

    def check(self, needs):
        """True iff every requested unit fits the pool's capacity."""
        for name, units in needs:
            cap = self.capacities.get(name)
            if cap is None:
                return False
            if units > cap:
                return False
        return True

    def try_acquire(self, needs):
        """All-or-nothing: acquire every unit or none (never partial)."""
        if not self.check(needs):
            return False
        for name, units in needs:
            if self._in_use[name] + units > self.capacities[name]:
                return False
        for name, units in needs:
            self._in_use[name] += units
        return True

    def release(self, needs):
        for name, units in needs:
            self._in_use[name] -= units
            if self._in_use[name] < 0:
                raise ResourceCapacityError(f"over-release on {name!r}")

    def in_use(self, name):
        return self._in_use[name]
