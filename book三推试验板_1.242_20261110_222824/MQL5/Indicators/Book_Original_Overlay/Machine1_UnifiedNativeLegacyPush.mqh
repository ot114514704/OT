#ifndef MACHINE1_UNIFIED_NATIVE_LEGACY_PUSH
#define MACHINE1_UNIFIED_NATIVE_LEGACY_PUSH
#include "Machine1_UnifiedNativeKernel.mqh"
// Port of live_xauusd_multitimeframe.py nested_balanced_three_push_v4.
// Engineering tolerances from the existing local version, not book quotations.
struct M1ULegacyPush {
 M1UPoint points[];
 int radii[],parent,children,direction;
 datetime known;
 double amplitudes[],overlaps[],centres[],tips[],bases[],speeds[],bar_overlaps[];
 bool urgent[],spikes[];
 double typical,balance,amplitude_ratio,route_sizes[],route_prices[],route_residuals[];
 bool route_usable[];
};
double M1ULegacyMedian(double &values[]){
 int n=ArraySize(values);if(n==0)return 0;
 for(int i=1;i<n;i++){double v=values[i];int j=i-1;while(j>=0&&values[j]>v){values[j+1]=values[j];j--;}values[j+1]=v;}
 return n%2==1?values[n/2]:(values[n/2-1]+values[n/2])/2.0;
}
bool M1ULegacyPushQuality(const MqlRates &rates[],const M1UPoint &points[],int first,int frame,datetime cutoff,M1ULegacyPush &out){
 if(first<0||first+5>=ArraySize(points)||frame<=0)return false;
 ArrayResize(out.points,6);ArrayResize(out.amplitudes,3);ArrayResize(out.overlaps,2);
 ArrayResize(out.centres,2);ArrayResize(out.tips,2);ArrayResize(out.bases,2);
 ArrayResize(out.speeds,3);ArrayResize(out.bar_overlaps,3);ArrayResize(out.urgent,3);ArrayResize(out.spikes,3);
 ArrayResize(out.radii,0);out.parent=-1;out.children=0;out.known=0;
 int positions[];ArrayResize(positions,6);
 for(int i=0;i<6;i++){
  M1UCopy(out.points[i],points[first+i]);positions[i]=-1;
  for(int k=0;k<ArraySize(rates);k++)if(rates[k].time==out.points[i].time){positions[i]=k;break;}
  if(positions[i]<0||out.points[i].known>cutoff||out.points[i].known<out.points[i].time+frame)return false;
  if(out.points[i].kind!=1&&out.points[i].kind!=-1)return false;
  if(i>0&&(positions[i]<=positions[i-1]||out.points[i].kind==out.points[i-1].kind))return false;
  double price=out.points[i].kind==1?rates[positions[i]].high:rates[positions[i]].low;
  if(!MathIsValidNumber(out.points[i].price)||MathAbs(price-out.points[i].price)>MathMax(1e-7,1e-9*MathMax(MathAbs(price),MathAbs(out.points[i].price))))return false;
  out.known=(datetime)MathMax((double)out.known,(double)out.points[i].known);
 }
 for(int k=positions[0];k<=positions[5];k++)if(!M1UValidRate(rates[k])||rates[k].time+frame>cutoff)return false;
 out.direction=out.points[0].kind==-1?1:-1;
 double minimum=DBL_MAX,maximum=0,median_values[];ArrayResize(median_values,3);
 for(int j=0;j<3;j++){
  double amp=out.direction*(out.points[j*2+1].price-out.points[j*2].price);
  if(amp<=0)return false;out.amplitudes[j]=amp;median_values[j]=amp;minimum=MathMin(minimum,amp);maximum=MathMax(maximum,amp);
 }
 out.amplitude_ratio=maximum/minimum;if(out.amplitude_ratio>2.0+1e-9)return false;
 out.typical=M1ULegacyMedian(median_values);out.balance=minimum/maximum;
 for(int j=0;j<2;j++){
  double a=out.points[j*2].price,b=out.points[j*2+1].price,c=out.points[j*2+2].price,d=out.points[j*2+3].price;
  out.centres[j]=out.direction*((c+d)/2.0-(a+b)/2.0)/out.typical;
  out.tips[j]=out.direction*(d-b)/out.typical;out.bases[j]=out.direction*(c-a)/out.typical;
  out.overlaps[j]=(MathMin(MathMax(a,b),MathMax(c,d))-MathMax(MathMin(a,b),MathMin(c,d)))/MathMin(MathAbs(b-a),MathAbs(d-c));
 }
 if(MathMin(out.centres[0],out.centres[1])<.12||out.centres[0]+out.centres[1]<.45||MathMin(out.tips[0],out.tips[1])<.08||out.tips[0]+out.tips[1]<.45||MathMin(out.bases[0],out.bases[1])<-.15)return false;
 if(MathMin(out.overlaps[0],out.overlaps[1])<-.12||MathMax(out.overlaps[0],out.overlaps[1])<.50||(out.overlaps[0]+out.overlaps[1])/2.0<.35-1e-9)return false;
 for(int j=0;j<3;j++){
  int start=positions[j*2],end=positions[j*2+1];double prior[];ArrayResize(prior,0);
  for(int k=(int)MathMax(0,start-20);k<start;k++){double range=rates[k].high-rates[k].low;if(range>0){int n=ArraySize(prior);ArrayResize(prior,n+1);prior[n]=range;}}
  if(ArraySize(prior)<5)return false;double baseline=M1ULegacyMedian(prior);
  double lo=MathMin(out.points[j*2].price,out.points[j*2+1].price),hi=MathMax(out.points[j*2].price,out.points[j*2+1].price);
  double travel=0,overlap=0;int same=0,dominant=0;bool spike=false;
  for(int k=start;k<=end;k++){
   if(rates[k].low<lo-1e-7||rates[k].high>hi+1e-7)return false;
   double range=rates[k].high-rates[k].low,body=MathAbs(rates[k].close-rates[k].open);
   if(range>=2*baseline&&body>=.65*range)spike=true;
   if(k>start){double delta=rates[k].close-rates[k-1].close;travel+=MathAbs(delta);if(out.direction*delta>0)same++;
    if(out.direction*(rates[k].close-rates[k].open)>0&&body>=.5*range)dominant++;
    overlap+=MathMax(0,MathMin(rates[k-1].high,rates[k].high)-MathMax(rates[k-1].low,rates[k].low))/MathMax(MathMin(rates[k-1].high-rates[k-1].low,range),1e-9);
   }
  }
  double efficiency=travel>0?MathAbs(rates[end].close-rates[start].close)/travel:0;
  out.speeds[j]=out.amplitudes[j]/(end-start)/baseline;out.bar_overlaps[j]=overlap/(end-start);
  out.urgent[j]=out.speeds[j]>=.70&&efficiency>=.68&&(double)same/(end-start)>=.65&&dominant>=2;out.spikes[j]=spike;
 }
 ArrayResize(out.route_sizes,3);ArrayResize(out.route_prices,3);ArrayResize(out.route_residuals,3);ArrayResize(out.route_usable,3);
 out.route_sizes[0]=(out.amplitudes[0]+out.amplitudes[1])/2.0;out.route_sizes[1]=out.amplitudes[0]+out.amplitudes[1];out.route_sizes[2]=out.amplitudes[0]-out.amplitudes[1];
 for(int j=0;j<3;j++){out.route_usable[j]=out.route_sizes[j]>0;out.route_prices[j]=out.route_usable[j]?out.points[4].price+out.direction*out.route_sizes[j]:0;out.route_residuals[j]=out.route_usable[j]?MathAbs(out.amplitudes[2]-out.route_sizes[j])/out.route_sizes[j]:0;}
 return true;
}
bool M1ULegacySamePush(const M1ULegacyPush &a,const M1ULegacyPush &b){
 for(int k=0;k<6;k++)if(a.points[k].time!=b.points[k].time||a.points[k].kind!=b.points[k].kind||a.points[k].price!=b.points[k].price)return false;return true;
}
void M1ULegacyPushBuild(const MqlRates &rates[],int frame,datetime cutoff,M1ULegacyPush &out[]){
 ArrayResize(out,0);int radius=2;
 for(int pass=0;pass<5;pass++,radius*=2){
  M1UPoint ledger[];if(!M1ULedger(rates,frame,cutoff,radius,ledger))return;
  for(int first=0;first+5<ArraySize(ledger);first++){
   M1ULegacyPush item;if(!M1ULegacyPushQuality(rates,ledger,first,frame,cutoff,item))continue;
   int existing=-1;for(int j=0;j<ArraySize(out);j++)if(M1ULegacySamePush(out[j],item)){existing=j;break;}
   if(existing<0){existing=ArraySize(out);ArrayResize(out,existing+1);out[existing]=item;}
   int n=ArraySize(out[existing].radii);ArrayResize(out[existing].radii,n+1);out[existing].radii[n]=radius;
  }
 }
 for(int i=1;i<ArraySize(out);i++){
  M1ULegacyPush item=out[i];int j=i-1;
  while(j>=0&&(out[j].points[5].time>item.points[5].time||(out[j].points[5].time==item.points[5].time&&out[j].points[0].time>item.points[0].time))){out[j+1]=out[j];j--;}
  out[j+1]=item;
 }
 for(int i=0;i<ArraySize(out);i++){
  int parent=-1,span=2147483647;
  for(int j=0;j<ArraySize(out);j++){
   if(i==j||out[j].direction!=out[i].direction||out[j].typical<=out[i].typical)continue;
   if(out[j].points[0].time>out[i].points[0].time||out[j].points[5].time<out[i].points[5].time)continue;
   if(out[j].points[0].time==out[i].points[0].time&&out[j].points[5].time==out[i].points[5].time)continue;
   int candidate_span=out[j].points[5].index-out[j].points[0].index;
   if(candidate_span<span){parent=j;span=candidate_span;}
  }
  out[i].parent=parent;if(parent>=0)out[parent].children++;
 }
}
#endif
