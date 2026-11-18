"""Audit pre-break chapter-5 A candidates against the user's Book and Wave sources."""
import hashlib
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from replay_book_pair_evidence import ARCHIVE, HISTORY, REVIEW, extract_sources, iso
from research_cases import load_bars
from wave2116_swings import confirmed_swings

OUT = REVIEW.parent/'book_adjustment_A_20261118'

def epoch(text):
    return int(datetime.fromisoformat(text).timestamp())

def wave_summary(wave):
    keys=('status','reason','direction','form','a_utc','a_price','b_utc','b_price','c_utc','c_price',
          'known_at_utc','wave_degree','subdivision_status')
    return {k:wave[k] for k in keys if k in wave}

def response(child, rows, parent_direction):
    """Use a later close through the counterleg origin to document resumption."""
    start, extreme = child['origin'], child['terminal']
    up = parent_direction=='up'
    resumed = next((r for r in rows if epoch(r['timestamp_utc'])>extreme[0] and
                    (r['close']>start[1] if up else r['close']<start[1])),None)
    return dict(id=child['scope_id'],relation=child['parent_relation'],start=iso(start[0]),start_price=start[1],
                extreme=iso(extreme[0]),price=extreme[1],membership_known=child['membership_known_at_utc'],
                resumed_close_time=iso(epoch(resumed['timestamp_utc'])+3600) if resumed else None,
                retirement_state=child.get('historical_range_state'))

def evaluate(window, snapshot, rows, native):
    from src.book_native_wave_process import recognize_wave_process
    from src.trend_trade_method_patterns import detect_wave_adjustment
    from src.trend_wave_state_adjudication import fit_native_wave_scope
    from src.book_trend_structure_judgement import judge_book_trend_structure

    cutoff=iso(epoch(snapshot['first_close'])-3600)
    through=[r for r in rows if window['start']<=r['timestamp_utc']<cutoff]
    frozen=recognize_wave_process(through,'H1',cutoff)
    scopes=frozen['active']+frozen['retired']
    owner=next(r for r in frozen['active'] if r['scope_id']==snapshot['id'])
    if 'owner' in snapshot:
        assert [iso(owner['origin'][0]),iso(owner['terminal'][0])]==snapshot['owner']
    bound_start=iso(owner['origin'][0])
    up=owner['direction']=='up'
    sides=(-1,1) if up else (1,-1)
    local=[b for b in native if window['start']<=iso(b.time.timestamp()) and iso(b.closed_at.timestamp())<=cutoff]
    swings=confirmed_swings(local)
    wave=detect_wave_adjustment(through,'H1',cutoff,owner['direction'])
    if wave.get('status')=='observed_candidate':
        assert wave['known_at_utc']<=cutoff and wave['a_utc']<wave['b_utc']<wave['c_utc']<cutoff
        wave=dict(wave,all_points_in_owner=wave['a_utc']>=bound_start,
                  wave_swings_known={key:iso(swings[(epoch(wave[key+'_utc']),side)])
                  if (epoch(wave[key+'_utc']),side) in swings else None
                  for key,side in [('a',sides[0]),('b',sides[1]),('c',sides[0])]})
    child_rows=[response(c,through,owner['direction']) for c in scopes if c.get('terminal')
                and c.get('parent_scope_id')==owner['scope_id'] and c['direction']!=owner['direction']
                and c['membership_known_at_utc']<=cutoff]
    child_rows.sort(key=lambda r:(r['extreme'],r['start']))
    for c in child_rows:
        t=swings.get((epoch(c['extreme']),sides[0]))
        c['wave_swing_known']=iso(t) if t else None
        c['source_before_break']=c['membership_known']<=cutoff and c['extreme']<cutoff
    through_break=[r for r in rows if window['start']<=r['timestamp_utc']<snapshot['second_close']]
    fit=fit_native_wave_scope(through,'H1',cutoff,[bound_start,owner['origin'][1]],
                              [iso(owner['terminal'][0]),owner['terminal'][1]],owner['known_at_utc'])
    judge=judge_book_trend_structure(through_break,'H1',snapshot['second_close'],fit['outer_line'],
                                     fit['parallel_projection'],adjustment=wave,wave_record=owner)
    assert judge['stage']==snapshot['stage_at_second']
    assert all(iso(epoch(judge[key]['break_utc'])+3600)==clock for key,clock in
               zip(('outer_break','turning_break'),snapshot['break_times']))
    change=judge['boundary_A_evidence']
    close=through_break[-1]['close']
    references={}
    def inspect_reference(label, when, price):
        if when is None or price is None:
            return
        beyond=lambda value: value<price if up else value>price
        fact=next((r for r in through if r['timestamp_utc']>when and beyond(r['close'])),None)
        references[label]=dict(time=when,price=price,dual_close_beyond=beyond(close),
                               before_first_close_beyond=iso(epoch(fact['timestamp_utc'])+3600) if fact else None)
    if wave.get('status')=='observed_candidate':
        inspect_reference('abc_A',wave['a_utc'],wave['a_price'])
        inspect_reference('abc_C',wave['c_utc'],wave['c_price'])
    inspect_reference('book_proxy',change.get('boundary_a_utc'),change.get('boundary_a_price'))
    for child in child_rows:
        inspect_reference(child['id'],child['extreme'],child['price'])
    return dict(id=owner['scope_id'],direction=owner['direction'],source=bound_start,
                terminal=iso(owner['terminal'][0]),terminal_price=owner['terminal'][1],
                freeze=cutoff,first_close=snapshot['first_close'],dual_close=snapshot['second_close'],
                bars_between=snapshot['bars_between'],price_at_dual_close=close,references=references,
                scope_children=child_rows,
                abc={**wave_summary(wave),**{k:wave[k] for k in ('all_points_in_owner','wave_swings_known') if k in wave}},
                book_verdict=judge['stage'],A=judge['boundary_A_state'],archived_boundary=change)

def candidate_follow(case, rows, retired):
    """Freeze only a same-owner completed return. Later closes never choose its level."""
    if not all(x['children_equal'] for x in case['warmup_checks']):
        return dict(status='ownership_changes_with_history')
    children=case['scope_children']
    if not children:
        return dict(status='no_direct_counterleg_identified')
    # Never bypass an unresolved newest return in favour of an older point.
    child=children[-1]
    if sum(c['extreme']==child['extreme'] for c in children)>1:
        return dict(status='last_return_ambiguous')
    if (child['relation']!='internal_return_stage' or not child['source_before_break'] or
        not child['resumed_close_time'] or child['resumed_close_time']>case['freeze'] or
        child['retirement_state']!='completed_excursion_before_origin_breach'):
        return dict(status='completion_not_reproduced')
    ref=case['references'][child['id']]
    if ref['before_first_close_beyond']:
        return dict(status='level_already_crossed_before_first_break')
    price=child['price']
    first=case['first_close']
    second=case['dual_close']
    out=dict(status='frozen_counterleg_extreme_candidate',price=price,extreme=child['extreme'],
             known=max(child['membership_known'],child['resumed_close_time']),owner=case['id'],
             wave_swing_known=child['wave_swing_known'],author_A_verified=False,
             before_dual=[],after_dual=[])
    for row in rows:
        close=iso(epoch(row['timestamp_utc'])+3600)
        if close<first:
            continue
        if retired and close>=retired:
            break
        target=out['before_dual'] if close<second else out['after_dual']
        if close>=second and (len(target)==3 or (target and row['timestamp_utc']!=target[-1]['close_time'])):
            break
        beyond=row['close']<price if case['direction']=='up' else row['close']>price
        wick=row['low']<price if case['direction']=='up' else row['high']>price
        target.append(dict(close_time=close,close=row['close'],wick_beyond=wick,close_beyond=beyond))
    return out

def reproduce_candidate_clock(window, case, rows):
    from src.book_native_wave_process import recognize_wave_process
    candidate=case['adjustment_review']
    child=case['scope_children'][-1]
    nominal=candidate['known']
    timeline=[]
    prefix=[r for r in rows if window['start']<=r['timestamp_utc']<case['freeze']]
    for i,row in enumerate(prefix):
        clock=iso(epoch(row['timestamp_utc'])+3600)
        if clock<nominal:
            continue
        source=recognize_wave_process(prefix[:i+1],'H1',clock)
        owners=[r for r in source['active'] if r['scope_id']==case['id']]
        owned=bool(owners and owners[0].get('terminal')==[epoch(case['terminal']),case['terminal_price']])
        relevant=[r for r in source['active']+source['retired'] if r.get('parent_scope_id')==case['id']
                  and r.get('terminal') and r['direction']!=case['direction']]
        newest=max((r['terminal'][0] for r in relevant),default=None)
        matches=[r for r in relevant if r['terminal'][0]==newest]
        exact=owned and len(matches)==1 and matches[0]['scope_id']==child['id'] and matches[0]['terminal']==[epoch(child['extreme']),child['price']]
        if exact:
            obs=response(matches[0],prefix[:i+1],case['direction'])
            exact=(obs['relation']==child['relation'] and obs['resumed_close_time']==child['resumed_close_time']
                   and obs['retirement_state']==child['retirement_state'] and obs['membership_known']<=clock)
        timeline.append(dict(close_time=clock,reproduced=exact))
    assert timeline and timeline[-1]['reproduced']
    last_failure=max((i for i,p in enumerate(timeline) if not p['reproduced']),default=-1)
    candidate['source_timestamp']=nominal
    candidate['known']=timeline[last_failure+1]['close_time']
    candidate['physical_prefix_checks']=timeline

def main():
    saved=json.loads((REVIEW/'paired_replay.json').read_text('utf8'))
    assert hashlib.sha256(HISTORY.read_bytes()).hexdigest()==saved['history_sha256']
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()==saved['archive_sha256']
    native=load_bars(HISTORY)
    rows=[dict(timestamp_utc=iso(b.time.timestamp()),timeframe='H1',symbol='XAUUSD',provider='saved_MT5_history',
               **{k:getattr(b,k) for k in ('open','high','low','close')}) for b in native]
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUT) as folder:
        extract_sources(ARCHIVE,Path(folder))
        sys.path.insert(0,folder)
        cases=[]
        for window in saved['windows']:
            start=next(i for i,row in enumerate(rows) if row['timestamp_utc']>=window['start'])
            for record in window['records']:
                if not (record.get('source_alive_at_second') and record.get('source_reproduced_before_first')):
                    continue
                case=evaluate(window,record,rows,native)
                variations=[]
                for extra in (48,96):
                    extended=dict(window,start=rows[start-extra]['timestamp_utc'])
                    alt=evaluate(extended,record,rows,native)
                    variations.append(dict(extra_bars=extra,abc_equal=alt['abc']==case['abc'],
                                           children_equal=alt['scope_children']==case['scope_children'],
                                           reference_levels_equal=alt['references']==case['references'],
                                           verdict_equal=(alt['book_verdict'],alt['A'])==(case['book_verdict'],case['A'])))
                    if not variations[-1]['children_equal']:
                        variations[-1]['alternative_children']=alt['scope_children']
                case['warmup_checks']=variations
                case['adjustment_review']=candidate_follow(case,rows,record.get('retired_at'))
                if case['adjustment_review']['status']=='frozen_counterleg_extreme_candidate':
                    reproduce_candidate_clock(window,case,rows)
                cases.append(case)
    for c in cases:
        print(c['dual_close'], c['source'], c['abc'].get('a_price'),c['abc'].get('c_price'),
              [(r['price'],r['resumed_close_time'],r['wave_swing_known']) for r in c['scope_children']],
              c['A'])
    report=dict(archive_sha256=saved['archive_sha256'],history_sha256=saved['history_sha256'],cases=cases)
    (OUT/'frozen_adjustments.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')

if __name__=='__main__':
    main()
