"""Triggers decide when a window emits its result."""
from windows import window_bounds


class WatermarkTrigger:
    """Fire when watermark >= window end.

    The watermark reaching a window's end means no more on-time events
    can arrive for it: emit result once, mark fired.
    """

    def maybe_fire(self, state, watermark, size):
        if watermark is None or state.fired:
            return None
        _, end = window_bounds(state.index, size)
        if watermark >= end:
            state.fired = True
            return (state.key, state.index, state.agg.result())
        return None
