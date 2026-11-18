"""Rebuild active Book rulers at the open of each marked H1, before reading its close."""
import csv
import hashlib
import json
import sys
import tempfile
from collections import Counter
from fractions import Fraction
from pathlib import Path
from replay_book_pair_evidence import ARCHIVE, HISTORY, ROOT, extract_sources, iso
from replay_book_adjustment_A import epoch

OUT = ROOT/'verification/book_august_prefix_20261118'
DATES = [('2026-08-28', range(5,22)), ('2026-09-01',range(2,14))]
CLOCKS = [date+f'T{h:02d}:00:00Z' for date,hours in DATES for h in hours]


def rulers(rows, cutoff):
    from src.book_native_wave_process import recognize_wave_process
    from src.trend_wave_state_adjudication import fit_native_wave_scope
    active = recognize_wave_process(rows,'H1',cutoff)['active']
    qualified = {}
    for owner in active:
        if not owner.get('terminal'):
            continue
        def point(key):
            t,price=owner[key]
            return [iso(t),price]
        fit = fit_native_wave_scope(rows,'H1',cutoff,point('origin'),point('terminal'),owner['known_at_utc'])
        if fit['qualified'] and fit.get('parallel_projection') and fit['parallel_projection'].get('qualified'):
            o,t = fit['outer_line'],fit['parallel_projection']
            signature = (tuple(point('origin')), tuple(point('terminal')), o['direction'],
                         o['known_at_utc'],t['known_at_utc'], *[(rows[line[p+'_index']]['timestamp_utc'],line[p+'_price'])
                         for line,p in ((o,'start'),(o,'end'),(t,'extension_start'),(t,'extension_end'),(t,'start'))])
            qualified[owner['scope_id']] = (owner, o, t, signature)
    return active, qualified


def rails(o,t,i):
    def value(x): return Fraction(str(x))
    s = (value(o['end_price'])-value(o['start_price']))/(o['end_index']-o['start_index'])
    v = (value(t['extension_end_price'])-value(t['extension_start_price']))/(t['extension_end_index']-t['extension_start_index'])
    return [float(value(o['start_price'])+s*(i-o['start_index'])),float(value(t['start_price'])+v*(i-t['start_index']))]


def replay_window(data,start):
    from src.book_trend_structure_judgement import judge_book_trend_structure
    from src.book_native_wave_process import recognize_wave_process
    rows=[r for r in data if r['timestamp_utc']>=start]
    closes=[iso(epoch(r['timestamp_utc'])+3600) for r in rows]
    snapshots={}
    def prior(i):
        if i not in snapshots:
            snapshots[i]=rulers(rows[:i],closes[i-1])
        return snapshots[i]
    cases=[]
    for clock in CLOCKS:
        i=closes.index(clock)
        active,qualified=prior(i)
        continuous_open=closes[i-1]==rows[i]['timestamp_utc']
        actual=recognize_wave_process(rows[:i+1],'H1',clock)
        at_close={x['scope_id']:x for x in actual['active']}
        events=[]
        stages=Counter()
        for sid,(owner,o,t,sig) in qualified.items():
            result=judge_book_trend_structure(rows[:i+1],'H1',clock,o,t)
            stages[result['stage']]+=1
            ends=[result.get(k,{}).get('break_index') for k in ('outer_break','turning_break')]
            if i not in ends:
                continue
            indexes=[j for j in ends if j is not None]
            first=min(indexes)
            first_pair=prior(first)[1].get(sid) if first>0 else None
            still=at_close.get(sid)
            current_rails=rails(o,t,i)
            previous_rails=rails(o,t,i-1)
            events.append(dict(id=sid, direction=owner['direction'], owner=list(sig[:2]),
                      identity=sig, signature_known=max(o['known_at_utc'],t['known_at_utc']),
                      break_times=[closes[j] if j is not None else None for j in ends],
                      stage=result['stage'], source_at_first=bool(first_pair and first_pair[3]==sig),
                      source_alive=bool(still),terminal_unchanged=bool(still and still.get('terminal')==owner['terminal']),
                      bars_between=max(indexes)-first if len(indexes)==2 else None,
                      consecutive=all(closes[j-1]==rows[j]['timestamp_utc'] for j in range(first+1,i+1)),
                      previous=previous_rails,current=current_rails,
                      close=rows[i]['close'],relation=result.get('current_boundary_relation'),
                      A=result.get('boundary_A_state'),order=result.get('dual_break_order')))
        cases.append(dict(clock=clock,continuous_open=continuous_open,active=len(active),qualified=len(qualified), stages=stages,events=events))
    return dict(start=start,cases=cases)


def main():
    OUT.mkdir(exist_ok=True)
    with HISTORY.open(encoding='utf-8-sig') as f:
        rows=[dict(timestamp_utc=iso(int(r['time'])),timeframe='H1',symbol='XAUUSD',provider='saved_MT5_history',
                   **{k:float(r[k]) for k in ('open','high','low','close')}) for r in csv.DictReader(f,delimiter='\t')]
    with tempfile.TemporaryDirectory(dir=OUT) as folder:
        extract_sources(ARCHIVE,Path(folder))
        sys.path.insert(0,folder)
        windows=[]
        for start in ['2026-08-17T00:00:00Z','2026-08-13T00:00:00Z']:
            win=replay_window(rows,start)
            windows.append(win)
            print(start,len(win['cases']),sum(len(c['events']) for c in win['cases']),flush=True)
    for a,b in zip(windows[0]['cases'],windows[1]['cases']):
        assert a['clock']==b['clock']
        both={r['id']:r for r in b['events']}
        for e in a['events']:
            e['warmup_equal']=all(e[k]==both[e['id']][k] for k in e) if e['id'] in both else False
    with ARCHIVE.open('rb') as source:
        archive_hash=hashlib.file_digest(source,'sha256').hexdigest()
    report=dict(archive_sha256=archive_hash,history_sha256=hashlib.sha256(HISTORY.read_bytes()).hexdigest(),windows=windows)
    (OUT/'paired_prefixes.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')

if __name__=='__main__':
    main()
