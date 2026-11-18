"""Fit the supplied Book algorithm to the exact native owner at its declared construction clock."""
import json
import sys
import tempfile
from collections import Counter
from fractions import Fraction
from pathlib import Path
from map_book_native_contacts import OUT, HISTORY, ARCHIVE, table, scan_rows, extract_sources, iso, epoch, pair


def replay_owner(r, all_rows, positions, warmup):
    from src.trend_wave_state_adjudication import fit_native_wave_scope
    from src.book_trend_structure_judgement import judge_book_trend_structure
    x,y=r['owner']
    ia,ib=positions[x],positions[y]
    first=max(0,ia-warmup)
    # The detector supplied the construction time, independent of its eventual cross time.
    known=r['known']
    prefix=[b for b in all_rows[first:] if epoch(b['timestamp_utc'])+3600<=known]
    owner=all_rows[ia:ib+1]
    up=all(b['low']>=owner[0]['low'] and b['high']<=owner[-1]['high'] for b in owner)
    down=all(b['high']<=owner[0]['high'] and b['low']>=owner[-1]['low'] for b in owner)
    if up==down:
        return dict(status='owner_envelope_ambiguous')
    a=[iso(x),owner[0]['low' if up else 'high']]
    b=[iso(y),owner[-1]['high' if up else 'low']]
    fit=fit_native_wave_scope(prefix,'H1',iso(known),a,b,iso(known))
    if not fit['qualified']:
        return dict(status='no_chapter3',reason=fit.get('reason'))
    o,t=fit['outer_line'],fit['parallel_projection']
    def pt(line,k):
        return pair((epoch(prefix[line[k+'_index']]['timestamp_utc']),line[k+'_price']))
    ab=(pt(o,'start'),pt(o,'end'))
    exact3=r['family']=='GUIDED_TURNING' and r['ab']==ab
    result=dict(status='chapter3_only', chapter3_match=exact3)
    if exact3:
        (t0,p0),(t1,p1)=ab
        slope=Fraction(p1-p0)/(positions[t1]-positions[t0])
        first_event=None
        previous=None
        for idx in range(ib,positions[r['cross']-3600]+1):
            bar=all_rows[idx]
            opening=epoch(bar['timestamp_utc'])
            level=Fraction(p0)+slope*(idx-positions[t0])
            beyond=(Fraction(str(bar['close']))-level)*(-1 if up else 1)>0
            if previous and opening!=previous[0]+3600:
                previous=None
            if previous and not previous[1] and beyond and opening>=known:
                first_event=iso(opening+3600)
                break
            previous=(opening,beyond)
        result['first_close_cross_from_known']=first_event
        result['native_clock_reproduced']=first_event==iso(r['cross'])
    if not t:
        result['missing_chapter4_reason']=fit['turning_boundary'].get('reason')
        return result
    ce=(pt(t,'extension_start'),pt(t,'extension_end'))
    d=pt(t,'start')
    shared_ce=r['family']=='GUIDED_SHIFT' and r['ab']==ce
    exact4=shared_ce and r['q']==d
    after=[b for b in all_rows[first:] if epoch(b['timestamp_utc'])+3600<=r['cross']]
    judgement=judge_book_trend_structure(after,'H1',iso(r['cross']),o,t)
    breaks={k:judgement.get(k,{}).get('break_utc') for k in ('outer_break','turning_break')}
    new_same=all(v==iso(r['cross']-3600) for v in breaks.values())
    return dict(**{**result,'status':'pair'},same_extension=shared_ce,chapter4_match=exact4,
                book_supports_this_line=exact3 or exact4,matched_level_clock=
                (breaks['outer_break'] if exact3 else breaks['turning_break'] if exact4 else None),
                native_construction=iso(r['known']),book_break_bars=breaks,
                book_stage=judgement['stage'],book_A=judgement['boundary_A_state'],dual_first_on_native_bar=new_same,
                chapter4_support=[iso(d[0]),float(d[1])],
                mt5_support=[iso(r['q'][0]),float(r['q'][1])] if r['q'] else None)


def main():
    rows=[dict(timestamp_utc=iso(int(b['time'])),timeframe='H1',symbol='XAUUSD',provider='saved_MT5_history',
               **{k:float(b[k]) for k in ('open','high','low','close')}) for b in table(HISTORY)]
    positions={epoch(b['timestamp_utc']):i for i,b in enumerate(rows)}
    causal={}
    for r in scan_rows():
        if 0<r['known']<=r['cross']-3600 and 'retrospective' not in r['state']:
            key=r['id']
            if key in causal:
                assert all(causal[key][k]==r[k] for k in ('owner','ab','q','known','cross'))
            causal[key]=r
    report=[]
    with tempfile.TemporaryDirectory(dir=OUT) as folder:
        extract_sources(ARCHIVE,Path(folder))
        sys.path.insert(0,folder)
        for r in causal.values():
            result=replay_owner(r,rows,positions,48)
            assert result==replay_owner(r,rows,positions,96),r['id']
            support=None
            if r['q']:
                q=r['q'][0]
                a,b=(contact[0] for contact in r['ab'])
                support='before' if q<a else 'after' if q>b else 'endpoint' if q in (a,b) else 'between'
            report.append(dict(id=r['id'],family=r['family'],clock=iso(r['cross']),owner=[iso(v) for v in r['owner']],
                               native_support_position=support,**result))
    (OUT/'native_owner_replay.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    for family in ('GUIDED_SHIFT','GUIDED_TURNING'):
        records=[r for r in report if r['family']==family]
        print(family,Counter(r['status'] for r in records),{k:sum(bool(r.get(k)) for r in records) for k in
                ('chapter3_match','same_extension','chapter4_match','dual_first_on_native_bar')})
    print('chapter 3 matching crossing clocks',sum(bool(r.get('native_clock_reproduced')) for r in report))

if __name__=='__main__':
    main()
