# NUMWORKS CITY: cars, people, cops, you
from gtalib import *

def hu(c,n):
 if c[7]>0:
  c[7]-=n
  if c[7]<1:
   ef(c[0],c[1],6,14)
   if c is g.P:g.dead='WASTED'
   elif rm(g.cs,c):g.mo+=50;g.ht+=25+35*(c[3]==1)

def ki(p):
 if rm(g.pp,p):ef(p[0],p[1],5,250);g.mo+=10;g.ht+=20

def hit(q):
 for p in g.pp:
  if ov(q,B(p)):ki(p);return 1
 for c in g.cs:
  if ov(q,B(c)):hu(c,25);g.ht+=5+15*(c[3]==1);return 1

def sp(k):
 cx=g.cx;cy=g.cy;cs=g.cs
 for i in range(9):
  u=RI(cx-3,cx+18);v=RI(cy-3,cy+12);t=tt(u,v);a=u%8;b=v%8
  if cx<=u<cx+16 and cy<=v<cy+10:continue
  e=N(u*T+10,v*T+10,(1+2*a if a<2 else 2-2*b)%4,k,0 if k==1 else CH(CC))
  if k>2:
   if t==1:g.pp.append(e);return
  elif t<1 and (a<2)!=(b<2):
   for o in cs:
    if ov(B(e),B(o)):break
   else:cs.append(e);return

def at(c):
 x=c[0];y=c[1];d=c[2]
 if c[6]>=0:
  a=(x+DX[d]*15-6,y+DY[d]*15-6,12,12)
  for o in g.cs+[g.P]:
   if o is not c and ov(a,B(o)):
    c[6]+=1
    if c[6]>45:c[6]=-30
    return
 else:c[6]+=1
 u=x//T;v=y//T
 if x%T==10==y%T and u%8<2 and v%8<2:
  o=[]
  for n in(d,(d+1)%4,(d+3)%4):
   if (n==d or (v,u)[n%2]%8==(1,0,0,1)[n]) and tt(u+DX[n],v+DY[n])<1:o.append(n)
  d=d if d in o and RD()<.6 else CH(o) if o else (d+2)%4
 c[0]=x+DX[d]*2;c[1]=y+DY[d]*2;c[2]=d

def ap(c):
 P=g.P;w=g.wl;x=c[0];y=c[1];d=c[2];dx=P[0]-x;dy=P[1]-y;s=2+w*.4
 if abs(dx)>abs(dy):p=2*(dx<0);q=1+2*(dy<0)
 else:p=1+2*(dy<0);q=2*(dx<0)
 if not w:p=q=d
 o=(p,q,d,(q+2)%4,(p+2)%4)
 if c[6]>0 or DX[d]*dx+DY[d]*dy>12:o=(d,)+o
 c[6]-=1
 for n in o:
  a=x+DX[n]*s;b=y+DY[n]*s
  if not bl(bx(a,b,n,1)):
   if n!=p and n!=q and c[6]<1:c[6]=15
   c[0]=a;c[1]=b;c[2]=n;break
 if w and ov(B(c),B(P)):
  if not g.pc:g.dead='BUSTED'
  hu(P,3);c[0]=x;c[1]=y

def ad(p):
 x=p[0];y=p[1];d=p[2]
 if RD()<.02:d=RI(0,3)
 a=x+DX[d];b=y+DY[d]
 if bl(bx(a,b,0,3),tt(int(x)//T,int(y)//T)):d=RI(0,3)
 else:p[0]=a;p[1]=b
 p[2]=d

def ok():
 P=g.P
 if g.pc:
  for a,b in((0,13),(0,-13),(13,0),(-13,0)):
   if abs(P[5])<1 and not bl(bx(P[0]+a,P[1]+b,0,4)):
    P[5]=0;g.cs.append(P);g.P=N(P[0]+a,P[1]+b,P[2],4,YL);g.pc=0;return
 for c in g.cs:
  if abs(c[0]-P[0])+abs(c[1]-P[1])<24:
   g.ht+=(8,40,0)[c[3]];rm(g.cs,c)
   if P[8]:g.tr.append(P[8])
   c[3]=2;c[5]=0;g.P=c;g.pc=1;return

def sh():
 P=g.P;x=P[0];y=P[1];a=DX[P[2]];b=DY[P[2]]
 for r in range(12,110,6):
  q=bx(x+a*r,y+b*r,0,3)
  if bl(q) or hit(q):break
 q=(int(min(x+a*10,x+a*r)),int(min(y+b*10,y+b*r)),abs(a)*(r-10)+2,abs(b)*(r-10)+2)
 R(q[0],q[1],q[2],q[3],YL);g.tr.append(q)
