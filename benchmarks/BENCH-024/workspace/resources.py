"""Resource pools."""


class ResourcePool:
    def __init__(self, capacities):
        self.capacities = dict(capacities)
        self._in_use = {name: 0 for name in capacities}

    def check(self, needs):
        return True

    def try_acquire(self, needs):
        for name, units in needs:
            self._in_use[name] += units
        return True

    def release(self, needs):
        for name, units in needs:
            self._in_use[name] -= units

    def in_use(self, name):
        return self._in_use[name]
