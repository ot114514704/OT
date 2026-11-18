"""Read a completed native H1 frame and compare its clock with the independent 8773 feed."""
import csv
import hashlib
import io
import json
import time
from urllib.request import urlopen
from map_book_native_contacts import OUT, ROOT, iso, epoch, point

BRIDGE=ROOT/'runtime/bridge'
SERVICE='http://127.0.0.1:8773/api/live'


def read_frame():
    candidates=sorted((BRIDGE/'NativeBookAudit').glob('*.receipt.tsv'),
                      key=lambda f:f.stat().st_mtime_ns,reverse=True)
    for f in candidates:
        before=f.read_bytes()
        receipt=next(csv.DictReader(io.StringIO(before.decode('utf-8-sig')),delimiter='\t'))
        if (receipt['symbol'],receipt['period_seconds'],receipt['provider'])!=('XAUUSD','3600','TradeMaxGlobal-Live'):
            continue
        prefix=f.name.removesuffix('.receipt.tsv')
        shapes=f.with_name(prefix+'.native.tsv')
        files=[shapes,shapes.with_name(shapes.name+'.line_contracts.tsv'),f.with_name(prefix+'.rates.tsv')]
        raw=[p.read_bytes() for p in files]
        if f.read_bytes()!=before or any(p.read_bytes()!=v for p,v in zip(files,raw)):
            continue
        native,contracts,rates=[list(csv.DictReader(io.StringIO(v.decode('utf-8-sig')),delimiter='\t')) for v in raw]
        cutoff=int(receipt['closed_cutoff'])
        if int(rates[-1]['time'])+3600!=cutoff or int(receipt['coordinate_errors'])!=0:
            continue
        index={r['id']:dict(k.split('=',1) for k in r['line_contract'].split(';') if '=' in k) for r in contracts}
        shifts=[]
        for r in native:
            if r['line_family']!='GUIDED_SHIFT':
                continue
            c=index[r['id']]
            a,b,q=[point(c,k) for k in ('A','B','Q')]
            assert c['provider']==receipt['provider'] and c['symbol']=='XAUUSD' and c['seconds']=='3600'
            assert (c['family'],c['owner_a'],c['owner_b'],c['construction_known'])==(r['line_family'],r['owner_a'],r['owner_b'],r['line_construction_known'])
            assert int(c['construction_known'])<=cutoff and int(c['display_known'])<=cutoff
            assert 0<a[0]<b[0]<cutoff and 0<q[0]<cutoff
            assert q==point({'Q':r['actual_a']+'@'+r['actual_pa']},'Q')
            position='before' if q[0]<a[0] else 'after' if q[0]>b[0] else 'endpoint' if q[0] in (a[0],b[0]) else 'between'
            shifts.append(dict(id=r['id'],owner=[c['owner_a'],c['owner_b']],a=iso(a[0]),b=iso(b[0]),q=iso(q[0]),
                               support_price=float(q[1]),position=position,book_adjustment_verified=False))
        return dict(chart=receipt['chart'],cutoff=iso(cutoff),input_hash=receipt['input_hash'],
                    snapshot_sha256=dict(zip([f.name]+[p.name for p in files],
                                              [hashlib.sha256(v).hexdigest() for v in [before,*raw]])),
                    shifts=shifts)
    raise RuntimeError('No stable completed native H1 audit available')


def main():
    snap=read_frame()
    with urlopen(SERVICE,timeout=15) as response:
        live=json.load(response)
    h1=live['current_consolidation']['H1']
    delta=epoch(live['latest_closed_end']['H1'])-epoch(snap['cutoff'])
    comparable=(live['market_source']['status']=='verified' and live['market_source']['server']=='TradeMaxGlobal-Live'
                and live['market_source']['symbol']=='XAUUSD' and h1['availability']=='live'
                and epoch(h1['known_at'])==epoch(live['latest_closed_end']['H1']) and delta==0)
    snap.update(captured_wall=time.time(),live_h1=live['latest_closed_end']['H1'],live_availability=h1['availability'],
                clock_difference_seconds=delta,same_closed_clock=comparable)
    (OUT/'native_snapshot.json').write_text(json.dumps(snap,ensure_ascii=False,indent=2),'utf8')
    print(snap['cutoff'],snap['live_h1'],delta,comparable,len(snap['shifts']))

if __name__=='__main__':
    main()
