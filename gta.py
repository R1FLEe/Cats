# NUMWORKS CITY - top-down crime game
from kandinsky import fill_rect as F,draw_string as S
from ion import *
from time import monotonic as mono,sleep
from random import randint as RI,random as RD,choice
from math import atan2

T=20;VW=16;VH=10;HY=22;W=66;H=42;GOAL=5000
DX=(1,0,-1,0);DY=(0,1,0,-1)
KS=(KEY_RIGHT,KEY_DOWN,KEY_LEFT,KEY_UP)
ROAD=(70,70,75);SIDE=(170,170,165);SEAM=(145,145,140)
GRASS=(70,150,60);TREE=(30,95,35);WATER=(40,90,200)
LINE=(235,200,40);WH=(240,240,240);BK=(0,0,0)
RED=(255,40,40);GLASS=(40,50,80);YEL=(255,220,0)
BLD=((160,80,70),(110,110,150),(180,150,100),(90,130,120),(150,110,150),(130,100,80))
BLDD=tuple(tuple(v*3//5 for v in c) for c in BLD)
CC=((200,30,30),(30,90,200),(230,180,20),(30,160,60),(120,40,160),(20,20,20))
PC=((60,60,200),(200,60,60),(60,160,60),(220,140,40),(90,90,90),(240,240,240))
SOL=(2,4,5)
HS=(8,8,8,3,3,3,3,4,9,2,8)
# kinds: 0 traffic 1 police 2 parked/player car 3 ped 4 player
# 6 target 7 blood 8 boom 9 bullet 10 marker

class E:
  def __init__(s,x,y,d,k,c=None):
    s.x=x;s.y=y;s.d=d;s.k=k;s.c=c
    s.v=0;s.t=0;s.hp=100;s.ob=None;s.nb=None

def tt(x,y):
  if x<0 or y<0 or x>=W or y>=H:return 4
  a=x%8;b=y%8
  if a<2 or b<2:return 0
  if a==2 or a==7 or b==2 or b==7:return 1
  if (x//8*7+y//8*13)%5==0:
    return 5 if a in(3,6) and b in(3,6) else 3
  return 2

def tile(tx,ty):
  x=(tx-cx)*T;y=(ty-cy)*T+HY;t=tt(tx,ty);a=tx%8;b=ty%8
  if t==0:
    F(x,y,T,T,ROAD)
    if a<2 and b>1:
      if b==2 or b==7:
        for i in(2,8,14):F(x+i,y+6,3,8,WH)
      else:F(x+18-18*a,y+5,2,10,LINE)
    elif b<2 and a>1:
      if a==2 or a==7:
        for i in(2,8,14):F(x+6,y+i,8,3,WH)
      else:F(x+5,y+18-18*b,10,2,LINE)
  elif t==1:
    F(x,y,T,T,SIDE);F(x+19,y,1,T,SEAM);F(x,y+19,T,1,SEAM)
  elif t==2:
    i=(tx//8*3+ty//8*5)%6;d=BLDD[i]
    F(x,y,T,T,BLD[i])
    if a==3:F(x,y,3,T,d)
    if a==6:F(x+17,y,3,T,d)
    if b==3:F(x,y,T,3,d)
    if b==6:F(x,y+17,T,3,d)
    if a==4 and b==4:F(x+6,y+6,12,12,(105,105,105))
  elif t==4:
    F(x,y,T,T,WATER);F(x+3+ty%2*8,y+9,8,2,(90,140,230))
  else:
    F(x,y,T,T,GRASS)
    if t==5:F(x+4,y+2,12,16,TREE);F(x+2,y+4,16,12,TREE)

def R(x,y,w,h,c):
  x-=CX;y-=CY
  if x<0:w+=x;x=0
  if y<0:h+=y;y=0
  if x+w>320:w=320-x
  if y+h>200:h=200-y
  if w>0 and h>0:F(x,y+HY,w,h,c)

def bc(x,y,d):
  x=int(x);y=int(y)
  return (x-8,y-5,16,10) if d%2==0 else (x-5,y-8,10,16)
def bp(x,y):return (int(x)-3,int(y)-3,6,6)
def bb(e):
  if e.k<3:return bc(e.x,e.y,e.d)
  r=HS[e.k];return (int(e.x)-r,int(e.y)-r,2*r,2*r)
def cor(b):
  x,y,w,h=b;a=x//T;c=(x+w-1)//T;e=y//T;f=(y+h-1)//T
  return tt(a,e),tt(c,e),tt(a,f),tt(c,f)
def blk(b):
  for t in cor(b):
    if t in SOL:return 1
  return 0
def ov(a,b):
  return a[0]<b[0]+b[2] and b[0]<a[0]+a[2] and a[1]<b[1]+b[3] and b[1]<a[1]+a[3]

def er(b):
  x,y,w,h=b
  for ty in range(max(y//T,cy),min((y+h-1)//T,cy+VH-1)+1):
    for tx in range(max(x//T,cx),min((x+w-1)//T,cx+VW-1)+1):tile(tx,ty)

def full():
  global trash
  for ty in range(cy,cy+VH):
    for tx in range(cx,cx+VW):tile(tx,ty)
  for e in fxs+peds+cars+bul:e.ob=None
  P.ob=None;trash=[]

def cam(f=0):
  global cx,cy,CX,CY,VR
  tx=int(P.x)//T;ty=int(P.y)//T;nx=cx;ny=cy;rx=tx-cx;ry=ty-cy
  if rx<4:nx=tx-11
  elif rx>11:nx=tx-4
  if ry<3:ny=ty-6
  elif ry>6:ny=ty-3
  nx=max(-1,min(W-VW+1,nx));ny=max(-1,min(H-VH+1,ny))
  if f or nx!=cx or ny!=cy:
    cx=nx;cy=ny;CX=cx*T;CY=cy*T;VR=(CX,CY,320,200);full()

def rm(l,e):
  if e in l:
    l.remove(e)
    if e.ob:trash.append(e.ob)

def fx(x,y,k,t):
  e=E(x,y,0,k);e.t=t;fxs.append(e);return e

def side(x,y):
  for o in((0,13),(0,-13),(13,0),(-13,0),(0,20),(20,0)):
    if not blk(bp(x+o[0],y+o[1])):return x+o[0],y+o[1]

def hurt(c,n):
  global dead,money,heat
  if c.hp<=0:return
  c.hp-=n
  if c.hp>0:return
  fx(c.x,c.y,8,14)
  if c is P:dead='WASTED';return
  rm(cars,c);money+=50
  heat+=60 if c.k==1 else 25

def kill(p):
  global money,heat
  if p not in peds:return
  rm(peds,p);fx(p.x,p.y,7,250);money+=10;heat+=20
  if p is mk:endm(1000)

def endm(r):
  global mt,md,mk,money,msg,msgt
  if mk:rm(fxs,mk);rm(peds,mk)
  mk=None;mt=-1;md=60;msgt=50
  if r:money+=r;msg='MISSION PASSED +$'+str(r)
  else:msg='MISSION FAILED'

def newm():
  global mt,mk,mtime,msg,msgt
  while 1:
    tx=RI(0,W-1);ty=RI(0,H-1)
    if tt(tx,ty)==1:
      x=tx*T+10;y=ty*T+10;dd=abs(x-P.x)+abs(y-P.y)
      if dd>400:break
  mt=RI(0,2);mtime=int(dd/3)+250;msgt=60
  if mt==1:mk=E(x,y,0,6);peds.append(mk)
  else:mk=fx(x,y,10,1)
  msg=('DELIVER A CAR HERE','KILL THE TARGET','GET HERE FAST')[mt]

def mission():
  global md,mtime
  if mt<0:
    md-=1
    if md<=0:newm()
    return
  mtime-=1;d=abs(P.x-mk.x)+abs(P.y-mk.y)
  if mt==0 and pc and d<26:endm(700)
  elif mt==2 and d<20:endm(400)
  elif mtime<=0:endm(0)

def spot(car):
  for i in range(8):
    tx=RI(cx-3,cx+VW+2);ty=RI(cy-3,cy+VH+2)
    if cx<=tx<cx+VW and cy<=ty<cy+VH:continue
    t=tt(tx,ty);a=tx%8;b=ty%8;x=tx*T+10;y=ty*T+10
    if car:
      if t or (a<2)==(b<2):continue
      d=1+2*a if a<2 else 2-2*b;r=bc(x,y,d)
      for o in cars:
        if ov(r,bb(o)):break
      else:return x,y,d
    elif t==1:return x,y,RI(0,3)

def spawn():
  n=0;np=0
  for c in cars:
    if c.k==0:n+=1
    if c.k==1:np+=1
  if n<5:
    s=spot(1)
    if s:c=E(s[0],s[1],s[2],0,choice(CC));c.hp=60;cars.append(c)
  if len(peds)<7:
    s=spot(0)
    if s:peds.append(E(s[0],s[1],s[2],3,choice(PC)))
  if wl and np<min(wl+1,4):
    s=spot(1)
    if s:c=E(s[0],s[1],s[2],1,0);c.hp=80;cars.append(c)

def desp():
  ax=CX-90;ay=CY-90
  for l in(cars,peds,fxs):
    for e in l[:]:
      if e is not mk and not(ax<e.x<ax+500 and ay<e.y<ay+380):rm(l,e)

def ai_t(c):
  d=c.d
  if c.t>=0:
    a=(c.x+DX[d]*15-6,c.y+DY[d]*15-6,12,12);k=ov(a,bb(P))
    if not k:
      for o in cars:
        if o is not c and ov(a,bb(o)):k=1;break
    if k:
      c.t+=1
      if c.t>45:c.t=-30
      return
  else:c.t+=1
  x=c.x;y=c.y
  if x%T==10 and y%T==10:
    tx=x//T;ty=y//T
    if tx%8<2 and ty%8<2:
      o=[]
      for n in(d,(d+1)%4,(d+3)%4):
        if n!=d and (ty,tx)[n%2]%8!=(1,0,0,1)[n]:continue
        if tt(tx+DX[n],ty+DY[n])==0:o.append(n)
      if o:c.d=d if d in o and RD()<.6 else choice(o)
      else:c.d=(d+2)%4
  c.x+=DX[c.d]*2;c.y+=DY[c.d]*2

def ai_p(c):
  global dead
  dx=P.x-c.x;dy=P.y-c.y;d=c.d;p=s=-1
  if wl:
    sp=2.6+wl*.3
    if abs(dx)>abs(dy):p=0 if dx>0 else 2;s=1 if dy>0 else 3
    else:p=1 if dy>0 else 3;s=0 if dx>0 else 2
    o=(p,s,d,(s+2)%4,(p+2)%4)
    if c.t>0 or DX[d]*dx+DY[d]*dy>12:o=(d,)+o
    if c.t>0:c.t-=1
  else:sp=2;o=(d,(d+1)%4,(d+3)%4,(d+2)%4)
  for n in o:
    x=c.x+DX[n]*sp;y=c.y+DY[n]*sp
    if not blk(bc(x,y,n)):
      if wl and n!=p and n!=s and c.t<=0:c.t=15
      c.x=x;c.y=y;c.d=n;break
  if wl and ov(bb(c),bb(P)):
    if pc:
      hurt(P,3);x=c.x-DX[c.d]*8;y=c.y-DY[c.d]*8
      if not blk(bc(x,y,c.d)):c.x=x;c.y=y
    else:dead='BUSTED'

def ai_d(p):
  sp=1
  if p.t>0:p.t-=1;sp=2
  if RD()<.02:p.d=RI(0,3)
  x=p.x+DX[p.d]*sp;y=p.y+DY[p.d]*sp
  r=p.t or tt(int(p.x)//T,int(p.y)//T)==0
  for t in cor(bp(x,y)):
    if t in SOL or t==0 and not r:p.d=RI(0,3);return
  p.x=x;p.y=y

def ai_b(b):
  global heat
  b.t-=1;b.x+=DX[b.d]*7;b.y+=DY[b.d]*7;r=bb(b)
  if b.t<0 or blk(r):rm(bul,b);return
  for p in peds:
    if ov(r,bb(p)):kill(p);rm(bul,b);return
  for c in cars:
    if ov(r,bb(c)):
      heat+=20 if c.k==1 else 5;hurt(c,25);rm(bul,b);return

def fire():
  global cool
  cool=6;b=E(P.x+DX[P.d]*11,P.y+DY[P.d]*11,P.d,9);b.t=22;bul.append(b)
  for p in peds:
    if abs(p.x-P.x)+abs(p.y-P.y)<120:p.t=80

def toggle():
  global P,pc,heat
  if pc:
    if abs(P.v)<1:
      s=side(P.x,P.y)
      if s:P.v=0;cars.append(P);P=E(s[0],s[1],P.d,4,YEL);pc=0
    return
  c=None;bd=24
  for o in cars:
    d=abs(o.x-P.x)+abs(o.y-P.y)
    if d<bd:c=o;bd=d
  if c:
    if c.k<2:
      s=side(c.x,c.y)
      if s:q=E(s[0],s[1],RI(0,3),3,choice(PC));q.t=150;peds.append(q)
      heat+=40 if c.k==1 else 8
    cars.remove(c)
    if P.ob:trash.append(P.ob)
    c.k=2;c.v=0;c.t=0;P=c;pc=1

def upd_p():
  global heat
  if not pc:
    dx=K(KEY_RIGHT)-K(KEY_LEFT);dy=K(KEY_DOWN)-K(KEY_UP)
    if dx:P.d=1-dx
    elif dy:P.d=2-dy
    if dx and not blk(bp(P.x+dx*2,P.y)):P.x+=dx*2
    if dy and not blk(bp(P.x,P.y+dy*2)):P.y+=dy*2
    return
  kd=-1;d=P.d
  for i in range(4):
    if K(KS[i]):kd=i;break
  if kd==d:P.v=min(P.v+.3,5.5)
  elif kd==(d+2)%4 and P.v>1:P.v-=.5
  elif kd>=0:
    if not blk(bc(P.x,P.y,kd)):P.d=kd;P.v*=.6
  else:P.v*=.93
  if abs(P.v)<.1:P.v=0;return
  v=abs(P.v);x=P.x+DX[P.d]*P.v;y=P.y+DY[P.d]*P.v;b=bc(x,y,P.d)
  if blk(b):
    if v>3.5:hurt(P,int(v*3))
    P.v=0;return
  for c in cars:
    if ov(b,bb(c)):
      if v>2:hurt(c,int(v*8));hurt(P,int(v*2))
      if c.k==1:heat+=15
      P.v=-P.v*.3;return
  P.x=x;P.y=y
  if v>1.5:
    for p in peds[:]:
      if ov(b,bb(p)):kill(p)

def draw(e):
  x,y,w,h=e.nb;k=e.k;c=e.c
  if k<3:
    R(x,y,w,h,c or WH);d=e.d
    if d==0:R(x+w-6,y+1,3,h-2,GLASS);R(x+2,y+1,2,h-2,GLASS)
    elif d==2:R(x+3,y+1,3,h-2,GLASS);R(x+w-4,y+1,2,h-2,GLASS)
    elif d==1:R(x+1,y+h-6,w-2,3,GLASS);R(x+1,y+2,w-2,2,GLASS)
    else:R(x+1,y+3,w-2,3,GLASS);R(x+1,y+h-4,w-2,2,GLASS)
    if not c:R(x+w//2-2,y+h//2-2,4,4,RED if fr&4 else (0,80,255))
  elif k<7:
    if k==6:c=(255,0,255) if fr&4 else WH
    R(x,y,6,6,c);R(x+2,y+2,2,2,(50,30,10))
  elif k==7:R(x+1,y,6,8,(140,0,0));R(x,y+2,8,4,(140,0,0))
  elif k==8:R(x,y,18,18,(255,140,0) if fr&2 else (230,40,0));R(x+5,y+5,8,8,(255,240,120))
  elif k==9:R(x,y,4,4,(255,255,80))
  else:R(x,y,16,16,LINE if fr&8 else (255,120,0));R(x+4,y+4,8,8,BK)

def render():
  global trash
  for b in trash:er(b)
  trash=[];L=fxs+peds+cars+bul;L.append(P)
  for e in L:
    n=bb(e);e.nb=n if ov(n,VR) else None
    if e.ob and e.ob!=e.nb:er(e.ob)
  for e in fxs:
    if e.nb and e.k!=8:draw(e)
  for l in(peds,cars,(P,),bul,fxs):
    for e in l:
      if e.nb and (l is not fxs or e.k==8):draw(e)
  for e in L:e.ob=e.nb

def dirs(dx,dy):
  return ('E','NE','N','NW','W','SW','S','SE')[int(atan2(-dy,dx)/.7854+8.5)%8]

def hud():
  global hs
  st=''
  if msgt>0:s=msg
  else:
    s='$'+str(money);s+=' '*(12-len(s));st='*'*wl
    s+='C'+str(max(P.hp,0)) if pc else ''
    s+=' '*(17-len(s))
    if mt>=0:s+=dirs(mk.x-P.x,mk.y-P.y)+' '+str(mtime//25)+'s'
    s+=' '*(28-len(s))+'L'+str(lives)
  k=s+st
  if k!=hs:
    hs=k;S(s+' '*(32-len(s)),0,2,WH,BK)
    if st:S(st,70,2,RED,BK)

def big(s,c):
  F(60,95,200,36,BK);S(s,160-5*len(s),104,c,BK);sleep(1.8)

def reset():
  global cars,peds,fxs,bul,trash,P,pc,heat,dead,mt,md,mk,cx,cy,hs,msgt
  cars=[];peds=[];fxs=[];bul=[];trash=[]
  P=E(690,410,1,4,YEL);pc=0;heat=0;dead=0;mt=-1;md=40;mk=None;msgt=0
  cx=26;cy=15;hs=None;F(0,0,320,HY,BK);cam(1)

def title():
  F(0,0,320,222,BK);S('NUMWORKS CITY',95,15,YEL,BK)
  for i,s in enumerate(('ARROWS  walk / drive','OK      steal / exit car','EXE     shoot',
    'Do missions, earn $'+str(GOAL),'Run over people: +$10','Cops come if you go wild!','','Press OK to start')):
    S(s,10,50+i*21,WH,BK)
  while not K(KEY_OK):sleep(.02)
  while K(KEY_OK):sleep(.02)

K=keydown
cx=cy=CX=CY=fr=cool=wl=0;money=0;lives=3;pok=1;VR=(0,0,320,200)
title();reset()
while 1:
  t0=mono();fr+=1
  if msgt>0:msgt-=1
  if cool>0:cool-=1
  ok=K(KEY_OK)
  if ok and not pok:toggle()
  pok=ok
  if K(KEY_EXE) and cool<=0:fire()
  upd_p();cam()
  for c in cars[:]:
    if c.k==0:ai_t(c)
    elif c.k==1:ai_p(c)
  for p in peds[:]:ai_d(p)
  for b in bul[:]:ai_b(b)
  for e in fxs[:]:
    if e.k!=10:
      e.t-=1
      if e.t<=0:rm(fxs,e)
  if fr%8==0:spawn();desp()
  mission()
  pv=0
  for c in cars:
    if c.k==1 and ov(bb(c),VR):pv=1;break
  if heat>0 and not pv:heat-=.15
  heat=max(0,min(heat,330));wl=int(heat//60)
  render();hud()
  if money>=GOAL:big('YOU WIN!',YEL);break
  if dead:
    big(dead,RED)
    if dead=='WASTED':lives-=1
    else:money-=money//4
    if lives<1:big('GAME OVER',RED);break
    reset()
  t0=mono()-t0
  if t0<.04:sleep(.04-t0)
