"""Run the archived Book construction on the latest closed H1 without moving the MT5 viewport."""
import json
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen
from map_book_native_contacts import OUT
from replay_august_book_prefixes import ARCHIVE, epoch, extract_sources, iso, rulers, rails


def fetch(endpoint):
    with urlopen('http://127.0.0.1:8773/api/'+endpoint,timeout=30) as response:
        return json.load(response)


def verified(state):
    h=state['current_consolidation']['H1']
    quote=state['market_source']
    return (state['status']=='connected' and state['model_input_origin']=='native' and
            quote['status']=='verified' and quote['server']=='TradeMaxGlobal-Live' and quote['symbol']=='XAUUSD'
            and h['availability']=='live' and h['bar_sync']['status']=='aligned' and not h['analysis_pending']
            and h['known_at']==state['latest_closed_end']['H1']==state['forming']['H1']['time'])


def check(rows, clock):
    from src.book_trend_structure_judgement import judge_book_trend_structure
    before=rows[:-1]
    cutoff=iso(epoch(before[-1]['timestamp_utc'])+3600)
    active,qualified=rulers(before,cutoff)
    current,current_qualified=rulers(rows,clock)
    current={o['scope_id']:o for o in current}
    result=[]
    for sid,(owner,o,t,sig) in qualified.items():
        assert max(o['known_at_utc'],t['known_at_utc'])<=cutoff
        facts=judge_book_trend_structure(rows,'H1',clock,o,t)
        breaks={k:facts.get(k,{}).get('break_utc') for k in ('outer_break','turning_break')}
        fresh=[k for k,v in breaks.items() if v==rows[-1]['timestamp_utc']]
        alive=current.get(sid)
        result.append(dict(id=sid,direction=owner['direction'],identity=sig,geometry=rails(o,t,len(rows)-1),
                           source_alive=bool(alive),same_terminal=bool(alive and alive.get('terminal')==owner['terminal']),
                           next_terminal=alive.get('terminal') if alive else None,
                           stage=facts['stage'],break_bar_open=breaks,new_on_close=fresh,
                           boundary_A=facts['boundary_A_state'],source_degree_verified=False))
    latest=[dict(id=sid,direction=owner['direction'],identity=sig,geometry=rails(o,t,len(rows)-1))
            for sid,(owner,o,t,sig) in current_qualified.items()]
    return dict(bars=len(rows),active_before=len(active),qualified_before=len(qualified),pairs=result,current_pairs=latest)


def main():
    state=fetch('state')
    if not verified(state):
        raise RuntimeError('Native H1 snapshot pending or stale; no current Book result emitted')
    h=state['charts']['H1']
    clock=iso(epoch(state['latest_closed_end']['H1']))
    assert h['closed_end']==h['bars'][-1]['closed_at']==state['latest_closed_end']['H1']
    rows=[dict(timestamp_utc=iso(epoch(b['time'])),timeframe='H1',symbol='XAUUSD',provider=state['market_source']['server'],
               **{k:b[k] for k in ('open','high','low','close')}) for b in h['bars']]
    assert all(epoch(a['timestamp_utc'])+3600<=epoch(b['timestamp_utc']) for a,b in zip(rows,rows[1:]))
    assert iso(epoch(rows[-1]['timestamp_utc'])+3600)==clock
    with tempfile.TemporaryDirectory(dir=OUT) as folder:
        extract_sources(ARCHIVE,Path(folder))
        sys.path.insert(0,folder)
        windows=[check(rows[-n:],clock) for n in (256,512,len(rows))]
    recheck=fetch('live')
    aligned=(verified(recheck) and recheck['latest_closed_end']['H1']==state['latest_closed_end']['H1'] and
             recheck['model_revision']==state['model_revision'])
    base={p['id']:p for p in windows[0]['pairs']}
    for window in windows[1:]:
        other={p['id']:p for p in window['pairs']}
        base={k:v for k,v in base.items() if other.get(k)==v}
    report=dict(captured_server_time=state['server_now'],market_source=state['market_source'],chart_clock=clock,
                confirmed_close=rows[-1]['close'],local_consolidation=state['current_consolidation']['H1']['label'],
                model_revision=state['model_revision'],current_at_recheck=aligned,windows=windows,
                common_preclose_ids=sorted(base),source_rows=rows)
    (OUT/'current_closed_book.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    print(clock,aligned,[(w['bars'],w['active_before'],w['qualified_before'],sum(bool(r['new_on_close']) for r in w['pairs'])) for w in windows],
          'common',len(base),flush=True)

if __name__=='__main__':
    main()
