"""Recheck a screenshot against the frozen native September H1 feed and six-point export."""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from research_cases import load_bars
from ict_trader.boundary_shapes import observe
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

base=Path(__file__).resolve().parent
dst=base/"verification/september_channel_review"
dst.mkdir(exist_ok=True)
bars=load_bars(base/"testdata/native_history_H1.tsv")
idx={int(b.time.timestamp()):i for i,b in enumerate(bars)}
def stamp(t):
    return datetime.fromtimestamp(int(t),timezone.utc).strftime("%m-%d %H:%M")
segment=[b for b in bars if "2026-08-30" <= b.time.isoformat() < "2026-09-29"]
channels=observe(segment,segment[-1].closed_at)["ranges"]
left,=[r for r in channels if r["observed_from"].startswith("2026-09-24T13:") and r["geometry"]["subtype"]=="channel"]
g=left["geometry"]
full=base/"verification/native_initial/CompanionBookThreePushPA_102923304041429.tsv"
lines=full.read_text("utf-16").splitlines()
records=list(csv.DictReader(lines[next(i for i,l in enumerate(lines) if l.startswith("known\tstart\t")):],delimiter="\t"))
patterns=[]
for start,end in [(1790614800,1790766000),(1790712000,1790780400)]:
    r,=[r for r in records if r["start"]==str(start) and r["end"]==str(end)]
    points=[(idx[int(t)],float(p)) for t,p in [v.split("@") for v in r["original_anchors"].split(";")]]
    assert all(abs(y-(bars[i].high if j%2 else bars[i].low))<1e-8 for j,(i,y) in enumerate(points))
    a,b=points[0][0],points[-1][0]
    def rail(n,m):
        i,y=points[n];j,z=points[m];s=(z-y)/(j-i)
        return [y+s*(a-i),y+s*(b-i)]
    upper,lower=rail(1,5),rail(0,4)
    widths=[u-l for u,l in zip(upper,lower)]
    amplitudes=[round(points[i+1][1]-points[i][1],2) for i in (0,2,4)]
    direction_move=bars[a-1].close-bars[a-30].close
    bar_range=sum(b.high-b.low for b in bars[a-30:a])/30.
    slopes=[(p[1]-p[0])/(b-a) for p in (upper,lower)]
    width_change=(widths[1]/widths[0]-1)*100.
    tolerance=max(bar_range*.25,min(widths)*.15)
    anchors_fit=all(abs(y-(upper if j%2 else lower)[0]-slopes[0 if j%2 else 1]*(i-a))<=tolerance for j,(i,y) in enumerate(points))
    inside=sum(max(bar.open,bar.close)<=upper[0]+slopes[0]*(i-a)+tolerance and min(bar.open,bar.close)>=lower[0]+slopes[1]*(i-a)-tolerance for i,bar in enumerate(bars[a:b+1],a))/(b-a+1)
    checks=dict(amplitudes_decrease=amplitudes[0]>amplitudes[1]>amplitudes[2],parallel_within_15pct=abs(width_change)<=15,prior_30bar_move_at_least_3_mean_ranges=abs(direction_move)>=3*bar_range, strict_wick_tolerance=anchors_fit,strict_body_enclosure=inside>=.85)
    patterns.append(dict(native=r,points=points,upper=upper,lower=lower,widths=widths,width_change_pct=width_change,amplitudes=amplitudes,strict_checks=checks,known=stamp(r["known"]),cross=stamp(r["event"])))
report=dict(channel=left,patterns=patterns,scope="H1 native bar index for rails; same six wicks as native PA export. Strict checks are code parameters; no author double-break adjudication.")
(dst/"review.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),"utf8")
plt.rcParams.update({"font.sans-serif":["Microsoft YaHei"],"axes.unicode_minus":False})
fig,axes=plt.subplots(1,2,figsize=(13.5,5))
def panel(ax,start,end):
    rows=[(i,b) for i,b in enumerate(bars) if start<=b.time.isoformat()<end]
    for i,b in rows:
        c="#296b58" if b.close>=b.open else "#a64f46"
        ax.vlines(i,b.low,b.high,color=c,lw=.85)
        ax.add_patch(Rectangle((i-.3,min(b.open,b.close)),.6,max(abs(b.close-b.open),.15),facecolor=c,edgecolor=c))
    ticks=rows[::9]
    ax.set_xticks([i for i,b in ticks],[b.time.strftime("%m-%d\n%H:%M") for i,b in ticks],fontsize=8)
    ax.ticklabel_format(useOffset=False,axis='y'); ax.grid(axis='y',alpha=.15);ax.set_xlim(rows[0][0]-1,rows[-1][0]+1)
panel(axes[0],"2026-09-24T07","2026-09-28T07")
panel(axes[1],"2026-09-28T12","2026-09-30T22")
for k in ("upper","lower"):
    raw=g[k]; p=[(idx[int(datetime.fromisoformat(q["time"]).timestamp())],q["price"]) for q in raw]
    (x,y),(xx,yy)=p
    last=idx[int(datetime.fromisoformat(left["end_at"]).timestamp())-3600]
    axes[0].plot([x,last],[y,y+(yy-y)*(last-x)/(xx-x)],color="#b87514",lw=1.9)
known=datetime.fromisoformat(left["known_at"])
axes[0].axvline(idx[int(known.timestamp())-3600]+.5,color="#566573",ls=":",label="首次可确认的收盘")
axes[0].legend(loc="lower left");axes[0].set_title("左侧　上升平行通道")
for j,p in enumerate(patterns):
    x0,x1=p["points"][0][0],p["points"][-1][0]; color=["#12729c","#6a608c"][j]
    for k in ("upper","lower"):
        axes[1].plot([x0,x1],p[k],lw=1.6,color=color,label=(["#62 蓝色熊旗","#63 灰色轮廓"][j] if k=="upper" else None))
    axes[1].scatter(*zip(*p["points"]),s=15,color=color,zorder=6)
axes[1].legend(loc="upper left");axes[1].set_title("右侧　两组轮廓与原六点")
fig.suptitle("XAUUSD H1　原生行情复盘｜横轴按实际 K 线排列",fontsize=15)
fig.tight_layout();fig.savefig(dst/"H1通道与右侧三推复核.png",dpi=145);plt.close(fig)
print(left["known_at"],left["end_at"],g.get("touches"),[ (p["amplitudes"],p["width_change_pct"],p["known"],p["cross"],p["strict_checks"]) for p in patterns])
