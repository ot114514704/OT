"""Match the user's physical-prefix Book rulers against saved native MT5 coordinates."""
import csv
import hashlib
import json
import sys
import tempfile
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from replay_august_book_prefixes import ARCHIVE, HISTORY, ROOT, extract_sources, iso, epoch, rulers

OUT = ROOT/'verification/book_native_mapping_20261118'
AUGUST = ROOT/'verification/book_august_prefix_20261118/paired_prefixes.json'
OLDER = ROOT/'verification/book_pair_replay_20261118/paired_replay.json'
SCAN = ROOT/'testdata/book_scan.tsv'


def table(path):
    with path.open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f,delimiter='\t'))


def pair(x):
    return (int(x[0]), Decimal(str(x[1])))


def point(contract, name):
    return pair(contract[name].split('@'))


def make_targets():
    august=json.loads(AUGUST.read_text('utf8'))
    targets=[dict(id=e['id'],event=c['clock'],family='August',sig=e['identity'])
             for c in august['windows'][-1]['cases'] for e in c['events']]
    records=json.loads(OLDER.read_text('utf8'))
    assert august['history_sha256']==records['history_sha256']==hashlib.sha256(HISTORY.read_bytes()).hexdigest()
    rows=[dict(timestamp_utc=iso(int(b['time'])),timeframe='H1',symbol='XAUUSD',provider='saved_MT5_history',
               **{k:float(b[k]) for k in ('open','high','low','close')}) for b in table(HISTORY)]
    with tempfile.TemporaryDirectory(dir=OUT) as temp:
        extract_sources(ARCHIVE,Path(temp))
        sys.path.insert(0,temp)
        for window in records['windows']:
            cache={}
            for event in window['records']:
                if not (event.get('source_alive_at_second') and event.get('source_reproduced_before_first')):
                    continue
                cutoff=iso(epoch(event['first_close'])-3600)
                if cutoff not in cache:
                    before=[r for r in rows if window['start']<=r['timestamp_utc']<cutoff]
                    cache[cutoff]=rulers(before,cutoff)[1]
                sig=cache[cutoff][event['id']][3]
                targets.append(dict(id=event['id'],event=event['second_close'],family='prior_windows',sig=sig))
    return targets


def native_rows():
    frames = sorted((ROOT.parent/'Book302_独立盘整实验_20261114/examples').glob('*.native.tsv'))
    frames += sorted((ROOT/'verification/native_r3/final/NativeBookAudit').glob('*.native.tsv'))
    assert frames
    seen = set()
    audit = []
    for f in frames:
        receipt=table(f.with_name(f.name.removesuffix('.native.tsv')+'.receipt.tsv'))[0]
        assert receipt['symbol']=='XAUUSD' and receipt['period_seconds']=='3600' and receipt['provider']=='TradeMaxGlobal-Live'
        assert int(receipt['coordinate_errors'])==0
        contracts={r['id']:dict(k.split('=',1) for k in r['line_contract'].split(';') if '=' in k)
                   for r in table(f.with_name(f.name+'.line_contracts.tsv'))}
        shapes=table(f)
        assert 0<len(shapes)<=int(receipt['shapes'])
        for obj in shapes:
            family=obj['line_family']
            if family not in ('GUIDED_SHIFT','GUIDED_SOURCE','GUIDED_TURNING'):
                continue
            c=contracts[obj['id']]
            assert family==c['family'] and obj['owner_a']==c['owner_a'] and obj['owner_b']==c['owner_b']
            assert all(Decimal(obj['expected_'+k])==Decimal(obj['actual_'+k]) for k in ('a','pa','b','pb'))
            key=(obj['id'],c['revision'],obj['actual_b'],obj['actual_pb'],c['event_known'])
            if key in seen:
                continue
            seen.add(key)
            audit.append(dict(source=f.name,id=obj['id'],family=family,owner=(int(c['owner_a']),int(c['owner_b'])),
                ab=(point(c,'A'),point(c,'B')),q=point(c,'Q') if family=='GUIDED_SHIFT' else None,
                display=[pair((obj['actual_a'],obj['actual_pa'])),pair((obj['actual_b'],obj['actual_pb']))],
                known=int(c['construction_known']),display_known=int(c['display_known']),cross=int(c['event_known']),
                state=obj['assessment_known'],pixel_mappable=obj['pixels_mappable']=='true'))
    return audit,[f.name for f in frames]


def scan_rows():
    unique={}
    for r in table(SCAN):
        family=r['family']
        record=dict(source='book_scan.tsv',id=r['id'],family=family,owner=(int(r['owner_a']),int(r['owner_b'])),
            ab=(pair((r['anchor_a'],r['price_a'])),pair((r['anchor_b'],r['price_b']))),
            q=pair((r['a'],r['pa'])) if family=='GUIDED_SHIFT' else None,
            display=[pair((r['a'],r['pa'])),pair((r['b'],r['pb']))], known=int(r['known']),
            display_known=int(r['display_known']),cross=int(r['cross']),state=r['state'])
        unique.setdefault(tuple((k,str(v)) for k,v in record.items()),record)
    return list(unique.values())


def main():
    OUT.mkdir(exist_ok=True)
    targets=make_targets()
    native,frames=native_rows()
    scan=scan_rows()
    # The same ID can end at different native bars in different historical views.
    # A proof of identical drawn segment requires both physical endpoints.
    def segment(r):
        return (r['id'],r['family'],r['owner'],r['ab'],r['q'],*r['display'])
    corroborated={segment(r) for r in native} & {segment(r) for r in scan}
    bars=table(HISTORY)
    positions={int(r['time']):i for i,r in enumerate(bars)}
    def projected(anchors, origin, time):
        a,b=anchors
        rise=(b[1]-a[1])/(positions[b[0]]-positions[a[0]])
        return origin[1]+rise*(positions[time]-positions[origin[0]])
    matches=[]
    for t in targets:
        sig=t['sig']
        owner=tuple(epoch(p[0]) for p in sig[:2])
        keys=[pair((epoch(time),price)) for time,price in sig[5:]]
        clock=epoch(t['event'])
        result=dict(id=t['id'],time=t['event'],sample=t['family'],owner_times=list(owner),
                    chapter3_contacts=sig[5:7],chapter4_contacts=sig[7:],chapter4_known=sig[4],direction=sig[2])
        for name,source in [('scan',scan),('native_frames',native)]:
            same=[r for r in source if r['owner']==owner]
            roles=defaultdict(list)
            candidates=[]
            for r in same:
                role=None
                if r['family']=='GUIDED_TURNING' and r['ab']==tuple(keys[:2]):
                    role='chapter3_two_contacts'
                elif r['ab']==tuple(keys[2:4]):
                    if r['family']=='GUIDED_SHIFT' and r['q']==keys[4]: role='chapter4_translated'
                    elif r['family']=='GUIDED_SOURCE': role='chapter4_extension_only'
                if role:
                    roles[role].append(r['id'])
                origin=r['q'] if r['q'] else r['ab'][0]
                actual=projected(r['ab'],origin,clock-3600)
                expected_end=projected(r['ab'],origin,r['display'][1][0])
                assert abs(expected_end-r['display'][1][1])<Decimal('0.000001')
                chapter3=projected(keys[:2],keys[0],clock-3600)
                chapter4=projected(keys[2:4],keys[4],clock-3600)
                candidates.append(dict(id=r['id'],family=r['family'],role=role,
                    source=r['source'],native_contacts=[(iso(k),str(v)) for k,v in r['ab']],
                    translated_contact=[iso(r['q'][0]),str(r['q'][1])] if r['q'] else None,
                    event_close_open_clock=iso(clock-3600),equation_at_event=float(actual),
                    chapter3_at_event=float(chapter3),chapter4_at_event=float(chapter4),
                    native_display_end=iso(r['display'][1][0]),native_end_price=float(r['display'][1][1]),
                    construction_known=iso(r['known']),display_known=iso(r['display_known']),
                    native_event=iso(r['cross']) if r['cross'] else None,
                    drawn_through_event=r['display'][0][0]<=clock-3600<=r['display'][1][0],
                    known_before_event=0<r['known']<=clock-3600,
                    same_native_segment=segment(r) in corroborated))
            result[name]=dict(owner_ids=sorted({r['id'] for r in same}),same_start_ids=len({r['id'] for r in source if r['owner'][0]==owner[0]}),
                              same_end_ids=len({r['id'] for r in source if r['owner'][1]==owner[1]}),
                              roles={k:sorted(set(v)) for k,v in roles.items()}, candidates=candidates)
        matches.append(result)
    report=dict(frames=frames,unique_scan_observations=len(scan),native_object_revisions=len(native),
                crosschecked_segments=len(corroborated),matches=matches)
    (OUT/'native_mapping.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    for name in ('scan','native_frames'):
        print(name,'targets',len(matches),'same_owner',sum(bool(r[name]['owner_ids']) for r in matches),
              Counter(k for r in matches for k in r[name]['roles']))
    print('positive control',len(corroborated))

if __name__=='__main__':
    main()
