"""Draw the owned Book pair and the frozen A reference on the observed H1 bars."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from replay_august_book_prefixes import OUT, iso, HISTORY
from research_cases import load_bars


def main():
    periods=json.loads((OUT/'intervening_geometry.json').read_text('utf8'))
    raw=json.loads((OUT/'paired_prefixes.json').read_text('utf8'))
    verified=json.loads((OUT/'boundary_sequences.json').read_text('utf8'))
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei'],'axes.unicode_minus':False})
    fig,(left,right)=plt.subplots(1,2,figsize=(12.8,4.7),width_ratios=[1,2.1],layout='constrained')
    local=next(c['events'][0] for c in raw['windows'][0]['cases'] if c['clock']=='2026-08-28T10:00:00Z')
    view=[b for b in load_bars(HISTORY) if '2026-08-28T05'<=b.closed_at.isoformat()<'2026-08-28T17']
    for i,b in enumerate(view):
        color='#18735d' if b.close>=b.open else '#bb583c'
        left.vlines(i,b.low,b.high,color=color,lw=1)
        left.vlines(i,b.open,b.close,color=color,lw=4)
    x=next(i for i,b in enumerate(view) if iso(b.closed_at.timestamp())=='2026-08-28T10:00:00Z')
    for j,name,color in [(0,'趋势线','#294e85'),(1,'拐点线','#7c5086')]:
        left.plot([x-1,x],[local['previous'][j],local['current'][j]],'o-',color=color,label=name)
    left.scatter(x,local['close'],color='#222',s=17,zorder=5)
    left.annotate('收盘 4612.61',(x,local['close']),xytext=(8,10),textcoords='offset points',fontsize=9)
    left.set_title('8 月 28 日　单破趋势线')
    left.set_xticks(range(0,len(view),3),[b.closed_at.strftime('%H:%M') for b in view[::3]])
    left.set_ylabel('XAUUSD 价格')
    left.legend()
    r=next(r for r in periods if r['dual_close']=='2026-09-01T12:00:00Z')
    pts=r['rows']
    assert all(v['same'] for v in pts)
    for key,color,label in [(0,'#294e85','趋势线'),(1,'#7c5086','拐点线'),(2,'#444','H1 收盘')]:
        start=0
        for stop in [i for i,v in enumerate(pts) if i and v['gap_at_open']]+[len(pts)]:
            fragment=pts[start:stop]
            right.plot(range(start,stop),[v['close'] if key==2 else v['levels'][key] for v in fragment],
                       color=color,lw=1.3,label=label if start==0 else None)
            start=stop
    seq=next(q for q in verified if q['id']==r['id'])
    right.axhline(seq['price'],ls='--',color='#a46b29',lw=1.2,label='调整低点候选 4450.62')
    for when,label,offset in [('2026-08-25T17:00:00Z','拐点线首次收破',(3,-17)),
                              ('2026-08-31T05:00:00Z','首次收破候选低点',(-75,-18)),
                              ('2026-09-01T12:00:00Z','趋势线首次收破',(-83,14))]:
        i=next(i for i,v in enumerate(pts) if v['close_time']==when)
        right.scatter(i,pts[i]['close'],s=20,color='#222',zorder=5)
        right.annotate(label,(i,pts[i]['close']),xytext=offset,textcoords='offset points',fontsize=8)
    ticks=list(range(0,len(pts)-5,24))+[len(pts)-1]
    right.set_xticks(ticks,[pts[i]['close_time'][5:10]+'\n'+pts[i]['close_time'][11:16] for i in ticks])
    right.set_title('另一组上升波段　两线分隔 110 根 H1 收破')
    right.legend(fontsize=8,loc='upper left',ncol=2)
    for ax in (left,right):
        ax.grid(axis='y',alpha=.15)
        ax.set_xlabel('MT5 图表收盘时间')
    fig.savefig(OUT/'八月Book原线与候选A.png',dpi=145)
    plt.close(fig)

if __name__=='__main__':
    main()
