# NUMWORKS CITY - GTA2-like game for NumWorks, ONE file.
# Run this script. Controls: arrows walk/drive,
# OK steal/exit car, EXE shoot. Earn $5000 to win.
# The code is stored in 4 text parts and compiled one by one
# with exec(): this needs much less memory than one big script.
# e=[x,y,dir,kind,color,speed,timer,hp,box]
# kind:0 car,1 cop,2 your car,3 man,4 you,5 blood,6 boom,7 marker
exec("""
from kandinsky import fill_rect as F,draw_string as S
from ion import *
from time import monotonic as M,sleep
from random import randint as RI,random as RD,choice as CH
T=20;DX=(1,0,-1,0);DY=(0,1,0,-1)
YL=(255,220,0);WH=(240,240,240);BK=(0,0,0);RE=(255,40,40)
TC=((70,70,75),(170,170,165),(60,45,45),(70,150,60),(40,90,200),(70,150,60))
BL=((160,80,70),(110,110,150),(180,150,100),(90,130,120))
CC=((200,30,30),(30,90,200),(30,160,60),(120,40,160),(20,20,20))
HS=(0,0,0,3,3,4,9,8)
KS=(KEY_RIGHT,KEY_DOWN,KEY_LEFT,KEY_UP);K=keydown

def tt(x,y):
 a=x%8;b=y%8
 if x<0 or y<0 or x>65 or y>41:return 4
 if a<2 or b<2:return 0
 if a in(2,7) or b in(2,7):return 1
 if (x//8*2+y//8*3)%5:return 2
 return 5 if a in(3,6) and b in(3,6) else 3

def tl(u,v):
 x=(u-cx)*T;y=(v-cy)*T+22;t=tt(u,v);a=u%8;b=v%8
 F(x,y,T,T,TC[t])
 if t==2:F(x+1,y+1,18,18,BL[(u//8+v//8*3)%4])
 if t>4:F(x+3,y+3,14,14,(30,95,35))
 if t<1 and a<2<=b:F(x+18-18*a,y+5,2,10,YL)
 if t<1 and b<2<=a:F(x+5,y+18-18*b,10,2,YL)

def R(x,y,w,h,c):
 x-=CX;y-=CY
 if x<0:w+=x;x=0
 if y<0:h+=y;y=0
 w=min(w,320-x);h=min(h,200-y)
 if w>0<h:F(x,y+22,w,h,c)

def N(x,y,d,k,c=0):return [x,y,d,k,c,0,0,100,None]

def bx(x,y,d,k):
 x=int(x);y=int(y);r=HS[k]
 if k>2:return (x-r,y-r,2*r,2*r)
 return (x-8,y-5,16,10) if d%2<1 else (x-5,y-8,10,16)

def B(e):return bx(*e[:4])

def bl(b,r=0):
 for u in(b[0],b[0]+b[2]-1):
  for v in(b[1],b[1]+b[3]-1):
   t=tt(u//T,v//T)
   if t in(2,4,5) or r and t<1:return 1

def ov(a,b):return a[0]<b[0]+b[2] and b[0]<a[0]+a[2] and a[1]<b[1]+b[3] and b[1]<a[1]+a[3]

def er(b):
 for v in range(max(b[1]//T,cy),min((b[1]+b[3]-1)//T,cy+9)+1):
  for u in range(max(b[0]//T,cx),min((b[0]+b[2]-1)//T,cx+15)+1):tl(u,v)

def cam(f=0):
 global cx,cy,CX,CY,tr
 u=int(P[0])//T-cx;v=int(P[1])//T-cy
 a=max(-1,min(51,cx+(u-11 if u<4 else u-4 if u>11 else 0)))
 b=max(-1,min(33,cy+(v-6 if v<3 else v-3 if v>6 else 0)))
 if f or a!=cx or b!=cy:
  cx=a;cy=b;CX=a*T;CY=b*T;tr=[]
  for i in range(160):tl(a+i%16,b+i//16)
  for e in fx+pp+cs+[P]:e[8]=None

def rm(l,e):
 for i in range(len(l)):
  if l[i] is e:
   l.pop(i)
   if e[8]:tr.append(e[8])
   return 1

def ef(x,y,k,t):
 e=N(x,y,0,k);e[6]=t;fx.append(e);return e
""")
exec("""
def hu(c,n):
 global dead,mo,ht
 if c[7]>0:
  c[7]-=n
  if c[7]<1:
   ef(c[0],c[1],6,14)
   if c is P:dead='WASTED'
   elif rm(cs,c):mo+=50;ht+=25+35*(c[3]==1)

def ki(p):
 global mo,ht
 if rm(pp,p):ef(p[0],p[1],5,250);mo+=10;ht+=20

def hit(q):
 global ht
 for p in pp:
  if ov(q,B(p)):ki(p);return 1
 for c in cs:
  if ov(q,B(c)):hu(c,25);ht+=5+15*(c[3]==1);return 1

def sh():
 x,y,d=P[:3];a=DX[d];b=DY[d]
 for r in range(12,110,6):
  q=bx(x+a*r,y+b*r,0,3)
  if bl(q) or hit(q):break
 q=(int(min(x+a*10,x+a*r)),int(min(y+b*10,y+b*r)),abs(a)*(r-10)+2,abs(b)*(r-10)+2)
 R(q[0],q[1],q[2],q[3],YL);tr.append(q)

def sp(k):
 for i in range(9):
  u=RI(cx-3,cx+18);v=RI(cy-3,cy+12);t=tt(u,v);a=u%8;b=v%8
  if cx<=u<cx+16 and cy<=v<cy+10:continue
  e=N(u*T+10,v*T+10,(1+2*a if a<2 else 2-2*b)%4,k,0 if k==1 else CH(CC))
  if k>2:
   if t==1:pp.append(e);return
  elif t<1 and (a<2)!=(b<2):
   for o in cs:
    if ov(B(e),B(o)):break
   else:cs.append(e);return

def at(c):
 x,y,d=c[:3];a=bx(x+DX[d]*16,y+DY[d]*16,0,3)
 for o in cs+[P]:
  if o is not c and ov(a,B(o)) and (o[3] or o[2]==d) and RD()<.98:return
 u=x//T;v=y//T
 if x%T==10==y%T and u%8<2 and v%8<2:
  o=[]
  for n in(d,(d+1)%4,(d+3)%4):
   if (n==d or (v,u)[n%2]%8==(1,0,0,1)[n]) and tt(u+DX[n],v+DY[n])<1:o.append(n)
  d=d if d in o and RD()<.6 else CH(o) if o else d^2
 c[0]=x+DX[d]*2;c[1]=y+DY[d]*2;c[2]=d

def ap(c):
 global dead
 x,y,d=c[:3];dx=P[0]-x;dy=P[1]-y;p=2*(dx<0);q=1+2*(dy<0);s=2+wl*.4
 if abs(dy)>abs(dx):p,q=q,p
 if not wl:p=q=d
 c[6]-=1
 for n in((d,) if c[6]>0 or DX[d]*dx+DY[d]*dy>12 else ())+(p,q,q^2,p^2):
  a=x+DX[n]*s;b=y+DY[n]*s
  if not bl(bx(a,b,n,1)):
   if n!=p and n!=q and c[6]<1:c[6]=15
   c[0]=a;c[1]=b;c[2]=n;break
 if wl and ov(B(c),B(P)):
  if not pc:dead='BUSTED'
  hu(P,3);c[0]=x;c[1]=y

def ad(p):
 x,y,d=p[:3]
 if RD()<.02:d=RI(0,3)
 a=x+DX[d];b=y+DY[d]
 if bl(bx(a,b,0,3),tt(int(x)//T,int(y)//T)):d=RI(0,3)
 else:p[0]=a;p[1]=b
 p[2]=d
""")
exec("""
def ok():
 global P,pc,ht
 if pc:
  for a,b in((0,13),(0,-13),(13,0),(-13,0)):
   if abs(P[5])<1 and not bl(bx(P[0]+a,P[1]+b,0,4)):
    P[5]=0;cs.append(P);P=N(P[0]+a,P[1]+b,P[2],4,YL);pc=0;return
  return
 for c in cs:
  if abs(c[0]-P[0])+abs(c[1]-P[1])<24:
   ht+=(8,40,0)[c[3]];rm(cs,c)
   if P[8]:tr.append(P[8])
   c[3]=2;c[5]=0;P=c;pc=1;return

def up():
 global ht
 x,y,d=P[:3];v=P[5];k=-1
 for i in range(4):
  if K(KS[i]):k=i
 if not pc:
  v=0
  if k>=0:d=k;v=2
 elif k==d:v=min(v+.3,5.5)
 elif k==d^2 and v>1:v-=.5
 elif k<0:v*=.93
 elif not bl(bx(x,y,k,2)):d=k;v*=.6
 P[2]=d;P[5]=v;a=x+DX[d]*v;b=y+DY[d]*v;q=bx(a,b,d,P[3])
 if abs(v)<.1:P[5]=0;return
 if bl(q):
  if v>3.5:hu(P,int(v*3))
  P[5]=0;return
 if pc:
  for c in cs:
   if ov(q,B(c)):
    if v>2:hu(c,int(v*8));hu(P,int(v*2))
    ht+=15*(c[3]==1);P[5]=-v*.3;return
  if v>1.5:
   for p in pp[:]:
    if ov(q,B(p)):ki(p)
 P[0]=a;P[1]=b

def dr(e):
 x,y,w,h=e[8];k=e[3];c=e[4];d=e[2]
 if k<3:
  R(x,y,w,h,c or WH)
  if d%2:R(x+1,y+3+7*(d<2),8,3,BK)
  else:R(x+3+7*(d<1),y+1,3,8,BK)
  if not c:R(x+3,y+3,4,4,RE if fr&4 else (0,80,255))
 elif k<5:R(x,y,6,6,c);R(x+2,y+2,2,2,BK)
 else:R(x,y,w,h,(140,0,0) if k<6 else YL if fr&(2 if k<7 else 8) else RE)

def rn():
 global tr
 for b in tr:er(b)
 tr=[];L=fx+pp+cs+[P]
 for e in L:
  n=B(e)
  if not ov(n,(CX,CY,320,200)):n=None
  if e[8] and e[8]!=n:er(e[8])
  e[8]=n
 for e in L:
  if e[8]:dr(e)

def hd():
 global hs
 s=ms
 if mc<1:
  s='$'+str(mo)+' '+'*'*wl+(' C'+str(P[7]) if pc else '')
  if mk:
   x=mk[0]-P[0];y=mk[1]-P[1]
   s+=' '+('N' if y<-30 else 'S' if y>30 else '')+('W' if x<-30 else 'E' if x>30 else '')+str(mm//25)
  s+=' L'+str(lv)
 if s!=hs:hs=s;S(s+' '*(32-len(s)),0,2,WH,BK)

def bg(s,c):F(60,95,200,36,BK);S(s,160-5*len(s),104,c,BK);sleep(2)

def rs():
 global cs,pp,fx,tr,P,pc,ht,dead,mk,mm,cx,cy,hs,mc
 cs=[];pp=[];fx=[];tr=[];P=N(690,410,1,4,YL)
 pc=ht=dead=mc=mk=0;hs='';mm=40;cx=26;cy=15
 F(0,0,320,22,BK);cam(1)
""")
exec("""
cx=cy=CX=CY=fr=cl=wl=mo=0;lv=3;po=1;ms=''
F(0,0,320,222,BK);S('NUMWORKS CITY',95,40,YL,BK)
S('OK: steal car  EXE: shoot',35,100,WH,BK);S('Earn $5000. Press OK',60,150,WH,BK)
while not K(KEY_OK):pass
rs()
while 1:
 t=M();fr+=1;mc-=1;cl-=1;o=K(KEY_OK)
 if o and not po:ok()
 po=o;up();cam()
 for c in cs[:]:
  if c[3]<1:at(c)
  elif c[3]<2:ap(c)
 for p in pp:ad(p)
 for e in fx[:]:
  if e[3]<7:
   e[6]-=1
   if e[6]<1:rm(fx,e)
 if fr%8<1:
  n=[0,0,0]
  for c in cs:n[c[3]]+=1
  if n[0]<5:sp(0)
  if len(pp)<7:sp(3)
  if wl and n[1]<min(wl+1,4):sp(1)
  for l in(cs,pp,fx):
   for e in l[:]:
    if e is not mk and not(CX-90<e[0]<CX+410 and CY-90<e[1]<CY+290):rm(l,e)
 mm-=1
 if mk:
  r=abs(P[0]-mk[0])+abs(P[1]-mk[1])<24
  if r or mm<1:mo+=500*r;ms='PASSED +$500' if r else 'MISSION FAILED';mc=50;rm(fx,mk);mk=0;mm=60
 elif mm<1:
  while 1:
   u=RI(0,65);v=RI(0,41);d=abs(u*T+10-P[0])+abs(v*T+10-P[1])
   if d>400 and tt(u,v)==1:break
  mk=ef(u*T+10,v*T+10,7,1);mm=int(d/3)+250;ms='GET TO THE MARKER';mc=60
 v=0
 for c in cs:
  if c[3]==1 and ov(B(c),(CX,CY,320,200)):v=1
 ht=max(0,min(330,ht-.15*(v<1)));wl=int(ht//60)
 rn()
 if K(KEY_EXE) and cl<1:cl=6;sh()
 hd()
 if mo>=5000:bg('YOU WIN!',YL);break
 if dead:
  bg(dead,RE)
  if dead=='WASTED':lv-=1
  else:mo-=mo//4
  if lv<1:bg('GAME OVER',RE);break
  rs()
 t=M()-t
 if t<.04:sleep(.04-t)
""")
