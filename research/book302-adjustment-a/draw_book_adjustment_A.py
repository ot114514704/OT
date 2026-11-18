"""Draw native H1 candles, wave references and the two independent Book break clocks."""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'verification/book_adjustment_A_20261118'
cases=json.loads((OUT/'frozen_adjustments.json').read_text('utf8'))['cases']
with (ROOT/'testdata/native_history_H1.tsv').open(encoding='utf-8-sig') as handle:
    bars={int(r['time'])+3600:r for r in csv.DictReader(handle,delimiter='\t')}
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei'],'axes.unicode_minus':False})
fig,axes=plt.subplots(1,2,figsize=(11,4.7),layout='constrained')
for ax,time,title in zip(axes,('2026-10-27T16:00:00Z','2026-11-10T13:00:00Z'),
                        ('10 月 27 日　两个 ABC 参考高点','11 月 10 日　事先冻结的调整低点候选')):
    rec=next(r for r in cases if r['dual_close']==time)
    end=int(datetime.fromisoformat(time).timestamp())
    timestamps=[t for t in sorted(bars) if end-4*3600<=t<=end+2*3600]
    for i,t in enumerate(timestamps):
        r=bars[t]
        o,h,l,c=(float(r[k]) for k in ('open','high','low','close'))
        color='#1b695b' if c>=o else '#9b3938'
        ax.vlines(i,l,h,color=color,zorder=2)
        ax.add_patch(Rectangle((i-.14,min(o,c)),.28,max(.02,abs(c-o)),facecolor=color,zorder=2))
    if rec['bars_between']==0:
        for key,color in [('abc_A','#84519b'),('abc_C','#286887')]:
            val=rec['references'][key]['price']
            ax.axhline(val,color=color,ls='--',label=f'ABC {key[-1]}　{val:.2f}')
    else:
        val=rec['adjustment_review']['price']
        ax.axhline(val,color='#286887',ls='--',label=f'调整低点候选　{val:.2f}')
    for stamp,label,marker,color in [(rec['first_close'],'首次收破一条线','o','#283448'),
                                     (time,'两条线均已收破','v','#de7e18')]:
        if stamp==time and marker=='o':continue
        t=int(datetime.fromisoformat(stamp).timestamp());j=timestamps.index(t)
        ax.scatter(j,float(bars[t]['close']),marker=marker,s=60,color=color,zorder=5,label=label)
    ax.set_xticks(range(len(timestamps)),[datetime.fromtimestamp(t,timezone.utc).strftime('%H:%M') for t in timestamps],fontsize=8)
    ax.set_title(title)
    ax.set_xlabel('H1 收盘时刻')
    ax.grid(axis='y',alpha=.18)
    ax.legend(loc='best',fontsize=8)
axes[0].set_ylabel('XAUUSD 价格')
fig.suptitle('分界点 A 复核　参考极值、影线穿越与收盘确认',fontsize=14)
fig.savefig(OUT/'分界点A复核.png',dpi=145)
plt.close(fig)
