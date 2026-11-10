#property copyright "Original Book archive three-push overlay trial"
#property version "1.241"
#property indicator_chart_window
#property indicator_plots 0
#include "Machine1_UnifiedNativeLegacyPush.mqh"
#include "Machine1_UnifiedNativeColours.mqh"
input bool ShowNativeThreePush=true;
input int HistoryBars=4000;
M1ULegacyPush nativeLocalThreePush[];
string nativePrefix,nativeSourceIdentity,nativeLocalThreePushRevision="";
string nativeThreePushGeometryRevision="",nativeThreePushDisplayRevision="",nativePushViewportKey="";
bool nativeLayoutPending=false,nativeCaptionsDirty=true,overlayEnabled=true;
datetime loadedNewest=0,loadedOldest=0,loadedClosed=0;
int loadedStart=-1,loadedCount=0;
bool pending=true;
void NativeRulerReviewObject(string name){} // Original standalone review hooks have no admission effects.
void NativeLine(string name,datetime a,double ap,datetime b,double bp,color colour,int style){
 if(ObjectFind(0,name)<0)ObjectCreate(0,name,OBJ_TREND,0,a,ap,b,bp);
 ObjectMove(0,name,0,a,ap);ObjectMove(0,name,1,b,bp);
 ObjectSetInteger(0,name,OBJPROP_COLOR,colour);ObjectSetInteger(0,name,OBJPROP_STYLE,style);
 ObjectSetInteger(0,name,OBJPROP_RAY_RIGHT,false);ObjectSetInteger(0,name,OBJPROP_RAY_LEFT,false);
 ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);NativeRulerReviewObject(name);
}
bool NativePushChainFits(const int &cx[],const int &cy[],int width,int height,const int &xs[],const int &ys[],int used){
 if(used+3>18)return false;
 for(int j=0;j<3;j++){
  if(cx[j]<32||cx[j]>width-52||cy[j]<112||cy[j]>height-100)return false;
  for(int k=0;k<j;k++)if(MathAbs(cx[j]-cx[k])<40&&MathAbs(cy[j]-cy[k])<28)return false;
  for(int k=0;k<used;k++)if(MathAbs(cx[j]-xs[k])<76&&MathAbs(cy[j]-ys[k])<28)return false;
 }
 return true;
}
void NativePushMark(string name,const M1UPoint &point,string text,string tip,color colour){
 nativeCaptionsDirty=true;
 if(ObjectFind(0,name)<0)ObjectCreate(0,name,OBJ_TEXT,0,point.time,point.price);
 ObjectMove(0,name,0,point.time,point.price);
 ObjectSetInteger(0,name,OBJPROP_COLOR,colour);ObjectSetInteger(0,name,OBJPROP_FONTSIZE,10);
 ObjectSetInteger(0,name,OBJPROP_ANCHOR,point.kind==1?ANCHOR_LOWER:ANCHOR_UPPER);
 ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);ObjectSetInteger(0,name,OBJPROP_BACK,false);
 ObjectSetString(0,name,OBJPROP_TEXT,text);ObjectSetString(0,name,OBJPROP_TOOLTIP,tip);
 NativeRulerReviewObject(name);
}
void NativeRenderThreePush(){
 string geometry=nativeLocalThreePushRevision+"|"+IntegerToString(ShowNativeThreePush?1:0);
 string revision=geometry;
 int width=(int)ChartGetInteger(0,CHART_WIDTH_IN_PIXELS),height=(int)ChartGetInteger(0,CHART_HEIGHT_IN_PIXELS,0);
 nativePushViewportKey=IntegerToString(width)+"|"+IntegerToString(height)+"|"+IntegerToString(ChartGetInteger(0,CHART_FIRST_VISIBLE_BAR))+"|"+IntegerToString(ChartGetInteger(0,CHART_SCALE))+"|"+DoubleToString(ChartGetDouble(0,CHART_PRICE_MIN),8)+"|"+DoubleToString(ChartGetDouble(0,CHART_PRICE_MAX),8);
 revision+="|"+nativePushViewportKey;
 if(!ShowNativeThreePush||nativeLocalThreePushRevision==""||ArraySize(nativeLocalThreePush)==0){if(nativeThreePushGeometryRevision!="")ObjectsDeleteAll(0,nativePrefix+"three_push_");nativeThreePushDisplayRevision="";nativeThreePushGeometryRevision="";return;}
 bool layout_ready=width>0&&height>0&&ChartGetDouble(0,CHART_PRICE_MAX)>ChartGetDouble(0,CHART_PRICE_MIN);
 if(!layout_ready)nativeLayoutPending=true;
 if(layout_ready&&nativeThreePushDisplayRevision==revision)return;
 bool geometry_changed=nativeThreePushGeometryRevision!=geometry;
 if(geometry_changed)ObjectsDeleteAll(0,nativePrefix+"three_push_");
 int label_x[18],label_y[18],labels_used=0;
 for(int i=ArraySize(nativeLocalThreePush)-1;i>=0;i--){
  M1ULegacyPush item=nativeLocalThreePush[i];
  string owner="three_push|"+nativeSourceIdentity;
  for(int p=0;p<6;p++)owner+="|"+IntegerToString(item.points[p].time)+"@"+DoubleToString(item.points[p].price,12);
  // Shared, collision-free owner registry: a pattern retains its colour when
  // a new candidate is inserted or the visible history window moves.
  color colour=M1RulerColour(owner);
  string base=nativePrefix+"three_push_"+IntegerToString(i)+"_";
  string role=item.parent>=0?(item.children>0?"中":"小"):(item.children>0?"大":"");
  string text=role+"三推候选 | nested_balanced_three_push_v4 | 平衡度="+DoubleToString(100*item.balance,1)+"/100 幅度比="+DoubleToString(item.amplitude_ratio,4)+" 重叠="+DoubleToString(item.overlaps[0],4)+","+DoubleToString(item.overlaps[1],4)+" | 同周期父="+IntegerToString(item.parent)+"；父周期未知；非入场";
  for(int j=0;j<3;j++)text+=" | 路径"+IntegerToString(j+1)+"="+(item.route_usable[j]?DoubleToString(item.route_prices[j],_Digits):"不可用");
  // Original local adapter joins push tips, not the five internal ZigZag legs.
  if(geometry_changed)for(int j=0;j<2;j++){
   M1UPoint a=item.points[j*2+1],b=item.points[j*2+3];
   NativeLine(base+IntegerToString(j),a.time,a.price,b.time,b.price,colour,STYLE_DASH);
   ObjectSetInteger(0,base+IntegerToString(j),OBJPROP_WIDTH,2);
   ObjectSetString(0,base+IntegerToString(j),OBJPROP_TOOLTIP,text);
  }
  if(!geometry_changed)for(int j=0;j<3;j++)ObjectDelete(0,base+"tip_"+IntegerToString(j));
  int cx[3],cy[3];bool visible=layout_ready;
  for(int j=0;j<3;j++)if(!ChartTimePriceToXY(0,0,item.points[j*2+1].time,item.points[j*2+1].price,cx[j],cy[j]))visible=false;
  if(visible&&NativePushChainFits(cx,cy,width,height,label_x,label_y,labels_used))for(int j=0;j<3;j++){
   string mark=j==2?role+"三推 3":IntegerToString(j+1);
   if(j==2&&false /* numerical labels owned by unified score switch */)mark+=" 平衡 "+DoubleToString(100*item.balance,1);
   NativePushMark(base+"tip_"+IntegerToString(j),item.points[j*2+1],mark,text,colour);
   label_x[labels_used]=cx[j];label_y[labels_used]=cy[j];labels_used++;
  }
 }
 nativeThreePushDisplayRevision=layout_ready?revision:"";nativeThreePushGeometryRevision=geometry;
}

void OverlayStatus(string message){
 string n=nativePrefix+"status";
 if(ObjectFind(0,n)<0)ObjectCreate(0,n,OBJ_LABEL,0,0,0);
 ObjectSetInteger(0,n,OBJPROP_CORNER,CORNER_LEFT_LOWER);
 ObjectSetInteger(0,n,OBJPROP_XDISTANCE,14);ObjectSetInteger(0,n,OBJPROP_YDISTANCE,44);
 ObjectSetInteger(0,n,OBJPROP_COLOR,clrOrchid);ObjectSetInteger(0,n,OBJPROP_FONTSIZE,10);
 ObjectSetString(0,n,OBJPROP_TEXT,message);
 ObjectSetString(0,n,OBJPROP_TOOLTIP,"原包三推独立图层；不改变、不过滤原盘整。原画法：同组同色，连接三个推进端点，编号1/2/3。闭合K线证据，非入场信号。");
}
void OverlayButtons(){
 string ids[2]={"toggle","example"};
 string texts[2]={overlayEnabled?"原包三推 开":"原包三推 关","定位三推"};
 for(int i=0;i<2;i++){
  string n=nativePrefix+ids[i];
  if(ObjectFind(0,n)<0)ObjectCreate(0,n,OBJ_BUTTON,0,0,0);
  ObjectSetInteger(0,n,OBJPROP_CORNER,CORNER_RIGHT_LOWER);
  ObjectSetInteger(0,n,OBJPROP_XDISTANCE,140+i*140);ObjectSetInteger(0,n,OBJPROP_YDISTANCE,75);
  ObjectSetInteger(0,n,OBJPROP_XSIZE,132);ObjectSetInteger(0,n,OBJPROP_YSIZE,24);
  ObjectSetInteger(0,n,OBJPROP_COLOR,clrOrchid);ObjectSetInteger(0,n,OBJPROP_BGCOLOR,C'22,29,42');
  ObjectSetInteger(0,n,OBJPROP_SELECTABLE,false);ObjectSetInteger(0,n,OBJPROP_ZORDER,200);
  ObjectSetString(0,n,OBJPROP_TEXT,texts[i]);
 }
}
bool OverlayLoad(){
 int available=Bars(_Symbol,_Period);if(available<40){OverlayStatus("book三推试验板：等待原生历史K线");return false;}
 int first=(int)ChartGetInteger(0,CHART_FIRST_VISIBLE_BAR);
 int visible=(int)ChartGetInteger(0,CHART_VISIBLE_BARS);
 int start=MathMax(1,first-visible-160);
 int count=MathMin(MathMax(600,HistoryBars),available-start);
 datetime closed=iTime(_Symbol,_Period,1);
 // Reuse while visible bars remain inside the original calculation context.
 bool inside=loadedCount>0&&first<loadedStart+loadedCount-160&&MathMax(1,first-visible)>=loadedStart;
 if(!pending&&closed==loadedClosed&&inside)return true;
 MqlRates rows[];ArraySetAsSeries(rows,false);
 int copied=CopyRates(_Symbol,_Period,start,count,rows);
 if(copied<40){OverlayStatus("book三推试验板：正在下载这段历史，保留上一版图形");return false;}
 datetime cutoff=rows[copied-1].time+PeriodSeconds(_Period);
 M1ULegacyPush next[];M1ULegacyPushBuild(rows,PeriodSeconds(_Period),cutoff,next);
 ArrayResize(nativeLocalThreePush,ArraySize(next));
 for(int i=0;i<ArraySize(next);i++)nativeLocalThreePush[i]=next[i];
 loadedStart=start;loadedCount=copied;loadedOldest=rows[0].time;loadedNewest=rows[copied-1].time;loadedClosed=closed;
 nativeLocalThreePushRevision=IntegerToString(loadedOldest)+"|"+IntegerToString(loadedNewest)+"|"+IntegerToString(copied);
 pending=false;
 OverlayStatus("book三推试验板 1.241 · 原包三推 "+IntegerToString(ArraySize(next))+"组 · 原盘整不变 · "+TimeToString(loadedOldest,TIME_DATE)+"—"+TimeToString(loadedNewest,TIME_DATE));
 int f=FileOpen("BookOriginalOverlay_"+IntegerToString(ChartID())+".tsv",FILE_WRITE|FILE_TXT|FILE_UNICODE);
 if(f!=INVALID_HANDLE){
  FileWriteString(f,"version\t1.241\nsource\tUnified_1.133/nested_balanced_three_push_v4\nchart\t"+IntegerToString(ChartID())+"\nperiod\t"+IntegerToString(PeriodSeconds(_Period))+"\nloaded\t"+IntegerToString(copied)+"\ngroups\t"+IntegerToString(ArraySize(next))+"\n");
  for(int i=0;i<ArraySize(next);i++){
   string row=IntegerToString(next[i].known);
   for(int j=0;j<6;j++)row+="\t"+IntegerToString(next[i].points[j].time)+"@"+DoubleToString(next[i].points[j].price,_Digits);
   FileWriteString(f,row+"\n");
  }FileClose(f);
 }
 return true;
}
void OverlayRender(){
 // Original renderer honours input toggle; independent UI uses visibility only.
 NativeRenderThreePush();
 for(int i=ObjectsTotal(0)-1;i>=0;i--){
  string n=ObjectName(0,i);
  if(StringFind(n,nativePrefix+"three_push_")==0)ObjectSetInteger(0,n,OBJPROP_TIMEFRAMES,overlayEnabled?OBJ_ALL_PERIODS:OBJ_NO_PERIODS);
 }
 OverlayButtons();ChartRedraw();
}
int OnInit(){
 nativePrefix="BOOK_ORIGINAL_"+IntegerToString(ChartID())+"_"+IntegerToString(GetTickCount64())+"_";
 nativeSourceIdentity=AccountInfoString(ACCOUNT_SERVER)+"|"+_Symbol+"|"+IntegerToString(PeriodSeconds(_Period));
 IndicatorSetString(INDICATOR_SHORTNAME,"book三推试验板 · 原包叠加 1.241");
 EventSetTimer(2);OverlayButtons();OverlayStatus("book三推试验板：读取原包三推；原盘整保持不变");
 return INIT_SUCCEEDED;
}
int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],const double &open[],const double &high[],const double &low[],const double &close[],const long &tick_volume[],const long &volume[],const int &spread[]){return rates_total;}
void OnTimer(){if(OverlayLoad())OverlayRender();}
void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam){
 if(id==CHARTEVENT_CHART_CHANGE){nativeThreePushDisplayRevision="";OverlayRender();}
 if(id==CHARTEVENT_OBJECT_CLICK&&sparam==nativePrefix+"toggle"){
  overlayEnabled=!overlayEnabled;ObjectSetInteger(0,sparam,OBJPROP_STATE,false);OverlayRender();
 }
 if(id==CHARTEVENT_OBJECT_CLICK&&sparam==nativePrefix+"example"){
  ObjectSetInteger(0,sparam,OBJPROP_STATE,false);
  int n=ArraySize(nativeLocalThreePush);if(n==0)return;
  M1ULegacyPush last=nativeLocalThreePush[n-1];
  int shift=iBarShift(_Symbol,_Period,last.points[0].time,false);
  int width=(int)ChartGetInteger(0,CHART_VISIBLE_BARS);
  ChartSetInteger(0,CHART_AUTOSCROLL,false);ChartNavigate(0,CHART_END,-MathMax(0,shift-width+20));
 }
}
void OnDeinit(const int reason){EventKillTimer();if(nativePrefix!="")ObjectsDeleteAll(0,nativePrefix);}
