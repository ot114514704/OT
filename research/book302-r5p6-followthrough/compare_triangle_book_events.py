"""Test Book-line association at each of the two closes of screened triangle exits."""
import csv
import json
from datetime import datetime
from pathlib import Path
from compare_triangle_followthrough import OUT
from replay_august_overlap import HISTORY, SCAN, NativeBar, load_bars
from worker import recognize
from book_auxiliary import select


def main():
    with (OUT/'triangle_followthrough.json').open(encoding='utf8') as f:
        events = json.load(f)['events']
    bars = tuple(NativeBar(b.time,b.open,b.high,b.low,b.close,b.spread*.01,3600) for b in load_bars(HISTORY))
    opens = {int(b.time.timestamp()):i for i,b in enumerate(bars)}
    closes = {int(b.closed_at.timestamp()):i for i,b in enumerate(bars)}
    clocks = {}
    for event in events:
        i = event['i']
        if bars[i-1].closed_at != bars[i].time:
            continue
        clocks[int(bars[i-1].closed_at.timestamp())] = ('first',event)
        clocks[int(bars[i].closed_at.timestamp())] = ('second',event)
    with SCAN.open(encoding='utf-8-sig') as f:
        lines = {}
        for r in csv.DictReader(f,delimiter='\t'):
            clock,known = int(r['cross']),int(r['known'])
            if not 0 < known <= clock-3600 or 'retrospective' in r['state']:
                continue
            needed = {k:r[k] for k in ('id','family','known','cross','state','owner_a','owner_b','anchor_a','anchor_b','price_a','price_b','pb')}
            if r['id'] in lines:
                assert needed == lines[r['id']]
            lines[r['id']] = needed
    rows = []
    for clock,(which,event) in sorted(clocks.items()):
        group = [r for r in lines.values() if int(r['cross'])==clock]
        if not group:
            continue
        i = closes[clock]
        start = max(0,i-512)
        before = recognize(bars[start:i])[0]
        after = recognize(bars[start:i+1])[0]
        for r in group:
            a,b = opens[int(r['anchor_a'])],opens[int(r['anchor_b'])]
            slope = (float(r['price_b'])-float(r['price_a']))/(b-a)
            line = dict(id=r['id'],family=r['family'],known=int(r['known']),clock=clock,
                        state=r['state'],owner_a=int(r['owner_a']),owner_b=int(r['owner_b']),
                        line=float(r['pb']),slope=slope)
            sel = select(line,bars[i-1],bars[i],before,after)
            assert not sel['trend_override'] and not sel['confirmed_reversal']
            ids = [m['range']['id'] for m in [sel['primary'],*sel['alternatives']] if m]
            hit = event['id'] in ids
            reason = next((x['reason'] for x in sel['rejected'] if x['id']==event['id']), None)
            rows.append(dict(book=line['id'], family=line['family'], book_clock=bars[i].closed_at.isoformat(),
                             triangle=event['id'], first_or_second=which, group=event['group'],
                             primary=ids[0] if ids else None, matched=hit,
                             reason=None if hit else reason or '当根无该范围或时序未通过'))
    report = dict(eligible_lines=len(lines), coincident=len(rows), associated=sum(r['matched'] for r in rows),
                  primary=sum(r['primary']==r['triangle'] for r in rows), rows=rows)
    (OUT/'book_associations.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    print({k:v for k,v in report.items() if k!='rows'},flush=True)

if __name__=='__main__':
    main()
