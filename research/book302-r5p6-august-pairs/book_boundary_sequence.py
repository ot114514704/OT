"""Order closed-bar observations of a previously frozen Book adjustment candidate."""
from math import isfinite


def boundary_close_sequence(observations, *, price, direction, known, first_break, dual_close, cutoff, seconds):
    """Return observable crossings separately from location. Clocks denote closed bars.

    The caller provides one verified wave and stops at its last extant close.
    A gap records the first observed side without reconstructing an unseen crossing.
    """
    if not (direction in ('up','down') and isfinite(price) and seconds>0 and known<=first_break<=dual_close):
        raise ValueError('Invalid frozen wave or break clocks')
    previous = None
    crossed = []
    gaps = []
    dual = None
    sign = -1 if direction=='up' else 1
    for clock, close in observations:
        if clock > cutoff:
            break
        if clock < known:
            continue
        if not isfinite(close) or previous and clock<=previous[0]:
            raise ValueError('Expected finite closes in strict time order')
        outside = sign * (close-price)>0
        if previous:
            prev_clock, prev_close = previous
            if clock-prev_clock != seconds:
                gaps.append(dict(previous=prev_clock, current=clock, outside=outside))
            elif outside and sign*(prev_close-price)<=0:
                timing = ('before_first' if clock<first_break else 'at_first' if clock==first_break<dual_close else
                          'between_lines' if clock<dual_close else 'on_dual' if clock==dual_close else 'after_dual')
                crossed.append(dict(clock=clock, previous_close=prev_close, close=close, timing=timing))
        if clock==dual_close:
            dual=dict(clock=clock,close=close,outside=outside,at_level=close==price)
        previous = (clock,close)
    return dict(crossings=crossed, gaps=gaps, dual=dual)
