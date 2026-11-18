"""Check every intervening physical H1 prefix for loss or redrawing of the same owned pair."""
import csv
import json
import sys
import tempfile
from pathlib import Path
from replay_august_book_prefixes import OUT, ARCHIVE, HISTORY, extract_sources, iso, epoch, rails


def main():
    report=json.loads((OUT/'paired_prefixes.json').read_text('utf8'))
    with HISTORY.open(encoding='utf-8-sig') as f:
        data=[dict(timestamp_utc=iso(int(r['time'])),timeframe='H1',symbol='XAUUSD',provider='saved_MT5_history',
                   **{k:float(r[k]) for k in ('open','high','low','close')}) for r in csv.DictReader(f,delimiter='\t')]
    results=[]
    with tempfile.TemporaryDirectory(dir=OUT) as folder:
        extract_sources(ARCHIVE,Path(folder))
        sys.path.insert(0,folder)
        from src.book_native_wave_process import recognize_wave_process
        from src.trend_wave_state_adjudication import fit_native_wave_scope
        for window in report['windows']:
            rows=[r for r in data if r['timestamp_utc']>=window['start']]
            times=[iso(epoch(r['timestamp_utc'])+3600) for r in rows]
            for case in window['cases']:
                for event in case['events']:
                    if event['bars_between'] is None:
                        continue
                    first=times.index(min(event['break_times']))
                    dual=times.index(max(event['break_times']))
                    snapshots=[]
                    for i in range(first-1,dual+3):
                        prefix=rows[:i+1]
                        wave=recognize_wave_process(prefix,'H1',times[i])
                        owner=next((o for o in wave['active'] if o['scope_id']==event['id']),None)
                        same=False
                        geometry=None
                        if owner and owner.get('terminal'):
                            pair=[[iso(t),p] for t,p in (owner['origin'],owner['terminal'])]
                            if pair==event['owner']:
                                fit=fit_native_wave_scope(prefix,'H1',times[i],*pair,owner['known_at_utc'])
                                o,t=fit.get('outer_line'),fit.get('parallel_projection')
                                if o and t:
                                    contacts=[[rows[line[k+'_index']]['timestamp_utc'],line[k+'_price']]
                                             for line,k in ((o,'start'),(o,'end'),(t,'extension_start'),(t,'extension_end'),(t,'start'))]
                                    same=event['identity']==[*pair,o['direction'],o['known_at_utc'],t['known_at_utc'],*contacts]
                                    if same:
                                        geometry=rails(o,t,i)
                        snapshots.append(dict(close_time=times[i],close=rows[i]['close'],same=same,levels=geometry,
                                              gap_at_open=rows[i]['timestamp_utc']!=times[i-1]))
                    results.append(dict(id=event['id'],window_start=window['start'],dual_close=case['clock'],rows=snapshots))
    (OUT/'intervening_geometry.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),'utf8')
    for r in results:
        print(r['dual_close'],r['window_start'],len(r['rows']),sum(x['same'] for x in r['rows']),sum(x['gap_at_open'] for x in r['rows']),r['rows'][-2:])

if __name__=='__main__':
    main()
