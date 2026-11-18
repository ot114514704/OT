"""Bind August Book prefix events to their own frozen A and local range evidence."""
import csv
import json
import sys
import tempfile
from replay_august_book_prefixes import ARCHIVE, HISTORY, OUT, iso, epoch
from replay_book_pair_evidence import extract_sources
from replay_book_adjustment_A import evaluate, candidate_follow, reproduce_candidate_clock
from replay_august_overlap import SHAPES
from replay_book_outline_side import EXPORT
from research_cases import load_bars
from worker import NativeBar, recognize
from book_auxiliary import select


def main():
    native = tuple(NativeBar(b.time,b.open,b.high,b.low,b.close,b.spread*.01,3600) for b in load_bars(HISTORY))
    rows = [dict(timestamp_utc=iso(b.time.timestamp()), timeframe='H1', symbol='XAUUSD',provider='saved_MT5_history',
                 **{k:getattr(b,k) for k in ('open','high','low','close')}) for b in native]
    ix = {iso(b.closed_at.timestamp()):i for i,b in enumerate(native)}
    audit = json.loads((OUT/'paired_prefixes.json').read_text('utf8'))
    export = EXPORT.read_text('utf-16').splitlines()
    start = next(i for i,s in enumerate(export) if s.startswith('known\tstart\t'))
    latest = list(csv.DictReader(export[start:],delimiter='\t'))
    cases=[]
    with tempfile.TemporaryDirectory(dir=OUT) as folder:
        from pathlib import Path
        extract_sources(ARCHIVE,Path(folder))
        sys.path.insert(0,folder)
        for c in audit['windows'][1]['cases']:
            for e in c['events']:
                clock=c['clock']
                assert e['source_at_first'] and e['source_alive']
                i=ix[clock]
                bt=[x for x in e['break_times'] if x]
                origins=[o[0] for o in e['owner']]
                common=dict(id=e['id'], first_close=min(bt),second_close=clock,owner=origins,
                            stage_at_second=e['stage'],break_times=e['break_times'],bars_between=e['bars_between'])
                adjustment=None
                if len(bt)==2:
                    # Prefix starts must contain the owner; an omitted owner is reported in the parent audit.
                    win=dict(start=audit['windows'][1]['start'])
                    case=evaluate(win,common,rows,native)
                    case['warmup_checks']=[]
                    offset=next(j for j,r in enumerate(rows) if r['timestamp_utc']>=win['start'])
                    for n in (48,96):
                        other=evaluate(dict(start=rows[offset-n]['timestamp_utc']),common,rows,native)
                        case['warmup_checks'].append(dict(extra=n,children_equal=case['scope_children']==other['scope_children']))
                    adjustment=candidate_follow(case,rows[:i+1],None)
                    if adjustment['status']=='frozen_counterleg_extreme_candidate':
                        case['adjustment_review']=adjustment
                        reproduce_candidate_clock(win,case,rows)
                    adjustment=dict(result=adjustment,children=case['scope_children'],abc=case['abc'],
                                    freeze=case['freeze'],book_A=case['A'],warmup=case['warmup_checks'])
                by_warmup=[]
                patterns=[dict(category=int(p['category']),state=int(p['state']),known=int(p['known']),event=int(p['event']),
                               start=int(p['start']),end=int(p['end'])) for p in latest if p['category'] in ('1','2','3','4')]
                for n in (256,512):
                    before=recognize(native[i-n:i])[0]
                    after=recognize(native[i-n:i+1])[0]
                    rail_info={}
                    for side,(role,when) in enumerate(zip(('trend','turning'),e['break_times'])):
                        if when!=clock:
                            continue
                        line=dict(id=e['id']+'/'+role,clock=epoch(clock),known=epoch(e['signature_known']),
                                  owner_a=epoch(origins[0]),owner_b=epoch(origins[1]),
                                  line=e['current'][side],slope=e['current'][side]-e['previous'][side],state='native_first_close')
                        selection=select(line,native[i-1],native[i],before,after,
                                         [dict(p,event_id=line['id']) for p in patterns])
                        hits=[r for r in [selection['primary'],*selection['alternatives']] if r]
                        hit_ids={r['range']['id'] for r in hits}
                        rail_info[role]=dict(primary=hits[0]['range']['id'] if hits else None,
                                             marked={k:r in hit_ids for k,r in SHAPES.items()},
                                             reasons={k:next((z['reason'] for z in selection['rejected'] if z['id']==r),None)
                                                      for k,r in SHAPES.items() if r not in hit_ids},
                                             pa=[{k:p[k] for k in ('category','known','start','end','observed_state','binding_basis')}
                                                 for p in selection['pa']])
                    by_warmup.append(rail_info)
                cases.append(dict(clock=clock,id=e['id'],previous=e['previous'],current=e['current'],close=e['close'],
                                  breaks=e['break_times'],A=adjustment,auxiliary=by_warmup,
                                  same_auxiliary=by_warmup[0]==by_warmup[1]))
    (OUT/'A_and_ranges.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),'utf8')
    for r in cases:
        print(r['clock'],r['same_auxiliary'],r['A']['result']['status'] if r['A'] else 'single',r['auxiliary'][0],flush=True)

if __name__=='__main__':
    main()
