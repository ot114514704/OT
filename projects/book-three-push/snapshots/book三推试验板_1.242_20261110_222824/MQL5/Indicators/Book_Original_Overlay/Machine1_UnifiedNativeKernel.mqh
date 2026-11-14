#ifndef MACHINE1_UNIFIED_NATIVE_KERNEL
#define MACHINE1_UNIFIED_NATIVE_KERNEL
// Native calculation only: no transport, files, DLL, web or trade calls.
// Port references: live_xauusd_multitimeframe radius2/alternating ledger;
// arrow_wave_scope.js alternate/reduce/build/developingBackground.
// Absorb only IEEE754 arithmetic roundoff, not a market tick or price band.
// C+(B-A) can be one representable double above an exactly equal quote.
bool M1UPriceReached(double price,double level,int direction){
 if((direction!=1&&direction!=-1)||!MathIsValidNumber(price)||!MathIsValidNumber(level))return false;
 double magnitude=MathMax(1.0,MathMax(price>=0?price:-price,level>=0?level:-level));
 double roundoff=4.0*2.2204460492503131e-16*magnitude;
 return direction*(price-level)>=-roundoff;
}
// Shared equal-unit return episode. -1 breaks the owner, 0 keeps C,
// 1 observes a deeper C, 2 settles the existing C's target. A candle with
// BOTH a deeper C and the old target cannot settle that old C: wick order
// is unknown. The caller owns closed/open clocks and historical outcomes.
int M1URulerReturnStep(const MqlRates &bar,int direction,double owner_a,double owner_b,
 double unit,bool have_c,double c){
 double extreme=direction==1?bar.low:bar.high;
 if(direction==1?extreme<=owner_a:extreme>=owner_a)return -1;
 bool deeper=direction==1?extreme<(have_c?c:owner_b):extreme>(have_c?c:owner_b);
 if(deeper)return 1;
 if(have_c&&M1UPriceReached(direction==1?bar.high:bar.low,c+direction*unit,direction))return 2;
 return 0;
}
struct M1UPoint {
 datetime time,known,replaced_time,left_boundary,right_boundary;
 double price,replaced_price;
 int kind,index;
 bool restored;
};
void M1UCopy(M1UPoint &to,const M1UPoint &from){
 to.time=from.time;to.known=from.known;to.price=from.price;
 to.kind=from.kind;to.index=from.index;to.restored=from.restored;
 to.replaced_time=from.replaced_time;to.replaced_price=from.replaced_price;
 to.left_boundary=from.left_boundary;to.right_boundary=from.right_boundary;
}
void M1UNew(M1UPoint &p,datetime time,datetime known,double price,int kind,int index){
 p.time=time;p.known=known;p.price=price;p.kind=kind;p.index=index;
 p.restored=false;p.replaced_time=0;p.replaced_price=0;p.left_boundary=0;p.right_boundary=0;
}
void M1UAppend(M1UPoint &points[],const M1UPoint &p){
 int n=ArraySize(points);ArrayResize(points,n+1);M1UCopy(points[n],p);
}
void M1UCopyPoints(const M1UPoint &from[],M1UPoint &to[]){
 ArrayResize(to,ArraySize(from));for(int i=0;i<ArraySize(from);i++)M1UCopy(to[i],from[i]);
}
void M1USort(M1UPoint &points[]){
 // Stable ordering is material for equal-time outside-bar extrema.
 for(int i=1;i<ArraySize(points);i++){
  M1UPoint p;M1UCopy(p,points[i]);int j=i-1;
  while(j>=0&&points[j].time>p.time){M1UCopy(points[j+1],points[j]);j--;}
  M1UCopy(points[j+1],p);
 }
}
void M1UAlternate(const M1UPoint &points[],M1UPoint &out[]){
 M1UPoint ordered[];M1UCopyPoints(points,ordered);M1USort(ordered);ArrayResize(out,0);
 for(int i=0;i<ArraySize(ordered);i++){
  int n=ArraySize(out);int kind=ordered[i].kind;
  if(n>0&&out[n-1].kind==kind){
   if(kind==1?ordered[i].price>=out[n-1].price:ordered[i].price<=out[n-1].price)M1UCopy(out[n-1],ordered[i]);
  }else M1UAppend(out,ordered[i]);
 }
}
bool M1UValidRate(const MqlRates &r){
 return MathIsValidNumber(r.open)&&MathIsValidNumber(r.high)&&MathIsValidNumber(r.low)&&MathIsValidNumber(r.close)
  &&r.low<=MathMin(r.open,r.close)&&MathMax(r.open,r.close)<=r.high;
}
bool M1URawLedger(const MqlRates &rates[],int seconds,datetime cutoff,int radius,M1UPoint &out[]){
 ArrayResize(out,0);if(seconds<=0||radius<1||cutoff<=0)return false;
 int closed[];datetime previous=0;
 for(int i=0;i<ArraySize(rates);i++){
  if(rates[i].time+seconds>cutoff)continue;
  if(rates[i].time<=previous||!M1UValidRate(rates[i]))return false;
  int n=ArraySize(closed);ArrayResize(closed,n+1);closed[n]=i;previous=rates[i].time;
 }
 for(int i=radius;i<ArraySize(closed)-radius;i++){
  int at=closed[i];bool high=true,low=true;
  for(int k=i-radius;k<=i+radius;k++){
   if(k==i)continue;
   if(rates[at].high<=rates[closed[k]].high)high=false;
   if(rates[at].low>=rates[closed[k]].low)low=false;
  }
  datetime known=rates[closed[i+radius]].time+seconds;
  M1UPoint p;
  // Python's equal-time lexical order is high then low. Keep both in the
  // ledger; their intrabar order is unresolved, never inferred.
  if(high){M1UNew(p,rates[at].time,known,rates[at].high,1,at);M1UAppend(out,p);}
  if(low){M1UNew(p,rates[at].time,known,rates[at].low,-1,at);M1UAppend(out,p);}
 }
 return true;
}
bool M1ULedger(const MqlRates &rates[],int seconds,datetime cutoff,int radius,M1UPoint &out[]){
 ArrayResize(out,0);M1UPoint raw[];
 if(!M1URawLedger(rates,seconds,cutoff,radius,raw))return false;
 M1UAlternate(raw,out);return true;
}
void M1UArrowPoints(const M1UPoint &ledger[],M1UPoint &out[]){
 M1UPoint unique[];
 for(int i=0;i<ArraySize(ledger);i++){
  bool ambiguous=false;
  for(int j=0;j<ArraySize(ledger);j++)if(i!=j&&ledger[i].time==ledger[j].time&&
    (ledger[i].kind!=ledger[j].kind||ledger[i].price!=ledger[j].price)){ambiguous=true;break;}
  if(!ambiguous)M1UAppend(unique,ledger[i]);
 }
 M1UAlternate(unique,out);
}
void M1UReduce(const M1UPoint &points[],M1UPoint &out[]){
 M1UPoint selected[];
 for(int pass=0;pass<2;pass++){
  int kind=pass==0?1:-1;M1UPoint same[];
  for(int j=0;j<ArraySize(points);j++)if(points[j].kind==kind)M1UAppend(same,points[j]);
  for(int j=1;j<ArraySize(same)-1;j++){
   bool choose=kind==1?(same[j].price>same[j-1].price&&same[j].price>=same[j+1].price)
    :(same[j].price<same[j-1].price&&same[j].price<=same[j+1].price);
   if(choose){M1UPoint p;M1UCopy(p,same[j]);p.known=(datetime)MathMax((double)same[j-1].known,MathMax((double)p.known,(double)same[j+1].known));M1UAppend(selected,p);}
  }
 }
 M1USort(selected);M1UPoint bridges[];
 for(int i=1;i<ArraySize(selected);i++){
  if(selected[i-1].kind!=selected[i].kind)continue;
  int kind=-selected[i].kind,reference=-1,extreme=-1;
  for(int j=0;j<ArraySize(points);j++){
   if(points[j].kind!=kind)continue;
   if(points[j].time<selected[i-1].time)reference=j;
   if(points[j].time>selected[i-1].time&&points[j].time<selected[i].time&&
     (extreme<0||(kind==1?points[j].price>points[extreme].price:points[j].price<points[extreme].price)))extreme=j;
  }
  if(reference<0||extreme<0)continue;
  if(kind==1?points[extreme].price>points[reference].price:points[extreme].price<points[reference].price){
   M1UPoint p;M1UCopy(p,points[extreme]);
   p.known=(datetime)MathMax(MathMax((double)p.known,(double)points[reference].known),MathMax((double)selected[i-1].known,(double)selected[i].known));
   M1UAppend(bridges,p);
  }
 }
 for(int i=0;i<ArraySize(bridges);i++)M1UAppend(selected,bridges[i]);
 M1UAlternate(selected,out);if(ArraySize(out)<2)return;
 datetime first=out[0].time,last=out[ArraySize(out)-1].time;bool changed=true;
 while(changed){
  changed=false;
  for(int i=0;i<ArraySize(out);i++){
   datetime left=i>0?out[i-1].time:first-1,right=i+1<ArraySize(out)?out[i+1].time:last+1;
   int extreme=-1;
   for(int j=0;j<ArraySize(points);j++)if(points[j].kind==out[i].kind&&left<points[j].time&&points[j].time<right&&
     (extreme<0||(out[i].kind==1?points[j].price>points[extreme].price:points[j].price<points[extreme].price)))extreme=j;
   if(extreme<0)continue;
   if(out[i].kind==1?points[extreme].price>out[i].price:points[extreme].price<out[i].price){
    M1UPoint p;M1UCopy(p,points[extreme]);
    p.known=(datetime)MathMax((double)p.known,(double)out[i].known);
    if(i>0)p.known=(datetime)MathMax((double)p.known,(double)out[i-1].known);
    if(i+1<ArraySize(out))p.known=(datetime)MathMax((double)p.known,(double)out[i+1].known);
    p.restored=true;p.replaced_time=out[i].time;p.replaced_price=out[i].price;
    p.left_boundary=i>0?out[i-1].time:0;p.right_boundary=i+1<ArraySize(out)?out[i+1].time:0;
    M1UCopy(out[i],p);changed=true;
   }
  }
 }
}
// Resolve a same-degree return witness to the true wick extreme inside its
// B-to-C interval. The right-hand confirmation clock is NOT more return
// history: if that extreme was already crossed before confirmation, the old
// witness cannot admit a different, later low/high as its C.
int M1URulerWitnessAnchorUnit(const MqlRates &rates[],const M1UPoint &a,const M1UPoint &b,
 const M1UPoint &witness,int seconds,datetime admitted,datetime observed,double unit){
 datetime known=(datetime)MathMax((double)admitted,(double)witness.known);
 if(seconds<=0||unit<=0||!MathIsValidNumber(unit)||known>observed||witness.time<=b.time||witness.kind!=a.kind||witness.time+seconds>known)return -1;
 bool up=b.price>a.price;int ci=-1;bool began=false,witness_seen=false;double deepest=b.price;
 for(int i=0;i<ArraySize(rates);i++){
  if(rates[i].time<b.time)continue;
  if(rates[i].time==b.time){began=true;continue;}
  if(rates[i].time+seconds>known)break;
  if(!began||!M1UValidRate(rates[i]))return -1;
  if(rates[i].time==witness.time){
   if(witness.price!=(witness.kind==1?rates[i].high:rates[i].low))return -1;
   witness_seen=true;
  }
  double price=up?rates[i].low:rates[i].high;
  if(up?price<=a.price:price>=a.price)return -1;
  if(rates[i].time<=witness.time){
   int step=M1URulerReturnStep(rates[i],up?1:-1,a.price,b.price,unit,ci>=0,deepest);
   if(step==2)return -1; // a completed earlier second cannot restart here
   if(step==1){ci=i;deepest=price;}
  }else if(ci>=0&&(up?price<deepest:price>deepest))return -1;
 }
 return witness_seen?ci:-1;
}
int M1URulerWitnessAnchor(const MqlRates &rates[],const M1UPoint &a,const M1UPoint &b,
 const M1UPoint &witness,int seconds,datetime admitted,datetime observed){
 return M1URulerWitnessAnchorUnit(rates,a,b,witness,seconds,admitted,observed,
  b.price>a.price?b.price-a.price:a.price-b.price);
}
// Measurement revision is distinct from close-based plan invalidation. Until
// the original unit completes or A breaks, a deeper CONFIRMED owner-degree
// witness may extend THIS source's correction even when closes hold the old C.
// WitnessAnchor still rejects post-target returns, broken A, future witnesses
// and points already overrun before their own confirmation. No new C is
// admitted from a wick alone without that witness; old prefixes reconstruct as-of.
bool M1URulerReturnContinuation(const MqlRates &rates[],
 const M1UPoint &a,const M1UPoint &b,const M1UPoint &anchor,datetime next_time,datetime next_known,int seconds){
  if(next_time<=anchor.time||next_known<=anchor.known||seconds<=0)return false;
  bool up=b.price>a.price;bool deeper=false;
 for(int i=0;i<ArraySize(rates);i++){
  if(rates[i].time<=anchor.time)continue;
  if(rates[i].time>next_time||rates[i].time+seconds>next_known)break;
  if(!M1UValidRate(rates[i]))return false;
  if(up?rates[i].low<=a.price:rates[i].high>=a.price)return false;
   // Caller has already validated the new owner witness and its known-at time.
   if(up?rates[i].low<anchor.price:rates[i].high>anchor.price)deeper=true;
 }
  return deeper;
}
bool M1URulerEstablishedReturnUnit(const MqlRates &rates[],const M1UPoint &witnesses[],
 const M1UPoint &a,const M1UPoint &b,int seconds,datetime admitted,datetime observed,double unit,M1UPoint &anchor){
 bool found=false;bool up=b.price>a.price;
 int order[];ArrayResize(order,ArraySize(witnesses));for(int i=0;i<ArraySize(order);i++)order[i]=i;
 for(int i=1;i<ArraySize(order);i++)for(int k=i;k>0;k--){
  int x=order[k],y=order[k-1];
  if(witnesses[x].known>witnesses[y].known||(witnesses[x].known==witnesses[y].known&&witnesses[x].time>=witnesses[y].time))break;
  order[k]=y;order[k-1]=x;
 }
 for(int k=0;k<ArraySize(order);k++){
  int j=order[k];
  int ci=M1URulerWitnessAnchorUnit(rates,a,b,witnesses[j],seconds,admitted,observed,unit);if(ci<0)continue;
  double price=up?rates[ci].low:rates[ci].high;
  datetime known=(datetime)MathMax((double)admitted,(double)witnesses[j].known);
  bool deeper=!found||(up?price<anchor.price:price>anchor.price);
  if(deeper&&(!found||known==anchor.known||M1URulerReturnContinuation(rates,a,b,anchor,rates[ci].time,known,seconds))){
   M1UNew(anchor,rates[ci].time,known,price,a.kind,ci);found=true;
  }
 }
 return found;
}
bool M1URulerEstablishedReturn(const MqlRates &rates[],const M1UPoint &witnesses[],
 const M1UPoint &a,const M1UPoint &b,int seconds,datetime admitted,datetime observed,M1UPoint &anchor){
 return M1URulerEstablishedReturnUnit(rates,witnesses,a,b,seconds,admitted,observed,
  b.price>a.price?b.price-a.price:a.price-b.price,anchor);
}
bool M1UEnvelope(const MqlRates &rates[],const M1UPoint &a,const M1UPoint &b){
 if(a.index<0||b.index<=a.index||b.index>=ArraySize(rates)||rates[a.index].time!=a.time||rates[b.index].time!=b.time)return false;
 double low=MathMin(a.price,b.price),high=MathMax(a.price,b.price);
 for(int i=a.index+1;i<b.index;i++)if(rates[i].low<low||rates[i].high>high)return false;
 return true;
}
bool M1UUnknownBetween(const M1UPoint &ledger[],datetime from,datetime through){
 for(int i=1;i<ArraySize(ledger);i++)if(ledger[i].time==ledger[i-1].time&&from<=ledger[i].time&&ledger[i].time<=through)return true;
 return false;
}
bool M1UDeveloping(const MqlRates &rates[],int seconds,datetime cutoff,const M1UPoint &origin,M1UPoint &end){
 if(seconds<=0||origin.known>cutoff||origin.index<0||origin.index>=ArraySize(rates)||rates[origin.index].time!=origin.time)return false;
 if(origin.kind!=1&&origin.kind!=-1)return false;
 if((origin.kind==1?rates[origin.index].high:rates[origin.index].low)!=origin.price)return false;
 int sign=-origin.kind,extreme=-1,last=origin.index;
 for(int i=origin.index+1;i<ArraySize(rates);i++){
  if(rates[i].time+seconds>cutoff)continue;
  if(rates[i].time-rates[last].time!=seconds||!M1UValidRate(rates[i]))return false;
  if(sign==1?rates[i].low<origin.price:rates[i].high>origin.price)return false;
  double price=sign==1?rates[i].high:rates[i].low;
  if(extreme<0||(price-(sign==1?rates[extreme].high:rates[extreme].low))*sign>0)extreme=i;
  last=i;
 }
 if(extreme<0)return false;
 double price=sign==1?rates[extreme].high:rates[extreme].low;
 if((price-origin.price)*sign<=0)return false;
 M1UNew(end,rates[extreme].time,rates[extreme].time+seconds,price,sign,extreme);return true;
}
#endif
