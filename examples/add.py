#!/usr/bin/env python3
"""AGX compute add without Metal.

Workload: out[i] = a[i] + b[i] for 4 float elements (metal_add capture).
Restores captured mappings, submits the decoded IOGPU sequence, then validates the CPU-visible result.
"""
# generated from add.cap — do not edit OPS by hand (2026-10-07 13:42 UTC)

import ctypes
import ctypes.util
import base64
import os
import platform
import struct
import sys
import time
import zlib
from dataclasses import dataclass, field

WORKLOAD = "add"
CLIENT_TYPE = 0x100005
EXPECTED = (11.0, 22.0, 33.0, 44.0)  # metal_add.m

MEMORY_RESOURCE = 1
MEMORY_TRAP_AUX = 2
MEMORY_EXPECTED = 3

_MEMORY_IMAGE = zlib.decompress(base64.b85decode(
    'c-rmU4`5W)o%jDUH<@H^NWvt7{Hb7wK@$i`prBv@Lj)EmQef3pR((RmR;^m)(XRFnJB)yY!Zb|9Lc}yiq!2NpHCC<05RoEPDyXem'
    'r6B^MRg1J(aWy>W`@JW~s;%9%zhC!x`hMBTCo^;JoqNwcf0IxXHJ{7DaBk$Fe_Z6C*TZD@syJ?`eJ$L_3!BzlvoN)9IJ7xx@=Tg3'
    '%o}OyvbN-A+V>MDRa{(bq9)O^CO_`k=lyE(V=2ZYGpBe(p-@@Uo8}F%ncZhgUXk5Cd%&i=AvQbY^Rl9mxkGXzGuKV5Feb0{Y`eex'
    'K3Bf~YRG=Sc%pqJ`->G9-)ZEva{JoC>Ak~IdmbZA)gb#`X~mff<t!&pNe$^)-s0X(WQFnu+IMD7nwXnvs^nW!Ris~s=8QWjR5c`|'
    '$IP=|C!8No&Dok8T-(s#3Ofeci!c=#vPbq9W6wQmI-+H%*+WD6ecgz&V{-l3Lp*(+Jut<7p3T#y-7&;wUhB8yyl!|SEyteMNORrw'
    'AzO}76P~?fqP`Nkt}-Wh<^0RLUO8_-@XF*tU9U_U>Ry>LKBTW?4-Bqrg1cfp+p^%CgR9(`tzRckwD;%OSK9Pij(sJ#y1dq387=GF'
    'pseqft;Wjh_u20jUf)&T;mL34Cyq27URi2g)<sdh|D%$9wTw=gc5$Ix{|M8n<uNoA<Pa~&tdv$Mp9$9lN4f55qgOW4zS5v&bls)V'
    'u2(LL2d`A-b-gmXDtP6*vaVOouS$!4?D~VN`m`&Y8Pu$qddIaE<%Z3FxfbQM_Ligle_TtVpQt6#Pt=m=Cu&LbZ&XXVN~~{4OYES0'
    'zdfiQGyikF=qka#eZ7c&qFzKlQ7@vOs29<{s$O(m-*COAEqZ;&+wTwEa_EbPY7eCxTGcTybhNc}99veO_?q;R!;Hz<nDlmfCX};u'
    '=88@7a_gY~IC5mB9Mmk<epR~VO#5F%pQV~i_u3Wq5z$vu^=p-Vl(p`%b#<<Hx@n7yv(M*-(<0YpghJ6+u4y(op{N<r*Mz3Ww6^rk'
    '(bq@xEkF9o0QXAl=qp3@m7Uo!JzB0QS!nVK((N@ARd{msm&)h)$C;AFraaYF=j_P%LOIWpO#58=->ixC^1Rv1wr4#z+TG;VOtKd+'
    'Kh^G+nQ7)`XPN$)6R%E{a+x&Ie$8Dv(S)M23ykTXJE>A$FG-r3RQpYKxT03K)3ez*NzPzy&vY|(MaG%}lhJcZd~9__L4oO8J*C1v'
    'uO9D(jD4lNz<&BTQ)c>m6~>cV<&BF-&P^RI-{;9O`-jJs%X!Z2H{A5^H?2bNlV8zMU`FKTnV>X^sy(kq$dudj$nfmd%*>MaO>6s+'
    'BS(UB`sB8*<UV$msW+$o=d)ZcXSs9IBrVhIkd)Vad&YB57;eif)67eob|7ZUc9L`<W^BeJTM0^*nzGahHkTL^vYESNLezw2*b|zU'
    'c4qkkle==737K(aMy@Bgw(RbvfA&Ac^!wZ_GcWbbNX+aktca!BeJ1MnXV%#7BUAPJ@%FBiMC^UE)oWg4{Ckh5j2P7JuFqc)uQ)+x'
    '4B7prrAe`B4TxwB&`+3IEc=_*)}y79op$E*RDDN2#kAIb^iFDp3F$j>E~fR`qwgI1b-yi@+ocZYn^0LS-=4+Jh?LmkuKMW>x35UO'
    'ACX}~Lu13F2HV<i>=|E|o1-}*BX;zi0q&iln(i2%R+qDax_qf^U%6VB<t(H|m)UcQwx$`an+<XW*^&N}v_AQ^6l?`eO&!r;!u@VM'
    '7#h)L!Y4>JnD7@Q<0jl!vdT`ABr8m~w`9Hv_mcEX_;^XXf6sWZe~);u|8enP|J-=6e@;BuKN=7AKQVsL$o~B$<@4v;l+Txx&zF?X'
    'mz2+!l+Txx&z~RcfBgJl|DLg6{~obm|Kno8{<*PW|D0H`f7Irsu6!=le#qSqy<>B2`!J#5TKa`WbE`v<xy!uB+~ui}xhqm4&1Tcl'
    'J3S)5JS4{&;gyHv*dtAO>qkA}=kw?KQ+HSM%k?Uny>h*(s{d54=7#OL`u4oD?0M(dbIvf~GU;1$O<1n0urN6PdErSJF<V<?oR}L)'
    'w{2-$d8(}watz~T`{T8Lsmjuxv2VGysjfPHOf8Pu8Wr=5{S;ezRkp?&S7Ys5M?Tfn^6N74-0NlT^`MRiN4)gE&_91xU2b-Dx!Kj_'
    'W>=S+U0rT=b-CHq<z`oxn_XRQc6GVg)#YYamz!N(ZgzFK+12G{SC^YzU2b-Dx!Kj_W>=S+U0rT=b-CHq<z`oxn_XRQc6GVg)#YYa'
    'mz!N(ZgzFK`Dk4(YhCJn`p7p@UjG}8XMf#D7L0mF$20H0KAv6XMy6&rR(*Ul>p0r?etgUS&RCZDKXxped~^hBcB9&7jbv?qb|hQ<'
    'XGgMce(FeeP}}$>ZFe#&yDr1dQndx=1=+VuQ(E|R+i!OD4U7K<J>Z|~|60xe|6;AJVfkvhNgIo%hC_MT^7DdlPJ!k~Gid&1uh>io'
    '73%Z9boHP2{1g7Rh7GP)j-8Pm4wXwsnH}<MZMLhdobpUPGe0lLkjV_rFemfISWYAs%SoLdTW;d9|Lz@%ea`cr6iP9hLXTzsy*@uX'
    '6snh!stU`q34Xnn&jddxry2GG{_>f{(*C~n@1Pe=?a<YFW=_P^_1a`o7KBW8pQoyH-QHRsmNkAx*lay$7DoDpL#=kPnfmYqv(>H~'
    'Lo*j|GQlzGPIG&XdRg}zY4;s1HK@o7N4L&33(LP1j&8o%zTUs*Hctwxf1jsveVH{3-(mZz{{6P+>$8zF?XzIT8SHz|gfGjrDf6e9'
    'x`wRtW|^?&Cb<whnvd@t{4`;lW_WUCrrA8qgsa;#Lz{=`&m^`Cla}BAjGa}*TRc<um8xNp8|`W|Bhgl929zZ;6AguCMsYG@X-DCr'
    'Xjw9UX+z<b>Gt{RdSBj;t~S2DU)$<0j+V77OB<eQlBd=hf9v$(raMinWRGV$>{%zHHLc-WO<8i_&WeJa<ps%8YwG>q#ER<%?#z`l'
    'NJf`*6f8GoOR~1alhG+{1v_HJEq7)V3^B=kyXT~h)w%i8>%%)XF6(>e&Z+{_rhRqO)5e^9wioLhGylMRlbpCOH`U}!PfonZGq0MO'
    'nK!?x_iAT~tj}dFTsOv^r<BljHCjS--<@8sB{k!s;3o`|zZK+J^ZEvBd+ENz>tmUol-rY)K`t-XwB>h0UQ~Miy8rb?+u%oR`F-PH'
    'kpH|#vt);f4Zh!tHN9eDrGNBH(_Ui+Z}3e2$xR)la{jLyQ~IVCs~dA)hx{b7?jm=76Q}F>HN9x+2d%ZoyXg0M-DLJ~>LVRR2RAOO'
    'o4uhy_D{~5Qc?Q-cS`CezS=5PBX{&89Yfw~UunywzGR;l%RT)OZ}6MXEUOzETxW9P)T)y24=u@^_=s2fYWvE%vA=EC{l-61G3f2Q'
    'L~`u3c**zQ8In8cgNl;hwy*5^3CB+95l^kvTGV-J?Z(Nb<<wj4ZL1p}oUhz*6TP>(Zeoo-Pn=$(+ty9BcUkrsUGvOj`|4_awPkdj'
    '-M91f)%LaI=o-7{?&_A)Z?ms8jgcR8+2ftQ+P=D@x@od~eye=;^maLpzJHq>e^$AiTHV-&jrw`xFK7?S?T%;kd`3^XFPwO1NZr_d'
    'c^ScV?+hn~4oXg%mY-%{cRzEPc1OE^M|)9ntWEj(@{~1KXL#=nNshfFYA$YHn4CK2>g+iOhR9E<W={TUp8VAAT3a7Fr!7BlV@l`P'
    '#rA7*`j4aLj`r&0=pRMRtL@8@V}F!q*4P~VTAtYxvn9IrfIn$^A~||rd)ABt)t%?<vU??_d3wJRQ&TnTCjZ#vNRC;n+4P8+F6;iL'
    '7IVN4$@y=HnhQ5BOpM;uzD)KT`=bNZlA~YSpQX?Dy{Feb@rpcCRhCFjs*9RhW6x?=o>^UPpWCyWWfs<r-c=?YtDfZr<%zmkyAJr;'
    'LtGj35X-xI23v!NrJiZe;8CqfCOM|AqM)w4pl(c^7G83a9UbqmpD@Lq*{k){EstjGDYE5%r{0(3)Hm&Uv{u(XT4&p;t(}$fsyDJO'
    'zvzO>5^uQ8S<_3rJe$+YOFYl!xU!P?WShzMqWD;wCZ}xPz&&=|6x^$sD}JlPdh~;?pNCcD+sCQ)ak?E}iqf=4oN(Fk+9L-2;pdqh'
    '#kzmKv7|12TRbIZ`~5NF^QCC#jjFKM5+0fv^xQK}n4sCG*rxoHb)^0lW9GW4`WuVqw8xrid#sjsGUgPSme(`Z3^cX=_4&2oYx7(7'
    'M(k{)Wkn>f&}0v}FIQ?zcAvT4a!G$l@H{+4pXas4Q{=wR(fb;{eRD7ZTr)n%`2|xYTVBkVV~^OJvB!R07-=13miV>tM0n94ne`<4'
    '#I-k!hc|TeUYZxFUA3TXkZHNQTS2gOp?SEuc3a__o~eCtL6tq*yEE)N4_7Z}7-(N>T(z|7PSaSuAU{XG+Hs|&+PCMQNRL-sDkb%='
    '@ecWvI)6b&;oG*RMHjV|=x=*Wd0|&>jV?`kGN$I#B*O8&GE24RJl@tgKiIoAd_{i3Uo=I&Z+RtS!9bJr7uhkZys%}Nlv8c^s(kwi'
    '!<HWxGA+C1l|*<!mCR5QMdQ6wv;;$W1^N@LP`Ui5HtYvw6P_`Cs+QgCJ;C##n>9z8mc1DTrKa=BwFhrBEr&AZl$zST2a{3L@>a&0'
    'V$<34BKvyn;rH#Ttntu;`S-~7_Vswrhua3fQQ6eAV%s7u)yeO-mF_QZs(t=l*>^=ZyG`wmJ@Hc0_vwRn-`W-1;!!i`$!i;$%%Bzf'
    '8;WghiH})RHK?Qg?zp$aGfVD$u<6lV!Lht0X`aa`j*r_@Rnp#icgsWF_6#wNk8Y~BCGbRhMX71o<hKtowGX{)k7?U%YN=^_sH1I&'
    'X?dbsYKiF_cZ;0!qr2oxHf7jXyq?>(^zNuHZhW+<<8C>IJtO;$tu0<wUH+ij%JrQi7RWw#x63}w8EcA6<J}vo)|+_IuKbdf<?Czj'
    'oh4VX{^pJn6YqCRyeLt=F7BTjAGkDcUDLvZp10H}`>wZIucoD1YL<Pb*V43bQLxRj1@@d9t2edUPgu6Js;eHwy+y%Z3xmBD>0Y*V'
    ')Z21g7?*ukZK^CZjSJ7txBJ}Yx5`%Wu1^}T&w^6(U*6JtLF<r~YH43~FI!7mR>}4)w{?@2v8vl<yLHy0Exo5z7RJNzExo7aN&TwS'
    'c3`)jm$A*x(t;JIo$H39&kg(7??NKow3X)vEqkD8Is8$}{!V_&A#K@jY0K{OaL|%_e#^D&2VBekrfb=6NXwq@TJ-WYLG8TVwd{Kf'
    'H0>RcmVLKt+4V)XW#95q%kJ6LvTHkfZ?i3X#e#++xz3<v+gkJR-M2Ir*4q2mtSxtyYuQx;XW3f4Vq4p~k6N~^nICJ}Upl5`?+RM>'
    'kiVv7@68xL(A0%p%l7Bycb%{82c>0)7j+aY(vr8IR_kAzZ@2Ag+4A{);z7&y<3Y>r8EVy*ZC7!+dYc`z;P5rB%!<almhM`-Zze>8'
    '7Ji$w>dx;r+8W+@WtFt^4>R_ZN(-0Pep|xU`P%uNo)>NW@R5#n(hIC9HSyb8yu!EZn@p(bwxE8;cXWEiZ^rB^wa>pV?L_NS?T-Cz'
    'rDo8J*V~qDk7a9W-{;@8ZDr7o{T&5n?6QnG1=800ZD<&@FRv-?tqa<E*D<|yL9LzeW<$vyJ5|tQHg4J!JK5Ae*<t&Sv73BT;*Q)o'
    'q1K-LpxgG?Bey)6QD9$Rwn)z83F!km&zfrAZCrL=mA!_iGv?TLpWGv@_K6O;!rl9%4}0SN{3a70x~O8%%dz#g6;zb$s=qVdv%wpD'
    'bNz;<Wv-R3-)4K6+Iv^#mr7qYN7_q=S9(k9y117J&fjfmpX>Pt{aed2*|u@jdA1fcuGrLGDCZ}yukdX<Zd`VAm9*2PL95k1G9FzT'
    'Tz}8RmfqXi3y<~#+VZ>lfyUdmYWwx=5gXS_KhUz?FE8q9(d)a}F(lq+>6YG!*21QqroPy=&z9R{OzZ5qt!kBwa?&sMSrA`k;{N_E'
    'z0Zx6BzkUZ)7rR7YMb^4XIB<B`KG<V?w#<KmgfZT+E44uT40aTRBfVD!;z!!b@qwd<25aGuVyW3)B5Res|f1p#QXwXH3vONSKqNE'
    'O@2@KRKBzo`CAD6J)y2Nv;EEa!Me1;ZWF#H88)r*bMlsj()yF$xeZ03P))+$RaGqQBCEYk{(PaOI%9mX$@R{T7i}^%Ew;WD+qPmB'
    '>)%%NIj^t#P4qf_K5mviZ+R$V^AOW9S^G3ygVoNc$WNYCH8W>U-Xhx~V<pkLbM|R#tUc?3d?|&JXyW|FsscNYtvzdee)fz|>&bGY'
    '<?>GUl}mGTQsteA`H9(Y#APdc2j!hhrh3ce=b{&ejJD#lmgtt*=S<Pp!-wZ&rf6#|$V_>{=8LJp^VjzTtF(tUPYqUW3xZrVC&=|{'
    'rUt7w+na4J&gtwIJ9uM{+Eq^_qdjbU-&35^xN3FVhMbn=84HSYYH!=_c|AG@Jb3WNXzlW?vd!%osY7xamyeHc$cb0mb@67iVS3Nn'
    '`OnzxnyNQT-R=>8XR%lKLF^tAZaVy4P}@Izs-w8A{hso0%RAl17l-19wtB_ySK2LF-s-m5wwQO`v$ehUaA%tx4c>ZJzCZN7tqqOu'
    'd|+F0<6G}nm6|2jJ?JgD;Q_Dl!v`DgGV$wdzw>^qd*g=>wB2RK+R?-w^-BBN2bJA3u6y6hc<Ws+Wc!cK8#c=L{LXvQ+7D;g&uV-p'
    '9=EfRLy>y>xraZH5&f-5rR}$7KiD?-kLI4vtoJ+aj5fV~K+oLPk~sxAiP=-DO0@^>Hs1CZIR_fnMdP#IYb!n2-c<X_ALV>^AF#D{'
    '?EH)c1v!nc9I&H(%Wga02`#y-$+Pd-Pw%{Bo%AwqHC5c@=1%boZGZR2_Uy*pi@ba6xyXEH$%Suw@fjQ22HXC!>BarQIqZnE+vC01'
    'ZL@8Qm+fy@W8yOow3XUfRPEDm%4hG`Z+m>15e_zuPw%fPk<rzTt4l6i>n)jaeY|n^+Kxuk^1O^5@e2=l-rJSgEl<llH)HqPwv-YV'
    'UVC|o{hTFdHO3Q{GzDYgg?6@kusyrwP`5p{Kis=k=Dc=f9&8?d<?=y;?aa32Mce*EwTIW*wYbdxPO<N-?I`)cGl}yjZY!~MwDHiv'
    'hI>rnh7Eee+P&*43PbV33p#p#(3)*h?f&*?jjz0I$Iq4zr4}?EdRvZV@6sT9tm_92-dtg7KU~)#$M@~sdia$~J4!ljU%dBV+dVSc'
    'nNqiZ_P@Q`@D2MJ@~qS(W><Q8w_fpWxpn#n?ERFj3qyAN8ebSn%$}4{DsAas-|V<bdW1_h2G_hhX0O?Fx99d&w^W(WuJ!CbyY;H)'
    'zcFZVYelr>`AGX<JF{9_RT{P9V5+_9r}ufqZ55%!IpZ7ks`nnOvR8d&V{puKS~_~aTc6$d^gg-Hx4NydrTP524twQ$_sJ;nbfn&1'
    '?K|%^4zgEfueK@}U+rr<_Qy-@Yb|^IJbRrx_RBou`8VX)7az#itKG4`!QSf~eyqe~e`Q}>uB9&J;kfOwqW!;dMT5-a>(2QgUes1$'
    '>b|{EUN_0u{a&%1eV80uCF=*tJfz01aa&_c%k8!Y<3;uplXJG}j3l{laa*Zun|gFxn<amUElr&B{-Eyqb1S#yWq-6szr7?e`@oV+'
    '{nWP`ir(`~?kij415K#Zq}E-$wn0Dt%|%t8a?E#QOY3IrZzwuwKmBZX%wH|=j&2!qTgFO$XFq+$n~mAWe){uU?6K#UnAF5s`}Fe@'
    '7rs43dd=jH&9)R~+jo*@%{L~rdr{*2{f*N9*3CG(O6q*_ta0}BO^fQzI#-{M-J7wX#Eji7vw-ZcOh5Bv`HPw-%hPh7$u$!;9Usnn'
    '&gMflU$A-asloFdCkM~hpR3OklSAbtx@w=JzeU=0_{fo+x@r%;2J7>`^i$xN_xaY}VLzG`tkRx{#KxFdnRy~wui2SZF=dY(6Svs$'
    'GgPCiZXHAOS_^eQFYNY<w(9nYtcqYH^tV(LADzkDIiemvxRQmvE3@<`zjj7Fevpja9oaIw4%N#Z$*d_=#ZxMabF;R1-WD_LiD-Lp'
    'MiDb6Bw3gjWbbm##qPH;pXcY-NpERLuCFt^c>N3Znf#tGXX!^*JI}w_w=0#br2U%L+9tD&J{ei^*G?01PS>1Sm<aVTRXumh&szMR'
    'X7}AyS@JW;2}P;;SDe9>hjV&l1;6>2IVmx&_~`b%KCyk*-#N8uxp$R$g_h-TcdzQgo4r1EgM`0efR>y$zM{9S_lfYPN}1nOrJ1sM'
    'sci>tOqt-PWyu`<*wvN(uA#C@exOy^_5OeNCqc1{&sqOMLH!Ho1vMj_^NcH}aLBkCmhjIgFSd=fBg>4oYlUi4UTklCZl>Mb%wC$z'
    '**rJXjLS^;<y!v|*(R21^6czzbH0>KcDA`X(>|}tHRcK9>Ubom<KfWR_S5D{EjF$09ara~uFmCsvd$g*-{-A=o#8tFrK5LS>fO%Z'
    'cOv0vY9ec~-rZbpQG>m^HNoG<1@F{$z0=l5YDw^Wjd0EEf<)+Otw@9yv`KA9_E?~`BN?rzkRCnZZ_`?m?QbnF4t`IP9+Y{qkNxcX'
    '#@%Y?^xmy@j=Qa`SZikR{=9I5v;}{S{aWGo2<h+hwO-zQv|cW#Du{dX$pZ?tURLNQXZu0D?CLdKn<(n4&;5ryRaLOfGZm5GsH0_e'
    'K6|d+Hdj`iXBqkJO{lJCuvMbxg4=^yKP5PNpWx{7w~4i3v(@f1>R>pyq6wpBg+2Mr<G8cC&avOls)A?iQTi>|U3~QK4U=9%kJX`n'
    'ubdbV95I-=XMcIxNu%WNCeN61(g^A0XZHvXkTbg`I~>(dNsLG>AEZZ_RdKSM(S(=da@g!qn<`}tnNZy~oTGd6@7iN%q<m0B_Bb!t'
    'W7Ny}G7@BuaC=-Me*<jysP3<6_n49CKI2lihx|NB=J_A(p=VV+)_q3T7J4ixmD~Gk+G9=V;f_^RQKHA%9~^7)rpglCBi9}4qE8%a'
    'WN==y$GY=Mj!w3P<QPNG(=8Gs()F*-litlzr){mP%@2N>VW01cE=`QuT0TVI4}O|4Z(wbPtyM)Y+pk@J%~{jg_0#L{40r#Eu02cp'
    'iE(Fl)dqVX3+;V8S}WZBJX$-V(}G&xRZ9kJ4QjosE#XmPwJt8aK4XH}T&8z15%eGfYl1c0xLR9JTSg^ij2d@hq(uM5_Qb7v_9I^M'
    'OkOCF9Jtfwre%rYW}W_qp}-VMc8+-I;C$0LaHsv+B$dW)-Xwo?Yd24fGv)GkxXBTTT=P<NdUDis+wDiECyGK^GW`c$&@j+WnzARD'
    'a@nQ-xOSNx$Qorrdfrv`sNM6fG<D<JJ)O4=?8pzwvr_wz&gia<Ns}BuQ`f!OqbI!}e|<O4`{IGKGG{LC(9vX#{H|m~y=S)9FH4S|'
    '<>}n0U%O|XX<e2aX;;h_MQf@C7*k+oR==!!oE(x?5tL8MsG96!N@74wPy%CWgVM{-i}<=#o!u&#w_VoZMTvgF)}5nj4&IoO>{n;^'
    '*}b&xOE0&{1SWAp-hP>lC5OLcx87Zx7<J1gtxIE8?$)}Le?gV)=gQ{wn`QUT9y6m|fAT!)P5ry$&QojT_e}Y<@_VLJe^aKlE`NEM'
    '`Hd;-7<I&&S-t$|XD7aN%ck|VR67T}B+tgw#rsIDIPHQIDeIB$-zS8})rNa%&2O^hP-H7i(?d0jLP!4&xwHT3vY5TPm)pKz-dWn2'
    'zdh3R8<?isOu76+heV-ikJxdiv+y}%&+CNkcKtMNSyO)#&9eP?V(3ntWhYM99*yX4sD7z`wVv>{o2;WVzeK+?Vnz1lrrS-sjCsiu'
    'Ua-YAzt-O414)zUZ;US^-3i-+eWT`pjC9HV&%|@h{LI9F1+%4`I-{GUWW4D?JLn&LQue^09Xv5IBP{hlJSx}qxAM2&(o=T!+uji~'
    'ojtSbuQ1vDwspu}6Gla~M+g@MTkBR0x5`g}8j^Oa?G43$ZmYO%)%F=%Rq0k8cB`IltD>&0hPghyvrkIv6|&W^nBD5BhRm+5Hh0aQ'
    'W>&A&ab&KJGS_zX{GTy?$iKG<{-s0HY7>>eWturDx!aa#tMru%^D^AKot~8Ey#AZc+hOLNuyygyqh%P(+B^FNGw1Ec%;4;2&K~k9'
    'pPAPxBVM@Zbi4mtJ3dx~wRe-Nt4Z1`eae2d=UuOBrJmb#M$;MIuCH#(&)n?UYn`HhGxn5@uh)JwL#!%p3r6DNPZ^09_Re)zljwOy'
    'z09tfR+xIJV@+{WDc7FN-ezmj?U@O0)76<eA0DTF=cDu1o_%EA+NYadLH}S@9Q>Q5qsN_>InkDqoA>8=U7wb1qEbgYy)E|L?CecC'
    'H=CEKrP$lkQatwW_&-beHUj_v000000000000000000000000000000000000000000000000000000000000000000000000000'
    '000000000000000@DC<-hW%1*|7Rbu@_)SR&l_h<y?q?8kGu-%!#|c>b7i;SyHI)9qdfl6^l+Vk?E$BUC=LJs000000000000000'
    '00000;D45syZ*8N*-z?S{IjQjU`H&M|1Q~Rh1_$=r!3FCE}1Ntob=rLlCO?Tyqe;+lWh22$-^mbd&%2gsJ<=5?I*d|N^$#39<Wl~'
    'aU}PSxcS$q?s$@qmt{Vl>W(Y9wc_~uQr+<-$7KBaj#T$Kl5Y*X|A(pW^CTm`7_%(ZeXe9hWWa({_xX}Hb|3p**qw*u8}-?5gx&c_'
    'uHE{zSHkYRBzNXz?F_r~ll)HR_MeB{c}jMBKi(2{=PUU@Ww!^y?z|;07&o;k?9N|uRJioVVRs#p^;XzjkK~K5)zpUFbxD53KX`N4'
    'U7zIJCq4N6u)9vl|2X)<lCZm8$?q=t@}jW2ZpnCFBp!CxFZn@h_YcxsIY|DmWz~O7bLAn~obtclN^|8RIqCkkeQB<IBu^N5b$gmC'
    'C&?dYUHej+D=*2EZ~y$cG*@nt>#m*i%QRPhlKXC&ur1A%qvW@@Uh+hmD^JN*E6tUw=A4<2q`C5yZ1;LSnC8k^^8WH}_oun?mh`$6'
    'Z%lLLF1cX&H#elY@|XOVGxo1bbN4~FZ=QE&n!6v8gC9SwA<f+v$=5E)`B9p?Ka#6k{ncsiK1t5#d*Z4zcfTaBc<C#*q`CVhxp`sj'
    '57ONIlk^|?uqMsjN69NkT%SmD_fv9dYh-DfyRVYf<xSOT?*8iiy6bB<rMdeo`OlHz3)9^Fmi*yWxi_Y{`>w}L_2#F!`!Cu3y_C*$'
    'R}Ul)7N7Kfx~mV8E5}s6o9^m`<fLCcbTHl356KgMTJrmJS5GAGyzkN9rMvnf`Rxst>`!;~Msm=~fqT<k{gKSR{)64=t{zEFz2Nm-'
    '>8?IWzCHVQze#uXN;2iX(2MD=eo6i+HuzWRuAWJrnsw>3>8`#>{^CauJd^I~o#ekQIevS(tACQMr`+_5bXN~0r@fT^WV)-5l9y$!'
    '+>-9<rR2iW(>ABO`YHMR&-QFeclA_qe`)<=>8`#?{!{d_N7G%sl^pQe*q^1l`YZYVnFAh5clB6u*3Y{CG~Lx_$tC;z=5$xDC1+mT'
    '{U_<JeoH?1?1}fLyLv9U<(1R#Nq6;K^1Q*7cc;60FWGU~_wPz~^<U3#%GUMit{rGO#WFOdJ!oz|XKlJ`7n1#cxqeN$YafzlT$H9M'
    '?L@L<=+|#gckM;;L;r;zrMq?`dD7ie>(X8Ok*wUkb#=OHN0N2ln0jlvYfq9d<^OtBx@%XG{?<!Zrn~l~=T#EYly)Y0>A?CG>8`y='
    '-W;2tDeX?n;kb8_>8}0h>py8&p6=SA<i#UrX-a$4^SGgxrnF1_yqPa8OLy&4GIe#s(sb8OC8rF(`g`fFy-HsFUWKN#TglUZ-d9uF'
    'ujEa!Ki!n>+Og#L@QaJmU3-?CecEFS(_OpP`+j)+f^^ruwLX-sx-s3gbIF#+md4Xvd)NE9Y{C3=*X|`_R=R8d={oS6BN5jRNKW4y'
    '`7q-81IbGk_WqBE>lY*k+*f)y;`#^4wlk*vDdPGG$>&q9Jrr^Mg=F#b^?!)CenWEm_nvzv;`$Fw(_K^g5y`#T)8CG`{zS6(@*ln#'
    'as7&9%ACD#L|p%(`&}~X^@!_dBs=E*;I)YBZzMNf@rS(;*Y8OFdf54UBCh|DT)cL3N5u6*l25K5p(*{5<h3Vm_-(}XOL{%OJ4I9a'
    'C&}~PS@&|p^;44ldX;KQe<gWt#ltT~T)!omIDg6u5!ZidIiLC4UqxI$Ci$J$uYW$``ZLMuVZAh^Uz7Y&<l&tW*S|@QJ$v?!i0kJh'
    'pD|gQ(%(t`?7c^}M_j)rIrEfjo{qTwPx6ZEi!`Ml)cf|r-fa=rAL{viaqW{4*Dp%eTz~o2i0dD<Jby4uQ~F6g?`u1sh`9bz%Rhbl'
    '=7{Sz^|)hhe>~#)Ps!ubu5XLDepE7Z`b<sfPxW}2Wt!5jN-i0cqbdEX<nq;r9*wwuR`SAse&vyf>u)8OmT&!8#Pz$9(Q_YoIO6(W'
    'trv@a{7}U8!&)AX-}+$0^~aJwH9z=i#P!RP!-p<=AmaLG$#W(xX^yylTJpJ3OYV=j{#vj9@Y0_|T)!<@^qu5=5!Zi9Zf>r<H{$wn'
    '$#J*dxiRAUbIIEW{N$d9>({lukA1u;;`(>VVf&uHJL39ztuNhww;|&Cd&!KAo~HEslFvSRf~NHUk|Rn-Y05aD?e6`5(UkE(GSce?'
    'O&J#?kN@`SA4lByAo*^;wzUyAPDsA>?(26(+;}1R^$(BJlyO7Lzo=YO#t*#@*IcD3<A@&rmvs#hH=by{8MWi~h#Ob*de?_FWqi^0'
    'd;Dlk8D}JWe(PFI8E+()J=IhfapR7*@3i0D7IEW`*24isnlcVa-g^9Hnlc_~d)?J|Ys8I9+8*Y<T^n)ZljPT){-UOgQ+mCxeM?iu'
    'E6JZf{P@a<8@IGS7?-Un<Cpfk*Ui$DaZI<HzV4QY8_y)?KJ}*+5jU<${&3GEO&Q-LUrFAoDdU{v6FYwYgNPgNw7uOrK~u&($v^&X'
    'wWf@JTJIh?v^?U*K`lRjx~7bWdR|Z6r77d0wtwSm%J``L=<Q$AlyOq)!CgO3MBI3(?Wk9gri`0<pI`l+ri`DGzl<DM8gb*O_PYzt'
    '(UkF2+sX7tz87)hs^m?V7ih}(s_o(FWtuY1YCm-Cd({y)-fB5rFh^6yUCF0oI~GUW_^ad3D`#lRIIR89H}27t@mO-huslr}mnHAb'
    'Pio5eto_00u%?XD+8=%U22B~SwSB$v_JW8Tx3zv<c!{Qr-;!q?e)-0T8^^UgH=Ls><GJ>K*ZndcapSty(`i#QWqg->WW<*F5jW23'
    '{->O&DdWB5eFHYdB5vH*_Lo<#DdWH1pEF`dd^Zn}ymNHC(|7X$$wg(0KJ?wZK=S^cOF!`4{6KQ<z90OD@8$`TC*F43`@WkmNEQ!Y'
    'f7o~P2Fd)j54`8Q`Ge%@x1RWu@8%JbXN7<LuJ7g(`Z=$?e#m$83dwj)=O2AHzmR<Ta1TwHXGs3G{}4@?Z%F>){fU|~?~r_Oah0ab'
    'KP1~9|94H9he&?!$92E=-F!r{cj;qq`)*z$`G<3Mzva96iJpJ2u%^sYB<sI1NK@u3l0Q0shNjG0Bq#5<K~v^0k{9i~<8|N7V<a2T'
    '`{jP$&1WRDD?fP6ck>#_>-G%Nl=+S1Z+6eplzEOG|LmojGT)JW;k3v0_-@`K*|hi%uljEOBiUI|q$%?t$&8CDHDx}e=e2jGrp${Z'
    'S3R+_-FNdNEkBd3Df1-BOMfs$Q|3#O_ua5qQ|3+j`o^EX;=B2i-oGzKG-Vzo`Lda!Df21GQ+h1ZlzElp<(Kbx$#?TB$tz7SO_^s&'
    '9@%-Jrp&kW`gYy<g74;Ck~0SU{@1>ne@X7YWt67O!z5crFVvLznB=bRJD>O6yi9UtR-UHJ&m@Nr`-Y~>(<Ik@`>|(zH(!%{X<t-R'
    '=55-}uDMuK=5Ko4y?(mGck?*O!N2aNDf2lk_q%6n%DhhN=gJ3v>AU%z<g+(NHD#VBnOT3Crp)&w*Z=hKr+qi?lRW9g{+crX)A9;^'
    'TT|wNl3Pk&_=WH0gL=HmQ#EB?DEal86`C?Xlw8<y=t<wr6SZ9SpQ|bJMadNz4{i0`yixMdNhfH^{88)A(3qyoBeh-)+q=bg^GV6;'
    '^S`Vq^GeAl%zc_NztsJ=_0g1hrk2aRxTefECBuE+eB5{QPQCB7=W5FQQ*z9aO>MrLhf1bRDAAPpsN}fIZ`G7}sh<B8zNXAiB}=}1'
    'y{61lwLHE3kNIxCD*5lp^E74Ns`dR(Pqz4O{;D~2w5H5sB`+R*kEYCLCB5D!Y0A7-vVYqTHD!LQ?PO$@rp$A-9KLm<rp$Ns{x5w0'
    'Vc*SrCG*akt10te$*KcyJmkB1u$IfzIhryb*7pAOT@U(hUMyMu<?}UVek|GNjpu&qyLqzqBNJz6%6wV!@I~7n@ZG#w`=g;#HD&%R'
    'S^Ma=X5Y=DwO=(;G-W<5x#sYb_xo;ME&2M|DVj3B*87|O)K7dj&(?9J_cTqJZ)^Fy_{@F2n|Euwo_w~Z%)cdfeD#HUeK!x+{<ZW%'
    'O_`5NRyK5O^xeE%vaID&O_`r-dz}CKdwe%f*Ky!?-_(@(y5#)BolU-*w@ZHWuA4Mv{;u`)NK{ki@shv%W38sl=Oyo`9;hkvddc07'
    'Y}Azbz4rIZMr+DEU&o)rTkrDSd|&b|bFQY$`z1%*{%WJ|=Kor+U%Ez9)&bf-H5yG>4`_SoUZW}N0?A}Xo~Eo1v>vS7s443N$qf&U'
    ')0Fjsw(GAy`(xj&8zj$cx<pgf4|+fT{k^rmTSsVn|LylQWj&$$J$0g{tSfZ99e=;3tS=-#{HMv9vd#$R0lU`tZoQ%9{<~{6W!<6W'
    'ySSUCtUvT~?rzYOb%@s6e>q)K)+3T%T(q;nck2?ZHzU8UDeDtG{#B`(vQE+c2G(iHdPVE~g(Ed(-J<Qb=d<;`Tfb<%{_<6tvX0T$'
    'O@^kdXS6;KTdOJS8tqTpD>P+&qxIWwuk+nHN6Y>0?`q0=N9)11FKEiTN5_fEhc#vWBYE~!=WEJ3NZZ4~_g4FEJ*4;ft(BUxF4A(m'
    'aFnL3k0cAmy>zSZ)=83&t^Bs8td}HnF7Br(>n5GI{OB=FSwBhMGPO!m)=}ENE)Q$UdP?%ke_E$0>niQP{xDTj)>qoEU+~UK->tKB'
    'KJ>*~G-bUddHTP7NmJHclH*U_{X^faza&SN-=rz)FunhqhiJ-rOw0G)=Wg-cx=fE3`HrTn&vbsg<s?m6r%CpG^B0=3Ueo%1{k591'
    'Zqxbg<^42e{igeG+M+4zIGqQ4_i9a9&uM*I-B(lAb=p6j_=Kjc@AST;UacwXJRN7h`~^)}?`eDd!xl|h_i6cmFjrI7f08Y8PSlij'
    'pk7z;Q<}0K)cNAf8#HBID7oiXCu_?3Q1Yq=pVO3eqU1gA#x-TVsM{?cswwM6t&fY^zwf*Cqt1_i{e4YYM{50zpP?!1NnKam^!tSG'
    ')|HYKdw--U>r37K*6EtE&Xi1T3~9=GQ~TlWKhczRr{uprHAhp{pW5&J_IOQMhw63z)03LA9@TkD_&b`iF4cKkuTo7}pXzzd>-e7U'
    ')~PzqjJ!ot)~h-`PMD%8>sD>gYdV+sZvCp~ea=rbWgQ#L|1Z^)^{lqT4gEA_U90Ca{aH;}-|GBge6^;mb9LTv(;1qw-jzJ9@4JhA'
    'x9-(?|NaI|S^sLgEt;b#>tO8{?)-wLtcUgfT=lG`tc$gNFZiCOtdF&x?mbge*2&tQlOHVd-FjK)=}Ve5W!)_K&re^aDeGtLr)Cvu'
    '$~s!dyRwdjzFSZ0^-o`|DeG$O_Z~b~Q`Xno?k~&Hly$b`_p6@Ll=ZgGn;UM@ly$e{7Y3cFDeG^oC+~IM=(}~eWUtJhY07$B%jJ@P'
    ')0B0&_CMj_nzBCEapd&_ao?@ewH@a)Y07$C=TGy#t|{ww$@J19O<BL|x;Ou|`Mz7n>wN6|J2hoJuiNdsSX0*Zdfa9CnzFvv_0^Ky'
    'G2gB8wO(zl*Oc|Xu0tkOYRbA_uQ!sXDeHfqKYsuK000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000093FC@!W900000000000000000000000000002^dn^CUEi$8j&;5@a={#~*<DY*&_E{f)'
    'f|+hcng{K7U$$F+B_$lrFg-%vku#1Qu}2S?PW#{Av;4fjymx_noMIm**+-gvbhnRw_R&Kx&zLOxNO#+vY#;gdA&1Sjj}z^qr+o~U'
    'GqI1bmg$ir18oklj}-gJu#f)s(aSzY*vDx5NOjwZJo|mfKDyaQU;8-TK2EcbG4@e>%yvS~*|(1`*hj8?oN6Cu*vF8MZ6_l3wLbQ7'
    'oP7+lkFoYq`YGFq-uCqz`}m@LoNgZ_e`Y%&1wPb1zGNSR{=#;m%)UR$J_dirc4DO6rs%KOP89x?+li37Uny=M6FQQ9Aao?f-oUHP'
    '0owqM9Ff~tDb@W*cl+#}BS*S-2K$zOKpzGG00000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000008*gyCfxgm1HP*'
    'l*{)UKKA+nV`5)*&*i;6DIe{hZ6EUVIQ!^fA3g2kc>CyOAHD4(@6S9!$NXnZntttLAG!9CWgnUDxaIB<`@|z;A2ChYKh=H>f6DcB'
    'ZU1p0bIe5;kBR^Q00000000000000000000000000QkG=Zi0W)|9^*&8JY6;Ka14A@ZQy)F)5#V=EsOd^#3Q}Z!XqNk6ZAu<HwE!'
    'uP=64<8r0T(4RTn37_$CUH_jD;)wO}_sc(HfA7=E=D%Mx;O;{gN&^4@000000000000000000000002^f6VD7__ySv%-{6itcQ+y'
    'q#pA<00000000000000000000000000000000000000000000000000000000001g5B*GQ{gG~_=UFwzWTnQU#w_zpXfXu?00000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '00000000000094Byr}&W3z<|KA@?};`^u21v{6n;0RR910000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000093p^pr0lm!3-i0000000000'
    '000000000000000000000000000000000000000000000008he6B+&RA3`=gV;-01^<Rx`kmqIBcY9B={Pgaj&|lbo&DVnMD?hgV'
    'biZrAvT??2w2#yZ`+dd#0g*c0n*'
))

class sel:
    NEW_RESOURCE = 0x09
    QUEUE_CREATE = 0x07
    NOTIF_QUEUE = 0x10
    QUEUE_FINALIZE = 0x1C
    SHMEM = 0x0E


# ── semantic trace (style follows allbilly/nvgpu add.py) ─────────

TRACE = int(os.environ.get("AGX_TRACE", "1") or 0)
TRACE_MAXDUMP = int(os.environ.get("AGX_TRACE_MAXDUMP", "128") or 128)

SELECTOR_NAMES = {
    sel.NEW_RESOURCE: "NEW_RESOURCE",
    sel.QUEUE_CREATE: "QUEUE_CREATE",
    sel.NOTIF_QUEUE: "NOTIF_QUEUE",
    sel.QUEUE_FINALIZE: "QUEUE_FINALIZE",
    sel.SHMEM: "SHMEM",
}

STAGES = (
    "IOKit Client",
    "Resource + Queue Setup",
    "Trap Submit",
    "Result Validation",
)

_TRACE_EPOCH = time.perf_counter()
_trace_event_id = 0
_trace_stage = 0
_trace_substage = 0
_trace_stage_started = _TRACE_EPOCH
_trace_status: dict[int, tuple[str, str, float]] = {}


def _fmt_rc(rc: int) -> str:
    return "SUCCESS" if rc == 0 else f"0x{rc & 0xffffffff:08x}"


def _fmt_value(value: object) -> str:
    if isinstance(value, int):
        return str(value) if 0 <= value < 10 else f"0x{value:x}"
    if isinstance(value, bytes):
        return f"bytes[{len(value)}]"
    return repr(value)


def describe_struct(value: object) -> str:
    if value is None:
        return "-"
    names = getattr(value, "__dataclass_fields__", None)
    if not names:
        return f"{type(value).__name__}[{len(value)}]" if isinstance(value, bytes) else repr(value)
    parts = []
    for name in names:
        item = getattr(value, name)
        if name in ("raw", "raw_tail"):
            if item:
                parts.append(f"{name}=bytes[{len(item)}]")
            continue
        if item not in (0, "", b"", False):
            parts.append(f"{name}={_fmt_value(item)}")
    return f"{type(value).__name__}({', '.join(parts)})"


def describe_call_input(selector: int, scalars: list[int], value: object) -> str:
    if isinstance(value, ResourceCreateIn):
        parts = [f"alloc=0x{value.alloc_size:x}", f"type=0x{value.type_version:x}"]
        if value.parent_handle:
            parts.append(f"parent=0x{value.parent_handle:x}")
        if value.parent_gpu_va:
            parts.append(f"parent_va=0x{value.parent_gpu_va:x}")
        if value.heap_flags:
            parts.append(f"heap=0x{value.heap_flags:x}")
        if value.backing_ptr:
            parts.append(f"backing_ptr=0x{value.backing_ptr:x}")
        return " ".join(parts)
    if isinstance(value, QueueCreateIn):
        return (
            f"exe={value.exe_path!r} label={value.label!r} "
            f"flags=0x{value.queue_flags:x} enable={value.enable}"
        )
    if selector == sel.NOTIF_QUEUE and len(scalars) >= 2:
        return f"ring_size=0x{scalars[0]:x} flags=0x{scalars[1]:x}"
    if selector == sel.QUEUE_FINALIZE and len(scalars) >= 2:
        return f"queue={scalars[0]} finalize={scalars[1]}"
    if selector == sel.SHMEM and len(scalars) >= 2:
        return f"size=0x{scalars[0]:x} flags=0x{scalars[1]:x}"
    return "scalars=[" + ", ".join(f"0x{item:x}" for item in scalars) + "]"


def describe_live_out(template: object, data: bytes) -> str:
    if isinstance(template, ResourceCreateOut) and len(data) >= 88:
        rid, rid_tag = struct.unpack_from("<II", data, 0)
        gpu_va, gpu_va2 = struct.unpack_from("<QQ", data, 8)
        slot = struct.unpack_from("<I", data, 0x24)[0]
        heap_size = struct.unpack_from("<Q", data, 0x28)[0]
        return (
            f"ResourceCreateOut(rid=0x{rid:x}, tag={rid_tag}, "
            f"gpu_va=0x{gpu_va:x}, gpu_va2=0x{gpu_va2:x}, "
            f"slot={slot}, heap=0x{heap_size:x})"
        )
    if isinstance(template, QueueCreateOut) and len(data) >= 16:
        queue_id = struct.unpack_from("<I", data, 0)[0]
        cookie = struct.unpack_from("<Q", data, 8)[0]
        return f"QueueCreateOut(queue_id={queue_id}, cookie=0x{cookie:x})"
    if isinstance(template, NotifQueueOut) and len(data) >= 16:
        ring_address, queue_id, _reserved = struct.unpack_from("<QII", data, 0)
        return f"NotifQueueOut(ring=0x{ring_address:x}, queue_id={queue_id})"
    if isinstance(template, ShmemOut) and len(data) >= 16:
        gpu_va, size, shmem_id = struct.unpack_from("<QII", data, 0)
        return f"ShmemOut(gpu_va=0x{gpu_va:x}, size=0x{size:x}, id={shmem_id})"
    return f"bytes[{len(data)}]"


def trace(tag: str, message: str, *, event: int | None = None, level: int = 1) -> None:
    if TRACE < level:
        return
    stage = f"S{_trace_stage}" if _trace_stage else "S-"
    if event is not None and _trace_substage:
        stage += f".{_trace_substage}"
    event_label = f"[E{event:06d}]" if event is not None else ""
    elapsed_ms = (time.perf_counter() - _TRACE_EPOCH) * 1000
    print(f"[{stage}]{event_label} {tag:<5} +{elapsed_ms:9.3f}ms {message}", flush=True)


def trace_blob(tag: str, data: bytes, *, event: int) -> None:
    if TRACE < 2 or not data:
        return
    shown = data[:TRACE_MAXDUMP]
    suffix = f" ... +{len(data) - len(shown)} bytes" if len(shown) < len(data) else ""
    trace(tag, shown.hex(" ") + suffix, event=event, level=2)


def trace_event() -> int:
    global _trace_event_id, _trace_substage
    _trace_event_id += 1
    _trace_substage += 1
    return _trace_event_id


def trace_reset() -> None:
    global _TRACE_EPOCH, _trace_event_id, _trace_stage
    global _trace_substage, _trace_stage_started
    _TRACE_EPOCH = time.perf_counter()
    _trace_event_id = 0
    _trace_stage = 0
    _trace_substage = 0
    _trace_stage_started = _TRACE_EPOCH
    _trace_status.clear()


def stage_set(number: int, note: str) -> None:
    global _trace_stage, _trace_substage, _trace_stage_started
    if TRACE and _trace_stage:
        print(flush=True)
    _trace_stage = number
    _trace_substage = 0
    _trace_stage_started = time.perf_counter()
    trace("CTX", note)


def stage_finish(ok: bool, note: str) -> None:
    elapsed_ms = (time.perf_counter() - _trace_stage_started) * 1000
    _trace_status[_trace_stage] = ("OK" if ok else "FAIL", note, elapsed_ms)


def trace_summary() -> None:
    if not TRACE:
        return
    print("\n" + "=" * 72)
    print(f"{'APPLE GPU REPLAY':^72}")
    print("=" * 72)
    for number, name in enumerate(STAGES, 1):
        state, note, elapsed_ms = _trace_status.get(number, ("----", "", 0.0))
        timing = f"{elapsed_ms:8.3f} ms" if state != "----" else "          "
        extra = f"  {note}" if note else ""
        print(f"[S{number}] {name:<28} {state:<4} {timing}{extra}")
    print("=" * 72)


def format_result(data: bytes) -> str:
    if WORKLOAD in ("add", "mul") and len(data) % 4 == 0:
        values = struct.unpack(f"<{len(data) // 4}f", data)
        return "result=" + repr(tuple(round(value, 6) for value in values))
    if WORKLOAD == "tri":
        return "center_bgra=" + repr(tuple(data))
    return "result_bytes=" + data.hex(" ")


# ── IOGPU input structs (selector payloads) ──────────────────────

@dataclass
class ResourceCreateIn:
    """Selector 0x09 s_new_resource input (104 bytes)."""

    parent_handle: int = 0
    type_version: int = 0x0001_0001
    resource_class: int = 1
    create_flags: int = 0x0100_0101
    alloc_size: int = 0
    suballoc_flag: int = 0
    parent_gpu_va: int = 0
    parent_gpu_va2: int = 0
    heap_flags: int = 0
    heap_lane: int = 0
    stride_or_count: int = 0
    create_info: int = 0
    backing_ptr: int = 0
    raw_tail: bytes = field(default_factory=bytes)

    def pack(self) -> bytes:
        if self.raw_tail:
            return bytes(self.raw_tail)
        buf = bytearray(104)
        struct.pack_into("<Q", buf, 0, self.parent_handle)
        struct.pack_into("<I", buf, 8, self.type_version)
        struct.pack_into("<I", buf, 12, self.resource_class)
        struct.pack_into("<I", buf, 16, self.create_flags)
        struct.pack_into("<I", buf, 20, self.alloc_size)
        struct.pack_into("<I", buf, 0x30, self.suballoc_flag)
        struct.pack_into("<Q", buf, 0x38, self.parent_gpu_va)
        struct.pack_into("<Q", buf, 0x40, self.parent_gpu_va2)
        struct.pack_into("<I", buf, 0x48, self.heap_flags)
        struct.pack_into("<I", buf, 0x50, self.heap_lane)
        struct.pack_into("<I", buf, 0x58, self.stride_or_count)
        struct.pack_into("<I", buf, 0x5C, self.create_info)
        struct.pack_into("<Q", buf, 0x60, self.backing_ptr)
        return bytes(buf)


@dataclass
class ResourceCreateOut:
    """Selector 0x09 output (88 bytes) — captured reference for addr-map learning."""

    rid: int = 0
    rid_tag: int = 0
    gpu_va: int = 0
    gpu_va2: int = 0
    slot_index: int = 0
    heap_size: int = 0
    cookie: int = 0
    cookie_flags: int = 0
    type_tag: int = 0
    out_heap_flags: int = 0
    raw: bytes = field(default_factory=bytes)

    def pack(self) -> bytes:
        if self.raw:
            return bytes(self.raw)
        buf = bytearray(88)
        struct.pack_into("<I", buf, 0, self.rid)
        struct.pack_into("<I", buf, 4, self.rid_tag)
        struct.pack_into("<Q", buf, 8, self.gpu_va)
        struct.pack_into("<Q", buf, 16, self.gpu_va2)
        struct.pack_into("<I", buf, 0x24, self.slot_index)
        struct.pack_into("<Q", buf, 0x28, self.heap_size)
        struct.pack_into("<I", buf, 0x30, self.cookie)
        struct.pack_into("<I", buf, 0x34, self.cookie_flags)
        struct.pack_into("<I", buf, 0x38, self.type_tag)
        struct.pack_into("<I", buf, 0x50, self.out_heap_flags)
        return bytes(buf)


@dataclass
class QueueCreateIn:
    """Selector 0x07 queue_create input (1040 bytes)."""

    exe_path: str = ""
    label: str = ""
    queue_flags: int = 2
    unk_mask: int = 0xFFFFFFFF
    enable: int = 1
    raw: bytes = field(default_factory=bytes)

    def pack(self) -> bytes:
        if self.raw:
            return bytes(self.raw)
        buf = bytearray(0x410)
        ep = self.exe_path.encode("utf-8")[:0x3C7]
        lb = self.label.encode("utf-8")[:0x37]
        buf[0x000 : 0x000 + len(ep)] = ep
        buf[0x3C8 : 0x3C8 + len(lb)] = lb
        struct.pack_into("<Q", buf, 0x400, self.queue_flags)
        struct.pack_into("<I", buf, 0x408, self.unk_mask)
        struct.pack_into("<I", buf, 0x40C, self.enable)
        return bytes(buf)


@dataclass
class QueueCreateOut:
    queue_id: int = 0
    cookie: int = 0

    def pack(self) -> bytes:
        buf = bytearray(16)
        struct.pack_into("<I", buf, 0, self.queue_id)
        struct.pack_into("<Q", buf, 8, self.cookie)
        return bytes(buf)


@dataclass
class NotifQueueIn:
    ring_size: int = 0x100
    ring_flags: int = 0x28

    def as_scalars(self) -> list[int]:
        return [self.ring_size, self.ring_flags]


@dataclass
class NotifQueueOut:
    ring_address: int = 0
    queue_id: int = 0
    reserved: int = 0

    def pack(self) -> bytes:
        return struct.pack("<QII", self.ring_address, self.queue_id, self.reserved)


@dataclass
class QueueFinalizeIn:
    arg0: int = 1
    arg1: int = 1

    def as_scalars(self) -> list[int]:
        return [self.arg0, self.arg1]


@dataclass
class ShmemIn:
    size: int = 0x4000
    map_flags: int = 0

    def as_scalars(self) -> list[int]:
        return [self.size, self.map_flags]


@dataclass
class ShmemOut:
    gpu_va: int = 0
    size: int = 0
    shmem_id: int = 0

    def pack(self) -> bytes:
        buf = bytearray(16)
        struct.pack_into("<Q", buf, 0, self.gpu_va)
        struct.pack_into("<I", buf, 8, self.size)
        struct.pack_into("<I", buf, 12, self.shmem_id)
        return bytes(buf)


@dataclass
class Trap0SubmitSnap:
    """Trap0 fast-path submit record (64 bytes).

    Offsets 0x10 and 0x18 are userspace block pointers, not GPU VAs. The
    capture stream stores and relocates the pointed-to 0x30-byte descriptors.
    """

    record_type: int = 0
    submit_flags: int = 0
    reserved: int = 0
    callback_0: int = 0
    callback_1: int = 0
    raw: bytes = field(default_factory=bytes)

    def pack(self) -> bytes:
        if self.raw:
            return bytes(self.raw)
        buf = bytearray(64)
        struct.pack_into("<I", buf, 0, self.record_type)
        struct.pack_into("<I", buf, 4, self.submit_flags)
        struct.pack_into("<Q", buf, 8, self.reserved)
        struct.pack_into("<Q", buf, 0x10, self.callback_0)
        struct.pack_into("<Q", buf, 0x18, self.callback_1)
        return bytes(buf)

# ── IOKit backend ────────────────────────────────────────────────

AGX_NAMES = (
    "AGXAcceleratorG13G_B0",
    "AGXAcceleratorG13G",
    "AGXAcceleratorG14G",
    "AGXAcceleratorG15G",
    "AGXAcceleratorG16G",
    "AGXAcceleratorG17G",
)


def prepare_call_struct(selector: int, struct_in: bytes | None) -> bytes | None:
    """Translate the legacy queue tail to the layout captured on macOS 27."""
    if (
        selector == 0x07
        and struct_in is not None
        and len(struct_in) == 0x410
        and struct_in[0x408:] == b"\xff\xff\xff\xff\x01\x00\x00\x00"
        and int(platform.mac_ver()[0].split(".")[0] or "0") >= 27
    ):
        return struct_in[:0x408] + b"\x01\x00\x00\x00\x00\x00\x00\x00"
    return struct_in


class IOKit:
    def __init__(self) -> None:
        path = ctypes.util.find_library("IOKit")
        if not path:
            raise RuntimeError("IOKit not found")
        self.lib = ctypes.CDLL(path)

        self.lib.IOServiceNameMatching.argtypes = [ctypes.c_char_p]
        self.lib.IOServiceNameMatching.restype = ctypes.c_void_p

        self.lib.IOServiceMatching.argtypes = [ctypes.c_char_p]
        self.lib.IOServiceMatching.restype = ctypes.c_void_p

        self.lib.IOServiceGetMatchingService.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
        self.lib.IOServiceGetMatchingService.restype = ctypes.c_uint32

        self.lib.IOServiceGetMatchingServices.argtypes = [
            ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32),
        ]
        self.lib.IOServiceGetMatchingServices.restype = ctypes.c_int

        self.lib.IOIteratorNext.argtypes = [ctypes.c_uint32]
        self.lib.IOIteratorNext.restype = ctypes.c_uint32

        self.lib.IOObjectRelease.argtypes = [ctypes.c_uint32]
        self.lib.IOObjectRelease.restype = ctypes.c_int

        self.lib.IOServiceOpen.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
        ]
        self.lib.IOServiceOpen.restype = ctypes.c_int

        self.lib.IOServiceClose.argtypes = [ctypes.c_uint32]
        self.lib.IOServiceClose.restype = ctypes.c_int

        self.lib.IOConnectCallMethod.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint64), ctypes.c_uint32,
            ctypes.c_void_p, ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
        ]
        self.lib.IOConnectCallMethod.restype = ctypes.c_int

        self.lib.IOConnectTrap4.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64,
        ]
        self.lib.IOConnectTrap4.restype = ctypes.c_int

        libc = ctypes.CDLL(None)
        self.mach_task_self = libc.mach_task_self
        self.mach_task_self.restype = ctypes.c_uint32

    def find_agx_service(self) -> int:
        for name in AGX_NAMES:
            match = self.lib.IOServiceNameMatching(name.encode())
            svc = self.lib.IOServiceGetMatchingService(0, match)
            if svc:
                return svc

        it = ctypes.c_uint32(0)
        match = self.lib.IOServiceMatching(b"AGXAccelerator")
        self.lib.IOServiceGetMatchingServices(0, match, ctypes.byref(it))
        svc = self.lib.IOIteratorNext(it.value)
        self.lib.IOObjectRelease(it.value)
        return svc

    def service_open(self, svc: int, client_type: int) -> tuple[int, int]:
        conn = ctypes.c_uint32(0)
        rc = self.lib.IOServiceOpen(
            svc, self.mach_task_self(), client_type, ctypes.byref(conn)
        )
        return rc, conn.value

    def connect_call(
        self,
        conn: int,
        selector: int,
        scal_in: list[int],
        struct_in: bytes | None,
        scalar_out_cnt: int,
        struct_out_sz: int,
    ) -> tuple[int, list[int], bytes, int]:
        struct_in = prepare_call_struct(selector, struct_in)
        n_in = len(scal_in)
        scal_in_arr = (ctypes.c_uint64 * n_in)(*scal_in) if n_in else None

        in_buf = None
        if struct_in:
            in_buf = ctypes.create_string_buffer(struct_in, len(struct_in))

        scal_out_arr = None
        scal_out_cnt = ctypes.c_uint32(scalar_out_cnt) if scalar_out_cnt else None
        if scal_out_cnt:
            scal_out_arr = (ctypes.c_uint64 * scal_out_cnt.value)()

        out_buf = None
        out_sz = ctypes.c_size_t(struct_out_sz) if struct_out_sz else None
        if struct_out_sz:
            out_buf = ctypes.create_string_buffer(struct_out_sz)

        rc = self.lib.IOConnectCallMethod(
            conn, selector,
            scal_in_arr, n_in,
            ctypes.cast(in_buf, ctypes.c_void_p) if in_buf else None,
            len(struct_in) if struct_in else 0,
            scal_out_arr,
            ctypes.byref(scal_out_cnt) if scal_out_cnt else None,
            ctypes.cast(out_buf, ctypes.c_void_p) if out_buf else None,
            ctypes.byref(out_sz) if out_sz else None,
        )

        scal_out = list(scal_out_arr) if scal_out_arr else []
        live_out = bytes(out_buf.raw[: out_sz.value]) if out_buf else b""
        return rc, scal_out, live_out, out_sz.value if out_sz else 0

    def connect_trap(
        self, conn: int, trap_idx: int, p1: int, p2: int, p3: int, p4: int
    ) -> int:
        return self.lib.IOConnectTrap4(conn, trap_idx, p1, p2, p3, p4)


def alloc_aligned(size: int, align: int = 16) -> tuple[ctypes.c_void_p, ctypes.CDLL]:
    libc = ctypes.CDLL(None)
    libc.posix_memalign.argtypes = [
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_size_t, ctypes.c_size_t,
    ]
    libc.posix_memalign.restype = ctypes.c_int
    libc.free.argtypes = [ctypes.c_void_p]
    libc.free.restype = None

    ptr = ctypes.c_void_p()
    if libc.posix_memalign(ctypes.byref(ptr), align, size) != 0:
        raise MemoryError("posix_memalign failed")
    return ptr, libc


def open_agx(iokit: IOKit) -> tuple[int, int]:
    """Open AGXAccelerator user client. Returns (service, conn)."""
    svc = iokit.find_agx_service()
    if not svc:
        raise RuntimeError("no AGX accelerator")
    kr, conn = iokit.service_open(svc, CLIENT_TYPE)
    if kr != 0:
        raise RuntimeError(f"IOServiceOpen failed rc=0x{kr:x}")
    return svc, conn


# ponytail: agx_call dropped — it was a 1-call wrapper that threw away
# a return value; inlined into execute_op below.


def submit_task(
    iokit: IOKit, conn: int, trap_idx: int, p1: int, p2: int, snap: bytes,
    p4_offset: int, allocations: list[tuple[object, object]],
) -> int:
    """Trap submit — ane submit_task ioctl equivalent."""
    p3 = p4 = 0
    ptr = None
    libc = None
    if snap:
        alloc_sz = len(snap) + 0x100
        ptr, libc = alloc_aligned(alloc_sz)
        dst = (ctypes.c_uint8 * alloc_sz).from_address(ptr.value)
        ctypes.memmove(dst, snap, len(snap))
        p3 = ptr.value
        p4 = ptr.value + p4_offset if 0 < p4_offset < alloc_sz else 0
        allocations.append((ptr, libc))
    return iokit.connect_trap(conn, trap_idx, p1, p2, p3, p4)


def close_agx(iokit: IOKit, svc: int, conn: int) -> None:
    if conn:
        iokit.lib.IOServiceClose(conn)
    if svc:
        iokit.lib.IOObjectRelease(svc)


# ── address remap ────────────────────────────────────────────────

# ponytail: OpenOp dropped — the captured open is replayed by open_agx(),
# so the no-op marker only existed to keep the OP list round-numbered.
@dataclass
class CallOp:
    selector: int
    scalars: list[int]
    struct_in: object
    struct_out_sz: int
    cap_out: object = None
    expected_rc: int = 0

    def pack_struct_in(self) -> bytes | None:
        if self.struct_in is None:
            return None
        if hasattr(self.struct_in, "pack"):
            return self.struct_in.pack()
        return self.struct_in


@dataclass
class TrapOp:
    trap_idx: int
    p1: int
    p2: int
    p4_offset: int
    snap: Trap0SubmitSnap
    expected_rc: int = 0


@dataclass
class MemoryOp:
    kind: int
    address: int
    offset: int
    size: int

    def bytes(self) -> bytes:
        return _MEMORY_IMAGE[self.offset : self.offset + self.size]


class AddrMap:
    def __init__(self) -> None:
        self._maps: dict[int, int] = {}
        self._ranges: list[tuple[int, int, int]] = []

    def add(self, old: int, new: int) -> bool:
        if not old or not new:
            return False
        if self._maps.get(old) == new:
            return False
        self._maps[old] = new
        return True

    def add_range(self, old: int, new: int, size: int) -> bool:
        if not old or not new or not size:
            return False
        learned = self.add(old, new)
        entry = (old, new, size)
        if entry not in self._ranges:
            self._ranges.append(entry)
            learned = True
        return learned

    def remap(self, value: int) -> int:
        exact = self._maps.get(value)
        if exact is not None:
            return exact
        for old, new, size in self._ranges:
            if old <= value < old + size:
                return new + (value - old)
        return value

    def contains(self, value: int) -> bool:
        if value in self._maps:
            return True
        return any(old <= value < old + size for old, _new, size in self._ranges)

    def patch_u64_buf(self, buf: bytearray) -> list[tuple[int, int, int]]:
        patched = []
        for off in range(0, len(buf) - 7, 4):
            old, = struct.unpack_from("<Q", buf, off)
            new = self.remap(old)
            if new != old:
                struct.pack_into("<Q", buf, off, new)
                patched.append((off, old, new))
        return patched

    def learn_resource_maps(self, cap: bytes, live: bytes) -> list[tuple[int, int]]:
        if len(cap) < 24 or len(live) < 24:
            return []
        learned = []
        old = struct.unpack_from("<Q", cap, 8)[0]
        new = struct.unpack_from("<Q", live, 8)[0]
        size = struct.unpack_from("<Q", cap, 0x28)[0] if len(cap) >= 0x30 else 0
        if self.add_range(old, new, size):
            learned.append((old, new))
        old = struct.unpack_from("<Q", cap, 16)[0]
        new = struct.unpack_from("<Q", live, 16)[0]
        if self.add(old, new):
            learned.append((old, new))
        return learned

    def learn_shmem_maps(
        self, cap: bytes, live: bytes, size: int | None = None,
    ) -> list[tuple[int, int]]:
        if len(cap) < 8 or len(live) < 8:
            return []
        old = struct.unpack_from("<Q", cap, 0)[0]
        new = struct.unpack_from("<Q", live, 0)[0]
        if size is None:
            size = struct.unpack_from("<I", cap, 8)[0] if len(cap) >= 12 else 0
        return [(old, new)] if self.add_range(old, new, size) else []

    def __len__(self) -> int:
        return len(self._maps)


# ── IOGPU submit sequence (BTSP equivalent) ──────────────────────

OPS = [
# ── resource setup (sel NEW_RESOURCE) ───────────────────────────

    CallOp(  # op 1: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(alloc_size=33840, heap_flags=0x10000, stride_or_count=0x38000000, create_info=24),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(gpu_va=0x100bdc000, gpu_va2=0x100bc80c0, slot_index=1, heap_size=0x10000, cookie=0x6e100328, type_tag=0x8f9fe, out_heap_flags=0x10000),
    ),
    CallOp(  # op 2: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(alloc_size=1136, suballoc_flag=1, heap_flags=0x20000, backing_ptr=0x10b4d4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid_tag=21, gpu_va=0x100df0000, gpu_va2=0x100bc8180, slot_index=2, heap_size=0x20000, cookie=0x6e10034f, type_tag=0x8f9ff, out_heap_flags=0x20000),
    ),
    CallOp(  # op 3: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df0000, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2, backing_ptr=0x10b4d4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid_tag=21, gpu_va2=0x100bc8240, slot_index=3, heap_size=0x20000, cookie=0x6e100350, type_tag=0x8f9ff, out_heap_flags=0x20000),
    ),
    CallOp(  # op 4: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df0100, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2, backing_ptr=0x10b4d4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=256, rid_tag=21, gpu_va2=0x100bc8300, slot_index=4, heap_size=0x20000, cookie=0x6e100351, type_tag=0x8f9ff, out_heap_flags=0x1ff00),
    ),
    CallOp(  # op 5: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df0200, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=512, rid_tag=21, gpu_va2=0x100bc83c0, slot_index=5, heap_size=0x20000, cookie=0x6e100352, type_tag=0x8f9ff, out_heap_flags=0x1fe00),
    ),
# ── queue setup (sel QUEUE_CREATE / NOTIF_QUEUE / FINALIZE) ─────

    CallOp(  # op 6: QUEUE_CREATE
        selector=sel.QUEUE_CREATE,
        scalars=[],
        struct_in=QueueCreateIn(exe_path='metal_add'),
        struct_out_sz=16,
        cap_out=QueueCreateOut(queue_id=1, cookie=0x6e100353),
    ),
    CallOp(  # op 7: NOTIF_QUEUE
        selector=sel.NOTIF_QUEUE,
        scalars=NotifQueueIn().as_scalars(),
        struct_in=None,
        struct_out_sz=16,
        cap_out=NotifQueueOut(ring_address=0x100e10000, queue_id=1),
    ),
    CallOp(  # op 8: QUEUE_FINALIZE
        selector=sel.QUEUE_FINALIZE,
        scalars=QueueFinalizeIn().as_scalars(),
        struct_in=None,
        struct_out_sz=0,
    ),
# ── resource setup (sel NEW_RESOURCE) ───────────────────────────

    CallOp(  # op 9: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df0300, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x10b4d54a0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=768, rid_tag=21, gpu_va2=0x100bc8480, slot_index=6, heap_size=0x20000, cookie=0x6e100357, type_tag=0x8f9ff, out_heap_flags=0x1fd00),
    ),
    CallOp(  # op 10: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df0500, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x10b4d54a0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=1280, rid_tag=21, gpu_va2=0x100bc8540, slot_index=7, heap_size=0x20000, cookie=0x6e100358, type_tag=0x8f9ff, out_heap_flags=0x1fb00),
    ),
    CallOp(  # op 11: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df0700, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x10b4d54a0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=1792, rid_tag=21, gpu_va2=0x100bc8600, slot_index=8, heap_size=0x20000, cookie=0x6e100359, type_tag=0x8f9ff, out_heap_flags=0x1f900),
    ),
    CallOp(  # op 12: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df0800, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0xc99092210),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=2048, rid_tag=21, gpu_va2=0x100bc86c0, slot_index=9, heap_size=0x20000, cookie=0x6e10035a, type_tag=0x8f9ff, out_heap_flags=0x1f800),
    ),
    CallOp(  # op 13: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df2800, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0xc99092298),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=10240, rid_tag=21, gpu_va2=0x100bc8780, slot_index=10, heap_size=0x20000, cookie=0x6e10035b, type_tag=0x8f9ff, out_heap_flags=0x1d800),
    ),
    CallOp(  # op 14: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df2900, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0xc990925b8),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=10496, rid_tag=21, gpu_va2=0x100bc8840, slot_index=11, heap_size=0x20000, cookie=0x6e10035c, type_tag=0x8f9ff, out_heap_flags=0x1d700),
    ),
    CallOp(  # op 15: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df3900, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0xc990928d8),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=14592, rid_tag=21, gpu_va2=0x100bc8900, slot_index=12, heap_size=0x20000, cookie=0x6e10035d, type_tag=0x8f9ff, out_heap_flags=0x1c700),
    ),
    CallOp(  # op 16: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df3a00, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0xc99092be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=14848, rid_tag=21, gpu_va2=0x100bc89c0, slot_index=13, heap_size=0x20000, cookie=0x6e10035e, type_tag=0x8f9ff, out_heap_flags=0x1c600),
    ),
    CallOp(  # op 17: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df3b00, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0xc99092ee8),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=15104, rid_tag=21, gpu_va2=0x100bc8a80, slot_index=14, heap_size=0x20000, cookie=0x6e10035f, type_tag=0x8f9ff, out_heap_flags=0x1c500),
    ),
    CallOp(  # op 18: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(alloc_size=1072, heap_flags=0x10000, stride_or_count=0x8000000, create_info=24),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x28000, rid_tag=21, gpu_va=0x100e14000, gpu_va2=0x100bc8b40, slot_index=15, heap_size=0x10000, cookie=0x6e100360, type_tag=0x8fa03, out_heap_flags=0x10000),
    ),
    CallOp(  # op 19: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x100df3c00, parent_gpu_va2=0x100df0000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x10b4d4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=15360, rid_tag=21, gpu_va2=0x100bc8c00, slot_index=16, heap_size=0x20000, cookie=0x6e100361, type_tag=0x8f9ff, out_heap_flags=0x1c400),
    ),
    CallOp(  # op 20: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(alloc_size=1136, suballoc_flag=1, heap_flags=0x20000, backing_ptr=0x10b4d4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x40000, rid_tag=21, gpu_va=0x105648000, gpu_va2=0x100bc8cc0, slot_index=17, heap_size=0x20000, cookie=0x6e100362, type_tag=0x8fa04, out_heap_flags=0x20000),
    ),
    CallOp(  # op 21: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x105648000, parent_gpu_va2=0x105648000, heap_flags=0x20000, heap_lane=17, create_info=24, backing_ptr=0xc99090000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x40000, rid_tag=21, gpu_va2=0x100bc8d80, slot_index=18, heap_size=0x20000, cookie=0x6e100363, type_tag=0x8fa04, out_heap_flags=0x20000),
    ),
# ── shared memory (sel SHMEM) ───────────────────────────────────

    CallOp(  # op 22: SHMEM
        selector=sel.SHMEM,
        scalars=ShmemIn().as_scalars(),
        struct_in=None,
        struct_out_sz=16,
        cap_out=ShmemOut(gpu_va=0x100e24000, size=16384, shmem_id=1),
    ),
    CallOp(  # op 23: SHMEM
        selector=sel.SHMEM,
        scalars=ShmemIn(map_flags=1).as_scalars(),
        struct_in=None,
        struct_out_sz=16,
        cap_out=ShmemOut(gpu_va=0x100e28000, size=16384, shmem_id=2),
    ),
# ── resource setup (sel NEW_RESOURCE) ───────────────────────────

    CallOp(  # op 24: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000, create_info=72),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x68000, rid_tag=21, gpu_va=0x105668000, gpu_va2=0x100bc8e40, slot_index=19, heap_size=32768, cookie=0x6f100364, type_tag=0x8fa05, out_heap_flags=32768),
    ),
    CallOp(  # op 25: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=50224, heap_flags=32768, stride_or_count=0x48000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x18000, gpu_va=0x105670000, gpu_va2=0x100bc8f00, slot_index=20, heap_size=32768, cookie=0x6f100365, type_tag=0x8fa06, out_heap_flags=32768),
    ),
    CallOp(  # op 26: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x78000, rid_tag=21, gpu_va=0x105678000, gpu_va2=0x100bc8fc0, slot_index=21, heap_size=32768, cookie=0x6f100366, type_tag=0x8fa07, out_heap_flags=32768),
    ),
    CallOp(  # op 27: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000, create_info=64),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x88000, rid_tag=21, gpu_va=0x105680000, gpu_va2=0x100bc9080, slot_index=22, heap_size=32768, cookie=0x6f100367, type_tag=0x8fa08, out_heap_flags=32768),
    ),
    CallOp(  # op 28: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x98000, rid_tag=21, gpu_va=0x105688000, gpu_va2=0x100bc9140, slot_index=23, heap_size=32768, cookie=0x6f100368, type_tag=0x8fa09, out_heap_flags=32768),
    ),
    CallOp(  # op 29: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0xa8000, rid_tag=21, gpu_va=0x105690000, gpu_va2=0x100bc9200, slot_index=24, heap_size=32768, cookie=0x6f100369, type_tag=0x8fa0a, out_heap_flags=32768),
    ),
    CallOp(  # op 30: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x1ff80, alloc_size=17456, heap_flags=65408, stride_or_count=0x18000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0xb8000, rid_tag=21, gpu_va=0x105698000, gpu_va2=0x100bc92c0, slot_index=25, heap_size=0x10000, cookie=0x6f10036a, type_tag=0x8fa0b, out_heap_flags=0x10000),
    ),
    MemoryOp(  # op 31
        kind=MEMORY_RESOURCE,
        address=0x100bdc000,
        offset=0x0,
        size=0x10000,
    ),
    MemoryOp(  # op 32
        kind=MEMORY_RESOURCE,
        address=0x100df0000,
        offset=0x10000,
        size=0x20000,
    ),
    MemoryOp(  # op 33
        kind=MEMORY_RESOURCE,
        address=0x100e10000,
        offset=0x30000,
        size=0x4000,
    ),
    MemoryOp(  # op 34
        kind=MEMORY_RESOURCE,
        address=0x100e14000,
        offset=0x34000,
        size=0x10000,
    ),
    MemoryOp(  # op 35
        kind=MEMORY_RESOURCE,
        address=0x105648000,
        offset=0x44000,
        size=0x20000,
    ),
    MemoryOp(  # op 36
        kind=MEMORY_RESOURCE,
        address=0x100e24000,
        offset=0x64000,
        size=0x4000,
    ),
    MemoryOp(  # op 37
        kind=MEMORY_RESOURCE,
        address=0x100e28000,
        offset=0x68000,
        size=0x4000,
    ),
    MemoryOp(  # op 38
        kind=MEMORY_RESOURCE,
        address=0x105668000,
        offset=0x6c000,
        size=0x8000,
    ),
    MemoryOp(  # op 39
        kind=MEMORY_RESOURCE,
        address=0x105670000,
        offset=0x74000,
        size=0x8000,
    ),
    MemoryOp(  # op 40
        kind=MEMORY_RESOURCE,
        address=0x105678000,
        offset=0x7c000,
        size=0x8000,
    ),
    MemoryOp(  # op 41
        kind=MEMORY_RESOURCE,
        address=0x105680000,
        offset=0x84000,
        size=0x8000,
    ),
    MemoryOp(  # op 42
        kind=MEMORY_RESOURCE,
        address=0x105688000,
        offset=0x8c000,
        size=0x8000,
    ),
    MemoryOp(  # op 43
        kind=MEMORY_RESOURCE,
        address=0x105690000,
        offset=0x94000,
        size=0x8000,
    ),
    MemoryOp(  # op 44
        kind=MEMORY_RESOURCE,
        address=0x105698000,
        offset=0x9c000,
        size=0x10000,
    ),
# ── submit (trap0) ──────────────────────────────────────────────

    MemoryOp(  # op 45
        kind=MEMORY_TRAP_AUX,
        address=0xc98c40480,
        offset=0xac000,
        size=0x30,
    ),
    MemoryOp(  # op 46
        kind=MEMORY_TRAP_AUX,
        address=0xc98c404b0,
        offset=0xac030,
        size=0x30,
    ),
    TrapOp(  # op 47
        trap_idx=0,
        p1=1,
        p2=64,
        p4_offset=132,
        snap=Trap0SubmitSnap(record_type=2, submit_flags=1, callback_0=0xc98c40480, callback_1=0xc98c404b0),
    ),
# ── GPU result validation ───────────────────────────────────────

    MemoryOp(  # op 48
        kind=MEMORY_EXPECTED,
        address=0x100df0200,
        offset=0xac060,
        size=0x10,
    ),
]


def execute_op(
    iokit: IOKit,
    conn: int,
    addr_map: AddrMap,
    idx: int,
    op: CallOp | TrapOp | MemoryOp,
    verbose: bool,
    allocations: list[tuple[object, object]],
    observed_outputs: list[bytes],
) -> int:
    """Run one captured op. Returns 1 when live behavior mismatches capture."""
    event = trace_event()
    if isinstance(op, CallOp):
        raw = op.pack_struct_in()
        prepared = prepare_call_struct(op.selector, raw)
        buf = bytearray(prepared) if prepared else bytearray()
        patched = addr_map.patch_u64_buf(buf) if buf else []
        name = SELECTOR_NAMES.get(op.selector, f"SEL_0x{op.selector:02x}")
        input_summary = describe_call_input(op.selector, op.scalars, op.struct_in)
        trace(
            "CALL",
            f"op={idx + 1} {name} sel=0x{op.selector:02x} "
            f"{input_summary} struct={len(buf)}B -> {op.struct_out_sz}B",
            event=event,
        )
        trace("ARGS", describe_struct(op.struct_in), event=event, level=2)
        if prepared != raw:
            trace(
                "PATCH", "macOS 27 QUEUE_CREATE tail: (0xffffffff, 1) -> (1, 0)",
                event=event,
            )
        if patched:
            details = ", ".join(
                f"+0x{off:x} 0x{old:x}->0x{new:x}"
                for off, old, new in patched
            )
            trace("PATCH", f"{len(patched)} pointer(s): {details}", event=event, level=2)
        trace_blob("IN", bytes(buf), event=event)
        started = time.perf_counter()
        rc, _so, live_out, out_sz = iokit.connect_call(
            conn, op.selector, op.scalars,
            bytes(buf) if buf else None, 0, op.struct_out_sz,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        matches = rc == op.expected_rc and out_sz == op.struct_out_sz
        trace(
            "RET",
            f"{_fmt_rc(rc)} expected={_fmt_rc(op.expected_rc)} "
            f"size={out_sz}/{op.struct_out_sz}B "
            f"out={describe_live_out(op.cap_out, live_out)} time={elapsed_ms:.3f}ms "
            f"{'OK' if matches else 'MISMATCH'}",
            event=event,
        )
        trace_blob("OUT", live_out, event=event)
        if rc == 0 and op.cap_out is not None:
            cap_raw = getattr(op.cap_out, "raw", b"")
            if not cap_raw and hasattr(op.cap_out, "pack"):
                cap_raw = op.cap_out.pack()
            if cap_raw:
                if op.selector == sel.NEW_RESOURCE:
                    learned = addr_map.learn_resource_maps(cap_raw, live_out)
                elif op.selector == sel.SHMEM:
                    learned = addr_map.learn_shmem_maps(cap_raw, live_out)
                elif op.selector == sel.NOTIF_QUEUE:
                    learned = addr_map.learn_shmem_maps(cap_raw, live_out, 0x4000)
                else:
                    learned = []
                for old, new in learned:
                    trace("MAP", f"GPU VA 0x{old:x} -> 0x{new:x}", event=event)
        return 0 if matches else 1

    if isinstance(op, MemoryOp):
        data = op.bytes()
        if len(data) != op.size:
            trace(
                "FAIL", f"memory image truncated: {len(data)}/{op.size}B",
                event=event,
            )
            return 1

        if op.kind == MEMORY_TRAP_AUX:
            ptr, libc = alloc_aligned(op.size + 0x10)
            addr_map.add_range(op.address, ptr.value, op.size)
            buf = bytearray(data)
            patched = addr_map.patch_u64_buf(buf)
            ctypes.memmove(ptr.value, bytes(buf), len(buf))
            allocations.append((ptr, libc))
            trace(
                "AUX", f"trap descriptor 0x{op.address:x} -> 0x{ptr.value:x} "
                f"({op.size}B, {len(patched)} patches)",
                event=event,
            )
            trace_blob("MEM", bytes(buf), event=event)
            return 0

        target = addr_map.remap(op.address)
        if not addr_map.contains(op.address):
            trace("FAIL", f"unmapped memory address 0x{op.address:x}", event=event)
            return 1

        if op.kind == MEMORY_RESOURCE:
            buf = bytearray(data)
            patched = addr_map.patch_u64_buf(buf)
            ctypes.memmove(target, bytes(buf), len(buf))
            trace(
                "LOAD", f"0x{op.address:x} -> 0x{target:x} "
                f"size=0x{op.size:x} patches={len(patched)}",
                event=event,
            )
            trace_blob("MEM", bytes(buf), event=event)
            return 0

        if op.kind == MEMORY_EXPECTED:
            trace(
                "WAIT", f"GPU output @0x{target:x} size={op.size}B "
                f"timeout=5.0s",
                event=event,
            )
            deadline = time.monotonic() + 5.0
            actual = b""
            while time.monotonic() < deadline:
                actual = ctypes.string_at(target, op.size)
                if actual == data:
                    observed_outputs.append(actual)
                    trace("DATA", format_result(actual), event=event)
                    trace("PASS", "GPU output matched captured result", event=event)
                    return 0
                time.sleep(0.001)
            observed_outputs.append(actual)
            trace("DATA", format_result(actual), event=event)
            trace(
                "FAIL", f"expected {format_result(data)}",
                event=event,
            )
            return 1

        trace("FAIL", f"unknown memory kind {op.kind}", event=event)
        return 1

    # TrapOp
    snap = bytearray(op.snap.pack())
    patched = addr_map.patch_u64_buf(snap)
    record_type, flags = struct.unpack_from("<II", snap, 0)
    callback0, callback1 = struct.unpack_from("<QQ", snap, 0x10)
    trace(
        "TRAP",
        f"op={idx + 1} trap{op.trap_idx} p1=0x{op.p1:x} p2=0x{op.p2:x} "
        f"record_type={record_type} flags=0x{flags:x} "
        f"callback0=0x{callback0:x} callback1=0x{callback1:x}",
        event=event,
    )
    if patched:
        details = ", ".join(
            f"+0x{off:x} 0x{old:x}->0x{new:x}"
            for off, old, new in patched
        )
        trace("PATCH", f"{len(patched)} pointer(s): {details}", event=event, level=2)
    trace_blob("SNAP", bytes(snap), event=event)
    started = time.perf_counter()
    rc = submit_task(
        iokit, conn, op.trap_idx, op.p1, op.p2, bytes(snap),
        op.p4_offset, allocations,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    matches = rc == op.expected_rc
    trace(
        "RET",
        f"trap{op.trap_idx} {_fmt_rc(rc)} expected={_fmt_rc(op.expected_rc)} "
        f"time={elapsed_ms:.3f}ms {'OK' if matches else 'MISMATCH'}",
        event=event,
    )
    return 0 if matches else 1


def run_workload(*, verbose: bool = False, submit: bool = True) -> tuple[int, list[bytes]]:
    """Open device, replay OPS, and return (mismatches, observed outputs)."""
    global TRACE
    if verbose:
        TRACE = max(TRACE, 2)
    if not submit:
        print(f"{WORKLOAD}: {len(OPS)} ops (dry-run, no IOKit)")
        for idx, op in enumerate(OPS):
            if isinstance(op, CallOp):
                name = SELECTOR_NAMES.get(op.selector, f"SEL_0x{op.selector:02x}")
                print(f"  [{idx + 1}] CallOp {name} sel=0x{op.selector:02x}")
            elif isinstance(op, MemoryOp):
                names = {
                    MEMORY_RESOURCE: "resource",
                    MEMORY_TRAP_AUX: "trap-aux",
                    MEMORY_EXPECTED: "expected",
                }
                print(
                    f"  [{idx + 1}] MemoryOp {names.get(op.kind, op.kind)} "
                    f"address=0x{op.address:x} size=0x{op.size:x}"
                )
            else:
                print(f"  [{idx + 1}] TrapOp trap{op.trap_idx}")
        return 0, []

    trace_reset()
    addr_map = AddrMap()
    iokit = None
    svc = conn = 0
    setup_fails = 0
    trap_fails = 0
    result_fails = 0
    submit_started = False
    result_started = False
    allocations: list[tuple[object, object]] = []
    observed_outputs: list[bytes] = []
    print(f"{WORKLOAD}: replaying {len(OPS)} ops")

    stage_set(1, f"open AGX user client type=0x{CLIENT_TYPE:x}")
    try:
        iokit = IOKit()
        svc, conn = open_agx(iokit)
        trace("OPEN", f"service=0x{svc:x} conn=0x{conn:x} SUCCESS")
        stage_finish(True, f"service=0x{svc:x}, conn=0x{conn:x}")
        stage_set(2, "replay captured resource, queue, and shared-memory setup")

        for idx, op in enumerate(OPS):
            if isinstance(op, TrapOp) and not submit_started:
                stage_finish(
                    setup_fails == 0,
                    f"{idx} setup ops, {setup_fails} mismatches, {len(addr_map)} VA maps",
                )
                stage_set(3, "submit captured command buffer through IOConnectTrap4")
                submit_started = True
            if (
                isinstance(op, MemoryOp)
                and op.kind == MEMORY_EXPECTED
                and not result_started
            ):
                stage_finish(
                    trap_fails == 0,
                    f"{sum(isinstance(item, TrapOp) for item in OPS)} trap(s), "
                    f"{trap_fails} mismatches",
                )
                stage_set(4, "wait for and compare CPU-visible GPU output")
                result_started = True
            failed = execute_op(
                iokit, conn, addr_map, idx, op, verbose,
                allocations, observed_outputs,
            )
            if isinstance(op, TrapOp):
                trap_fails += failed
            elif isinstance(op, MemoryOp) and op.kind == MEMORY_EXPECTED:
                result_fails += failed
            else:
                setup_fails += failed

        if result_started:
            stage_finish(
                result_fails == 0,
                f"{len(observed_outputs)} output check(s), {result_fails} mismatches",
            )
        elif submit_started:
            stage_finish(trap_fails == 0, f"{trap_fails} trap mismatches")
            stage_set(4, "no expected output in capture")
            stage_finish(False, "missing GPU output record")
            result_fails += 1
        else:
            stage_finish(setup_fails == 0, f"{len(OPS)} calls, no trap captured")
            stage_set(3, "no trap operation in capture")
            stage_finish(False, "missing trap operation")
            trap_fails += 1
            stage_set(4, "no expected output in capture")
            stage_finish(False, "missing GPU output record")
            result_fails += 1
    except Exception as exc:
        stage_finish(False, f"{type(exc).__name__}: {exc}")
        raise
    finally:
        if iokit is not None:
            close_agx(iokit, svc, conn)
        for ptr, libc in allocations:
            libc.free(ptr)

    trace("CLOSE", f"released conn=0x{conn:x} service=0x{svc:x}", level=2)
    return setup_fails + trap_fails + result_fails, observed_outputs


def verify(fails: int, observed_outputs: list[bytes]) -> None:
    if observed_outputs:
        print(format_result(observed_outputs[-1]))
    if fails == 0:
        print("PASS (GPU output and all IOKit results matched)")
    else:
        print(f"expected={list(EXPECTED)}")
        print(f"FAIL ({fails} replay mismatch(es))")


def main() -> int:
    global TRACE
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="list ops only, no IOKit calls",
    )
    parser.add_argument(
        "--trace", type=int, choices=(0, 1, 2),
        help="trace level (default: AGX_TRACE or 1)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="same as --trace 2",
    )
    args = parser.parse_args()

    if args.trace is not None:
        TRACE = args.trace
    if args.verbose:
        TRACE = max(TRACE, 2)

    try:
        fails, observed_outputs = run_workload(
            verbose=args.verbose, submit=not args.dry_run,
        )
        if not args.dry_run:
            verify(fails, observed_outputs)
        return 1 if fails else 0
    finally:
        if not args.dry_run:
            trace_summary()


if __name__ == "__main__":
    sys.exit(main())
