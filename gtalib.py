# NUMWORKS CITY: map + drawing (needs gta.py, gtaai.py)
from kandinsky import fill_rect as F,draw_string as S
from ion import *
from time import monotonic as M,sleep
from random import randint as RI,random as RD,choice as CH
class Z:pass
g=Z()
# e=[x,y,dir,kind,color,speed,timer,hp,box]
# kind:0 car,1 cop,2 your car,3 man,4 you,5 blood,6 boom,7 marker
T=20;DX=(1,0,-1,0);DY=(0,1,0,-1)
YL=(255,220,0);WH=(240,240,240);BK=(0,0,0);RE=(255,40,40)
BL=((160,80,70),(110,110,150),(180,150,100),(90,130,120))
BD=((80,40,35),(55,55,75),(90,75,50),(45,65,60))
TC=((70,70,75),(170,170,165),0,(70,150,60),(40,90,200),(70,150,60))
CC=((200,30,30),(30,90,200),(30,160,60),(120,40,160),(20,20,20))
HS=(0,0,0,3,3,4,9,8)
K=keydown;KS=(KEY_RIGHT,KEY_DOWN,KEY_LEFT,KEY_UP)

def tt(x,y):
 a=x%8;b=y%8
 if x<0 or y<0 or x>65 or y>41:return 4
 if a<2 or b<2:return 0
 if a in(2,7) or b in(2,7):return 1
 if (x//8*2+y//8*3)%5:return 2
 return 5 if a in(3,6) and b in(3,6) else 3

def tl(u,v):
 x=(u-g.cx)*T;y=(v-g.cy)*T+22;t=tt(u,v);a=u%8;b=v%8;i=(u//8+v//8*3)%4
 F(x,y,T,T,TC[t] or BD[i])
 if t<1:
  if a<2<=b:F(x+18-18*a,y+5,2,10,YL)
  if b<2<=a:F(x+5,y+18-18*b,10,2,YL)
 elif t==2:
  a=3*(a==3)-3*(a==6);b=3*(b==3)-3*(b==6)
  F(x+max(a,0),y+max(b,0),T-abs(a),T-abs(b),BL[i])
 elif t>4:F(x+3,y+3,14,14,(30,95,35))

def R(x,y,w,h,c):
 x-=g.CX;y-=g.CY
 if x<0:w+=x;x=0
 if y<0:h+=y;y=0
 w=min(w,320-x);h=min(h,200-y)
 if w>0 and h>0:F(x,y+22,w,h,c)

def N(x,y,d,k,c=0):return [x,y,d,k,c,0,0,100,None]

def bx(x,y,d,k):
 x=int(x);y=int(y)
 if k<3:return (x-8,y-5,16,10) if d%2<1 else (x-5,y-8,10,16)
 r=HS[k];return (x-r,y-r,2*r,2*r)

def B(e):return bx(e[0],e[1],e[2],e[3])

def bl(b,r=0):
 for u in(b[0],b[0]+b[2]-1):
  for v in(b[1],b[1]+b[3]-1):
   t=tt(u//T,v//T)
   if t in(2,4,5) or r and t<1:return 1

def ov(a,b):return a[0]<b[0]+b[2] and b[0]<a[0]+a[2] and a[1]<b[1]+b[3] and b[1]<a[1]+a[3]

def er(b):
 cx=g.cx;cy=g.cy
 for v in range(max(b[1]//T,cy),min((b[1]+b[3]-1)//T,cy+9)+1):
  for u in range(max(b[0]//T,cx),min((b[0]+b[2]-1)//T,cx+15)+1):tl(u,v)

def AL():return g.fx+g.pp+g.cs+[g.P]

def cam(f=0):
 cx=g.cx;cy=g.cy;u=int(g.P[0])//T-cx;v=int(g.P[1])//T-cy
 a=max(-1,min(51,cx+(u-11 if u<4 else u-4 if u>11 else 0)))
 b=max(-1,min(33,cy+(v-6 if v<3 else v-3 if v>6 else 0)))
 if f or a!=cx or b!=cy:
  g.cx=a;g.cy=b;g.CX=a*T;g.CY=b*T;g.tr=[]
  for i in range(160):tl(a+i%16,b+i//16)
  for e in AL():e[8]=None

def rm(l,e):
 for i in range(len(l)):
  if l[i] is e:
   l.pop(i)
   if e[8]:g.tr.append(e[8])
   return 1

def ef(x,y,k,t):
 e=N(x,y,0,k);e[6]=t;g.fx.append(e);return e

def dr(e):
 x,y,w,h=e[8];k=e[3];c=e[4];d=e[2];f=g.fr
 if k<3:
  R(x,y,w,h,c or WH)
  if d%2:R(x+1,y+3+7*(d<2),8,3,BK)
  else:R(x+3+7*(d<1),y+1,3,8,BK)
  if not c:R(x+w//2-2,y+h//2-2,4,4,RE if f&4 else (0,80,255))
 elif k<5:R(x,y,6,6,c);R(x+2,y+2,2,2,BK)
 else:R(x,y,w,h,(140,0,0) if k<6 else YL if f&(2 if k<7 else 8) else RE)

def rn():
 for b in g.tr:er(b)
 g.tr=[];L=AL();V=(g.CX,g.CY,320,200)
 for e in L:
  n=B(e)
  if not ov(n,V):n=None
  if e[8] and e[8]!=n:er(e[8])
  e[8]=n
 for e in L:
  if e[8]:dr(e)
