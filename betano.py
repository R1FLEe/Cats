# Anuncio com confetes: logo Betano, jogador e telemovel (NumWorks)
# OK/EXE: explosao de confetes
# <- ->: vento
from kandinsky import fill_rect as F,draw_string as S
from ion import *
from time import monotonic as M,sleep
from random import randint as RI,choice as CH
K=keydown;WH=(255,255,255);H=222
# fundo: laranja (baixo/esq) -> vermelho (cima/dir), diagonal escura a direita
A=(255,105,20);Z=(232,30,62)
PAL=[(30,18,54),(105,22,80)]+[tuple(A[k]+(Z[k]-A[k])*n//11 for k in range(3)) for n in range(12)]
CO=((255,230,0),(0,210,255),(90,235,120),(255,255,255),(180,110,255),(255,160,210))
# logo: letras B e t a n o, 5x7, 1 bit por pixel
L=((30,17,17,30,17,17,30),(0,0,14,17,31,16,15),(8,8,30,8,8,9,6),
   (0,0,14,1,15,17,15),(0,0,30,17,17,17,17),(0,0,14,17,17,17,14))
P=6;X0=14;Y0=20
# jogador (pixel art 2x2): por linha, trios (x,comprimento,cor) com chr(v+40)
PP=((232, 178, 140), (192, 130, 98), (56, 38, 28), (244, 244, 248), (196, 198, 212), (255, 100, 20), (38, 38, 76), (24, 24, 50), (26, 26, 26), (112, 22, 32), (48, 30, 24))
PR=(
'/*(Q*(','.,(P,(','-)(.))/,(?-*O,(S))T)(','-*)/,(=0*O,(S*)',
'-+)0+(<2*O+(R+)','-,)1*(<2*O+(R+)','.*)0+(<+*?,(C+*O+(R*)',
'.)(/))0+(<)*=/(D))E**O+(R))S)(','/))0+(<)(=*2?,(C*2E))F)*O+(R))',
'/*)1*(;))<+(?)2@*(B)2C*(E*)O*(Q*)','/*)1*(;*)=,(A))B+(E*)O*(Q*)',
'/*)1*(;*)=,(A))B+(E*)O*(Q*)','/*)1*(;))<,(@*1B*(D+)O*(Q*)',
'/)(0))1+(<))=*(?,+C)(D*)N+(Q))R)(','/)(0*)2+(=))>)(?,1C*)M+(P*)R)(',
'0)(1*)3+(>))?,1C*)M*(O+)R)(','0)(1*)3+(>))?,1C))L+(O*)Q)(',
'1)(2*)4+(7)->.)J)-K+(N*)P)(','2)(3*)5+->.)J+-M*)O)(',
'2)(3))4*-6++>.)I++L*-N))O)(','2+-5-+>.)H-+M+-','3/+=)->.)D)-H/+',
'42+>)-?,(C)-D2+','43+?)-@+(C*+E),F0+','52+?)-@*(B)-C*+E*,G.+',
'6,+:)(;-+@*-B++E+,H,+','6,+:+-=0+E-,J*+','7++:+-=0+E.,','7,+;)-<1+E.,',
'85+E.,','85+E-,','85+E-,','85+E-,','85+E-,','85+E-,','84+D.,','84+D.,',
'84+D.,','84+D.,','84+D.,','93+D.,','93+D-,','93+D-,','93+D-,','93+D-,I)/',
'8).93+D-,I)/','84.D./','84.D./','84.D./','84.D//','75.D//','75.D//',
'75.D//','75.D//','71.B*.D0/','70-?).B).C0-','9+(<*)>)-C)-D+(G+)',
'9+(<*)D,(H*)','8,(<*)E+(H*)J)(','8+(;+)E+(H+)','8)(9*-;*)E*(G+-J))',
'8,-<)(F--','8--F--','8--F--','8)+9+-<)+G+-J)+','8-+G,+','8,+G,+',
'8,+G)+H,0','7-0F/0','6/0F/0','7-0H,0','',)
PX=40;PY=H-2*len(PR)
# telemovel: retangulos (x,y,w,h,cor) e frases
OG=(255,95,0);SC=(246,246,250)
PH=((217,64,90,158,(80,80,95)),(215,66,94,156,(80,80,95)),(217,66,90,156,(18,18,24)),
    (220,70,84,152,SC),(250,70,24,5,(18,18,24)),(220,76,84,22,OG))
PT=(('APOSTA','DO DIA:','O stor','falta','hoje!','ODD 99.9'),
    ('CERTO:','A mae','manda','arrumar','o quarto','ODD 1.01'),
    ('BONUS:','Wi-Fi da','escola','funciona','ODD','1000.0'),
    ('AO VIVO:','Bateria','da calc','acaba no','teste','ODD 1.50'))
ph=0;DT=[0]*7

def ci(i,j):
 d=i+j*.55
 if d>36:return 0
 if d>33.5:return 1
 return 2+max(0,min(11,int((i-j*.8+8)*11/40)))

def on(c,r):
 i=c//6;j=c%6
 return 0<=i<6 and j<5 and L[i][r]>>(4-j)&1

def txt(y0,y1):
 # marca linhas de texto do telemovel para redesenhar (uma vez por frame)
 for i in range(7):
  y=78+19*i+7*(i>0)
  if y0<y+18 and y1>y:DT[i]=1

def fl():
 for i in range(7):
  if DT[i]:
   DT[i]=0
   if i:S(PT[ph][i-1],222,85+19*i,OG if i in(1,6) else (35,35,45),SC)
   else:S('Betano',232,78,WH,OG)

def fix(x,y,w,h):
 i0=x//8;i1=(x+w-1)//8;j0=y//8;j1=(y+h-1)//8
 for j in range(j0,j1+1):
  for i in range(i0,i1+1):F(i*8,j*8,8,min(8,H-j*8),PAL[ci(i,j)])
 x=i0*8;y=j0*8;w=(i1-i0+1)*8;h=min((j1-j0+1)*8,H-y)
 if x<X0+225 and x+w>X0 and y<Y0+42 and y+h>Y0:
  for r in range(max(0,(y-Y0)//P),min(6,(y+h-1-Y0)//P)+1):
   s=X0+(6-r)*2
   for c in range((x-s-3)//P,(x+w-1-s)//P+1):
    if on(c,r):F(s+c*P,Y0+r*P,P+3,P,WH)
 if x<PX+100 and x+w>PX and y+h>PY:
  for r in range(max(0,(y-PY)//2),min(len(PR)-1,(y+h-1-PY)//2)+1):
   d=PR[r]
   for k in range(0,len(d),3):
    a=PX+2*(ord(d[k])-40);b=min(a+2*(ord(d[k+1])-40),x+w);a=max(a,x)
    if b>a:F(a,PY+2*r,b-a,2,PP[ord(d[k+2])-40])
 if x+w>215 and y+h>64:
  for q in PH:
   a=max(q[0],x);t=max(q[1],y);b=min(q[0]+q[2],x+w);e=min(q[1]+q[3],y+h)
   if b>a and e>t:F(a,t,b-a,e-t,q[4])
  txt(y,y+h)

def new(top):
 # [x,y,vx,vy,cor,tamanho,fase,caixa]
 if top:return [RI(0,315),-RI(5,120),wd,RI(6,16)/10,CH(CO),RI(3,6),RI(0,23),None]
 return [PX+50,PY+20,RI(-40,40)/10,-RI(10,50)/10,CH(CO),RI(3,6),RI(0,23),None]

wd=0
for j in range(28):
 for i in range(40):F(i*8,j*8,8,min(8,H-j*8),PAL[ci(i,j)])
for i in range(6):
 for r in range(7):
  for j in range(5):
   if L[i][r]>>(4-j)&1:F(X0+(i*6+j)*P+(6-r)*2,Y0+r*P,P+3,P,WH)
 sleep(.12)
fix(PX,PY,100,H-PY);sleep(.3)
fix(215,64,96,H-64);fl()
C=[new(1) for i in range(45)];po=0;hint=120;fr=0
while 1:
 t=M();fr+=1
 if K(KEY_LEFT):wd=max(wd-.1,-2)
 if K(KEY_RIGHT):wd=min(wd+.1,2)
 o=K(KEY_OK) or K(KEY_EXE)
 if o and not po:C+=[new(0) for i in range(min(25,80-len(C)))]
 po=o
 if fr%150==0:ph=(ph+1)%len(PT);F(220,100,84,H-100,SC);txt(100,H)
 for p in C:
  if p[7]:fix(p[7][0],p[7][1],p[7][2],p[7][3])
 fl()
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
  else:fix(0,200,320,22);fl()
 t=M()-t
 if t<.03:sleep(.03-t)
