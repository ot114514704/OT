"""Replay the supplied Book source on the saved XAUUSD H1 history."""
import argparse
import ast
import csv
import hashlib
import json
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
REVIEW = ROOT/'verification/book_pair_replay_20261118'
HISTORY = ROOT/'testdata/native_history_H1.tsv'
ARCHIVE = Path(r'C:\Users\qkn\Downloads\forex-ai-source-main.zip')
PERIOD = 3600

def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace('+00:00','Z')

def extract_sources(archive, dest):
    prefix = 'forex-ai-source-main/'
    pending = ['__init__', 'book_native_wave_process','trend_wave_state_adjudication','book_trend_structure_judgement']
    visited = set()
    with ZipFile(archive) as z:
        names = set(z.namelist())
        while pending:
            module = pending.pop()
            if module in visited or not module.isidentifier():
                continue
            visited.add(module)
            name = 'src/'+module+'.py'
            if prefix+name not in names:
                continue
            contents = z.read(prefix+name)
            path = dest/name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(contents)
            for node in ast.walk(ast.parse(contents)):
                if isinstance(node,ast.ImportFrom) and node.level == 1:
                    pending.extend([node.module] if node.module else [a.name for a in node.names])
        model = '04_wells4_support/W4-20261020-FORCE-CALIBRATION/model.json'
        path = dest/model
        path.parent.mkdir(parents=True)
        path.write_bytes(z.read(prefix+model))

def replay(data, opening, until):
    from src.book_native_wave_process import recognize_wave_process
    from src.trend_wave_state_adjudication import fit_native_wave_scope
    from src.book_trend_structure_judgement import judge_book_trend_structure
    rows = [r for r in data if opening <= r['timestamp_utc'] < until]
    clocks = [iso(int(datetime.fromisoformat(r['timestamp_utc']).timestamp())+PERIOD) for r in rows]
    scopes = recognize_wave_process(rows,'H1',clocks[-1])
    results = []
    denied = Counter()
    discovery = {}
    for scope in scopes['active']+scopes['retired']:
        if not scope.get('terminal'):
            continue
        def point(p):
            return [iso(p[0]),p[1]]
        fit = fit_native_wave_scope(rows,'H1',clocks[-1],point(scope['origin']),point(scope['terminal']),scope['known_at_utc'])
        if not fit['qualified']:
            denied['outer_scope_unqualified'] += 1
            continue
        outer,turn = fit['outer_line'],fit['parallel_projection']
        geometry = judge_book_trend_structure(rows,'H1',clocks[-1],outer,turn)
        if geometry['stage']=='unknown':
            denied[geometry['reason']] += 1
            continue
        events = [geometry[k].get('break_index') for k in ('outer_break','turning_break')]
        item = dict(id=scope['scope_id'],direction=outer['direction'],scope_known=scope['known_at_utc'],
                    retired_at=scope.get('broken_at_utc'),stage_at_window_end=geometry['stage'],
                    break_times=[clocks[i] if i is not None else None for i in events])
        if None not in events:
            first,second = sorted(events)
            prefix = judge_book_trend_structure(rows[:second+1],'H1',clocks[second],outer,turn)
            future_filtered = judge_book_trend_structure(rows,'H1',clocks[second],outer,turn)
            assert prefix == future_filtered
            relation = prefix.get('current_boundary_relation',{})
            in_scope = not scope.get('broken_at_utc') or scope['broken_at_utc']>clocks[second]
            if first not in discovery:
                before = recognize_wave_process(rows[:first],'H1',clocks[first-1])
                discovery[first] = {s['scope_id']:s for s in before['active']}
            prior = discovery[first].get(scope['scope_id'])
            frozen = False
            if prior and prior.get('terminal'):
                check = fit_native_wave_scope(rows[:first],'H1',clocks[first-1],point(prior['origin']),point(prior['terminal']),prior['known_at_utc'])
                keys = [('outer_line',('start_index','end_index','start_price','end_price','known_at_utc')),
                        ('parallel_projection',('extension_start_index','extension_end_index','start_index',
                                                'extension_start_price','extension_end_price','start_price','known_at_utc'))]
                frozen = check['qualified'] and all(check[name].get(k)==fit[name][k] for name,fields in keys for k in fields)
            def value(x):
                return Fraction(str(x))
            def signed_gaps(i):
                line=value(outer['start_price'])+(value(outer['end_price'])-value(outer['start_price']))*(i-outer['start_index'])/(outer['end_index']-outer['start_index'])
                shifted=value(turn['start_price'])+(value(turn['extension_end_price'])-value(turn['extension_start_price']))*(i-turn['start_index'])/(turn['extension_end_index']-turn['extension_start_index'])
                sign=1 if outer['direction']=='up' else -1
                return [sign*(value(rows[i]['close'])-x) for x in (line,shifted)]
            def consecutive(i,j):
                return all(rows[k]['timestamp_utc']==clocks[k-1] for k in range(i+1,j+1))
            def hold(n):
                for i in range(second,second+n):
                    if i>=len(rows) or not consecutive(second,i):
                        return 'missing_contiguous_bar'
                    if scope.get('broken_at_utc') and scope['broken_at_utc']<=clocks[i]:
                        return 'source_retired'
                    if max(signed_gaps(i))>=0:
                        return 'returned_or_touched'
                return 'held'
            origin = next(i for i,r in enumerate(rows) if r['timestamp_utc']==iso(scope['origin'][0]))
            up = outer['direction']=='up'
            reference = (max(r['high'] for r in rows[origin:first]) if up
                         else min(r['low'] for r in rows[origin:first]))
            reclaim = None
            extension = None
            last_checked = second
            stop = 'window_end'
            for i in range(second+1,len(rows)):
                if not consecutive(i-1,i):
                    stop = 'session_or_data_gap'
                    break
                if scope.get('broken_at_utc') and scope['broken_at_utc']<=clocks[i]:
                    stop = 'source_retired'
                    break
                last_checked=i
                if reclaim is None:
                    if i>second+3:
                        stop='three_bar_window_elapsed'
                        break
                    if signed_gaps(i)[1]>0:
                        reclaim=i
                elif (rows[i]['close']>reference if up else rows[i]['close']<reference):
                    extension=i
                    stop='new_extreme_on_later_close'
                    break
            follow = None
            if reclaim is not None:
                next_open = clocks[reclaim]
                gaps = 0
                reason = 'history_end'
                last = next_open
                for bar in data:
                    if bar['timestamp_utc'] < clocks[reclaim]:
                        continue
                    gaps += bar['timestamp_utc'] != next_open
                    next_open = iso(int(datetime.fromisoformat(bar['timestamp_utc']).timestamp())+PERIOD)
                    last = next_open
                    retired = bar['low']<scope['origin'][1] if up else bar['high']>scope['origin'][1]
                    advanced = bar['close']>reference if up else bar['close']<reference
                    if retired or advanced:
                        reason = ('both_on_one_bar_order_unknown' if retired and advanced else
                                  'source_retired' if retired else 'new_extreme_on_later_close')
                        break
                follow = dict(end=last,reason=reason,observed_time_gaps=gaps)
            item.update(timing=geometry['construction_timing'],bars_between=second-first,
                        follow_after_reclaim_across_sessions=follow,
                        prior_extreme=reference,quick_turning_reclaim=clocks[reclaim] if reclaim is not None else None,
                        new_directional_extreme=clocks[extension] if extension is not None else None,
                        observation_end=clocks[last_checked],observation_end_reason=stop,
                        source_reproduced_before_first=frozen,continuous_between_crosses=consecutive(first,second),
                        holds_two=hold(2),holds_three=hold(3),
                        first_close=clocks[first],second_close=clocks[second],
                        stage_at_second=prefix['stage'],both_outside_at_second=all(relation.get(k) is True for k in ('outer_outside','turning_outside')),
                        relation_at_second=relation,source_alive_at_second=in_scope,
                        A=prefix['boundary_A_state'],source_known_before_first=geometry['construction_timing']=='known_before_first_break')
            if first==second and frozen and in_scope:
                sign=1 if up else -1
                item['chart']=[]
                for k in range(max(0,first-3),min(len(rows),first+5)):
                    if rows[k]['timestamp_utc']<max(outer['known_at_utc'],turn['known_at_utc']) or not consecutive(min(k,first),max(k,first)):
                        continue
                    if scope.get('broken_at_utc') and scope['broken_at_utc']<=clocks[k]:
                        break
                    line,shifted=[float(value(rows[k]['close'])-sign*g) for g in signed_gaps(k)]
                    item['chart'].append(dict(close_time=clocks[k],outer=line,turning=shifted,**{key:rows[k][key] for key in ('open','high','low','close')}))
        results.append(item)
    return dict(start=opening,end_exclusive=until,bars=len(rows),accepted=len(results),omitted=dict(denied),records=results)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',type=Path,default=ARCHIVE)
    args=parser.parse_args()
    REVIEW.mkdir(parents=True,exist_ok=True)
    with HISTORY.open(encoding='utf-8-sig') as f:
        data=[dict(timestamp_utc=iso(int(r['time'])),timeframe='H1',symbol='XAUUSD',provider='saved_MT5_history',
                   **{k:float(r[k]) for k in ('open','high','low','close')}) for r in csv.DictReader(f,delimiter='\t')]
    with tempfile.TemporaryDirectory(dir=REVIEW) as temp:
        extract_sources(args.archive,Path(temp))
        sys.path.insert(0,temp)
        windows=[replay(data,a+'T00:00:00Z',b+'T00:00:00Z') for a,b in (
            ('2026-09-20','2026-10-03'),('2026-10-18','2026-10-31'),('2026-11-01','2026-11-14'))]
    report=dict(archive_sha256=hashlib.file_digest(args.archive.open('rb'),'sha256').hexdigest(),
                history_sha256=hashlib.sha256(HISTORY.read_bytes()).hexdigest(),windows=windows)
    (REVIEW/'paired_replay.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    for win in windows:
        both=[r for r in win['records'] if 'bars_between' in r]
        print(win['start'],win['bars'],win['accepted'],win['omitted'],len(both),Counter((r['timing'],r['source_alive_at_second'],r['both_outside_at_second']) for r in both))

if __name__=='__main__':
    main()
