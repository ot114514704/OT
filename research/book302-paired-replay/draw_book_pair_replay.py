"""Draw the two observed reclaim sequences from their frozen native ruler values."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

folder=Path(__file__).resolve().parent/'verification/book_pair_replay_20261118'
windows=json.loads((folder/'paired_replay.json').read_text('utf8'))['windows']
events=[r for window in windows for r in window['records'] if r.get('chart')]
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei'],'axes.unicode_minus':False})
fig,axes=plt.subplots(1,2,figsize=(10.8,4.3),sharey=False,layout='constrained')
for ax,date in zip(axes,('2026-10-02','2026-11-10')):
    record=next(r for r in events if r['second_close'].startswith(date))
    bars=record['chart']
    for j,bar in enumerate(bars):
        color='#237054' if bar['close']>=bar['open'] else '#b24238'
        ax.vlines(j,bar['low'],bar['high'],color=color)
        ax.add_patch(Rectangle((j-.14,min(bar['open'],bar['close'])),.28,max(.03,abs(bar['open']-bar['close'])),facecolor=color,edgecolor=color,zorder=3))
    ax.plot([b['outer'] for b in bars],color='#243e89',label='趋势线',lw=1.8)
    ax.plot([b['turning'] for b in bars],color='#b87710',label='拐点线',lw=1.8,linestyle='--')
    for key,marker,color,label in [('second_close','v','#752c3c','同根收破双线'),('quick_turning_reclaim','o','#285c69','收回拐点线')]:
        j=next(i for i,b in enumerate(bars) if b['close_time']==record[key])
        ax.scatter(j,bars[j]['close'],s=52,marker=marker,color=color,zorder=5,label=label)
    ax.set_title(date+'　H1 收盘')
    ax.set_xticks(range(len(bars)),[b['close_time'][11:16] for b in bars],fontsize=8)
    ax.grid(axis='y',alpha=.2)
    ax.set_xlim(-.5,len(bars)-.5)
axes[0].set_ylabel('XAUUSD 价格')
fig.legend(*axes[0].get_legend_handles_labels(),loc='outside lower center',ncol=4,frameon=False)
fig.suptitle('同根双破后，两次收回拐点线的时间不同',fontsize=15)
fig.savefig(folder/'双线收破与收回复盘.png',dpi=155)
plt.close(fig)
