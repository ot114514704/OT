"""Check the three subsequent H1 closes against the same pair frozen before a dual cross."""
import csv
import json
from datetime import datetime, timezone
from fractions import Fraction
from verify_book_panel_r5p7 import ROOT, OUT, NativeBar, inspect_close


def main():
    with (ROOT/'testdata/native_history_H1.tsv').open(encoding='utf-8-sig') as f:
        bars=[NativeBar(datetime.fromtimestamp(int(r['time']),timezone.utc),
                        *(float(r[k]) for k in ('open','high','low','close')),0,3600)
              for r in csv.DictReader(f,delimiter='\t')]
    index={b.time.isoformat().replace('+00:00','Z'):i for i,b in enumerate(bars)}
    decisions=['2026-10-01T06','2026-10-02T19','2026-10-29T09','2026-11-10T19']
    reports=[]
    for clock in decisions:
        i=next(i for i,b in enumerate(bars) if b.closed_at.isoformat().startswith(clock+':'))
        pairs=[p for p in inspect_close(bars[i-511:i+1])['pairs'] if p['event']=='same_bar']
        assert pairs
        for p in pairs:
            def price(line,anchor,j):
                a,b=line[:2]
                slope=(Fraction(str(b[1]))-Fraction(str(a[1])))/(index[b[0]]-index[a[0]])
                return Fraction(str(anchor[1]))+slope*(j-index[anchor[0]])
            records=[]
            for j in range(i,i+4):
                if bars[j-1].closed_at!=bars[j].time:
                    break
                close=Fraction(str(bars[j].close))
                trend=price(p['trend'],p['trend'][0],j)
                turning=price(p['turning'],p['turning'][2],j)
                side=1 if p['direction']=='down' else -1
                outside=side*(close-trend)>0 and side*(close-turning)>0
                records.append(dict(clock=bars[j].closed_at.isoformat(),close=float(close),trend=float(trend),
                                    turning=float(turning),outside_both=outside))
            assert records[0]['outside_both']
            reports.append(dict(owner=p['owner'],direction=p['direction'],clock=clock,records=records,
                                three_more_outside=all(x['outside_both'] for x in records[1:]) if len(records)==4 else None))
    result=dict(method='Frozen pair extrapolated on observed H1 bar index; diagnostic after the event, no automatic A or reversal confirmation.',reports=reports)
    (OUT/'frozen_pair_followthrough.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    for r in reports:
        print(r['clock'],r['direction'],[int(x['outside_both']) for x in r['records']])


if __name__=='__main__':
    main()

