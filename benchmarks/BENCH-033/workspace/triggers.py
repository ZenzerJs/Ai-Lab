"""Triggers decide when a window emits its result."""
from windows import window_bounds


class WatermarkTrigger:
    def maybe_fire(self, state, watermark, size):
        if watermark is None:
            return None
        _, end = window_bounds(state.index, size)
        if watermark >= end:
            state.fired = True
            return (state.key, state.index, state.agg.result())
        return None
