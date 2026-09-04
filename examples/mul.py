#!/usr/bin/env python3
"""AGX compute mul without Metal.

Workload: out[i] = a[i] * b[i] for 4 float elements (metal_mul capture).
Restores captured mappings, submits the decoded IOGPU sequence, then validates the CPU-visible result.
"""
# generated from mul.cap — do not edit OPS by hand (2026-09-04 14:42 UTC)

import ctypes
import ctypes.util
import base64
import os
import struct
import sys
import time
import zlib
from dataclasses import dataclass, field

WORKLOAD = "mul"
CLIENT_TYPE = 0x100005
EXPECTED = (10.0, 40.0, 90.0, 160.0)  # metal_mul.m

MEMORY_RESOURCE = 1
MEMORY_TRAP_AUX = 2
MEMORY_EXPECTED = 3

_MEMORY_IMAGE = zlib.decompress(base64.b85decode(
    'c-rmU4PaE|o$v8yPBO`ykc3GDd8uHCK@$i`prBv@Lj)EmQef3pR=pwOR;^m)YFGQh4kI9;Fbz|&5HXDrDMXBDja92LM5IWS3TmrX'
    'X^4Pm)gmocTn+d6|IZU-)z<FXd%Ji0{n*JbGjq<FbDs0OCZQ&3K9_^x+{i)yxX3}Thso|$aoke-TDXrFHm$j4VQSxSXmix$nKV<F'
    'H`3H)ZOP5F?<Y>GxVYFvO`>N_e%!Oq`_<&fQjAGvPVtIDp|Yem%^PAfyU&)qBD;O|fK7QrY<9@!Wkn-%hvY_PuA5k4OkV5Rc7OYQ'
    'u6+M5A^ZK}iT0K3FIHT9r;*pn?Q09C_YOzxd5knwgY0{y6=yD#vz$C7HKb>Gi+eYb70MfE-<dgSVs5Ibl5b5_k$xSTGw!5N)sT=L'
    'GtYjVaDF^BXKQY7Z9{`A>=<Y-!c=6)9@%4zJ@=^Th?b>h4-M(}btBG>$@OOs@$`B2z!dv=Hcy*&#}J!&t>2XMy5Wtq9D80P&2`s@'
    'Y&k|vc=nQs`by}!%ADYp^Dpmu<-7sGE0YIxy)tR2du7V_kiL>VFu1M>?uzwn%Yt(bu5xF#ew{qg-k)P%Y13;t_Lbo3@>+jsw5)T3'
    'vc6lk8Y{2gXTMu`eOGyhC%>VeIMQ@@WvO*p7e)2{k4pB{GCF12#f5VHBTTE7$IwuaL%blfQd*^aCR`I7<+`hlUfD?dN`scsb(coF'
    'Ub!qDyi%Fh^~&t3;Fa^rx?VZIDlPi4>kqE#)2?u4P_t(09oJfv8#e#xT9nt?TaNaBxt2sfQA?tqs3p-))RO35sg`t=Sl^JA*g^Sz'
    'dr&`S{>OUJRf2#0dJ+9Zy@-CIUPM1pFQR`@z395W;d)J5^!kps-ygc=&=(KY9!fd1s$*d2Xlv;>wyZw!HR&aX8I!Xy>FxAPC}-)+'
    '6`SPc)<OS%<j71ps9CK2s&vbl_P>ZeOEsD9wJYo+qOYdv*DCucYu#n*>Rj)1(-s+LpU(}aMXt*Tg`%-s(`<4=Q8S{i2~Ce_ZRwk%'
    'uaD?ke)N?A?v>clSBB~<JF{bYv|LlN(Bu`Q+iNJQ@Z{<*mCy5!GbM{nd8)0>*^%*ua-Job_PO-GSrhB!d9#^q&w6gOyUDGYWG`TT'
    's@*R$)6C7zGW|0rUY#oCGHIgyn!9wO2}NfY7}Gy@Ql-3Jk~B4`_M7Z*MXhe9XR~vXoWb0l>1OPTj5P%&qvw?P*y@ae0@Js8N`-x1'
    'J>Cl$`$~C%{q%9B%=Gsvj3>3q8yAtBn>t*+&y!>J505LC^PJmnxar?-T7}*xzoMhSjL6M1L1`3KdtQ%_DYxg5;n}O1nI-R=*7hSu'
    'js)lQ$!%T9ee5h#Z%+M>XSrO?a_6K;TBg|{DX;nVjOU&(+?H9UnU^;0K+KlyB<VuT*o;ZG5|k`8WvLTvE-@x#Gk3{^s0q!mCp0hZ'
    '%<=^$cjYt_GULjOTu*Rq+1*Y5?0<;q_qkbSUh0{VnAura5lglEOw{kstg+umrt0_O?OiE}*!yU!*SyI1_a09fF{s^LpT8nrae~em'
    'vinU-lVa5x5YZZ-pD?pn_BXAqM@uI=?ab+^`i^{xX|4U}ozw~w(s$%sOzX8r-#PZ{ep@QHOC8QPp|V)MJ&T<YDY3;}_0t<}Uy*u0'
    'BEy7+#)e4^wzc2bGrlf2M{`6*?C3iK+&e=x-7!9`E@uUG`BK}ya<wkYSxAj8v*#3TO*2|I8{`VIBmF07ee!K7*b17OI-<jb``vgj'
    'G@{LfPmpXd;V($WO}MXQm7OL@R+w;a$$S&;CFz;)@sf7`p7CJ+9`RuR<Kn^ox$$8CoOrN*G#>1KV*H?y{rgMG=g+q(pD!t&FDaid'
    'DW5MXpD!t&KR?+2`1!&9J!8TCJz~NB$HjvEb7R5&Ik8~>sLe}V`CO{~kh>px$L8AhVM4>T^b3pTR)->UmwA!7%TptBSENLm&8DMw'
    'dPIJCNRBnaD-X%BN1F21k9x$<=TG&g?ylyS>s2&+<$6_B|Dj&Z4cl||?RjU}^Uks7oMFOc(zoWCuv}MRVQ~KQ!jm#$wzkMPF*lNK'
    '+tRr5R9h$H7{<%?$7}ymm8Csn-*RnJU3L7JS{$`CD&`scDYo>gY>hRp#@e}#e5$ME*Jb3n*UQ}NK^+f{c<FzlfBvkx-0bRdv#ZO^'
    't}Zvby4>vQa<i+;&8{vtySm)$>T<KI%gwGXH@mvr?CNr}tIN%<E;qZn-0bRdv#ZO^t}Zvby4>vQa<i+;&8{vtySm)$>T<KI%gwGX'
    'H@mvr?CNs!(YjpLy43shk#D5D{#P8&{<4uQ81;^hXWoB)JiE+|OwDer`uJ$pakTIK_?G{bu`Khy?N~PX=m^&AMzzlx$=d$pNVfV<'
    'j%45X)RF9<w((8c?qpVWU51^dY75Q_vTvEDwD9S+-|Xre7XKA`z(3XhwVMC;Vy&%V`D(gJ8;hofLwVWq^MY_rf#yilcm8It*h~l&'
    '>hnK$^`H0r6aKb_4X#&?osk_5l}ksN9rA2#wyUh1@=QH5KQG9T$qddgC-cTwP9zq~Nu3{CZsM{3>K%%G&hwuXN->*4k7fR?K0iAY'
    's+W?g3d^$ze!Z5@1V1RJ8TJGI{F%kl{<ih+pchT;(A9coPQ=vp+GJ7|giLmyr>b<_-dZ1)HGW3eY&~ceM*4<Bt#+}Q`tSs^)vg>v'
    'GZ$|%!7=Jib9;_@S@#@i_Z=-YsK^UPx6U;S%fA_pZob;S-oNKIPYSDlpQmztnKcaGVf(87{kG@pvyn6HvtY#;?0e9JFUz$l^QW1*'
    'hOF~unXu+2xez;=kMAA)G+~@(cyeW?**wgItJ^a}n}_MoB(@Bbmf!!3omItKJX80Ts$r2E?P@e5(N<^%lqEA04TWY#aWZ3RN8zGq'
    'Su%fVL*bU`_WA01U*3<dHom@J+v+clmbENP8=h*Cr`8&O>-6HLJ58))k7qjUStp}4t>IfuS#sdcih`Zx1<6xu>iu8Git7gM%#|}p'
    'MwfIHEH`CKvbMyN(J5^OJ7UExcV-j}G0A+p=cJ9*x%t!U!#g%E>wD+UsshudeRb2*#+-b%7wa4||G<2coVYJH)#OZ1PQ1u7ubP^f'
    'H@~X)YG;b9&t)xKH^!c)l+blGT0(W-nO?6YHRGb-Ck&In8RS{>`UY!z>Au73W0{_m+mn?+E-%-#<#$6~RC@lp|Mf=O;74rvef?mN'
    '|F}o9WQU0jzTb;Ay<%defACDxUSkGt@J#>7O&z6j{;wNT`lc7F8*^WW{3NsPB6ofhr|bDOy=dwOt+mIy=y!SDWcG0CBOOHtH!iE2'
    'y`e$&PtKZBQTn}iO6n%Q+A38ecl0A2L*8m%Y0IU)WS<wyJ^c}H@SD#ps~a0!XL91ys*>*wEy<nuh*$b*`^vhpziHR~#y?Uq=<U2j'
    'a_qEt$@ktFk~`^xijv>7uk88>$4==HPp#Ej)Ol*{#>uAT)LZRss~aDjuiSAHy|=n<VvRmeoL-~b)=jl{S@s!S^UP%X>S}$pWpth0'
    'xAXMX_O;~b8oTH2>Xy@Qv#&Lcksox~<DI_RzPh8jX|jEOt9<tKb~%o|f14bCR=J#7-PneW`g!9oXb;Nmj%W0IMo+mfoOowQ-PnD3'
    '8Nqe$3@3&TN=}-VpJrcoKXaLON4tMVdr@+%P5Jrqlr>jpc<&5Jj=dymE^c3#oI2;~>^TR9$WN+fPX3oX`KjHtwmx)DTYliil+Lk>'
    '?bqb=A4Sa_?bXTAKa84J+m|KB{xHw1u{rv+JhLZeOLXl4f70|sa`e9TtQiNYJI~u?_exCj^nN9#rfSwr{*lR%9J5xl=@Bzs*8NQ_'
    '=71lP^WP9P7j9gb7`>}~nd~?AhX<-9N58f|OP}w1Pp^C86?vwrERmd47d5rUp4F~Av%1_qw`VuYEUX*7t4umpJ<AKq6Lqt89q_e>'
    'xH9M=mUs0GwgwMNJ=31Sqgs<pa!g%CL0x%4-IzKpyyPT1I^JPFVTwJoSL>@=9?jTOWXu0fy)VhBZ`$){t*(8v&bC!sJ1gZ?Z)9D5'
    '(FK(y-f)|<rk8kmHm8@Dc%IF1WhL>+Hk0i|@v$~dPT9PHd+fR?xK}e*{6>fM=m%Xt539<zk5ldAbUVHjrD=~i;j-hkM-2MI&oeuU'
    'b^m;0NnQH3cuLIn`(wuEOVQ37Rbj6sJTx=txo4a(L9<V>P5CM7Nc}Cw%ym=sHx|!nk2TfySS{~l%qcQ0uV<_oXlniI^J~M`=C|yP'
    '*x5+Sib!6e$sTfFuGE<9K6Ab0lKzt5d3cIG&ufjR$bFro_ceU`=3oT4W_*zI3#Ll8yqGb^9<e!NkNvtZ(mKd2@oVFW@S;I7>q+#9'
    'Yi}42Z|LZ~G%r%SYC+o|({gvWf?(@H^Kf(Rw!$|(Q~TnADtoqfXV`Zhu3peE(7x8VYH8J-rm=cKevW*#<4Q}lZ_huG9<R7mO6s5E'
    '9r7u4{(_Few{1;}E@~^$-}adD!mivJU7GY{OwFlDgyVf>mTJ#=ysdG5uy<|viu{DXXo`H_@=C^nfhOrMvSU_xVaqZpr`qsU`Sufr'
    'Ek7<~T6W7TiSU9dnV}?##(Sq|35N0t^e0%Ma`{nh*bmAkJY)P+ExXx!g6BgwYmPK6dov13P3M(s58h~64rR<KHMM&WCZne1t&BCr'
    'rnBco_VwDs@7q;b<Dm!h?~(28>+zlsw+()yvZ-mswnbX1lizPE-Cy2R`~17I?}~1Ao7x?F;-#kV(+BOowJWy8qh`>P*ETenK`Zt*'
    '6x-SoAG4-vP)GaSac_xdmfZVb)1$kBV|h!`Jd;x#AGfEfq`md-mWR6S8DbhA-BfQ&;EDE%Qq!`@Zy#c6A9~py)3({vQq%ZQN81q7'
    '@<g}P64N>E7CGlfcgdM-%CN6^J-2P?-BDlM_-Iqd-Es_jM)n<BTfD5g{6V#q>pMp*kbUlMmwlQu))bk>yEjy=H}Rrf`6VmM*Vo=V'
    'ORi%5%^f8s-tU%pQKEcZ+&?!yaB1GUriBSTZ>drCU2nBsO-r@ZEc;BarD@@!V4GzN>^V19Z)&xluxx2nS3Qb*i-Nrt274{iy=?2K'
    'x8=AnF8i$7R9R>m7oMGO_qok)m964kpEO>d1*PV{yruVo)*&s`(!T6owwAQ4lI>e=>n1H@RkzJ{>#RjvdQYn?jECb}dQZ)h`c<jz'
    'z-~P+W1F3&1uITF*9}LX8}_l^g+#h(E6)#F_CV8e_@kEn?fjNQ+Opr$mfh#!pe6VGrfb;`xR(75*RtP`mObCK=;dpI+IhQc+4mM`'
    '+B+gG`)=2=>x*p5zU8Bq-LtD@*LL*YW?S}(1r0@Vok7dCwdUcwZ)q&7wfC=CTka~?va1HpvbB1}wzhR2wQO56Ki0CpbWF?M6}0Rj'
    'e@V;Un=yW%sSCT7?a$5cI$zrlO3Mx}>L^&GC2v2i*1tC2Zrjze<@5W*gO=^bgO=Sh)T%ApuHtm{Halp+;cHx(6^(Z--L-h%Oo#?8'
    '{5EOTo!@D+HN5l6Drx5*X6z}I7A~#*wuG(oweveYFWUIwBOU9c7g$qj;<vSUg>Tn4nNZVhLH&;J==6%;jM-OepMPK4iPopu9sAo#'
    '&7c>rw=LTq%huGs&%bNi%Ag(lI||I$Wf^k{q^<Yc&@gCUUQ^s#7qs=RV|wd?T07y*hLSyYs-VYg+_WinvZ;Nt!}cFzH~FT-9l3Kt'
    'tv&lex9zb<Zh11Jz`nk0k(|jB(g$>&HPyb`xa__vdks%#%(3r2xkp;<6CHAeyZ1>S_Qd`9O(s5cQN^H_W9w}zs3_T0e`maBgE#o*'
    '`VCFXTq|9_&Gs_2_pZz@mA-6_w3iOA^p@6jaW4^^zuVG2*Ygkhx0YqHZR4u*Y%OYBv8laK&QD%n;oElHxa{UCX{SqrR;ztvJi0Wv'
    '{+@{~y|=X&9_<IT<#+W1jkj&p_UqdtHm;X`pk=*ZUewj1*LSmHNW9O|Exi-1g-tz8eX(tyEw{;-*4cAg)hZd~q+jf_Aim1P{ry{d'
    'pBpPl^xW2_wQ-fyHti42t}JZwO?!deJK-%Y&k5eOpVpbRz#gTk+C-;@BS+us>=U=gYg*`D&05r^_0!*05!BO(`31Ua4tkKTzGF+8'
    '{GRZsd}%B4w-EY!LS1QQ`<wHFb!mg$CVWjYY+B{#<Sh%O^(Vb^8;U}qnuNcrs#w}ZR(qTL`9e!|#`t2B>zy4h+GJ{4Y<(-XZN)6s'
    'zpdzVUSIc{=ym#h+$??G@=(U+A*N%p_G!8XtDRAipFFE-X3m_vMYcu8N}_e=?9<j*d)5W{QVJ!}#QBX?1$G`=d)D~;>=~ifljTUu'
    '<(=#+m*(cA$~zPD6SLol%U1Rd$~%`#^_I)eMK25)ZN+CT(JiyjnWC?U56{U=(big!nev3q7gK}hukQ&~X%B6l8m!tD1i5NXkn7h>'
    '4OVZqH``pC)7dX}@WvjstDZ_md)W5Ar#Po^)#|nlIW5aG78K{y-nQNIdUOtW@ZgQn+T~kio7*!|hvYOaA0OY46R)=G;>~8m^q#fz'
    'pRwCDRd1HM-6Q_aVz2On*gYoPbojlXwtx6kM{!&GJ>}t+ce;%)4#f{`^@`uGv|F^i)ortFG4H%*YkTeC&Ne$5y!Ebpf9QQ%8yesF'
    'z_#SZx8AQRHA}90&|7lD1772Y4>sIo;@8=J=lxjs#t$E8yUUEVqlrE0mG-p{D!XS~_r90$*1KNF_8*-$Y?Sf&o%f`*AI`9!)%Z?4'
    'Zf7HhBK7uj4}Tyd`dg7o+i%T&ux;=k%sri1?|0l8ZF>EHp1G|ha|&`2v!_;-Y7g9PyzMV?4m7Nb#%I6RR(i0#srHpW$ocL*U~BEz'
    '`56leavEPbU`P9w-FChcT5?&FXWz4*-g(J7>1Ez(s<_L|o#GeT{_YR$*^RpwdH2|Jk@?P&3*YwQGd8vjw*6((i~ECf*b!;B$9u8c'
    'X4@7o+uyLp#Ah66E48zz+Na-?&)%`$_V_X*9Bdk&-d|NBqpKZPmt45kTQcMNc;oK19gU{tc^N(87as7uw=1(-o|buT#_qRmDJ3qv'
    '_VN<@IZMuJj3+K>3dY0>?QHj8dv?pAZhLHhxOc70dF{wN*gX8o<%0&>nQhC9w*7}{53jXrahd;}V&7TYQSyOj66a6cR$}XD<Dr8M'
    '_n5>D8}x{^d)HMIhT?}8boBn9HQS`x{q4~jUwPY(pDiCsEoeOSwj9ger9t*s*AE)Jxx&<bxUNHv@7ufe@GF;glyus@c<;fsdt|gT'
    'rEdT1e|@*%>-IC`S*c0PuJrV7z2e()>+}!U`zc!&hV1w?zA%)SJt?D9+R{J2*>RQh2$yUOu6cLNUbE?L&+V;lsWP8k>)CyF>s8Nx'
    'W6<E%ifGI8k@mrMX0^7eG-}7eRD0D=@AHb=Dnf~K#y9F!?>$&$ulmZy;F#yMbo73=KD+VheR7>|bz5Ug^Z9ih_R9C}lTqU7NWHz<'
    'ciw9pWUtI#ZB;P7+ShjMkC)olTK4*R_Bwa$mwCqXZ^*GPK9H|hyJLTYz1KVZSc%F0%D%W<OI^ytaob}>`+xn42ARj#o%2DwsI9`('
    'eQTq<Zj!P4y<$82FgdnL)(?_-NR3_Nw#Js0+iefVi|i*R=WNv(Npj!fwo=(P_2{-XOMV|)nmFhELEZJ|R&LA7{$P)Odr4yUfhC#x'
    'sc$zFz2}+SSGL9nnoy}pt-E+_gMR*-i>f~5nD54x*3H=8P;}6K`q}Q7zg*xQ-7@C3jFtS>e)^0z8?%r7^yjzOW6v)!sfn}p>E|ad'
    'e0z%Yn#moTZ7IyQ?<CKfZ%k<SqQv?88>RoPn{jrP)cNFD<Lv937S)|~u09{TH)BDG8M|9%0oh-fe&)&Y7d20or{zAAYbI<uKAiWQ'
    '&4+BhVDsKngXcR=4xX<+SDz;)hssNI)jmgmi?r+Tks~{G)gF8e*5`ljr@%4q^R2(bel#msr9BaejWMw@^F*{>voot=${sr=Zn5KM'
    's76=aI)>)87V3Up*zFf>)$J2m6~Rd8Z>cCgI+M3^L_L0RB@263X6a9U?TmW-AQ`(mvSoH1s+T>ISyQTtr&Jc_W^M7jEoRsg(e~hs'
    'B4$iTvM?{m-sPH$-EU()&(E)u-qMg<UuSsn`WNgo`8{FI(vPloo`17%S1MUa`!%n%O=cT?GP2~aohIa*t~s+X5$a>AdhV8=wfH^F'
    '?z^k9<Y$l*ic<BjID;z>=k&-5e)BPNQes^3(d~PEV*9SYb86Fa?<(^OEz9BVUe$#+dwuK%34g%=Eje#|MQ>a06X8vjGQX)xGiCEq'
    '+Ya2AGQm&Fk~#XZt1JCoLuHlxK&!Ir{r~Duf?^q;v;KvG`WMa%YDPHc8COo>ka0CE;h#}nY#VDwmKkl=3e~2(*xvZuOuM<6y)>D#'
    'd2Xf|mznU(wf-ftO)S;q+1cUdd?}mkY;$#{eO{Go%oE1d@kmg|!=bb7r_GgGY+BtruFgeWoy+@Vojdlw&s+aG!*%{kNAI@OyPd)B'
    'M8eV3MAl-xySd(?277mFg1?Uo-l^?+r>&3FlHm6m;hNb6iO|tnkq9qnliHB%u|R7_GFnj~J$l05rnMy7-&$TA{GKE|DDz|=``P!6'
    'yVcI=y<6=ZcUxPr*397jdEo|W3;r7WwZiWa(%<K6y}bEoy<AXL5clMh2NY_(tk6%+_Jexa)oZvmQPfqR`ww}ls$iREDk8yAN6YMd'
    '_FTJduB<xGGV<G-P+iYpt3=NQw+FR;N^tZ(!O`V!6Klg}tKDbR!EkUz6GqJnd-9vdac6g(W51nM1<%-{^jomI_~_poCcT6nt3&@@'
    'IWZtOVlZ>h{_?bwM#<kzo-yU55z@=g?hzg!XLe0?II5qL7?D~&NRKkB;$%6a2`|Uxu-T(FRmvDLp}KE4NB8L8wa3s%`JjmGabB>;'
    'sF(9)B*-4&_P9p=2H5UV-Cxu0F(cD`#-(l#`FWJg^FP`{&#HQ?`;4wF^jK0VxA)hy$C}W?9jmIMM31#UIM(D%l_k1It~=I6pE%aY'
    ';Jjv!b?22FoooxqF@~O}TO>xL>tCHGy_=;@+gewfAN(}KKHn8xni#dUe2Bgu{4`_Uz}gI3tBPK>U%URAv!=7_r`O>b?*0{BdzSVS'
    '<Ie7?4fZ}3+WUC4R=E3lw01<N1+~7bmJHY$)OuH2!lTA&U0is5#sssuOz&bM=s^b71Z%i)wYHwNj7rKFHSWYniT;i4iCgvTN4(^j'
    'yig)JaHq{p%M!!QI{ghpfhm;i9P!e@`KEK=PW!b<DvjN|N&e{8Zk`xt%H{8HlOqzj=B4QL<f!Sk+mB996os^8`VYLIVW6EfWlu2W'
    'vP=JQ?J_%%HOhqaysPX{yXReL>c+KuI&T};ksp+2rS>76(OnypCOLklu6wgbPkKTA`fi^0#RF$$&RpD~qsbciUCD@g&up(>mK;6H'
    ')45T<cF#Q1x-2=;u9z>1)>I8Jrohasep&Z8IV7zjD4&*5HQC3M#DJQh1jf_`rI()<@pY>@yHzr8yR5^D68(a$J4e+VyfG!&ug>nX'
    'duiR5UT%{KOyY#R{W2R%4u8pRy}LLu>XuDfm&UBzt#v8?f-2k3mCfrn%kG^$W=6aI<ayMa`gg~jr`E{tneuDp_e`h$x=d?b{_-;O'
    'Yg5)S>WDS7dil}MPJHQ>P3vu`b`E$+o{g!C_mNt0+65_6)+61&PY92z4foQT-(<_7$X1x9hiVpuj{Y5TXaCh@F?)3{w|&99v$QjR'
    'd!*|(Fip3aa`}f2i9*vJvExo>;d92G*9qJ0`f1#<rv4_HW&82O(49KVPMokk8qwcS{X+k0J>hLPSx0AniGF9qitNixx0`ku^O7gL'
    'V2f*ht-Z$wk|xpL7+*%Z6SfEYM$G{k>5~1QiRYU6nTY`lW=lDBMmI^xc+-P+&_DR3?14c$cw%HmSn7XxRIcl9<!`^Gr|j&vy(4Bi'
    'duG>PVY2&e>yW)BjEZWH5H1R~)~y<Dm7fANB<)t)8;bwbR&m{`?K8Hj(ycn|Rz2NTMO|ABbA5VepOn@sWUFB@yVX+-nO$3L?wUQ#'
    'tX`|*$Xp#|uI=jiKV$rme{U1~ONXY_CMti+G;>mNw=L0D=_?oJWw>`cJt@z5{WqPr!^}Hj>*Ae9%P^R=clHZr&fAZf!P(E8J>*k9'
    'Gp|)fyl~O!cK^9{e5?p-?<QAQleAa*l>KVYyI$8yJ-6wMrZc=<U)`3Ux!JSVIz|6x>?s{zul;C-SXJB>jKsyCG7>NBo$Ib9(esRY'
    'nO!xlF!fT$n&PHXu05H(&DNsZGZWsXt21>zJWl`4N9V0Q`^dbtPdB}S{=uv`_%};Ok2^1OqAevi@6YqPJ}uisrH*!bTkN~p*_(83'
    'HZN04vA3tCc<kTtf0puX1^@s6000000000000000000000000000000000000000000000000000000000000000000000000000'
    '00000000000002s?@a6r`=#9e&pu-1e}C7XH_n)P`#4}9c@@-$zc0Dw%5K4Tq4KatdHlWU;W`1^15OW78~^|S000000000000000'
    '0002Me=jL_{eAzlpVYhfXHS2}j#w`LO|sDnx#yBkS)O}cGFdP=>ACkMUmclvHN|Zw+3?+xhg014lDEB3eOrp#Pja!9;`Wz3V5Pd_'
    'NbVhR^RH6f@gyHF%X~c59anN|#qsy0y5mcZ$@tYBsqS+m-x_%T4^rLdNk)D?W?8EHT*->afCZ`U^CfTWKK8w^I}gb>>a*VnyYrD;'
    'yY;KDgxz^b?##>D8FuF<`R&Z@KMT9_l<f9?yd~_;SMq_%ZV!arc}rd}ZfaB5oxkL$aOsc2?m8svt+2Zu$roR%sSUg9lKhH)@aC|)'
    'KFPOFdhmN;cb$^|e(;4QVRyZf-&ykIMPYZ{lJUGqJnXJt@`KjyAEdc*ko;fEs{fGY%0sd_<$u4G=E_BK(*14w(p>pSo-p$2_B2;c'
    'l0VA2_N6peUXm%_`q^`7uG}QoT|4I&X|DVv_uVvMTbe6J$!~4F<cTy_o|3Irnk!e$IWr$gbLA`9?)7>w&6Ts{{pH>6Pjlrh>2)jK'
    'nC8k|a>4R%Y)EtEFZoYr>|dAW?t^aMJnzmlcRwTtKYm(6n!7KOuU(S!!!&n)Bv-fktJB<llAO`^#8qkTeo0>O(pPRtbN5Yh^TOKi'
    'r@8wl=|A#eO`5xpl2?wnK9T0`r{vPs$kH@-UnQ%{o2t{?{nh(**H>>!bN5;DA0xvTrn&nq`Gc!+Z%lLdU5}gU%};apU$XmqDV^!A'
    '9!MT6KI#2*S05x-j;VY%-PH@pNxyvPV7jXxk|+M8<ag<=o=Dz#-=n`xclAZ`TN^IfpYH07<e-%U_olo0Bbj~u2fNc<J(8Sy!Rx!y'
    'U44>#d-iXCo$l(DWXgS^7t>w+lKf?C@GsL{J(D~&>(Xb_U44`M`41m>Cf(IL$$wpP{PuKL|0G*ax#{QWt{zHGdnx_NbXOlGFUwrH'
    'CEe9a$%Un-ZBBRfQ}X$r?%9;?>Z#=Z()!2JU451Ohv;RGrn`D8IpDRiKTUV_SMvQc2RxMS>apakpLYLAx~tEUOZNHA>8@T&&b+w$'
    'kJDZKmVEHp6YouT^;~kxE2rO+?&`bbd4ntOPIvWQvg5Mv-Iea@zn<Tet?ScWJJ529WoSx!(A<2^+H}`0B>Vkh{hD;wJ|xe$C{0t^'
    'iDb#puic*R+Kc3e{tG`$ckM><q`RlqrMvbcS-E@b>U7tRB<sFD_11LPo+Mw&|JAB=*RCY}t(UG$ckN5ht0bf;?M(90f%PlWU3-(f'
    'IW|F4+MSleaqlG4UHjA5f84M<-L*r>i$~7Vl=i6SaYHXnX_xwWGhbSk?%Jnh>gtB2>8_nhP8ojnchg;amAv}B3QcLZlBfTyucowL'
    '$(v$-yeZwaW6AO17Z;_w_AEL3w8s{vyLPSj{qXt)>8^cieJERXW4deSk}Z!dji<ZzuJ?1<g8AvL-Al%-bl3jVb>KHgBCa2hoW3{m'
    'VZ`+Zl9w#({qGUiFGvo!uk>)l^$(J5XH5HJ#Pt)B&!=2_DB}7H$>Qhhe;;xEhUE6|KKD+<^&gt1yQcIbl6$kKza4S?iDd8PKX^0Z'
    '`W4BPIeXuTxc)`=yJXbs5!cU1cFg_$YZ2GqNN&91_j@C*-;w;)u=DpsT>m4vc<ttni0g+WpIkpeQ~D#xYfs$pn~3X|^m=}Kil+2W'
    'lIOj%?&XN<rzHFJD%F(!O7h%_hhL1ieoHcO{*)IYuK&_<KJz!fjJSSG^4qUp|9r&tXOh*!dTC0(Ci$hv!#g9cf0G=0_Us)I*Uw2l'
    'W3n`*zmxpwdyj07xPDJ^<|)@a9dZ4i<Q3N!X-Yq+_w9wf+aj(%)bsn|+9xBfUzDu5{_?F6*FS1`et(#z^pkqt*LFS;as8#1fBN>#'
    '5!Y|(amU>Lc*OOelE<Z8-xhKGsAT5!nVQm{>hUtmG^JmaTrwy}Q~FoQ<*N@p8gc!s<c0tE$|Dii-%2hm-}=*t>vtui=RWXo#Pz>g'
    'FBbjip@{2;wLBib^}&eik0pO%zW<Ym>z5^m4_)>^#P!dT=S*7C9C7`$<a48z+#hlMwO;?>r9Y0iep|BW+sXSPuK$+Y++2Ha#P#En'
    '<8HlkW5o66lD7}|@jVgOuWNlD`*>5t_3x6y_C0@h#P#!9U%LNxL&Wv>k{KI4P3iX~pMCTMP3iw7N0g4zlyN}Y-TVKfDdT};q}L6a'
    'GA>9S|E<+Oin#GX^4)%IYa?!)kbLXi*YAwD@j~)zA0DSE<A#=hQMsm!A9^3Ixk^*U5k3Ad>KY<$JkfeHYRBynH?HXQt`BR<_@eFi'
    '_|cj&&PewB=CztK-bgNcs;MsG#vN_nX}`TK;>I7XhXaZ<WgL>c_4vy)WjxaMx~uWlh#Qx*J<NT(HsZ!7$*(^BMNJu}^m<?WrlyQn'
    'l0SR+@s$xbZfSooE?ZN^FYR})o24n^m~J<H-7OI}o=MJq>W?cTZd{Z6!JbK)GQLT^lDt(@#yQC+cKq)95jWmxd%Jalri^=%fB5Zc'
    'O&R~R-aT??dBlx_T7Ld?O&JgMyq>yCQ^rMY|Hjvp@lpHH+rO$Q<D}MuyMC64xbafkQLiFR88`JlzxrKG89ya|5jn6l;>J<!cNd(a'
    'DdVZOlj)CqH{!-s$(t@O(3J62+r!h#G-aICe(2iwsv~Z^)pELEj;4&el26BWERMMGSI3`M&d`)`So@)`-=itxvE+tfd73gVOWvEG'
    ')RggA`-9P8O&O=PKl;`UnlfH%`+DW=1raxHYyG<L5=|MuCC@ti@{JKUj%#^tI7d^)bM61G`$atB#&xZy)23+3_%8X#h%NIYZk*Ts'
    'PdQUl#(T;825gE&+_<mpFRxrv#(%v(XT*;9ZXO_c=jeE+@8$!Ni^>*#=(~A=<o!LDe&D<Lf#lqM-~V^t%@ZU~yzRF4eK%i_EFQl8'
    'u<zy#lKE>Nc+Yq92g%iMJ@H51%_Ahw3jgX|-_0lVb6$J>kniRdlJT0(KlpBbA^G&-9-1=Gko-;mA(}GZko@`k6E$VtA^G6qDovSx'
    'NVY%zZ<;a>k^JtD>VD_D`G{oi(#PKR-MmEd_vh?>%Xjk=J^x-|O_`@i)_;AFrp#9)e|Y{3O_{eyPTp~Yrp#X?FWPy>>%N=ENH(7L'
    'i~YWv&q!uhe(;*_<~5Sn?HQyg^Bc)u@1CV8^Bg_?*-JHLz9ad<X^-vk-MmM#Y4Pu0_1*kOva_N{Q|3XE85dV-%6v%AYwt=;nHNc}'
    'dSYk0@8(BZekNN}=1G#5et(Ll%$FqZyJ4}W%$xM}jX!(Eck?H`e_xDf$~;Q)Wiv%n=2McV^jM}T^D4>9FW>Q!@8(yMSDId$GS8Ac'
    'vhzYsnQ!U!?Yi>?-_5%uXAJn=uY5QElH7mGC{3A%Nw$t&s44R?$z9!dKJUAEndHo@JWZLONe&<ObxoP4Nv`|WW6%0-z9#w7zNn_m'
    '+q9isbFrq(-}JhB{bYyl=5dmPf7MM>=5t!^chA<8d7akJl@I>Hck?^RXK#*b$~;dpv;HzoneR!i|H<P|`)=MRdD4shHD&&%<rVst'
    'rpyB+x0Jr{bKlJe^>~%1YRbG&@@q9KG-ZA$xv=HXlfIiLYPsw`S5xMTk}EPE+UmP`qvWBJPSBM3qt>6HF-@6AYP}k^cZ=`llaklx'
    'e_2!Jm6A`G`!r>Ksrzs1qbc)DEth$5O_^^>hWozxxbNnjdf#i$)s*?C<d`Fy+I%+;l}wvZqABxH$#Iw8swwkQJ^w3wO_`rcmVEho'
    'O_`@^d3yUF^WA(^^52r@Y0A7+>-!&{Z1LUvRdeWQO_|3^UOf69O_|S1dc9B5lzFXW|F$1!%KTQ_$;d2CndfRbeDg+4neXcTU-<sR'
    'zMJ<-=AAcJQ|7;tRR`X9$anK#EtjctG-W=l?fq-J9`xP3ShD=f=WELRShCL>&;7)A^JMKuCeF~5`Lg8Ui?%=DyLq$rM?<G-%KTZf'
    '_R($4zMDsDziOsv%6wXK&EY5S_uaf&^7XY-G-ZCR_c#5iANy{et>a4XX__+M*7AArnfrV<@78ub`D{&@e@pK8mly8!-8@|T*U}3$'
    'Wj-!h+0e1kck^<|vX)CVWqz*hasKb_@!dRK$ARB|LsRDKlJgIDHu-MeF8PhSZqk(byVlnuQB9f0Oa9^ywVE=Ym%O8Tpr*|0C3iov'
    'QB&sk+TSl5tts<-9e)mQy~}s=eaXAbxtcQXmmG2XtBt;!|7*Q|=^9O02WbD)Xf$O#pzWo5ji#&%B$F9=nzBC7da!b%rmPbrH#{^>'
    'Q`QUGuD|x|k9@aokUX>L5=~h@=>7P&_tyGu9ii?0H{aEi^@Q&C)QOt1uF&yz{Qa7;zL5OzA0}(cIwP0|>{{cy^@f)FZ?Dyqb%&Pk'
    ';%=I<{?O04yFpXdAzE+$>2yt5k4S!T(ar|ntxL4tjQpCWtWWg#SEXvoIz{&zSf?rL6|MIdj?|QOi?-XI&(`~H{i5~y%U5a2I!0eN'
    '8Je=5(fT}Wt){GNv_EaH(3JI!)^ESP&Ufn^E%&>>qbchhtq0q_pegGf9VaRu)|B;+<k?r9uPN&wZ4U?ETkX5`klyFFR%*(+NXzlU'
    'QJS(ok}Mea(yhK*CrLiG@>`m+UXskYxSyu1n{?jt!^bpb{UmwI)GAF`M``=IJgh0}DakMYah;~DtF-_6{Zvg^UunO7!8<E`x6ab}'
    '&=+sfl=YV6>HqpAO<8wIjz4+#4}7=&k{nrnlcuc0^!{%iqABY!E#G^eyTy0wGCf}8+nTaI)A{k1lQd<WCfWDRpKHo`P3!yh*J{eT'
    'P3O0l_tTX1o9@49i>9pObRO`Xt2Jdkr}b@hUrkxpY5#QM6PmKV)BBQowWh4|be#S27c^zPr|t3gTQp_er{({_TuoX3Nw&;6QB&4|'
    'dR@g&Y07#~=ZiCM(3Ewd<ep!itSRe5$*UfGPE*#2lJ~qD*Oc|5Znu1>rmP#aJ}zqip6}L=IzRr^_cUc4sr5I0hNi41bzO1O?-IUS'
    'S4vjw{h_9;FLnD{r)$bOQ!=$Nq$%r7?T5SnSX0)WlK=eF98Fn&YQOiJ<27X+s@MGwPio3~ROcz-Z)?iBROfBIN;PGDs^>MY<Ga3F'
    'r|LK}@)k{5uj=?XVTz`#TeUr}>0IKw^{bxuIX~8vb!;&Izf@D!v)T?f^wX4et)9>HXEkMgtMiNT)ta)-)p^HFXK2cLSMs#J?=JS;'
    'x>xJ{`x`W6{j2S^XpW|=gSB6{^9!1?9@hJF)w7ziF4p?J;Jcc#KGu4=_e@P$Cu@67ez3@Q>t&s%FKO14b+hC@K7Ey@te>@?npLPN'
    '>u4SC$~qSMZauBnKYg{PtgE%(d+=OMSzl|rzbr>n*4dKZt9nXP*4sL7Zn#NP*4>g{7<8tltiQFMyw`c7@7Cdxy)u8QDeG}9mrMRt'
    'Q`Y6$|AdEY%KBW#k=GBzeYZ~6cAV3sDeHBeKh67^rmWi~(@TpqW&N(}-u&0*`)(bt^Re^q)RgtSZnyJdO<C9LahK(5%KBc{S4(!s'
    'e7DZmdbPD)Q`Y;s4w+P`DeHc{-bkLNtp9!f`~d&}000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000Q?V7Tud1N0000000000000000000000000008i}R{oh=WJdp%`yV;ddE~CfKmC5}vp)U='
    'Gu@0d58Cg(Y`6YON;sThdW5_qXB;_Vj~+6e_P@Vn`FVeS?*jKY#Xe55k2L$}ZXf;ZqlaFeF<JJJ?zTJGKJx8D4x4QsC)!6(`xq`~'
    'Vjp2G(<4U)+8kgXDfW?JAN}p4mwk+|kJ0v#>b4Vk_WO{1bhD4X_Hn#@oMs<m?4$UY?S!1OZy#T<k6imW)jrO!k0Br1PDJc$eeB~n'
    '`xs^)W9_5#Q??Vm?dv)A@kRSM-9AeG#CAdoe5ieV$vy`Cne9ZGeSegF4E~Jm#7MhM(O<BgDEtez6CroMQrtc!bR_*i=tzpafmfRY'
    'wgDVDBDb+ps{4`d_Sri}j&$z~_AUQ_J`4Z=00000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000PxqB8jgNlG88<@'
    '<@*gEd;Nehv9NnC@9jzXX#Z^ckf+DlM-ThxX&=YiM=$&6Z6A4m;t@LLKV#DLYajc_wT~?O$aKdocaPX79wGaPY0Cbo_G|c4uCHtR'
    'j|-V&F2Z<J1ONa4000000000000000000000002M-&A)K{G0y&KZMN4l)wF1r2d)ruJ(*c`P4H%Ml7QLKM8+zv2J?Yf{z_Pb|iRx'
    'vCA5lD_w^E#Nkf(jF0R3|AY`ntdGB6{u%pwpH?>i^{N4PAG%N)00000000000000000000000000Koq+r<>s4l8-Wf)qk@dI_8mj'
    '%=Z8Q00000000000000000000000000000000000000000000000000000000Q@cVGp+SUx|yD5)fkhN8jBjU%rl|I6bt|W00000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000{GIWl_Dd{eQf-9X<Jj*jL#EP3IVA-E000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '000000000000000000000000000000000000000000000000000000000000000000000000000{P)mPzJy$QE&%`l0000000000'
    '000000000000000000000000000000000000000000000z+X*d^uxao+4PKgT%OneOKgKYFT1|mdy?j)^TMG&v;CT{2HRJDZ2RcD'
    '|K#?|8)qLC#@ufod1w9~`l;Od'
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
        struct_in=ResourceCreateIn(type_version=0x10001, create_flags=0x1000101, alloc_size=33840, heap_flags=0x10000, stride_or_count=0x38000000, create_info=24),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(gpu_va=0x104f78000, gpu_va2=0x104f640c0, slot_index=1, heap_size=0x10000, cookie=0x6f1004d5, type_tag=0x8fa0e, out_heap_flags=0x10000),
    ),
    CallOp(  # op 2: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x10001, create_flags=0x1000101, alloc_size=1136, suballoc_flag=1, heap_flags=0x20000, backing_ptr=0x10fcd4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid_tag=21, gpu_va=0x104fa8000, gpu_va2=0x104f64180, slot_index=2, heap_size=0x20000, cookie=0x6f1004ee, type_tag=0x8fa0f, out_heap_flags=0x20000),
    ),
    CallOp(  # op 3: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104fa8000, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2, backing_ptr=0x10fcd4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid_tag=21, gpu_va2=0x104f64240, slot_index=3, heap_size=0x20000, cookie=0x6f1004ef, type_tag=0x8fa0f, out_heap_flags=0x20000),
    ),
    CallOp(  # op 4: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104fa8100, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2, backing_ptr=0x10fcd4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=256, rid_tag=21, gpu_va2=0x104f64300, slot_index=4, heap_size=0x20000, cookie=0x6f1004f0, type_tag=0x8fa0f, out_heap_flags=0x1ff00),
    ),
    CallOp(  # op 5: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104fa8200, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=512, rid_tag=21, gpu_va2=0x104f643c0, slot_index=5, heap_size=0x20000, cookie=0x6f1004f1, type_tag=0x8fa0f, out_heap_flags=0x1fe00),
    ),
# ── queue setup (sel QUEUE_CREATE / NOTIF_QUEUE / FINALIZE) ─────

    CallOp(  # op 6: QUEUE_CREATE
        selector=sel.QUEUE_CREATE,
        scalars=[],
        struct_in=QueueCreateIn(exe_path='metal_mul', queue_flags=2, unk_mask=0xffffffff, enable=1),
        struct_out_sz=16,
        cap_out=QueueCreateOut(queue_id=1, cookie=0x6f1004f2),
    ),
    CallOp(  # op 7: NOTIF_QUEUE
        selector=sel.NOTIF_QUEUE,
        scalars=NotifQueueIn(ring_size=256, ring_flags=40).as_scalars(),
        struct_in=None,
        struct_out_sz=16,
        cap_out=NotifQueueOut(ring_address=0x104fc8000, queue_id=1),
    ),
    CallOp(  # op 8: QUEUE_FINALIZE
        selector=sel.QUEUE_FINALIZE,
        scalars=QueueFinalizeIn(arg0=1, arg1=1).as_scalars(),
        struct_in=None,
        struct_out_sz=0,
    ),
# ── resource setup (sel NEW_RESOURCE) ───────────────────────────

    CallOp(  # op 9: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104fa8300, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x10fcd54a0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=768, rid_tag=21, gpu_va2=0x104f64480, slot_index=6, heap_size=0x20000, cookie=0x6f1004f6, type_tag=0x8fa0f, out_heap_flags=0x1fd00),
    ),
    CallOp(  # op 10: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104fa8500, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x10fcd54a0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=1280, rid_tag=21, gpu_va2=0x104f64540, slot_index=7, heap_size=0x20000, cookie=0x6f1004f7, type_tag=0x8fa0f, out_heap_flags=0x1fb00),
    ),
    CallOp(  # op 11: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104fa8700, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x10fcd54a0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=1792, rid_tag=21, gpu_va2=0x104f64600, slot_index=8, heap_size=0x20000, cookie=0x6f1004f8, type_tag=0x8fa0f, out_heap_flags=0x1f900),
    ),
    CallOp(  # op 12: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104fa8800, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0xa2709e210),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=2048, rid_tag=21, gpu_va2=0x104f646c0, slot_index=9, heap_size=0x20000, cookie=0x6f1004f9, type_tag=0x8fa0f, out_heap_flags=0x1f800),
    ),
    CallOp(  # op 13: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104faa800, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0xa2709e298),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=10240, rid_tag=21, gpu_va2=0x104f64780, slot_index=10, heap_size=0x20000, cookie=0x6f1004fa, type_tag=0x8fa0f, out_heap_flags=0x1d800),
    ),
    CallOp(  # op 14: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104faa900, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0xa2709e5b8),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=10496, rid_tag=21, gpu_va2=0x104f64840, slot_index=11, heap_size=0x20000, cookie=0x6f1004fb, type_tag=0x8fa0f, out_heap_flags=0x1d700),
    ),
    CallOp(  # op 15: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104fab900, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0xa2709e8d8),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=14592, rid_tag=21, gpu_va2=0x104f64900, slot_index=12, heap_size=0x20000, cookie=0x6f1004fc, type_tag=0x8fa0f, out_heap_flags=0x1c700),
    ),
    CallOp(  # op 16: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104faba00, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0xa2709ebe0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=14848, rid_tag=21, gpu_va2=0x104f649c0, slot_index=13, heap_size=0x20000, cookie=0x6f1004fd, type_tag=0x8fa0f, out_heap_flags=0x1c600),
    ),
    CallOp(  # op 17: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104fabb00, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0xa2709eee8),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=15104, rid_tag=21, gpu_va2=0x104f64a80, slot_index=14, heap_size=0x20000, cookie=0x6f1004fe, type_tag=0x8fa0f, out_heap_flags=0x1c500),
    ),
    CallOp(  # op 18: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x10001, create_flags=0x1000101, alloc_size=1072, heap_flags=0x10000, stride_or_count=0x8000000, create_info=24),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x28000, rid_tag=21, gpu_va=0x104fcc000, gpu_va2=0x104f64b40, slot_index=15, heap_size=0x10000, cookie=0x6f1004ff, type_tag=0x8fa13, out_heap_flags=0x10000),
    ),
    CallOp(  # op 19: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104fabc00, parent_gpu_va2=0x104fa8000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x10fcd4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=15360, rid_tag=21, gpu_va2=0x104f64c00, slot_index=16, heap_size=0x20000, cookie=0x6f100500, type_tag=0x8fa0f, out_heap_flags=0x1c400),
    ),
    CallOp(  # op 20: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x10001, create_flags=0x1000101, alloc_size=1136, suballoc_flag=1, heap_flags=0x20000, backing_ptr=0x10fcd4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x40000, rid_tag=21, gpu_va=0x104fdc000, gpu_va2=0x104f64cc0, slot_index=17, heap_size=0x20000, cookie=0x6f100501, type_tag=0x8fa14, out_heap_flags=0x20000),
    ),
    CallOp(  # op 21: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104fdc000, parent_gpu_va2=0x104fdc000, heap_flags=0x20000, heap_lane=17, create_info=24, backing_ptr=0xa2709c000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x40000, rid_tag=21, gpu_va2=0x104f64d80, slot_index=18, heap_size=0x20000, cookie=0x6f100502, type_tag=0x8fa14, out_heap_flags=0x20000),
    ),
# ── shared memory (sel SHMEM) ───────────────────────────────────

    CallOp(  # op 22: SHMEM
        selector=sel.SHMEM,
        scalars=ShmemIn(size=16384).as_scalars(),
        struct_in=None,
        struct_out_sz=16,
        cap_out=ShmemOut(gpu_va=0x104ffc000, size=16384, shmem_id=1),
    ),
    CallOp(  # op 23: SHMEM
        selector=sel.SHMEM,
        scalars=ShmemIn(size=16384, map_flags=1).as_scalars(),
        struct_in=None,
        struct_out_sz=16,
        cap_out=ShmemOut(gpu_va=0x105000000, size=16384, shmem_id=2),
    ),
# ── resource setup (sel NEW_RESOURCE) ───────────────────────────

    CallOp(  # op 24: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, create_flags=0x1000101, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000, create_info=72),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x68000, rid_tag=21, gpu_va=0x105004000, gpu_va2=0x104f64e40, slot_index=19, heap_size=32768, cookie=0x70100503, type_tag=0x8fa15, out_heap_flags=32768),
    ),
    CallOp(  # op 25: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, create_flags=0x1000101, alloc_size=50224, heap_flags=32768, stride_or_count=0x48000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x18000, gpu_va=0x10500c000, gpu_va2=0x104f64f00, slot_index=20, heap_size=32768, cookie=0x70100504, type_tag=0x8fa16, out_heap_flags=32768),
    ),
    CallOp(  # op 26: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, create_flags=0x1000101, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x78000, rid_tag=21, gpu_va=0x105014000, gpu_va2=0x104f64fc0, slot_index=21, heap_size=32768, cookie=0x70100505, type_tag=0x8fa17, out_heap_flags=32768),
    ),
    CallOp(  # op 27: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, create_flags=0x1000101, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000, create_info=64),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x88000, rid_tag=21, gpu_va=0x10501c000, gpu_va2=0x104f65080, slot_index=22, heap_size=32768, cookie=0x70100506, type_tag=0x8fa18, out_heap_flags=32768),
    ),
    CallOp(  # op 28: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, create_flags=0x1000101, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x98000, rid_tag=21, gpu_va=0x105024000, gpu_va2=0x104f65140, slot_index=23, heap_size=32768, cookie=0x70100507, type_tag=0x8fa19, out_heap_flags=32768),
    ),
    CallOp(  # op 29: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, create_flags=0x1000101, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0xa8000, rid_tag=21, gpu_va=0x10502c000, gpu_va2=0x104f65200, slot_index=24, heap_size=32768, cookie=0x70100508, type_tag=0x8fa1a, out_heap_flags=32768),
    ),
    CallOp(  # op 30: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x1ff80, create_flags=0x1000101, alloc_size=17456, heap_flags=65408, stride_or_count=0x18000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0xb8000, rid_tag=21, gpu_va=0x105034000, gpu_va2=0x104f652c0, slot_index=25, heap_size=0x10000, cookie=0x70100509, type_tag=0x8fa1b, out_heap_flags=0x10000),
    ),
    MemoryOp(  # op 31
        kind=MEMORY_RESOURCE,
        address=0x104f78000,
        offset=0x0,
        size=0x10000,
    ),
    MemoryOp(  # op 32
        kind=MEMORY_RESOURCE,
        address=0x104fa8000,
        offset=0x10000,
        size=0x20000,
    ),
    MemoryOp(  # op 33
        kind=MEMORY_RESOURCE,
        address=0x104fc8000,
        offset=0x30000,
        size=0x4000,
    ),
    MemoryOp(  # op 34
        kind=MEMORY_RESOURCE,
        address=0x104fcc000,
        offset=0x34000,
        size=0x10000,
    ),
    MemoryOp(  # op 35
        kind=MEMORY_RESOURCE,
        address=0x104fdc000,
        offset=0x44000,
        size=0x20000,
    ),
    MemoryOp(  # op 36
        kind=MEMORY_RESOURCE,
        address=0x104ffc000,
        offset=0x64000,
        size=0x4000,
    ),
    MemoryOp(  # op 37
        kind=MEMORY_RESOURCE,
        address=0x105000000,
        offset=0x68000,
        size=0x4000,
    ),
    MemoryOp(  # op 38
        kind=MEMORY_RESOURCE,
        address=0x105004000,
        offset=0x6c000,
        size=0x8000,
    ),
    MemoryOp(  # op 39
        kind=MEMORY_RESOURCE,
        address=0x10500c000,
        offset=0x74000,
        size=0x8000,
    ),
    MemoryOp(  # op 40
        kind=MEMORY_RESOURCE,
        address=0x105014000,
        offset=0x7c000,
        size=0x8000,
    ),
    MemoryOp(  # op 41
        kind=MEMORY_RESOURCE,
        address=0x10501c000,
        offset=0x84000,
        size=0x8000,
    ),
    MemoryOp(  # op 42
        kind=MEMORY_RESOURCE,
        address=0x105024000,
        offset=0x8c000,
        size=0x8000,
    ),
    MemoryOp(  # op 43
        kind=MEMORY_RESOURCE,
        address=0x10502c000,
        offset=0x94000,
        size=0x8000,
    ),
    MemoryOp(  # op 44
        kind=MEMORY_RESOURCE,
        address=0x105034000,
        offset=0x9c000,
        size=0x10000,
    ),
# ── submit (trap0) ──────────────────────────────────────────────

    MemoryOp(  # op 45
        kind=MEMORY_TRAP_AUX,
        address=0xa2708c660,
        offset=0xac000,
        size=0x30,
    ),
    MemoryOp(  # op 46
        kind=MEMORY_TRAP_AUX,
        address=0xa2708c690,
        offset=0xac030,
        size=0x30,
    ),
    TrapOp(  # op 47
        trap_idx=0,
        p1=1,
        p2=64,
        p4_offset=132,
        snap=Trap0SubmitSnap(record_type=2, submit_flags=1, callback_0=0xa2708c660, callback_1=0xa2708c690),
    ),
# ── GPU result validation ───────────────────────────────────────

    MemoryOp(  # op 48
        kind=MEMORY_EXPECTED,
        address=0x104fa8200,
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
        buf = bytearray(raw) if raw else bytearray()
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
