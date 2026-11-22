"""Pipeline: events -> watermark -> per-(key,window) state -> results."""
from watermark import Watermark
from windows import WindowState, window_of
from triggers import WatermarkTrigger


class Pipeline:
    def __init__(self, size, lateness, aggregator_factory):
        self.size = size
        self.wm = Watermark(lateness)
        self.factory = aggregator_factory
        self.trigger = WatermarkTrigger()
        self.states = {}
        self.results = []

    def push(self, event):
        wm = self.wm.observe(event.ts)
        # BUG: late events are still aggregated — is_late never checked
        idx = window_of(event.ts, self.size)
        state = self.states.get((event.key, idx))
        if state is None:
            state = WindowState(event.key, idx, self.factory())
            self.states[(event.key, idx)] = state
        state.add(event.value)
        fired = []
        for st in self.states.values():
            out = self.trigger.maybe_fire(st, wm, self.size)
            if out is not None:
                self.results.append(out)
                fired.append(out)
        return fired
