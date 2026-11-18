"""Plot the November native finite shift and Book translated line on their original contacts."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from map_book_native_contacts import OUT, HISTORY, table, epoch, iso


def main():
    results=json.loads((OUT/'native_mapping.json').read_text('utf8'))['matches']
    m=next(r for r in results if r['time']=='2026-11-10T13:00:00Z' and r['native_frames']['owner_ids'])
    shifted=next(x for x in m['native_frames']['candidates'] if x['family']=='GUIDED_SHIFT')
    c,e,d=m['chapter4_contacts']
    q=shifted['translated_contact']
    bars=[r for r in table(HISTORY) if '2026-11-09T01'<=iso(int(r['time']))<'2026-11-10T16']
    idx={int(r['time']):i for i,r in enumerate(bars)}
    def ix(t):
        return idx[epoch(t)]
    def label(ax,p,mark,color,offset):
        x,y=ix(p[0]),float(p[1])
        ax.scatter(x,y,color=color,s=26,zorder=5)
        ax.annotate(mark,(x,y),xytext=offset,textcoords='offset points',fontsize=9,color=color)
    slope=(e[1]-c[1])/(ix(e[0])-ix(c[0]))
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei'],'axes.unicode_minus':False})
    fig,ax=plt.subplots(figsize=(10.8,4.5),layout='constrained')
    for i,r in enumerate(bars):
        op,cl=float(r['open']),float(r['close'])
        color='#32715e' if cl>=op else '#b35141'
        ax.vlines(i,float(r['low']),float(r['high']),color=color,lw=.9)
        ax.vlines(i,op,cl,color=color,lw=3)
    ax.plot([ix(c[0]),ix(e[0])],[c[1],e[1]],color='#536e9b',label='外延线（两套方法锚点一致）')
    a,b=ix(q[0]),ix(shifted['native_display_end'])
    ax.plot([a,b],[float(q[1]),shifted['native_end_price']],color='#975d21',ls='--',label='MT5 存档平移轨（事后可知）')
    z=ix(d[0])
    # The archive pair is frozen at the close of the owner's terminal bar.
    last=idx[epoch(m['time'])-3600]
    freeze=idx[epoch(m['chapter4_known'])-3600]
    def dp(x):return d[1]+slope*(x-z)
    ax.plot([z,freeze],[dp(z),dp(freeze)],ls=':',color='#774d93')
    ax.plot([freeze,last],[dp(freeze),dp(last)],color='#774d93',label='压缩包 Book 拐点线（从该组构造可知起实线）')
    assert abs(dp(last)-shifted['chapter4_at_event'])<1e-7
    label(ax,q,'Q 4054.96','#975d21',(5,-13))
    label(ax,d,'D 4084.71','#774d93',(5,-15))
    label(ax,c,'C','#536e9b',(-10,6))
    label(ax,e,'E','#536e9b',(5,1))
    ticks=list(range(0,len(bars),6))
    ax.set_xticks(ticks,[iso(int(bars[k]['time']))[5:16].replace('T','\n') for k in ticks])
    ax.set_xlabel('MT5 图表时间 · 横轴标 K 线开盘')
    ax.set_ylabel('XAUUSD 价格')
    ax.set_title('11 月 9 至 10 日　同一外延线经不同支点平移')
    ax.grid(axis='y',alpha=.14)
    ax.legend(loc='upper right',fontsize=8)
    fig.savefig(OUT/'外延线和两个平移支点.png',dpi=145)
    plt.close(fig)

if __name__=='__main__':
    main()
