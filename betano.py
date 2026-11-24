# Confetes + logo Betano (NumWorks)
# OK/EXE: explosao de confetes
# <- ->: vento
from kandinsky import fill_rect as F,draw_string as S
from ion import *
from time import monotonic as M,sleep
from random import randint as RI,choice as CH
K=keydown;WH=(255,255,255)
# fundo: laranja (baixo/esq) -> vermelho (cima/dir), diagonal escura a direita
A=(255,105,20);Z=(232,30,62)
PAL=[(30,18,54),(105,22,80)]+[tuple(A[k]+(Z[k]-A[k])*n//11 for k in range(3)) for n in range(12)]
CO=((255,230,0),(0,210,255),(90,235,120),(255,255,255),(180,110,255),(255,160,210))
# letras B e t a n o, 5x7, 1 bit por pixel
L=((30,17,17,30,17,17,30),(0,0,14,17,31,16,15),(8,8,30,8,8,9,6),
   (0,0,14,1,15,17,15),(0,0,30,17,17,17,17),(0,0,14,17,17,17,14))
P=6;X0=14;Y0=20;H=222

def ci(i,j):
 d=i+j*.55
 if d>36:return 0
 if d>33.5:return 1
 return 2+max(0,min(11,int((i-j*.8+8)*11/40)))

def on(c,r):
 i=c//6;j=c%6
 return 0<=i<6 and j<5 and L[i][r]>>(4-j)&1

def fix(x,y,w,h):
 i0=x//8;i1=(x+w-1)//8;j0=y//8;j1=(y+h-1)//8
 for j in range(j0,j1+1):
  for i in range(i0,i1+1):F(i*8,j*8,8,min(8,H-j*8),PAL[ci(i,j)])
 x=i0*8;y=j0*8;w=(i1-i0+1)*8;h=(j1-j0+1)*8
 if x<X0+225 and x+w>X0 and y<Y0+42 and y+h>Y0:
  for r in range(max(0,(y-Y0)//P),min(6,(y+h-1-Y0)//P)+1):
   s=X0+(6-r)*2
   for c in range((x-s-3)//P,(x+w-1-s)//P+1):
    if on(c,r):F(s+c*P,Y0+r*P,P+3,P,WH)

def new(top):
 # [x,y,vx,vy,cor,tamanho,fase,caixa]
 if top:return [RI(0,315),-RI(5,120),wd,RI(6,16)/10,CH(CO),RI(3,6),RI(0,23),None]
 return [125,40,RI(-40,40)/10,-RI(10,50)/10,CH(CO),RI(3,6),RI(0,23),None]

fix(0,0,320,H)
for i in range(6):
 for r in range(7):
  for j in range(5):
   if L[i][r]>>(4-j)&1:F(X0+(i*6+j)*P+(6-r)*2,Y0+r*P,P+3,P,WH)
 sleep(.15)
wd=0;C=[new(1) for i in range(45)];po=0;hint=120
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
 if hint:
  hint-=1
  if hint:S('OK: confetes  <- ->: vento',30,200,WH,PAL[0])
  else:fix(0,200,320,22)
 t=M()-t
 if t<.03:sleep(.03-t)
