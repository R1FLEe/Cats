# NUMWORKS CITY - run this one
# also needs scripts gtalib.py and gtaai.py
from gtalib import *
from gtaai import *
GOAL=5000

def up():
 P=g.P;x=P[0];y=P[1];d=P[2];v=P[5]
 if not g.pc:
  a=K(KEY_RIGHT)-K(KEY_LEFT);b=K(KEY_DOWN)-K(KEY_UP)
  if a:d=1-a
  elif b:d=2-b
  if not bl(bx(x+a*2,y,0,4)):x+=a*2
  if not bl(bx(x,y+b*2,0,4)):y+=b*2
  P[0]=x;P[1]=y;P[2]=d;return
 k=-1
 for i in range(4):
  if K(KS[i]):k=i
 if k==d:v=min(v+.3,5.5)
 elif k==(d+2)%4 and v>1:v-=.5
 elif k<0:v*=.93
 elif not bl(bx(x,y,k,2)):d=k;v*=.6
 P[2]=d;P[5]=v;a=x+DX[d]*v;b=y+DY[d]*v;q=bx(a,b,d,2)
 if abs(v)<.1:P[5]=0;return
 if bl(q):
  if v>3.5:hu(P,int(v*3))
  P[5]=0;return
 for c in g.cs:
  if ov(q,B(c)):
   if v>2:hu(c,int(v*8));hu(P,int(v*2))
   g.ht+=15*(c[3]==1);P[5]=-v*.3;return
 P[0]=a;P[1]=b
 if v>1.5:
  for p in g.pp[:]:
   if ov(q,B(p)):ki(p)

def hd():
 P=g.P;mk=g.mk;s=g.ms
 if g.mc<1:
  s='$'+str(g.mo);s+=' '*(12-len(s))+('C'+str(P[7]) if g.pc else '');s+=' '*(17-len(s))
  if mk:
   x=mk[0]-P[0];y=mk[1]-P[1]
   s+=('N' if y<-30 else 'S' if y>30 else '')+('W' if x<-30 else 'E' if x>30 else '')+' '+str(g.mm//25)
  s+=' '*(28-len(s))+'L'+str(g.lv)
 if s+str(g.wl)!=g.hs:
  g.hs=s+str(g.wl);S(s+' '*(32-len(s)),0,2,WH,BK)
  if g.mc<1:S('*'*g.wl,70,2,RE,BK)

def bg(s,c):F(60,95,200,36,BK);S(s,160-5*len(s),104,c,BK);sleep(2)

def rs():
 g.cs=[];g.pp=[];g.fx=[];g.tr=[];g.P=N(690,410,1,4,YL)
 g.pc=g.ht=g.dead=g.mc=g.hs=g.mk=0;g.mm=40;g.cx=26;g.cy=15
 F(0,0,320,22,BK);cam(1)

def mis():
 P=g.P;mk=g.mk;g.mm-=1
 if mk:
  r=abs(P[0]-mk[0])+abs(P[1]-mk[1])<24
  if r or g.mm<1:
   g.mo+=500*r;g.ms='PASSED +$500' if r else 'MISSION FAILED';g.mc=50;rm(g.fx,mk);g.mk=0;g.mm=60
 elif g.mm<1:
  while 1:
   u=RI(0,65);v=RI(0,41);d=abs(u*T+10-P[0])+abs(v*T+10-P[1])
   if d>400 and tt(u,v)==1:break
  g.mk=ef(u*T+10,v*T+10,7,1);g.mm=int(d/3)+250;g.ms='GET TO THE MARKER';g.mc=60

def main():
 g.fr=g.wl=g.mo=0;g.lv=3;g.ms='';po=1;cl=0
 F(0,0,320,222,BK);S('NUMWORKS CITY',95,30,YL,BK)
 S('OK: steal car  EXE: shoot',35,90,WH,BK);S('Earn $'+str(GOAL)+'. Press OK',55,150,WH,BK)
 while not K(KEY_OK):pass
 rs()
 while 1:
  t=M();g.fr+=1;g.mc-=1;cl-=1;o=K(KEY_OK)
  if o and not po:ok()
  po=o;up();cam()
  for c in g.cs[:]:
   if c[3]<1:at(c)
   elif c[3]<2:ap(c)
  for p in g.pp:ad(p)
  for e in g.fx[:]:
   if e[3]<7:
    e[6]-=1
    if e[6]<1:rm(g.fx,e)
  if g.fr%8<1:
   n=[0,0,0];V=(g.CX,g.CY)
   for c in g.cs:n[c[3]]+=1
   if n[0]<5:sp(0)
   if len(g.pp)<7:sp(3)
   if g.wl and n[1]<min(g.wl+1,4):sp(1)
   for l in(g.cs,g.pp,g.fx):
    for e in l[:]:
     if e is not g.mk and not(V[0]-90<e[0]<V[0]+410 and V[1]-90<e[1]<V[1]+290):rm(l,e)
  mis();v=0
  for c in g.cs:
   if c[3]==1 and ov(B(c),(g.CX,g.CY,320,200)):v=1
  g.ht=max(0,min(330,g.ht-.15*(v<1)));g.wl=int(g.ht//60)
  rn()
  if K(KEY_EXE) and cl<1:cl=6;sh()
  hd()
  if g.mo>=GOAL:bg('YOU WIN!',YL);return
  if g.dead:
   bg(g.dead,RE)
   if g.dead=='WASTED':g.lv-=1
   else:g.mo-=g.mo//4
   if g.lv<1:bg('GAME OVER',RE);return
   rs()
  t=M()-t
  if t<.04:sleep(.04-t)

main()
