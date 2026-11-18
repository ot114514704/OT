"""Read the live status and replay freshness faults in memory on the same native model."""
import json
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path('D:/盘整研究资料/项目/盘整研究')
sys.path.insert(0, str(ROOT))
from ict_trader.current_consolidation import live_reports


def fetch(endpoint):
    with urlopen('http://127.0.0.1:8773/api/'+endpoint, timeout=40) as response:
        return json.load(response)


def main():
    state = fetch('state')
    now = state['server_now']
    report = state['current_consolidation']
    for period in ('H1','M15'):
        assert state['charts'][period]['closed_end'] == report[period]['known_at'] == state['latest_closed_end'][period] == state['forming'][period]['time']
        assert state['charts'][period]['bars'][-1]['closed_at'] == report[period]['known_at']
        assert report[period]['availability'] == 'live' and report[period]['bar_sync']['status'] == 'aligned'
    cases = {'disconnected':dict(status='disconnected'), 'stale':dict(polled_at=now-17),
             'quote_idle':dict(last_tick_change_at=now-32)}
    faults = {}
    for expected, change in cases.items():
        rows = live_reports({**state,**change}, now)
        assert all(r['availability']==expected and not r['actionable_current'] and r['forming_observation'] is None
                   and not r['candidate_observations'] for r in rows.values())
        assert all(rows[k]['known_at']==report[k]['known_at'] for k in report)
        faults[expected] = {k:r['availability'] for k,r in rows.items()}
    samples = []
    for i in range(6):
        if i:
            time.sleep(2)
        s = fetch('live')
        samples.append(dict(wall=s['server_now'], poll=s['polled_at'], raw_quote=s['quote']['raw_epoch'],
                            verdicts={p:r['label'] for p,r in s['current_consolidation'].items()},
                            closed=s['latest_closed_end'],revision=s['model_revision']))
    assert len({x['raw_quote'] for x in samples})>1
    assert len({x['revision'] for x in samples})==1 and all(x['closed']==state['latest_closed_end'] for x in samples)
    result = dict(source=state['market_source'], chart_times=state['latest_closed_end'],
                  label_basis='MT5 raw chart clock; historical timezone is unverified',
                  verdicts={p:r['label'] for p,r in report.items()}, faults_in_memory=faults,samples=samples)
    (Path(__file__).parent/'live_status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')

if __name__=='__main__':
    main()
