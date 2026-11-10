// Display identity only: never alters source endpoints, scores or admission.
#ifndef MACHINE1_RULER_COLOURS
#define MACHINE1_RULER_COLOURS
string m1RulerColourOwners[];
color m1RulerColourValues[];
// Sort a COPY: allocation order binds owners to colours and must not change.
// The former nested scan revisited every historical owner pair on each bar.
int NativeColourCollisionCount(const color &values[]){
 int n=ArraySize(values);if(n<2)return 0;
 color sorted[];
 if(ArrayCopy(sorted,values)!=n||!ArraySort(sorted))return -1;
 long duplicates=0,run=1;
 for(int i=1;i<n;i++){
  if(sorted[i]==sorted[i-1]){duplicates+=run;run++;}
  else run=1;
  if(duplicates>=2147483647)return 2147483647;
 }
 return (int)duplicates;
}
color M1RulerCandidateColour(int slot){
 if(slot<0)return clrRoyalBlue;
 color palette[20]={clrRoyalBlue,clrDarkOrange,clrDarkViolet,clrSeaGreen,clrCrimson,
  clrTeal,clrSienna,clrDeepPink,clrSlateBlue,clrOliveDrab,clrSteelBlue,clrChocolate,
  clrMediumVioletRed,clrDarkCyan,clrFireBrick,clrBlueViolet,clrForestGreen,clrDodgerBlue,clrDarkGoldenrod,clrIndianRed};
 // Light strokes on dark charts; same owner registry spans rulers and pushes.
 color bg=(color)ChartGetInteger(0,CHART_COLOR_BACKGROUND);
 bool dark=((int)bg&255)+(((int)bg>>8)&255)+(((int)bg>>16)&255)<384;
 color bright[20]={C'102,179,255',C'255,174,66',C'200,145,255',C'93,210,160',C'255,121,141',C'86,216,216',C'221,167,125',C'255,136,208',C'164,164,255',C'180,211,102',C'123,194,224',C'246,171,119',C'223,133,192',C'111,204,197',C'236,139,131',C'173,137,250',C'126,215,132',C'112,161,255',C'231,195,101',C'223,155,162'};
 if(slot<20)return dark?bright[slot]:palette[slot];
 // A 21-bit permutation gives 2^21 distinct RGB cells, unlike the finite
 // quantized HSV palette that exhausted during the three-year replay and
 // looped until signed slot overflow. Each channel mapping is injective.
 uint cell=((uint)(slot-20)*2654435761)&2097151;
 int floor=dark?80:12,span=dark?175:168;
 int red=floor+(int)((cell&127)*span/127),green=floor+(int)(((cell>>7)&127)*span/127),blue=floor+(int)(((cell>>14)&127)*span/127);
 return (color)(red|(green<<8)|(blue<<16));
}
int M1RulerColourSlot(string owner){
 for(int i=0;i<ArraySize(m1RulerColourOwners);i++)if(m1RulerColourOwners[i]==owner)return i;
 int slot=ArraySize(m1RulerColourOwners),candidate=slot; color value=clrRoyalBlue;
 // At most slot occupied cells can precede a free one. Include the twenty
 // explicit palette entries in the bound; never spin until integer overflow.
 for(int attempt=0;attempt<=slot+20;attempt++){
  value=M1RulerCandidateColour(candidate++);bool used=false;
  for(int i=0;i<ArraySize(m1RulerColourValues);i++)if(m1RulerColourValues[i]==value){used=true;break;}
  if(!used)break;
 }
 ArrayResize(m1RulerColourOwners,slot+1);ArrayResize(m1RulerColourValues,slot+1);
 m1RulerColourOwners[slot]=owner;m1RulerColourValues[slot]=value;return slot;
}
color M1RulerColour(string owner){int slot=M1RulerColourSlot(owner);return m1RulerColourValues[slot];}
#endif
