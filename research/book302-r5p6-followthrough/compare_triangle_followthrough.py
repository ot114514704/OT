"""Measure subsequent closes for early geometric exits without refitting Book or frozen rails."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from replay_august_overlap import HISTORY, OUT as ARCHIVE, SHAPES, load_bars, NativeBar
from ict_trader.native_triangles import observe_triangles

OUT = Path(__file__).resolve().parent/'verification/triangle_followthrough_20261118'
SEPARATION = '2026-09-02'  # first full day after the marked September 1 example


def summarize(records):
    groups = {}
    for group in ('buffered','geometric_only'):
        rows = [r for r in records if r['group']==group]
        valid = [r for r in rows if r['outcome'] is not None]
        groups[group] = dict(events=len(rows), usable=len(valid), excluded=len(rows)-len(valid),
            held_all_three=sum(r['outcome']['outside_count']==3 for r in valid),
            returned_at_least_once=sum(r['outcome']['outside_count']<3 for r in valid),
            third_close_beyond=sum(r['outcome']['last_outside'] for r in valid))
    return groups


def main():
    bars = tuple(NativeBar(b.time,b.open,b.high,b.low,b.close,b.spread*.01,3600) for b in load_bars(HISTORY))
    closes = {b.closed_at.isoformat():i for i,b in enumerate(bars)}
    opens = {b.time.isoformat():i for i,b in enumerate(bars)}
    prior = json.loads((ARCHIVE/'triangle_exit_audit.json').read_text('utf8'))
    shapes = {s['id']:s for s in observe_triangles(bars,bars[-1].closed_at)['ranges']}
    events = []
    for row in prior['records']:
        first = row['geometric']
        if not first:
            continue
        shape = shapes[row['id']]
        side = first['side']
        i = closes[first['time']]
        assert closes[shape['known_at']] < i-1
        a,b = shape['geometry']['upper' if side==1 else 'lower']
        x,y = opens[a['time']], opens[b['time']]
        slope = (b['price']-a['price'])/(y-x)
        edge = a['price']+slope*(i-x)
        distances = [side*(bars[j].close-(a['price']+slope*(j-x))) for j in (i-1,i)]
        assert min(distances)>0
        buffered = min(distances) > .15*shape['frozen_atr']
        assert buffered == (row['buffered'] == first)
        horizon = bars[i+1:i+4]
        comparable = len(horizon)==3 and all(bars[j].time==bars[j-1].closed_at for j in range(i-1,i+4))
        outcome = None
        if comparable:
            beyond = [side*(b.close-edge)>0 for b in horizon]
            outcome = dict(outside_count=sum(beyond),last_outside=beyond[-1],
                           future_closes=[b.close for b in horizon])
        events.append(dict(id=row['id'], known=shape['known_at'], i=i, clock=first['time'], side=side,
                           edge=edge, group='buffered' if buffered else 'geometric_only', outcome=outcome))
    # Keep the earliest-known representative of each time. Admit the next event
    # only after the last selected event's three future closes are complete.
    events.sort(key=lambda e:(e['i'],e['known'],e['id']))
    chosen = []
    for e in events:
        if not chosen or e['i']-chosen[-1]['i']>3:
            chosen.append(e)
    assert all(b['i']-a['i']>3 for a,b in zip(chosen,chosen[1:]))
    partitions = {'all':chosen,'before_sep02':[e for e in chosen if e['clock']<SEPARATION],
                  'from_sep02':[e for e in chosen if e['clock']>=SEPARATION]}
    out = dict(source_sha256=hashlib.sha256(HISTORY.read_bytes()).hexdigest(), native_bars=len(bars),
               all_candidate_events=len(events), distinct_times=len(set(e['clock'] for e in events)),
               nonoverlapping_events=len(chosen), summary={k:summarize(v) for k,v in partitions.items()},
               separation=SEPARATION, target=next(e for e in events if e['id']==SHAPES['triangle']),
               events=chosen)
    (OUT/'triangle_followthrough.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps({k:v for k,v in out.items() if k!='events'}, ensure_ascii=False, indent=2))

if __name__=='__main__':
    main()
