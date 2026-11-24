# Confetes + logo betano (NumWorks)
# OK/EXE: explosao de confetes
# <- ->: vento
from kandinsky import fill_rect as F,draw_string as S
from ion import *
from time import monotonic as M,sleep
from random import randint as RI,choice as CH
BG=(20,24,48);OR=(255,102,0)
CO=((255,60,60),(255,200,0),(60,200,90),(60,140,255),(255,90,200),(255,255,255),(255,140,0))
# letras b e t a n o, 5x7, 1 bit por pixel
L=((16,16,30,17,17,17,30),(0,0,14,17,31,16,15),(8,8,30,8,8,9,6),
   (0,0,14,1,15,17,15),(0,0,30,17,17,17,17),(0,0,14,17,17,17,14))
P=7;X0=37;Y0=70;H=204;K=keydown

def on(c,r):
 i=c//6;j=c%6
 return 0<=i<6 and j<5 and 0<=r<7 and L[i][r]>>(4-j)&1

def fix(x,y,w,h):
 F(x,y,w,h,BG)
 if x<X0+245 and x+w>X0 and y<Y0+49 and y+h>Y0:
  for r in range((y-Y0)//P,(y+h-1-Y0)//P+1):
   for c in range((x-X0)//P,(x+w-1-X0)//P+1):
    if on(c,r):F(X0+c*P,Y0+r*P,P,P,OR)

def new(top):
 # [x,y,vx,vy,cor,tamanho,fase,caixa]
 if top:return [RI(0,315),-RI(5,120),wd,RI(6,16)/10,CH(CO),RI(3,6),RI(0,23),None]
 return [160,95,RI(-40,40)/10,-RI(10,50)/10,CH(CO),RI(3,6),RI(0,23),None]

F(0,0,320,222,BG)
for i in range(6):
 for r in range(7):
  for j in range(5):
   if L[i][r]>>(4-j)&1:F(X0+(i*6+j)*P,Y0+r*P,P,P,OR)
 sleep(.15)
F(0,H,320,1,OR);S('OK: confetes   <- ->: vento',25,H+2,(200,200,210),BG)
wd=0;C=[new(1) for i in range(45)];po=0
while 1:
 t=M()
 if K(KEY_LEFT):wd=max(wd-.1,-2)
 if K(KEY_RIGHT):wd=min(wd+.1,2)
 o=K(KEY_OK) or K(KEY_EXE)
 if o and not po:C+=[new(0) for i in range(min(25,80-len(C)))]
 po=o
 for p in C:
  if p[7]:fix(p[7][0],p[7][1],p[7][2],p[7][3])
 for i in range(len(C)-1,-1,-1):
  p=C[i];p[6]+=1
  p[2]+=(wd-p[2])*.05;p[3]=min(p[3]+.08,1+p[5]*.15)
  p[0]+=p[2]+(.7 if p[6]%24<12 else -.7);p[1]+=p[3]
  if p[1]>H or p[0]<-10 or p[0]>330:
   if len(C)>45:C.pop(i)
   else:C[i]=new(1)
   continue
  s=p[5];w,h=(s,2) if p[6]//6%2 else (2,s)
  x=int(p[0]);y=int(p[1]);a=max(x,0);b=max(y,0);w=min(x+w,320)-a;h=min(y+h,H)-b
  if w>0 and h>0:F(a,b,w,h,p[4]);p[7]=(a,b,w,h)
  else:p[7]=None
 t=M()-t
 if t<.03:sleep(.03-t)
