"""Recheck frozen A candidates against physical prefixes and independently reflected prices."""
import json
from book_boundary_sequence import boundary_close_sequence
from replay_august_book_prefixes import OUT, ROOT, HISTORY, epoch, iso
from research_cases import load_bars


def main():
    aug=json.loads((OUT/'A_and_ranges.json').read_text('utf8'))
    prior=json.loads((ROOT/'verification/book_adjustment_A_20261118/frozen_adjustments.json').read_text('utf8'))
    subjects=[(r['id'],r['direction'],r['first_close'],r['dual_close'],r['adjustment_review'])
              for r in prior['cases'] if r['adjustment_review']['status']=='frozen_counterleg_extreme_candidate']
    for r in aug:
        if r['A'] and r['A']['result']['status']=='frozen_counterleg_extreme_candidate':
            raw=json.loads((OUT/'paired_prefixes.json').read_text('utf8'))
            event=next(e for c in raw['windows'][-1]['cases'] for e in c['events'] if e['id']==r['id'] and c['clock']==r['clock'])
            subjects.append((r['id'],event['direction'],min(r['breaks']),max(r['breaks']),r['A']['result']))
    bars=load_bars(HISTORY)
    data=[(int(b.closed_at.timestamp()),b.close) for b in bars]
    lifetime=json.loads((OUT/'intervening_geometry.json').read_text('utf8'))
    report=[]
    for owner,direction,first,dual,ref in subjects:
        first,dual,known=map(epoch,(first,dual,ref['known']))
        end=max(epoch(r['close_time']) for r in ref['after_dual'])
        native=[r for r in lifetime if r['id']==owner and epoch(r['dual_close'])==dual]
        if native:
            assert all(all(x['same'] for x in r['rows']) for r in native)
            follow=native[0]['rows'][-3:]
            assert [epoch(x['close_time']) for x in follow]==[dual,dual+3600,dual+7200]
            end=dual+7200
        observed=[x for x in data if known<=x[0]<=end]
        assert observed[0][0]==known
        rule=dict(direction=direction,price=ref['price'],known=known,first_break=first,dual_close=dual,seconds=3600)
        for j,(cutoff,_) in enumerate(observed):
            snapshot=boundary_close_sequence(data,cutoff=cutoff,**rule)
            actual=boundary_close_sequence(observed[:j+1],cutoff=cutoff,**rule)
            assert actual==snapshot
            reflection=boundary_close_sequence([(t,-p) for t,p in observed],cutoff=cutoff,
                       **{**rule,'direction':'down' if direction=='up' else 'up','price':-ref['price']})
            assert actual['gaps']==reflection['gaps']
            assert [(x['clock'],x['timing']) for x in actual['crossings']]==[(x['clock'],x['timing']) for x in reflection['crossings']]
            if actual['dual']:
                assert actual['dual']['outside']==reflection['dual']['outside']
        report.append(dict(id=owner, direction=direction, price=ref['price'], first=iso(first),dual=iso(dual),
                           known=iso(known),end=iso(end),prefix_tests=len(observed),author_A_verified=False,
                           sequence=actual))
    # An unobserved gap may start on the opposite side. A touch counts as a touch.
    k=dict(price=100,direction='up',known=0,first_break=1,dual_close=4,cutoff=5,seconds=1)
    example=boundary_close_sequence([(0,101),(1,100),(3,99),(4,100),(5,99)],**k)
    assert len(example['gaps'])==1 and example['dual']['at_level'] and [c['timing'] for c in example['crossings']]==['after_dual']
    (OUT/'boundary_sequences.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    for r in report:
        seq=r['sequence']
        print(r['dual'],r['price'],seq['dual'],[(iso(c['clock']),c['timing']) for c in seq['crossings']],len(seq['gaps']),r['prefix_tests'])

if __name__=='__main__':
    main()
