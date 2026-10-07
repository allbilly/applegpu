#!/usr/bin/env python3
"""AGX triangle render without Metal.

Workload: red triangle into 8x8 BGRA texture (metal_tri capture).
Restores captured mappings, submits the decoded IOGPU sequence, then validates the CPU-visible center pixel.
"""
# generated from tri.cap — do not edit OPS by hand (2026-10-07 13:42 UTC)

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

WORKLOAD = "tri"
CLIENT_TYPE = 0x100005
EXPECTED_CENTER_BGRA = (0, 0, 255, 255)  # center pixel, metal_tri.m

MEMORY_RESOURCE = 1
MEMORY_TRAP_AUX = 2
MEMORY_EXPECTED = 3

_MEMORY_IMAGE = zlib.decompress(base64.b85decode(
    'c-rip4`7qkx&P1mHfi&Qwx$&j5HNHtwzZVPz@Zl~)WU@hS?NWua@AWZY|7LjKi$-AU5JHI23g6#Va2X?%Ai6-W}Q0iN=1fD9WZt1'
    'l$8t|GGMh+hh7Z7^E~fKnl??F0=nJ1??=;b^5#9~Jm)#j`Ik3&5e{)yv|H0{?Z)}GcD=tyy`b>?mGYQ%ux=I2>0+s6h*jI+5KfUO'
    'vYit|ZOYE{Wcj}L3xzl335W0wsLt@{^7XLl40nPMzT{#(N7D*?`Ye5v)YQQ{ojLOS)DhdAqof9?ycCCR@u+lL>Beb=LO7e}$n^4g'
    'Iz9iYCZ8{#CXb|kvGArx1s!wAV@pd0Ssl`j38Fk#zBjt?%B5uGjADz%R^G4P^`>afEcs69^l9l9QBF@qc@F;_lQ!iGTKOoA^K{C;'
    'Q?K(_(srerbsJ;WFpwoHAqwr3B6X6GwmU??QD8|Oqw(|F@pIf%|I|@BzfR3ckmX7J(yX73lIm=}m+ZRdXkwbQYl67zZcX~pA*}OO'
    'OyeWkU1e$Jk?R(Qj$Av!JTfCUbY%J%b)>jR<0GkAX1%7W8nd+prp;z8_oedR8PjC@L>_73x<no^Yv*i!L$I&YO<!-JvnJE=ZSvXD'
    'yF>oA&N#{?P7ndTz*3uXql4T3GT#vP(Z#cF%BK2{7tQRCF`B8PbW>9jn#n&??=W+@YmwlZO^`?G*++NX><AsX#bX{RbB2!0D>si^'
    'TM#;OU3sFTOa0ASbyveuGqOs##W{-7t)kCS<ZK>9xqZe_;)se8M^uzJqN2ocj-n*wu^}3Jteu{}YQ{%t=eP)Y@Z86RBPuQ&QE}mj'
    'iVH_vaS^KDIIh!9uHQiU{KNY{{Njf-A0~YGKp;yC_m)7UucH3?bl+GZ(zg2aeY()nR+g^aPKTRw|L64SQp!{;=W&&W<z)GvjbB+r'
    'vO0FFeAxJ?h5wezM?v!e8LNx+%SDTAihRA;nrOSru4xW;x@Z(>nnR2qBD4}WN6U~jK0bbkD|}>xI^qr=8N)~RrMfw{bdkSQI5U%E'
    '9dZhFs{PGWo^ig&UoKo08P2J;qHMA=KUuz}@i%2!9ldT8^Q6^_9p{Pk>gloqODr;7a<W*Qnj(fLPg`Umzf7Md|E8~;CN#&qOd*D+'
    'PcNh6`94u?kxx>sg*AL0TeELES+ICOl9;^K{z#^<4=DCbuCixliXm0Sh4OV(k**1O#FZ&apCSsxaJ^9I6jk~Z8|h-pIC}1+JcnDS'
    'xX8}M!^Vl>!)6t7I~j$6Off#)DNJwVROxzuO}L~Tc3sw{G=<(5&8??TpEhlZK393Ji<Oo&md;kLCM)+%pUyr_)yQ8<q{WMej*~u1'
    '78QxJ+T7B&(`g71lkL-G5ah2E1(vB&R|ug=O<yt9A+*`jpo+vRU6mqz-7KMrDFuS+W7aM8JTW}=-`)H?Jw;SluC%$uzU)G`MW&g?'
    '&#$bO&uugLd68_De4A`X8D15(qLVKqjL&UV^)uFb3WxHFA$8cSL~<)ffQ=)7ODN5w^rE>r?48uaD@!c=4wWLBYdYSs6bg;sAzMWA'
    'o#A&P{~nQEd6;52Ludu=3~9wa8+mMbC_eRZ@(9KKc)QTXxW`fi%jg%<;=9t*SjXGl;de%;cgC=)Ji3eJ6f>4@mi;T8W0|a=h%S&e'
    'Ihqp%$7Vg%Ak{W}I>(bCy&wbBVi_M0)?xRxYvWslbtq}QuwF>&5!NB3<#L%sS}3f8NHc`>0#aRA2a?M413YH>{vI>^`5rTUy2nhP'
    '<}uSdJZAcfJne$g4=1Jamq?}ZNvV8NDxZ|fC#CX9sr)5o`hiQ#^aI>x`u=V+{rPS)eY)FBpXN5xJEY#M{BtvpL#jQv#TLu{A+&Mq'
    '{p_5@Rhn(_D&4ktwZ*o0ZGx>)Y!A2e_zagud5zay8s$AfxSBgg#IqyTc&b`8!^O2|)LmSw@=kHJ*eY!`q}?gf?lft$U04ffY)uzd'
    's#kWlX@7-vy4@|Kh31LHwj|k?rnoFJCMXY~ry4~(zLcl%$T-BseJT{=5mD@r5#`o}EJb>+Tt=)=5i8d^RH};dyX;PNyg(f{W8BQ~'
    '=01$iy~T2)iseQX%Z)0Q8&xbfs#tDRvD~O)xlzS(ql)E570Zn(mK#+pH>y}}RI%KsV!2Vpa-)jnMitAADwZ2nEH|oHZd9?{sA9QM'
    '#d4#H<wh0DjVhKKRV+8ESZ)l*azXP-z5AJO0v$hx^I3c|nK|o)=QF+U^VuzGW@=P(RoB@p5FUHGo_Qv7S@J*aTs9*-gEgvIt+$!1'
    'CFV@FKITmJ&2DG1cJAZbx!=*M>@K@prE(8;nmVL_m3nxI95+K_!}4=50>&Eu+-I3@`BD~FISpD@lpCQD&V9vn(ITjo4NX|uPPr4h'
    'uftiF&!Z`o>%PLO)uoCZG|!|Zd)#TZ``l^5?OttJ;*RaV=Cdr{YwWJy9IkV!Rddlmo2u!uH^^ODnk$(;39%YZQ#HX#7E0@EZg-lr'
    'Znf~Z&$NZl)_>Er1hHNFRq{Wo{8UY=BTtoE>D5%Dj{P&$F#R-J7SOY0?nLpq<8E%Y(qGY!`n1Cm;N5<5noZPRuw5inY9e*;%jLZ9'
    'Z?3b_X9RYu*wrqU+J;!QX1Q6lJUdnFk~>eWboq8+=2814mGZK;IpqYIb|OVkj&61AS}c~j?zK90ERx5E57@1fvxX0TIi0#&#kjq4'
    'tQ$V;)eL?$p;W#ycdTaGc456GT`Kj9Qr?5s>T`vabvso=t_F$*nV&{XVYSXEOQwEgt!hoyxIcMQc8;ZyWB3*O%JX*WqV_B0V{P}z'
    '-K^c)k}XCQ_>#T#*<yB{&%QE{z06VI%UD^Ty|YBVUSDU>`;PU(;P-2qjpdGlrd5gKEW&qbjWBkV<oO>J?)*c#2uQ1aj_PLXgQCEf'
    'wXZO9pDWXMX?30P2X|g=*1mMIz~@*I$XqQ7R;29o_#DM8nS0%NO^@0$M+sksOgVjPReDBAoptZlRYM-#SDq<ac&zuoBE-l!x;r>&'
    'N!t?PoAz$HMWmJZrroHEKZ)wnHGkr^+Lu84d)iCaPLg(#hwiFo57mCRq>eo``$qE<iW&EsdR4^`^RodO{;iwb$vXM%r7}}jyI7_F'
    '?r}P3=BWMeqb-*_C;j)0c2oc35NrNk;lAWa-R*xzxJQ4W3;$suF4?S$;WPY!(PaO7LX1A9yK5(H3(zN_wKppJrj@XL{x?Nk?gp9P'
    'jem9aqt(Zy&joVYx2~$4x4E9u`{ouGj{f2M`L)yj)J&m~KJmH0sN=2cq+jat-__memp`Xpa%|74+R0`;ebZ)^=l^g_e)_cM^wEE6'
    'T~|B#kFA`p=()n&6Hc#h@+?pO58oe^KK)c-{vTV{g+3wKM<e2;H5^63OKY~y5KWgpD4VUe$h4PQTsWSns-0HNuf3O7^SQM%Wh+yf'
    'iPd{%$fN7|Xw$@6nKpR&dU?z@v0A1)Sk-j-L-Lq^5`9o6^SgY#Ji52aKSRELkjgG;rF{7PhbaHKE;6lla{X2=uju+#({DfB!}d%p'
    '-e&c_KdN@}yH2}V?|oM9m|WlVSs97)xcbay)=yiFpSI@sCQGHyr;8t1WY^yx<(s^~A#Q42>YF)#QR@7*QS?by>5Q*B=~KTuWjq9D'
    't!}$7Avk%t{Oc?EnM3@vwaPc~Cl2wa)>XdAKXHmjq)z;^Qyg+jk8Wr)rk8kq6W?u3ncY?uy!L=h<(;K-dwFMCSZineOr()c+Q906'
    'PL$B+2L2||Cg)jc|7M4{Ve3-w!~?CXDBa|rv{jK#{PU3%e*NxAuJ^QCoua(J>ziKd5H&(tb-*dsyX0$W-CVJ>cH)5o8d%xN>s{X3'
    'xd++|9wBZsM~Ky-kwHfASj&~tg6BDsgl|%9VP>r>vvyJ~JI^;=&W=BoB@|1`{!~}h^t}C0j`aVd+%CSE$D|$2RW;Ao%DyV2vy6`F'
    '6KXSZt}n~i$4Q-AlCL|ZmbmhDUFwvAe9sK2zSbPiWT_&ppd#y#+;^F6Rl4?%JgqxUg+5O!&ybHx<>PWWzvLwHh&c6@fjlCb<Kfw?'
    'uH5IH-CR<ewA+*5mgD}Uq6~6v#bt%EF4i&0=EyyJ=v3Chc~a?9+6jCWq;%s<zT)v3k61J1h}HDIeSVH;de8nymZ&lA&Zx28nbCCE'
    'CRZa(Yi-VKkveKyIz>$C;KllCQe%br+FH!7oz0#EYS;PPuGWWlm@~i~MW!yvoJrdBrhUH5vC)1={#|No&J`<+8jshyESFY2-oYLo'
    '4L#P)fk7*swwebjTXIFymVTM$+1cXR#+u#P$8=HiW@Wjwc8guU^K4aReU?1d@W9IQM@2(bWkwqPmGeqdl_Bl-CV2{PCQtpBCqSjt'
    '8kK?U6Ee~q%UbgJYLRedhjf=?rBA0hHLcof^$ej^uC%#GMx0@$uCd;l;Wd^O)AOcx?3G!<XDpL*mMgny75S;gdV7W}VeIPjHPLjC'
    'j(Dw=<+MWa<`n4{vj;V2CVv8^x#*)_t6}=aI=g5l`)=ML^Yxe=GtJd#(_wq&Xc4?^L;HQA=|lVc(W2&XyU!t-j@uu}6TtyD%HuU3'
    'e<F8v4Ie(8@i?6?k9!6@+j7a#GQWTA?q%%N8K1O_KH~D%y#5iTUE5EdQ?vJwXS5jdO1n&3vv#+~A#z{3v)(Uq*B+_QlhNXt^hkMb'
    'pmmE!U!jW?Pdx2^{(za6z9LZ<X?dP0hsyI?o3}JQ)9=tI(eV8CI_ZHITMI{vrtL=SC{gpw+cHntXDy>e!!v=FQKIR^ewKU@oN_<e'
    '{QLp3WV>A+(Fg3_IVez<*YLbQu!ZuF7Rh&HwCE|d8M!rOn}XvjDb1EvO4De6Bu6xC*<8L!cybP8<gasWs(E5A)ne0{K)&z{yWf-J'
    'b#3$**Lbp4Iyd^4df9G@DEY3wo@>)oMUf?6ab5gNmzn3Rs+2Z2RBdmTC9GOm9*QH6zRXOu)J(OEQ_0>@C;hn8Lunq^UY0Eymd?qL'
    'X&y3~=`2sEq#}N0dd+xy=b*~wQB76Uzho*IB~1^|`ArY?qn`0Vza8@Ilw~^y%___GSUo!j&2&<Hm2p3iXII#F%T=1WW0h-NtK+q?'
    'U9P3r`f)GMFne~EX!^LLXMZQ7=|k?>$GK+@e%9>C1MXEl`zh74zo~lmQR>-CRF7W$h#8#^tDgNtCaY`_>e*XV&#udnJ^TKSo;@Jc'
    'vugr_cFUf<wz58l>S^|D88y#txxXR1Mz&ug_uL0m&o0lJE2Dbt?v{-mJzGX*m!AD^5k32W*|SH*)3XoTi?T$mRrPFRaYo2qISx|K'
    'wk``~E@RKj(rS!5Gvv9Uo=xQs_Lx1}@R&V&fY!`CTkhg`_cqV$!PYyJ&vJ@XPggzO5K|py4}XYyb@00lGQxwml~X_e)P86*^>FI#'
    '4|!$G*DML@x})LK=K>pP6nJE`@I2I{XP>C^3(fzK8Q-40K|Sx7TOO%-{S)dZ98WcSkF<;yxo_Srd$!C=M(U8)KazbVckhuvrkK3S'
    'K0lNC`moLQx$ipt9(|+P*F$;g8_lSldaOSGkX$Noo(<c#yGM$emjZJ9n7rK(`6}n&)Ea4h?n8%U&P^}bGv)DB%gB-!X$%NnHB-LZ'
    'uxeYmtivnz`SRVD4pFatF+epu_%4lMFFu*!7oIW83Ul9fZ<4*BF#kZ^qn-iv`Xy`XHv3npUb<<w9A#>rSeG%H#<Ka;Ujq8*`<pj<'
    'bgyZ@I#a%8`_1vKX%(H@@W8b)iW=5#Z_OtA==fSg_Tz?CYs#sgt~7fskC7h7O0)h0ygLW&Zp{vl1KjgN<3PhhySV=vGRKBZG!8Uv'
    'GF&;K9=)lboI^Z=SMD6-ZO--&5OsO7e>Octb6Rk~?(zp{mZNcTaHZz~;W3Wv9CVF4-#cJ;3rFJv6m2{n%qh$E8=^H+ruOP9U1{dK'
    'vb11IrOd@&B^)!Yw(xtw!5*2Pf2lf}vaE&U)7V{T#_6<-Ox`t{BS>iM*qKPz8DGwzzCz!n;OmUM(@ZsXWSINXdU=lZ4xd#t)936>'
    'OR4w!^lR#KG_Bfe94ODDev#7JLSKJqs<Id5iFAFACuh5;Zj$kqC;N(6&fm=#eC-f*C3_>ko-&tTH$7wDF-inx@R-JXu$tM08NRE^'
    'OVj2%m&qRK&Ue&a{Vw;$nyaqQATQ)Qyw^39XUcVK%~eGisk61_k(ASFdMEX^mFZ~~dS_aOcivGCoh4h4-dQkHUrnE@-k=HY#aFH1'
    'GgGfF=Hu3n=O-s{Z_P|jcv0$`7W4Ichs<5tGdpIQyS7SGADD0IrblL)yEi$S?Z`_D4s*BP*T3e0mwk@@vcDh7OKW&weaq&wrq%Y!'
    'ytJB!Ue)#f!4Xfl-{+`Vy^GFy*lrn>*08$BvpLOECHKWU#O9I#HB0u$^ZZpiD7O21-e0a~pK?Dgtp1Nrn$iC0%YnR>*2i7eruX|5'
    '<!PP|cj<Ybl*u!ij`!Okd(8VMWwh6P9Bh%Z!SRpi`G=p#XlQu<l<dh3$3H0_Emqw1w7%k=r}TzTpRRvQc<z$p&L{5k8a{oh<uNf?'
    '&L%R~+vKrRW#`%N`b4)M|47&5_z}EkE6vaEpQPUYv0awc@V>_*S0f+V>SVbepQ0K4xUEc%Tl1c7x#R=!crfLYz@rZTdu?pFjFS18'
    'Y2JA=%SZDF+^<NE7in$v8y%i`CtF6hxB6?|`GD*_*e0WP@)CPxW?I8LZF076Iw;pW+KOBJx_nQT9$c`IMw#RO!pGFw$#a7o?>=Zv'
    'Z8*40e_Yx^>zx%hoX|b9x3*j&$4md4M@$>`+FE6PZ}!_E`{FG}>K_rF*=;SO<tnP?m19))-Xn6vrxoEPqT!Vz<@q$b%6WCg4IA_o'
    'v+wpa9NZ9S5KXVs?BThgP1jG9r8d1n>s<T66VglG8}3|~FUwhRRfEU7z;DipH^|j)duwXbhy4!8@$m2lTJy@8`4aK$I}39!kt^G#'
    'H)a3VYChf|_u{nvyI8)nA&`Gc7vAfp?ar4m+VEj}{o}%W&t}fC=J3YCY|Zm=Wnj>$=2T&k>1A#W@0^hHXVa$?1q~mbpuA)&<;uM7'
    '&b?$up{V(EV}SBEWNSV9&dq`Rpd5=2x3@e_vz-{N(x-mwqxx^iGU(N4;hk5eb8Ee0NWTS*HrbwZcD5$xucB<tJ8!yuH1(zbIu^K{'
    'MuY`h%{m`+%Q}nmq;1FhS!g}GL6>O`a;=vf&Ap_#(9!g|t@RSQvf5BS+9Bsbi>&o4@9KFig_`&3q6V(@;r4P_>)RU4Jg;sF4Em@p'
    'wc(X_sh-FCJtDpN`o@5)`QdkImUzWhCu{ru$%b56Gg;embAFY__8#$!mdBb78%|lzy+>%B@%mB9`=+)GuI=6<^|Gz^8t#0N`jvM*'
    'RF~R>XFYPnat!~*t@X5yuf6(|C#R)Q)P8#_9Tz_LlX{+9eTXy}l6ASX4yl%V+-CPmmpr%KlOs#?&ELf<65qSaTSn8lmhib!^Z({v'
    '>Am`s-1GQzD|O~AAIRJv&iBr1TanDAo~X|`sf+Y?c6qXdHd<I}Z`x4L<sVyC-c6n#xmVWCK2o34E=!-I@_eIG51;8)XS(zMB1@lr'
    'tRXeB^w)RFyqDw)i}$K`xqR;pCyHs*^zGdty)aL{<GX5!5Zb|I-s_Gu(D++BdrmpUyzi<h^7!^;wO3ukuO}b2SLTb!2Wb_M`jwI^'
    'N76TPUUDU-?@1R^w-2;BUz7Tb)csPQxYT^Tccl4x(>46sJ418j^R9h9UxhmG@#)k1c-L<JHTUN|eF}WGpFdY<Zo}=WuzC!+9ycoK'
    'Z^|<Hx96)C5!VmKo?ZD?qaa0VrdcK+>l#e<$Q?n@`hs(_?2UyBj|u-;x%Q<`!BUFa?@I`#>})t@egaT6jjy!j$@0z5IK2awaX$(U'
    'SXO_lXd1AaK204U&vHJzGB~)neTnc7mQD1sE`q~m7Cs_#c$IV5Cl>_45i2tuk;hjSu9K^PJ#xjM$(6&aE!lGAP+`n0o-fa)^@H~!'
    '_rsa=4XhD+)H=dDh(0eK&foX6UUuVD^IKhhk8s{1-|^Q8XO7J#f{x#{-Iq}7*ww7<acEv$F6Q}Dj44~`GYx0+BHryxX`^qqeaFhr'
    'MM8p;ufodbE-k_Q4xW7O7V>$enc79qhw`_wWNaop@sMyA7YkwUvX?3`&n}BNTc&(sefMXpGs-&7Na^N#T%og-CCw3eyE{_ay0=7V'
    '9cMSkK08!1EnKsHF~3(9N;AjwlF&Q6<c=s!dNNd6zwT{ojyT)hQF091nxoI?&Z?)CC1jN<$E8QKogTKz=)N3R^cme-ACapptvBoS'
    '9<A@Loc(4*x+zkxHGSQj5D}3H5w%K)S-!H?9dWiRp*L&Y332)QITh_>;T(FtYf2lHL*H5s3>TWrsV!Ob=9z@}{JqE#(PJDUlqR|R'
    'T;<uJa#MTt^v$Msw^9kq&C;qPN^^IVmfE!sm}l2ToL%jRS!1VpMjd@mQI}`g+{It+7!|s+Y?qn;9*zMOcaDynwyK=gch0FxdCi^A'
    'O6j&Fm3wPM?t40?i&2}_?$3%Z#@{wa;5}*b`AIY0%jo$cvqhZryjqQ9X&q&@b@pJt?(5=+NFh^4TG_Arx;WB0<!kG`Wn5_;<rPGf'
    '=j=YGF69+;w#w+KWlAD)cXgkxOYSAT*QRqi<@M?auP=%ywXEklDLdT}DHg@$1$UplzBR(@brI!N$5mckAH3cik^9!Ta&PXOdvcsT'
    ';bpb{NSDvc)XbXR(GIN<cI@eFM{4($w?(9A?QBzO_m;QC-wtY)b*6WW&yMtnbws*32F{GR=8<Rfm^!oT_}69BFNnz1*^wrt`&<h;'
    '&alP1ep!^>v9>CSD9sg}SJzcu#MvbsHSQN<mDiD9zurAt9pPDbL^+E(%8501N1xHH^>q=sR(IGIV^vfaeMVo#`InPvMc~jWE|cZ!'
    'N6c~GeZG9Y#*BQ&`69gXZjES@<_J5t#;(1p)t-p6n|t-uo>;!>cIDj`k#}pamWcB^&Ti|~5_xv-{tczM-t>~|{0`fk5v55__F`K>'
    '#M#b{l4Go;3Oe#j?ZK*M)ho{LD5oT%99Ks<soj@Ta(*w7t46j(=SR#*=ZnQ7Xv}iBi?52g0$QZbTHpDs-u$dqByHz+%#B;m?--M-'
    'BkXW@E+M6R%j+UiRCi7hYp&}4te)12=SR$55#?>|?5P+lpytly_3Lr17?Jy)&bh~0D|UZYuPYL#L+e-v((}-a)!AAj#yT(}g-qR3'
    'iqJYxo%K-MUUyL$p><$HdCu;0>bef>sl2Z1z=+&kaphjpdu?LZFFA=uZc9RF<i0h5ULOmO<m)whJv98fj`x23!>==i8u@uI*pu(e'
    '_{>3^(h^SDpHo`miLNgBC-+dRR?a&!Y^7PYvrE}SyD2+0uCi0REp<NUdZbG!nQ_!Gv!j#@U6jj0`ON9=9>%gz+9$b%J_y%!GnaZI'
    '{5o5x7VVt>`p)@>_sV>BTeuF{q1?<mbV;4kdp*>dJ@v6;T*j%e#ik7>yV&qS3>)J2W%r|<S(-@bT-vD^rS*%uw0J)Us^lK$4EI2@'
    'Jsk<1+tZfNxjki%?XlF(wM*_&J6l5cwKL*wPovlN9F)+xJ^OdD!O_)*hx*!{wjSDZXqVCko#WDC_r$y|EtlD)<(z$Lx$G|W$UO6w'
    'dnn$XIIc^}6?Cy7FNO`taodpEL(5I*Qrfr}rKNUT+V(T(i9P@I4x?{((AAJxbme1&aERTyd{v}BDoU$%cU<|%sirF*1FHGT$7|}!'
    '$8J4`uY45QZwp=d_=5W&U-`(|7kTAlHvP^#U08EUrly6ie7N|^N3C#~S3X`3UHSO!XL#jft#HqZ|H{Xj?$3_6@}bT+gDW2@Wt>+&'
    'Vw@du<wMo%oLu=>(>bqRu6(TR(YEI3GtThJhq9`ND<56Xi0jHnFV^clT7M3%e5~y;4!U0X=-FC#LR`M?@yf?QzVfj(S@h<ag!ug3'
    '^~#4z)5DbyRqi>t^0B6KUcFrTh*9G%S3cI-+_TQjm5()@bBb~0L!H&<D<3LdFIPUgob|a}`A{D0!<COU-KXes<zsE^y7ckN$J!o!'
    'SJ2t2K41Chk}k%TkF~wEOdqd&#HdpbS3Y|7g1gUN@9oM*&*jzi!Ry^!`RF<K=FYi)hF3n69eud+v8MYJU9Nn@(GGE3`Jged=PMs;'
    'I-e2Ol@FDshbtfIjB|43qf1`BT=`Hn?%~SEn$BmO;gyfI-CGrL<zsDkKIrAjhqA4QD<56X=<}72fqdm->sem;SleTpbiMM?v#<8V'
    '@>N_{K6<vK>y?k5EukwPz52HgS3Y{St?QK!RdNqkK2&~ZdF5kG=UlqE^3h}D_HgB6t;0R5_bVT3I-m6!T=`HX^x?{fO3}-ek1l7O'
    '#gz}`sa~#ptm%AK+*dx<_E?+N?$0{wD<8_*K3w^Tk)q3$kF{}oy|*hLJ^Q7gr}E;s^3ikdCB4_Cmn$Cw`O3%E@Rg5&$HF5yU-=j~'
    'H2j*cd<^U#e$Aim59BK!Ta$ZiEx!6Nkgt4f4PO@+$X7nLTH=YWF8TL*<zrxG*h;f(XP2^vc2jn0TxIug<zwKHE~R9~QNzrRQbM2F'
    '(V6jI`55>?xUT$p>%bG?*Zle6z+-xs{MU5Oztg9W1KYxN$PVRZ)}c%4l-}#1&g}K`)`6$O7MnJl>|(<QF>Hw6mpxqh7|2&XB1$_I'
    'qqKf;m)55%9|N7?9%#0wBcXG9+7ddqCtvyKq14W`OYTxTzVgvc?TonFv)3yh0|zB^ZqNQ*Y;bh7VQpXAvxh4m1BZ4gZO}O`Ep|`L'
    '>(X+WU0TlBr<Tj^Qjg3tZ@IPc_QY{rTCSjr4S6waNRHcv9<F>0oY1ATaWP7ZapmI-dScIigDEdByj7I0rQe5$=3}pfeo@o?y)K&5'
    '&hqywV=O8B+mCtuuM#_?UN`P4etq*JDRhq`>!QpQjdVo+6uvuxV@`@?SDUbk`KC@OlJE1KfQQlDxGHjX1vZL+Lrkp5+8x*|(l32E'
    'U5F*i(<i>|U>*0C^wg3(Z<=r=(>=ruQ9@cVY*)*DqGIq4`B%PIrruk`?+xJh()c}tW@7oCCLH`;3LUL5n(4jEgj2m&!0%b#ruQ^@'
    'uVTcW_WKfEyt!<W?k*4$v=__VlZ1Ts;<a_AmNl!_t)|}XmS;M|izQ-`Mz5zkO?A0Uols_Kf!oyVI#Zp^rVeT~)gidV7i~^cg^P7L'
    '-v!vlzXd8ZMrw2ivV(jdt%t?IE#(H?1!yYWhkZ|a=w9Boi{)9~tCl}Zk(aK2wSJJMRfnRnfPagWoFdfyp3L9-d#`G#=U)O_cNXTE'
    'sWS3pDiz7LY>m>+<+P3zoqxwvYu!;kvPBo(0qzl$#%C$k2l3t9TbzUV%*(BU&kR~y^an-I*dhN`SX=CG%68b1`=*#mXY2{xoyD5d'
    'rhXw+Xqe^Ir&2D9QmmcJv#RoJg=Tri4ppA?0@o^-QdoRQ_>y<>Rld^YJGthwC^u(|Ri`_0iD2?{u|$+sneUC2@0CyDyU1J?akn|X'
    'p=bFp?p0N5w9x&~gIQ|~cjz4Rd^7Ecj#TDvp}jfgovwp9rG>YNrZKO{R`6a@xrFcYJ?ag<1DJJorZtUwhJTB29k<Fe#@)|%-|>%;'
    'r|s8;FQ<m?f>b4y?%uOXYJphhS{2ONpL?4uLvxMdUu3_b)9?7wN7M+hMyyJoBvY+vU7CKGOtq$YX?n_A1>&``%F?x^JYszHboe)T'
    '=6Eu~Yj=x^EdHBQO@Bx6^D%qm-|}%CKG-8`VVyG8s_mlRl>3e9kvVj)ChMB7<|NB}j2gr32+rQoF8^NELVqW%mq)x-=k!cD3VE+~'
    '9?6pGZxrs4g@u}bsc6nxDAic=)hxQAI!5L<l=6`|i2NJo2C|C^9l`PIWKQ|Fv;;D5ER_DdpUPNJFWbR;i*q{V=e^3AeX;a<{?w9@'
    'S^cR#YpCo|kH|Cg9~C0&&cZZl!_9OH@BAl(EAy*`BL5{(msO~1-rH`p>lRt|cv%OTHh-S9>6^M1ysJ)@5WKoZTH+n=+;|Dy-}6mT'
    'H?l?-!7%}uzyC$y&Z^Nh|M)py&9YGGfk5`Xx+6HOhDx8hPNvTvAX>BQ^)#77b}qH+JEAp{(#)1Mr8Frg0`h%F@VX<EW?nVryH_;l'
    'a=t=byrxj|4xVGz$+87U0-5q$-#asPQ6shri#(%wWWB6ITEMQ$`unHKT$AaSp3}o;RFBM(?*wl+a`c1<&LF#k8rkQ)qtdMRRM{3q'
    'g<9~QT4}G$(KYf$S>|l#E~>F_>eIR$fVSpu7b5#+JuP^{iQE(N=u@0OS(y2pEdRUTu~T3Lr}DewE6jIC>=~Iu*WYgoG`#2VXGw28'
    'E6=^*Uh`Zz+PY;<x62@x=Vr-P+9rGW_{A!xk8)2~d~|COdiOmcF8QD^P3Dv<bDAn!?tW=w)-`4gZuuaPJ*Tk0Z)z#q>YpdX=#_<O'
    '6`Y6vI?<fJyfDpoP<rhH@pwsp|7_vTe_BuTy(zua-t3o0UKg(1qcZ>Nj@kb@z&}H{@}H9L@0E2w;r5p}{8t|hWZziWKREl?iW39;'
    'Q(6Pr-_iT~Uizjkj=Jc58CQ8t(mOMb6wCL=2=^$zOut?Fp;c^_?=KM|=Uo}eQx4hX`*N%pC8NmqgsgkOy@k>@2eKFI{exp#R~(n+'
    '9|~k%Qz(2(WbK>97MDY&s2k;zF*#<x{n!A%CL`4*9KIPoT^tfyD8H;ZvIVu~c6a}Z8T*S*Sn`+3_G*!}enQrIkBo%=zO}NpyTw*l'
    'e>y*tT73L&Ds6zw%^`Dp;%@UyDy@0c0eb%}`F?P~ZkelZ#5eg}S+~0E=VVRCzhys8In|B4muezwx?kq)@aM?fs0WXsw7yZdo2f>~'
    'KDU_q&Hjb&^_THomw80iX4D#rfSkFZbINk=r~bXa_&tjp8OpNci0>OwYQB5VkwEq-T~y3oV?QqPN3;a8-;f@%)TL{hR^r<tb(ts;'
    '4sXtSzI&c`QtLwcr#!qlYxq7FzLeT@?QKyKNThpS)Gp*>mmNsg^btkAoMq|S8d2h(v@ekTTA{_8v#gkZoqgHPbS+`~Rem|zk6Kx%'
    'rC+utU9-s7IifXhd7<Xp{<1C(lx>#1EJf7G_SbxycIjfLYm>|3pCm2ZQD_NHSz|vTWD1e@w63M61a)z$Y_tEmV}a~X=uT=UWe%=Q'
    '{;Ne@zMn?>k2ps2$6Oo8reA*#JE4nXb^hR_)}zPeXe(TKH2UNmD1J})4Ec1OYjZGX4gH2VMS9Oizx!Qt^oXpje7dJ>b8wiq_?QUr'
    '9a}4|_R8}DJabiyd%-5h^-<=(d(!c*AejFWO7J?K<Az1dWmfa91wrer8Mlh2dGxO!c(16`E~dF`N~<}S4bE3{nODwZ^p2eS<*G`K'
    'cxA`r5&wvrH;nY?!oNV&4Uu8tx0X+%IlUsKh-R7*+w|My3SqI#zjWjEV`;9roj-}YK7*b=MOIJp(3w-{{L<yu^WD+b@tpvxr_rh*'
    'IHh{59I;bs%jxej`%w{`Uu&BoXGMRZSSFVGCwZo2>a==ZoFUJcQbWJCo>V(Fbhh^j(YlH6V7N@DU(yFtJo3HtaWeHE>XyoU7akGm'
    'Q{<~MQJp@C@^miuS*0c%T#=q4RcO@}Hx!2NQx{ry)kWCopAxcxtz`Rxlj_KZ1>2-mWCQ)HHo@E2x?8HvcNYGYY%Kn(v~4llChL?T'
    '>oiqbmm#g2s%)JiUzLdx(^lW5^3~6^5^1YE*E!v5^>4e1RtYKcwa`ksvvnMQ{(L?EyF0nme^Tgv57M4V)zUiOlv?@zyyZSBr%qJ+'
    'CedrHI=G<Depv9)T2URGv~97p`VJ4(=ayQ*^WK7OiMa`~>^ncu&3hy~tx|4Fmv-MKQ+^<-y<Zc~$GEiGdtEY$PjYEqSxPSVVXkwv'
    '@6uY;KFe|siQuKrZe1l?b6dl2rI(j|^%5#&gg;%{H&uEdUHn1%V^XawrDELNr(X%Ta&W;iX{Gc<x-7ZGyI@-x-6cbMFr7T;yL6jr'
    '=K|TTx-4r_?X#~4`6^v(Yb}-@O&2#hiz;qdY<Gu!*B%|C?8n!r2e~fdyK4qh>e`pc(aGWDdwx!l-9!eP9G!I0pluD_Qm8jb%c|vH'
    '-;^h%1qZ8qleU?<pxyNS9nzv&QNWh9ivrm)D`Z@xe8BGpN7Uy2g*-(OU*L0Ao1U6f`-zL%r%-xDrl`&REA>tp^S%sj!7BMmMvU~('
    'pqGSiVhg7-SF?f1LX8>$88v|$v@Uy5a|It<;BA+E{VrLbHl5aG*%USY<8o$_)kqz7g6{nw`@Cq)k=3cV?vvfO3;(>2%JXQ>zhN8C'
    '`TkY%U0Ds^EpjMqkz>9bHTdjNA1pj9eYI21r!mp0-c1p$a+Z~=)|TAEl(V2$vgUHmE!*s~%8|3pxw&G@&J~B{nzp6*u-q@-%B$aT'
    '|I>N(TRMGKx+dFc2aj;~x6}yp9@oLkeDr)$$2jO8b^o#)T5k^X(m#YF{8_$f^xBsqbC~5AL-XMfx%CL9_;%ky<5Bqn`MkRPR$A?3'
    'ERf?{tBlx+%l7O(ERRqRm#a}Xtzd&GJ853qBwX|=ecVoNfzml-nP^@SUawbVt>-oR0bZkXtc}@0YxH4h;kM{zpB8K1Bv<mhqaVDO'
    ')jQ#$RvXv+ZTd##WwJHjmbDr6M#d(Zy9?#tDZZ9Xa%Oy+<JCV&*4Ilj(rYbSWU9Al%o^WXd|b}E2QtnVPD;D`xSZGClJ%LgDmdni'
    '74p?6Z@TuHjKlHEg-51cF5J5B(znd-WsX~C_PYYP`T2vW4qPg&9<yJFgb~&0Ij`yBEw|kJ>|1zT1RcACTa(Xa8>OpzpQLBe{VqnV'
    'njn0RHDkptQSBclTsd+k3y!KTe2`ipP$OIKjR1RNgiN)kwMP2B{z3WbwG83cR;8xw%-}uMuvc}`sh3F~(S1$GM^Ym{X|Wn@Ddacl'
    'Y2)Sc{N2*ihI@*+o36~@GLkFV<32}WA>C=lYwTptr>DpT^;1h8Of`17^2~jF67A!=y$_0Z*7qOPb-MrPV0Hh|0et__oFQt@Y#ltr'
    'YTmKD<E|qecM)4i^}Nn*-u+{SxzD!dq)!#R1GF0L)-)AsZxrTHtQkJD=6X>E-Qmw`-OhVdIl{>3NVT@`KMycLn>yIepIl5eQl($V'
    '_H-YZ)dBzj000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000001>M_j$0k?i>2oc{Fb;OWO2V!!Y1t@xp$L`)D*%V%GfXMZKZYPF00ntu9<)2C(bnh47O{(=5)?zR5%@ja^O'
    '>C^K6)29=Jg^JZRAuRHdC?9tDNS2RO`EbZbx_tDPk3sS=L_UVf$8h;@%14HLjFgXT`N)-zJo(6%j{^A^Cm)x}#{~JfTs|ghz1P1t'
    '`z@MHOV%9PP|c}jXqj5JmZueH<FpCdM9rlYY16ftT8TDCyH>kiE7Rs{H*2?QcWd9#Dm1rNsV&!5YSr2rZJoAWtJ5CQHfo!-t=f~?'
    ')7o=dv$jLqrM;%@*WS|J)>^eg+7a!T)~0=+ozzZgLbvEPJz4L~es{0_C)g2|(=up;lMh@dUpwU^TZrK4fA0R<a~03FeE0ug3<dxI'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000RKFsi`)8{'
    '&oq}+?>Mg8?cWqb<&!euvbx}>|Eu&j#VK5(L=%zizcZ<s4h)jV9q<$Qzl!@;=ELRc{2TxP000000000000000000000000000000'
    '00000{8NzdnD#GSf6Kpk{r|-|Em8VC(gum9UX#8o(baKMU*-&-uHGm8(**CI64ZI5^*_jeHbI?F`q2KWhZ0me(&dr_m7cUsVo~{!'
    '9v;8u_ZF2O=?ewPFIZH*q`L|SZnLQTNhjHV|5J-9hxB;XlRvho@<?sJnY7BH$|Wtdji|J!@=5PIZ}Lg2vV-(!UFuP*vWIlTuCKjg'
    'Rd$i?bEfRGD*H&kll<zht;$Z)exG=ntjb=}r^@<0WmR^QUO#1~->U2<z05lLXI51Y(mIJ%)ra)WKUddSRlP{RVzjTZs``<h_`=ga'
    'w5ocN{!jb<6;@SW((kVL@-nNcH>t;I^H^2=Nl!JOcPdf&f%LyuReg}C{6X57@c)h{D!-6Uf3oG>MCBjSp%WIhCMrLX{w(Frw-S}V'
    'NE5#O>(>&M-$*y!Isdnb%73Kqet+ujMCC`)Z|_?0VxsaVX|p6z`IU8k>2rz7zof1D1y3g`Ka)P`>i1-#@;9m8FK=t2@;hne>ThmN'
    'RQ@OZ&nu2>OjPZ_=Qmb7nyA`?^pY38RG+BYh4jx0(teVt+J|&~v#~x=wG-*=As0Q6sM?G4*0;WLf1+wP(j7}{ew3)%kJNbX)9OUk'
    'j-<DZzuTLr+LLr;vu$OfYFE-Km%l1ewJ*2VV_*AzqH1T-|FDf)nyA{F^vAcS-<PP`o%6NmOA=N4lb&}nA(*7%fV4gD3!fyZcpzOj'
    'sqCX96&Iw_-*~1yNyP{0MZd`ZYm$l+(nq&F|Cb~cFQnhzyx>TZiW}10by<g#RQ!;p-hJv|l8PhJnb*H}AW6j&>4|xN`9qS5E7F8*'
    '+M7u#zDVD2U-CwhiZjwnQ*QoUl8QId-~8mMJxMC=NWZmW;Hyb0{z#iI{{C;0R2-7ddMoLrBo&XOw<NFInWW;9bm{0X?MPDbN&5OP'
    '4{c9UaY}k*bltC#RJ@Y@yW^JUlT_T2j`;KBUnZ&eCH>^e5zi#4I3}I@%kzGbq~e)$#k)phl8S56(wolvd6J56(x-oS(Gy83&PjK^'
    'bNS;*D&9%2y`*eQl8SrMz%4&~EJ?*b+gH46Q<CZj>?gOKmHGqgj;l8$seVB^?6;d9NmBiT^oko3S*f3p=8yUM!%3>YkbY|H|4EYS'
    'H>6+KGP5>G^&ir*gS*xzseVLS`;D0oCaL~J`c}s8A4pRDiqzP3^SUI}zu2yPjg|Tt>CIVnYm-!eBVFU3%1Zr?{c!&Kz9iNE`1sH3'
    'S0|}{NP5$RxvbP5*^YZIV5NS^<(0m*DoOQEQp@`Kl}W0fk`|9!^n)bTUr868EM%pAOM3aQhp<xrCH=np@83^S{g|}K`sT7E)t^b{'
    'ed$+AlT^RvcK>)&Ws>UO91jH#+?S;KIcd|cR(g_Df9LjGRk<Wd^?OpcBuVxEB%b)iX`31cNJ|deKDDXwfONsqLH}b@;{xf3ZKFT7'
    'squld<%(H<x2bW0^!0>0KeVawf;8{-y1&`fxIy~r4_<rUrp6CeaULs;Bcz8@OHSC-ctSd8^^cF))VM;LF#qsTn;Ks@-Ga;Bv#D{0'
    'G_d$bf3~UdhIH$#e>-eb;|}TX$6j~Hrp6!A<r{VcY-$`LeQDEpRvM2;@4RU9A8l$};`;pMVpbZTNUwc=<J&ehPLU3~U^FX@SESbz'
    'KKrIkja#JN>x%c=)cD1IzVeT6*wi>i`knXge%+?VGt#QD7qHT}M*45IXZP9E_(nQ;&b+-gHO`Ul5h<)R-jV+D<a4ju)VN1ldhs2v'
    '*wpw(dh6XetTYaCyX`-`+or}tw(pA@Ub3lik+k~mg}ZEOd}M$AXe=v@lWg~$!53|6yk!3;y}HAu#!b$5(!(#<)c8qye&XFNHZ_it'
    'CYO}5(s;`GB^R*LxJtSrH;t9XSJKt%KYZS%##z!E{^OnJY-+qEUFq8OOPd;ZNgdZb^{h>ezZ@6Ke)fz_jl=AZ7an}trp9B^Ux*+5'
    '!luS$(s5%}J!MnlGwIdSS2WtxI8FN6Wh<VvsqvcY|MAM7+tj#Cn)4msHk%s1Nq02XJYiGgIO&uJAKhwG<2mWWBYyt4O^xdu?~`Bf'
    '+tm0@I`-Yyx7gG;&+&5JUpCv+cu#8Is<YC#Px`y(hqBW6Pda||Wvnz0aKHQHKUrx$Ahlg^4=c?JqyxXb{%1BdKahSjtYw2u%@d@@'
    'KYH&`o0>03zy9g@tTb=1|8rcdG=FeA+;KZA%_E%uZ)@vqYChq(xoq#lHZ`wseK%QIX@24UJ8&W^%`>C}?!A+h<{Q#gFZ*k4YTn`g'
    'o%olBY-;}DI2@6~O7jrug9C42rTK{a>w$&`ZE9ZP{;>E&jZMu@q+fgGi>x$Haee=MFDuPgq`!Xlg>^PHZ}E6AC6$%tFCKUAn#)S_'
    '7@t?N@qU|{&qx=){P(psHLsEW_|SA#n%_v@@jb{&^Bn1md;j_)o0{*qzdbmWmF7Lt5B{>AmF7Q=yXQV!ZBz3g`_Cw0rTLKUdigO{'
    'niskM3xk#BM;=EX{u(RIlN<++{n~3&^CkDA3vyU#-sE=v(+^l_{v`dat!<@E&7(Z-R$k3Y^C|a}lIMP4Q}Zh6_ZMce()`N(;gwaa'
    'G|%!lbmz$`o0@OgPuI_9rFob175CodHZ}k9{PWHgtTYevIP{IjS!q5d-8|OGO7k-56B#~MnxA<*m}q6Cd78(gZ{Nd8^ELOccTQB='
    ')V$5{b;ANyn!ib}`uOepY-%27e{Q~-mF9CE|L*#&$EN0Wj?-DitTexqJ~w{n5}TUmIsL^~veJA{x^2XEw@uCa-2a>|R+|60eXeky'
    'Hq<(R^wEi)prO_Sq{|AHeQKz60qK(iR-Q7{`haxtyFdCLL#-1?FM8;qPYktQAk7=M>0?8!8%Q%YJay7g>j%>H$6x%rq1F+kS6P4m'
    'k)hTTT+W~0`_NG93Q|vX@B>4wFGyecxIZhcGf4k9d=x9KH%Nc;$uw44caT24yquNRAEd1>e2<mZA*4U}S?ym9wH_fIH2PO347DyH'
    '{oB<Cj~i-z!uDTaWu<irY27z+S!umO`jhKsv(mbSbjIF$SZV!2dgH#IzGtX)3~9r)zdd58^$clh*{MGpYF$Hm*P&ciTHlcV;ow|W'
    'TIX>7b5^p_dWUrXmwt7~Q0pF2|MI{6$x!Pb(qLf@E3Jb_?KhRN(t3#PI=qgR)<vWbytuE`Q0pW1pGak;brR{#KPqOW^%Ci}dzQ1('
    'x`~f({q;MBT0e37ebL5B>nPH<MKLR_r${gEzlxRCRiq0S?tRNp>nqaR#09Lh&LTa%?*>*{Z*lz&Ji6ad>n_sSBmVk(L#@9^kKBJ5'
    'E3Lywn<p-1rS%x;f%EpgZm4w`X=#d+mDXpZ<Hml2mDXvb8^8Ul-x+GXM*7yf4pv&XaX-7`CRSR%alJ42#a=_L<47<0eLq%O&#~XP'
    '%wwf>9mnUor+;gx^&RQ&);L&cokyBncMB`6_eeMW;)PcXweBPR!kfccY5m9k(!R|~>p;?-qxb*DQ0qa?uk2D*S{IUjy?QMxtq)0;'
    'HhuV#q1K7)mm}A((t43}t^Ju@hFUk0e)xr<th9dQ_!;A7rFA67)!4&34Yi&my*uN}thBBqeNk*<rS&DJ-#wU>)|u>=3J)u-H%YBS'
    'j=f;0btkub%{8pF{v@4rdV7nZ)}f?{Q}bDAJxV%d;e)KSE@k^~HCSnVN}B)WyIE<S%Kp@k{K`=4RnqVIu4SclE64laUurVc`jvIe'
    'L{?hIlHN4&aaLN-lInxLz)I^{(%~&XW~KEl_mc@JthCN$KiqpCE3J3A{g;07tfAJuq|R#>v(oyPw7l);Glp6RvtMS;XQlNp_xG<K'
    'c-m0wVp7+auVbb4G3nr=ul>SM>tr5Brp;!h^)l(lH@^Cmq1Mej9*vpFO6zCRn&)>n8fqQQ<EkiTrS&xFBOkx?q@mW;r0;DgW~KEt'
    'w{OzRKR47mo9C55vsh`p&Hj0F&o)D?ySZP_n8QlzZ_>SA-T#E4*5N$9j=q7F*5jmQ^?|L1T9=a+G~LWf>vQgpOaA(}q1Nd<5B%ku'
    'th8PyUGj0zZ>V)U={FzyJ}a%?IbKgYSZN(k`r8j`SZO^^`qQc`R$AAS9(-;qE3NN&yk9kumDc$@|9rgbF+;8QNgor}u+qApbo|4A'
    'YB1FLpX2(iJ6LHSz~fVcV5R*4_m}gkS!rKD>a#mpX@9_Rux=|W?Gs2hKQo1u_6yvvzy7<Q8EW4^dZm8>EA1b+J-&BxgQ4~j+~5EB'
    '16JBkaJrW-Vx@fr&$mTSveN#7^wWQz!AkoKa~*Kt5ku`a*zbS2la=-z?BC`6SZV*k<!q^ErF{s;?SEd*O8XJgFD~0xZ>W6<$IXPV'
    'v(o;A^S|A~O8XQ}msQJ3`xTD+8z!*QzJ>ekfZx>_YX8D<{pH(PX&=MKg`Ji5GaS!jH?Y#ahR4&^LRQ+}aC{rBwT9Z~u-~_QmzDNA'
    '90$8EWTkx%&l6?OveN#Cbk6P9vC=+>`$PN5^@iFHaXTMh$4dJm_TvqgvC{sCG;_*Z4;pHpMEa|B-)5!#5^35^!&qtG#Os!y{EC(K'
    'Po($HEN7*C6!))%R#w_ik$(B_8(C>z#pBoCX0p=$ipTZq-(P2_eHO2WzIZ<??YBrT|JJ{;(!PtdXym~k8*2YWI>GgQR@#Sg`|lXV'
    'O8YVP?-Q@xZ>W74=V$v4EA7vCeZ2Dvth7%f9dhh9th8U_c)$BjR@%4m`gY+kR@%RD`t3VeX&=YyfbTA1rTrYo+xj7_w6Ejw>7o}|'
    'X@AG<Vp+sW`#hd!zkDGp?f1Ap{%t2K?fcmOrxvr){*Sb2{za^`59E5~z06AcL0&JG-or}!LefKTjAW(#A?fW;zs5@YMAFAU^03l='
    'k<VK_hL!e>9FNOde`u)vBd?Et|3g;VM{@jnu3)A8B=0M}|5vY}_LZcChkwFK`%6Cm!4g*5XOdbPG*;Sg@;H3n&sk~TN%~(e&u69m'
    'Cy#r79LP%hP_FmCzr;%WQC_E5zr#xVQeL-RFq)P2r)*b6;0K1<r}8{A;eJ-yuk!pjwV0Lmt=yj<39c~I{*~>%`sb{)k2Tl-H?z`y'
    'miyu6VXU;TWqV3~$4dKKUSAYdvC=-5*B#%#f|d5Wq+c5H(Q-rWdpYhu+007&U+%X#^I2&h%;UnN7qZfRnA_*}-?7rZnB%+h2duO|'
    '<~TikB`fWdxj*|(Ei=@9nb+wn8d+)IO!^<M+|Ek-XC9~KX0y^hn&-QMz*0l)r@8(m>se`E&EwwF*Raz5n*04NX{@x*CjDXg%dE8D'
    '=5=%Z_gQJ*O?qMOm8`V?<~TVSyw6bkaMBBsf5}SwarVoCZ?V$8oW~#QI9A%9^E~oio5xW5bneG#epcGA^ZKdc>#VeICruii!%F*i'
    '-uGtwd5NL+@w^_p?on3S&+~cvZepc<J?FbBgO&F8yuVs;&~2!FKF8IrI#$~6^FCyH87uAkxxO|hEA9UceEk6c000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '00000007{BJ$ZTX0RR9100000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000RJp(PIN3H)y#*Bk99e|NE7ZY>NUMr)UPA`5c#mm'
    '$NBQnUp@xN$3XeGKt2Y^hcm`QQ~z1GghVk|<#nNa43&>z@-bYUD^H3_Z{d^{&V$llq>hh}j|^q^7rLY=5M~8ks(i}Ct<q=8zv=R!'
    'o5hJV`ADI%6ND&Hj&VmkEb^~gB=cWNpDh2{y76!5{OIFa#48<v2mk;800000000000000000000000000000000000000000095u'
    'oF~lR^#AWb6YK2%cq=SjUJr_RzR?h!e%T*_?hW7wy>KV;eG)z^>hw&`-zhTBX*mhv>mprT-fjKBXMx#%A%73;=8V%3{HuDYzsIcm'
    ')Nb#<A;dVPmFoSjuZ6px*-zYApJ~7RhmBLs9b=GL<IqSn?Eh4K|M%m*g6=mHi+`5B9_nw_GwpBx%joNT7aFHS_e=`4U2pk>`lr^Z'
    'ubvq;5qYnrb5pN>MYKpixiuayX<Vf{Hqkww=EIEu00000000000000000000000000000000000004l`3WxQqlK0nb;%xpq+w@k='
    'k&>_@T}%)`OQPWx<*7nc7%lDhC6rs_vjNTWS^jF_8Z=10O18)|Dzr-Z_r+}YB;hU)FFNZ?9n@^9rPWl2n50Qv-b?ub>4Va$<(d%A'
    '<~viZqTO&<+O27prYd_;o@iQX&&(6K+jr=?$bF_o{w<#*G>1Jnb-A>mkbj2jHR^|u2Cemlw~8ifi(Lp`R=F;mBUXC9=pK<J93s`2'
    'n?ZLOsIXpZcMGer&#KEh2aVG9CBi>Lp0GogujbdU6Q#@LQ|S$7^W3jkL@=d#$_8oQPI;`hU#UlPYa%seC+FpC9xKnV=JdB}JKBYH'
    '_Bg3yWlFChoR5+{#*V-enZrtHssD9RwpnKUY}L#9$Tvv$v}DQG`!+U=6(ZeOm@dSW%JLMdM<L&#A$7L0_$sp4+3b|ht%L8kW^h}z'
    '57tG~1O0YL->jO}k|*}1vIp|!x5;)J!Ous%5m+b62MhMEEK;P7e@oe&O?i!3XHDn4njWypBkiMf5g0LnN*?@1OQuwn=O~Z#QDDq)'
    'X;tm`H*5*}b<O{TaNcYa!oNj0v!w>dzqR7H2#$Fp;O1jTWS8)cdCNo9sg*~?ewp{E)?|8hwB0ISJ-cbQKJqnPcn9p)N6EADJu;_c'
    'o49=Gt1Vgbc<ILC@=?;#Z)VGsDYqsHK9VVq<fdsNU@T1FBZYM2@})u^c~|Q=Qa*u>+!=A?qrr4!a>S9A6n^d*BA=J2{1XzK&Bt_p'
    'Ua!mN^VRwE+%5Qd20f?W<CZQj*7XFhO*m}ADN^+-T$W^~7-N;Tmub?ghShC#Slr5sW}AjnX7rZQ6;9bX{mZ5m<q=jC_T36q7f(bk'
    '<!4+MPj4yRUFy<Zy%w3C))P8B9f+{5K7N07u`UoRWr9js5W~~^ReO^~F4f-jJYPQV$ib_J^L9|)6)A<Xw;G1qS{BReg$W(?lDYS6'
    'U3IK_750|0qzA8e&T*#MmjZ+3^E$H~TFAzADoP?eP~I00MBA=%@$@B^k{IpNrlKUmn=P??lB9gHD9WNoDCMr=cFJWMJ+~DHtjfz{'
    '28Yr{SvO#%w60?C9<p(O+qx$z-)SoPLe`BL5Hqh4GbyjEV#;e+q>Zs#Y>nAU88mjSH2t6tiHP~ZqGvzsiPbWkOMWl*vZaF~bLqBa'
    '3Ws#$o6(niqgzQuVtGUzW$saR<h;+LI?6U_i^^rDiebv-a<XMu==|vREe*GC#faBbE4TI9qdJ#2H_7Zv7s}^qzRIBIJ5?VeI~vTI'
    ')eq^g&l87zgUP0f0k6{EVWm;_b&10IA)O-nydEODG)7%RIa*BH0}=MNgzX*Cn?K)RdtZxbZ=H(e3p;WT#N!RleL$?%3gtdg#rTDt'
    'BF83kNH=C?44&z{jC;wv=ov3|8?Q9|QBD?DtGK_gqpXa0%W}oCw(v}?4dru4jp7kjmG?c*P;RP@^%1#w;?2z+tB&=3_fl`|vfu1)'
    '<%2Xi#;dgjJzuY8jR^Z&dMiD8r4TA*x{A>Y!zm)>wR!Qb54s&aGsxOd#17KpvoLzbRrM{5$Sot@+)85ASLW9D`c}u$n}(We?-sIF'
    'H(Sj^&sDkQXHsr-E$USaNBG3kn@?h|AZDo;j<hX2<Ig+u89$W2@<V{ERb{nAl{GkKS-q}QRD|e*JG>Ey*Bg6cMTpF;OH1|Ojaci6'
    '_<H)lWZK!?5V5n%PoyLN5pl$yKu3xrj#zX$QWSAyqo5;&5l3c;@Sbrw9qD_G7R4OZvty4roNx3hrgJ`IRlt}QVeMQIu2C0j!?WkS'
    'Gg<3|O5Dl$Pmd~bTHi~IbM>O4y;IH|(S9bYm{>D-z$l5R*UMb5nNc+@j#bkUz4^Acb<Z5pcOUk==7}Eh0>*4rqioURUfM#lekf%*'
    'r!0*xrM)9%&n39xXqR&Cq1Q&VLI$_g)sdg`uyu3dw9XZ$b&hUljDT@XpS=*W@IU+P`QA&2?K#s=bEEupU7S|9<FvvZ!%zPeXF0AY'
    'KV5&0TGAHPlD$RSZY!1lwFsXr<M=C&IC44r^}nP1dSfqE+v4mUYTadtUS~eb<&^bOj!JJYi16#ZoN`{|>=@tYE|#*0T;fb)FY7Tb'
    '^Vxs%qx^SMeD$(a$LBwL^eWiT<t&J^oRWx|-_9w&8mH$=`tCDJJnQ0-yneYo!gDvWFK>xBVz%_neQ#-d^%+=Q5@UUEYef0eMA*jV'
    'eX}S!cQaCM>!lsky413$mq=0P*?V4jH?WWIh^Wziw&EKRNBZ>HUW8q8eBrznooQb7$h`XWX{9CB=XOuBMT@&y6mP!vJyGNN|BJJ|'
    '_Qcs<XSPF_HJogDIHFz)dC#yiGFExd;Ep(A=RWuC$W$B;-;C;WcXjP^y?@4O+0(Vp^`6Eaz1!Ny<$vo8%8!o3d!u^px4QP+IBe{?'
    '<LU7;T1#7x{m;Yx{%(}NzY{yEB6GL5Mbz;OKJT?euhWlm`4y3Cg1+b5$u1w~_`UdZ>~8O5=|fGsOK*>7pER8N!_o*#z1%*Y$Tbt!'
    'W=XdrNF4jMPW9+hN_(ufy05Ee`}P^NCAzID&o0NlL}hn-yk7duVs4YF2penI>g5qfN=3LOm&X@#-PjT3@wh(0?PhOfu5DLz+oxmZ'
    '(`k>jm~;3+-*T{YzlVrjV*H;yC-Pi!e}u=k@m^we#F1idCvU_NvlgrRSPMrVYZ1%;KRn}dLzY*caSO&*qPxeqH~smeD1Z9;XqCH<'
    'R=HyMb4?%1bw&AeZJasS`WOke9zR3qT$f9E%zrR)$HsnM7v<+4$7yZk9ycCqBloo3t$iK{Thiw%1D$rb6`WhmndfFN>syUt?E6CY'
    'JjH&ljqtM>SL^%c=T3V&v!x#DV@s9vv87^tU*iCm{*$w4ugJQr;N0rYqP;qD>$@c-ef%cC&NQ<2*@)KEljz8nh$Fe&*EU8R@o@}1'
    '8gb-)uJt2P*C-y2b&VnpKa})o9*^8%ch|lf;*74y9e5}Qvvxo0rcL{FJuPBybA~ze^0~mh+%64K?XoGB<?&vfi`W&OVGiBw5zWtK'
    '9_w4XblRVqW8>yNw(Oo*{j2xuW|lp1%uUa7e|a);_rdM*c*GHNl<>zIC3?5ytZEUfk8F$TzmK2!HAZ`MDdsr;^WNJl@=9aGPA9JO'
    '?LF^92J(vc7m*_#w@za>ZE*(ICp+!S%&QJhotvB^_Gf2xJ<}5FTHHr$?bCg?Hs;Q~^Z5BpkE2lEcHw83gS{>8z0w9d+5Bomoa9;P'
    'NK3?#qZ~QUMI13({FkwO*thGkmY6Nxw|u(!3?i2;fBp>GI@ZoVe7%Z2&>VG*`g!e~TuJVxE~TR5^8#1+b9~yr_?CLw6FhA{cW9x!'
    'eO8ZWu*dyoYT^|R8bK=b!nXSo4Bagp$-R&4nLKvvjHuf#uG@}?BiD*>l$^CquH?_BuARTTu`8-JJGFCLYN$NZd%L5`+jUOLbALwO'
    'b0x<+hFs5|x9pFo-+GRqeGx}aa*g*y99bm7BhT^<uXJ;D%3)gOTNSe1x3sc7p^~2&(>#Nxx!(-cqCzi{)>l|UbtrIl_02-jYkA44'
    'ysB_1VXyg&O3&cR*yWWC>OSJkmC<Wawcq!d*1kHb_GT-*5oO0~pQ#-spK~iz59)o4tLN2gYlJ7v9sk==zS*yRmbR7*>gt<pw&OsA'
    '9m_@7vgI9?bzGSX_vLV@;no^pmfF!)6?(BO*;h5KJz*N#r|b&ZX<Am1SfuP*6xDVf(W@P+mbE7=>ukp|&){XUlvQ2r2>Z#ZVyIU;'
    'x@*l>*=K<$pS7Nq&q6*5*&1%$UVOI4*?pTHin1^84{6gqXVRwO+K253MRvHgEA+}fwdo#bU#=#1y9b@gpV{agem#}P--(PkGIS6f'
    '85nV-y&oM3Mt+-vXR!8&BX{!na4h18i`(#MR2#ml{UdxA-7jk*+HiUJYVmp9jp0?r?Fq%^I5o39VP^N^RAqRa@~wKcJ>gY8t7=bs'
    '!XAE>qIz`5zQk#CzAa>5o73IHzVt+d7wbgW({WlKwkA&N!?isF>qB;5%dOuQW%mi~OuQbpBTlb}>)B_!&nzn9voCB_M~n0^D!ToJ'
    'El0@7$kj6Y{(~srxA(#KVO#s``><C&Q{Q*k7cTiTi|Ni*Uc=t~B*MF8BHRL9cCz8!#JscL6`9}VIu%v!C+D=>=)L7!@!8a?x48Z$'
    'f5X)tF%Nx*BVE_Ke!orVU40V#jN9Ve`ox{w(=I46s&?#w&#=X9T&^vm+`C2Ck}l<5+x=CWbGipzEaEQr9PUNCYmv7(0#hSAWBMvN'
    '%2)Q!#aGp5<EwMBL+$P=up`PFsru*9g4I!bLnqtQKgu4*=VDLvUUfw`trK1Y&-?uLrtyuy$^5O;ya?~5@>SrBh$9nu-9IGa$OQKJ'
    'pok;YBD|xBukN4ee)!zB#o6z9J6rWGdv9oz_lD^I$jFJ_0h_HnJj%|Y@!R>C?vT%*l|R#6XY5|~B=?|^5uUu6eVeIw{jFz4H@*$8'
    'ljr^8cdng&uiQsFKhHgCmtXntoSq%!?U85Y?ayz=YDP<Ll>OPCgZ*c-qdl8w`8;>0z4hN#zWzHQa!%xk8XIxM&TUi>)kb;x+0^~B'
    '-}#2>SQN1{AKU2)S;)ThrG@PYg>7FfNC;i0H7s)H6yrMu{n;PmBK%P-!ah5La-zT0x|#F4G^&Jg`q|dxT>GTkogYV#E5iCr_Sof7'
    '^_g&n^@;v1>~rSb1ENZ}{G7GPoCuE<_V~*>H5bbq)oMmQle4PL%{dqJ_)VT7_Ee$X^_vDRJ?_$1h063TEox6FGE1MPN{_xzn)&<t'
    'qNoxJ^>b6->d(xRC1>>ew3hx<ySpRmdpUnA=EjI4M|o5%jW{xsV|u3E^}Yquqx?4Q9JSP0`K`yCV|{1X{I>b5h#Jio;aaP5XLftd'
    'qv!Ujl;x(It9ALBEQtOVT`QMV5>@uB_{&}!F1w0Xyi~Tmn95!i>fwg1yRvT-ahI_wlyhYLrg8m3ex~}x^NmV3N7OYDH8y=PC&~w<'
    '=iL8$&W#VkrB&FMMfo|_?_SN{8P1KW<u&@bwjjEt1($t&MA>(Wur;de>%0H#KI~y$!LWyUZ4&mdZxydl<m+^EJ;_#u`dsukylxj~'
    'Qf4^ks4~OWbW>(;u{f4LtzH=67q59ghKM7k@5-WlcVi!X7qT|mccB`dd*8(_GgMM~*uSxT7kTH@!2jp&{bQrrzWuOs$Me&7W;`=C'
    '#)kmU*X4`&A|7%GLR^aYIuk!X<XXr=2qA=!zrH+5DWwh}ghz?v`1$(z^0>rtc!Ux{2qBbGN-3d~FTEv*Qc5YYCI}%eLI_z1A%u`+'
    'A%qY@^{jp7c%8k@K4<T9&e%i#0=AgF*ZQor&sqC()?O>IjiAu&2?cXqL!y#|awxF;<{d<qZ3?oK)}gY<c@|gg(Q+18W?}V%iYt4N'
    'zDvLwyF&bJ%bg*A(zFQT%iUz9U7?`#E-#X1MJzyU57DE?ryhNRxN;v^X;0v`*<yoO-tj(;mk3>q=}w3rkKnu%h#v>g$VTwpgJ|R#'
    's{;_?>$B_+DQlw`@du69u;5v_1$?cSXm~Ib?E18R3B$IJtlS$gw!=YSs}!r-;XDMsHH5Ss2W<z@$S%$FNKU#ATRz!;M892AUQ0QG'
    'x4S8Jh-f{euC;QUkL!t!B@PoA4wVi0LJ-J%jOoQb*$ENl353Hv@Y16sq8uSu9SN07e(I(BY_Qs5&tV330<f!lbPQ*TXeLsgCG&Pp'
    'D9Myz_s)q-$2`asRLt+iQo+Rjw(orK<}>8G*GYoe3167`J0Xm+d)q{&lOALW>ZGvTwk9j7Iv8_~V_&kn*&%Cn7{ekGv(qT@FuPGr'
    'W;`2Gl{Xko<({*r{|K_3P=A)QHE@ps^DB_|a0`v}u-m+7<OF!{B{ahDxIpkYFNsH=XFOUQYITn#E)$6^xkzNxN{BVvb~+eKTnX{D'
    'xGsm3tLVkLl=UsiB~z2|I@sqrl9b7Qji7N=5{*t#R|+MqMX^7-fBXwU_PPgTsidc1uA4;nUtDxIZp+7dM7<l-D+9)Qq+_DTu<ITm'
    'shL&ppb@6oZT#gyGk5QhhdP0=g0f$hP!ch?pV|FMV%s|*<qCE-(lNijPiDXCVfG#s-ElR$m`n_yK@3npk}{TPlyDvoLeka0>~6`&'
    'ocK0RHRxiZXmlZX<U`_r1zZ1<xSehzJ45LaLFplnl3J}dpD5Yf%Z{n`plOQ3EfJ*IG1&8CA#(E&jhqDSpQ4exX1>FRq^nxlL?9CN'
    '?=3U5IPUo8M8apjC1kq4ATvLocHL$ArrieHy(YGMMdTj~c|~4Tej44_<-@-T@l{Y>hdfs?vWayV4sQt#Z$fHX4Ex4Gz7yMSU}-<$'
    'yMpZQ5gK7tddCTR?|h&)EbR2+Wj4{*e3m`_fmr0dq(#KB(k*sl2+h1fGuImOQA;Y;qu7-~E&dUE!d7-S2c4o=j@M^`-X}%$Xneyw'
    '>I?Cx&mqrMiDCtLkCK?pxgHn$<`%BvkpcANd#%{Kt=Si&XceDP6RrxR%StSmP9QSTl-%>@Ih@p2;j=rO)Em*rQHUSv(8z0cX9tb2'
    'nq$>f{C<pA`RwSTf|y$Mo|sd|yRk%u_&~BMkV-o?8Zn+DSH+(tGgVS-MbtCz6P4-9!m2(uRPnq_J(0Jr?D9JGyc<i*Ardu6O4KK?'
    '$$T>7oGMjh6}gybvvl+@0XuUElJN?=`B24kG)-0fS+=oCnFWb@=9i+wj#2$Wg7ShYxp_Nn`@4=M77=|HdeC<`2!1Lm^Zm4mWxQAM'
    '_ac`PWR_G(F(*+P$6SWrH&^lJ>ZMg4d8eoZhb7AqMGKB^eC8+12^z~J(I^P~WCih)<yFcYPqg6fCla&tD4z7^!b!gqY48A^2d(5y'
    'y#~MELCe(y$yHTStW?w&!(kT_MV)z|mMWg3SySbUce2so8p}2(JENt_BjY54k{YuVm0<(#0%Gk*4|a=VEy1w0$`>mY9rw$12;byv'
    'r+1LpzP(Cq{uTj0u#U{!QRP+gpmcZ0iUodP3zC`fKO3uf{%1YWt5Z?0KHqw^IPyQ6h=d!flz5dW{d&f3fo-nhPqLe;JhK@#QH~=2'
    '6P5XzwjSR2+sJu;D?w?CB1)Zt^L`gWX{!&E0%ec{F_M)>+D?$!R;9#*L`6K(4sveYUgeWVik5*#iWb6N>z8qz6#feM!|;^WNvLbK'
    '1dS|O4Bx;IGCSbb(s49$2O^MuG|~jmt9@vM-N)Zu#oyfAMXb3~(VBrWPSJuRhq;IBo!wR5*Xj}M(7gncJ!*_rG!TACDoV5M7zNL?'
    '1B4gaPq>tQRe`Wx(K7T97RIBj8|Xoz%Ymvu_$V7)ZnGR>vf{yDm?)bS+fkId(pt$k(x2D+TmE2X#z*qqdcNydlo$Vvd|WdC&xs>Q'
    'v(JF;AR4*O@`cezr)EBHJj>WpW}U64mmwnkU{x@ynOQk3x0kFl<ZGS2fKh6Z&SxA!nlM&x7>#V#OureLdKx?2LQM?h^?{Z@lw_Rz'
    'ceg&!RlMont@n5RYG&|%Lu1P>O?s7-F?+;VEz#Dkx7n@ICGZxOxp|amI#LErY2?OmK1NnQT87m-rv>L>MJ{C!Dzsk4u?=L8pG6}V'
    'z&}r+k@qZ<mEd-~DtL`3ZaoOMt@d?b4QrUI8MBVeDy=q{*9Ry6Otp9G?Ong-60O~OYjIU0clI06J%{7qucwjb`!o|BC7E)%A=4BB'
    'dA$uh3C44?44LZlMVacbOx7<pXNWYXt2`r=GLR|xb!xC%AGAZLFe7%6`J((8{PhAth2eCL;B?l9)eLJ*?SFyQg1||ARgwQb1tcz#'
    'Z(0`+5__HRtws*z^+QD&M)UgUlnmyRZ&pWM?<m@^kk<>7f6hA8tser<0#E9V7H<`qS?b@=Sge`lLlYS<%FCEAWQ-Uxa!+OdG7f6N'
    ';bq8>GGvmL#cdy)g(vwh2*+EnGp?c$hV>PK^<@wKV8}1j&(OcDSRc;ohaIriOR^X;&+6#bJLIvp_MW{?P`m2ELk-l3hZ-7q_E6Rf'
    '<wh0X3+1}a8EU1q2CS!ee7zRLyfX3fUGU=DNHf-F<|fhgmon+fu)RgryIIlLI`@@jJ>TyVoo-hJYuD0xEQY*?*4wR_5^(FSbH2sv'
    '<E*noQ(n#UnMdxaeP$Nqx*=SyLX19!M$W*K{V^VaJuymR^aljr`(?y;I0$?_oT#j84udBbh~}eJ<+Js$AU1zQq$re83VK%BZ-f6<'
    '`zoe^pPB4zGX{S8lzjbpf<{;u&c{_=B@g0c6##A?PEuUn3cIa9ka=1)eKw`17iO>LM5<>2*vtEw%DcV%pRL5+{vMvwZ!t#+nJTZU'
    '_-;2Zao(wBKJPh=_B!7aF8j&sh^8!4*-m0yMj*Q#LQs5F1{A%X*UTI#b}NL)`r3!A<vM$Luy~ozVB+dj@A3B{)<uY5{I<%w2bb%l'
    '#=Z+rAX(RHru4>Xve~|VY9!yJ=NrFwK0V|$FY~lGo)*&Vh6|DTeLylZOg@tNKg=j5eTwXQAp!aAD7#<_eE*B$3<U694UMp@ye~xe'
    'PgVZxXx4{8y03Bjy3wQ$G=4wn>rHxp<M(zaDZA?aA*9Vl&D2kB%@kW}B+}ZXw-(oIBj>5oYIoQj6|!0=>|ev-vfw6@6TJ*PB8jwO'
    'dd7*K(Ew2OrKfOK(b=pM{3DGt*{Ye^4o&4FJ5(Sg*g{>VL|c>I*7&{k98y~K5xZ4FR!z&VI?Gr!G1#OJPOi#oW2M-BOT_I~-K0s+'
    'o?^33=>+wz5)4(h?;c#2F^D<mV_m_Y>d^?pqmJN_3(yLMAn-6&G3rSnv_)s8UEp7Hh-UTS;MVRDR34if=BsJVL91?X;e%N;G7@QT'
    '(%VaTPR0~XdZF?ATw=6IA1%rvjv}^e>T4OZa%&k9C`DjT!N(RL1XxA5MuN$F1x%PkJSI$f8BCa6nurXIzGYx*mtx4E>{43GnAKQ|'
    't?Z<)okjA1|01IM0tMaKio87TeqznhSsdnbbQXna6y9uKhg2$>YuEhD*W#lF)ZOo(<{;AWNER})(a05u0$b6@PS*JYja0+_X%6#Q'
    'U`q*hODYOGQ5M*8@V;e4`et9!)9fskXSsr`vn(8pN6>fI)O>5)cx=ho*>?AWKddJ2>{aB=wlb_NnL>meq~61hG2t4b+3Ij`Yj+A_'
    '!WOdXngH<}4gyc<7+dU3iy<alho3;;Uu(mB&S6`a&*^Hl!K2N&BB+N5y-QPGMIj=$%Q<W(nyyvXR3UD+<{WmA)!WN}b0G+vm1A++'
    'ubSX*8<5r$?DiJHVO=<Q340v67)-6Q!G#C(8lhWP9%1*`!hGj|4PoyRsmAfvo*bKqEE_$@;x|_JViB*gx!hCpCR7C3gV4DFUvIXf'
    'kr4QGSD3G?yoF%8*$1Yo=K(*MdX4$*o^st`{<d{jSgMLdC?lv#v5m~wEjgolT?#6T*jHE$*PUTLBWwqece`f<WaaI1tl_$wNVL;4'
    'f~>|y51DaySgMLes5yu_6QM5YIOrAZ-(Do|Ik4M4Vz<3Sr#+H74STH>66$ok8NNTvS8Ui9R>x{sV8erC_Wd4a@AO*lG$fNd!fJ&K'
    'g!x(_ePO<SL2uY&Wsgvgpx$jiS)(uPvEoO_b5+=oOs$YXV#$H9a!rnqs5a~&GW(#1**({W4SB2fH75hvph)%waD(>@K3~JL;W&Pi'
    'gTD=j`5LoF!hBVU!(m^QKth4nm<>7C78xPlJRJ5|@gpRvF?*DtG!phz2_zJFjoFY4v(0M8o(%JKCr*U<JIlwzN>w95zUyg(oNLCO'
    'A`+hTEg{qWG@1F-wCmm%R;wj)Da_XrIZteQj_7qJ?A0P3YiNX=Ysp>+^Y`)3hdo!H2#IRRUL-hN2&-w~yOwN7=1V!NC2}pyXOmtg'
    'C|&Y_(y$;q<tka_vX50dJtO8ELs{!NTo3aVKdyy+R{XGen_psgPsm!=!#*p4*u*8OC>0c0fG5BLJVLsJ;dycojeG%YZ-@EX#W#tE'
    '{1WzDJtGuo-H(un9c49U?~o_J?XXfsj*zIv?A<V5)!|M!kV+k)velTCiW6AHxd&ms2FQJ~3+{z|R_X|qtu}1Pxi)Np*zQ3%kcu23'
    'QEk|V<Q!foJAcw59a&t1Gs6q~^_SgdAbi4OqQ|4M>)~88_9>C*Nm!L%vfAo7nel1axH(a@WT!9tw*D&2_h=j=XW18FKkSngjh6(C'
    'v1w<J>`n!*iPo<I<dNQz*<V)-k0iIJ&;Jf0xd?i5H^O%*H1ZUxhtEYLM<GfGqmcqU8$KaC?!&WT0*$cBwBzJ7{w_fN%5!DfkaG{B'
    '_r$*^!m2EmwI=Nc;ydpHVXi#Xq?O_$*&F{$n6EMWnIQ8itjcZ$RAbhK2ht)uNAo2d6z^oMF&m2TJ`QUK#5nn^F&mPvsc;T<bp~m}'
    'YR^_j_}a5^f^9ew6kFw$GjXmxn~d-=e|5w!`@#5xG?_UWnQp#F<|`iKh3X?bFO(zlXChwNs-U?(#tStN3F{+Xc_%B&F(<;GVH+Yr'
    'GES<zkZOgiMZokgM_N3GJ-i5wykNP?5x!REe1huSh*uUXfNHTJQ3l-{*8PB3sxcBIAH`Umg#?oY5wARzYwb!89F*7-n3b0x`I$zG'
    'Bm4<{QKa&CD(n60rNq`tB0(}s%>S2>RhCAAV4M^%5pYUwwq61pT?>+b5u5^7q7lYNt%&fP#`4J5#z&RrXLWE^5r1A837&Cc=&dH`'
    't%?NAMEOC_>sLQky}2#I=f~zFd~Dwm5ytjmljE?>yk|T?E15AbIinJ5B9KMQ53MC~wfWSvoy@paa>hQ-nzne#7uX2-0=-DyM{vI1'
    'hDQ1!ir5t4bBWeR_#Q-^MDKMjdRH0JOXNp|g=|V3>QzL=wO1Jnwt+~uUQ#*{2egsQxIuEp&Or2)=|XUm^&B9!+7jV8h)of73EcRr'
    'aPe1h1A&mqjfDEX>B%@n`Ca4`y_G*jhlSim_1`JhAxMIZwmH!()2W-R(dE8I_3tvpw{~x+zqm#iZe2`jQ>gQbLm?ykre6+k`W__p'
    'W0s2<;dz<u#J1aPZEKHS$+iVaA9bFk$1%FwMRw3mmmO4N>>yD#&Thg+?BdyoxR8wq7qfkPqd!6&i$4`+8xs~rJY)1v!B2|0#l3Nr'
    'd!{WA#qCGhFeYmc@!B3+ueC^%w0iBI7+yQxV2|Nmg5e%_3^S!Q{sh(lz1a<(;!2HvFa)cFMOG2>JO{`LZom5pE^KlUwr_aGlN=;7'
    'A5fgxQ~r!VHo51=HsA-2;Zq^J*$+kde4&2A3-u9wdwnCRs&AhoFEmIb?DuUEb~YR$GY?A6ERJr3+(=l+R|umVJ4{9alOx2AhlwtS'
    '6m=Q)Y)2aV*u4>k$w~Z3#5-1^jHaVxm0=&NxMehj*)!ORNyy|tiqTMmY!q-DqJT3IzMuFBG{Slw9Ve&bW1`b>SjcI(#!^B?i_Ym9'
    'JK6ceN#e05B5K$c8ti-VoFYDO($NQ0qb27(t`;@f;WGpg!g-_x%V;`F5IZBe$HlP~<3P?44&<ze1BnZn3dtBt$bpDwR*1E%JkkZS'
    'Q_ef?6mPK=!|)=(@Pa&siZPZK4CP}jx#!jDKZ5UKQB>m#atfX!9IAnHxQkCM5SiSF@cBkpBYeKm6>@^O?3ums%C%Veq-#W?t3LUp'
    '>tx1jW!JG!`YzxtVw0Oh-Wz3O`e=-0$Nk(UC*oTXKm3x_K6i+|w>>jUvif!^e#w6r;q!AI5Z>S(LFsP94=d$|+v;?T_D2cg4<f3('
    'leKGhft;&H17w^?ZjuLP$&KTCOgO$r1f_=&RaVLm_fv4R;Zx#mk0XBgC2Nk=Got%b&&-knSK$)f$nDrhIH`X?8r*?B{05DT1BPP}'
    'zMAF>!reTN1jSZ4d$U?p#C1AnwV{dZV}bKdENAI8S?OgYC_btje2(>w-aB%xe@kNiH#5#hS-H4zBH_D$xVQ;2^LWH7v*cBG`AqsX'
    'aDLZNJj}S7Pb4SjBhl+aMe$D7r}<|h?I+*N62svOnfY_XE8`Rd4)VRf<H*V^b159<IS25Bz<4K?=M#<ch=rqG`6v%Ok84yU&g`m='
    '@+a|lG&p|A>Q_mEQgzfXv*d^KDR}yV{}@iwYmhE?;55Aujf_L|Fb9o<!9VMw{4*y<{4*U5g2hsOuF_b{j<>0g@?1(?v|M}?yW`eC'
    'R;-T(%~Q$kI4{wb_)9@!l+PBMOEjGm{n~gcD=*U&<xd2SQGdM50y1M$bY?P|#CP_ZqdbSUILh-ii-;ZzqtneVS#7n1NVM29vP{RN'
    'WX2^fGsZpZDB`5VclK69`8#{dqWtN&IT{>ewVa@_EIKocmGzXcl4!jm8UzEy_>k3P_Lb3@%z1L{sswNH4N?BCU3--0^72vsu3bx%'
    '=d;#CE0NE#+P{_fWj^Yav0^+>8?kw7v{G`R#CPr1MR{(vgCNr$trR}Xde^Qq%5y90qCqoIjO$uYe7rLnTrQLZN|JGoo6V!Z33NsI'
    'yLOwS{9U_E1ltYKO5?4pJ9-N_Wo?f7Wu_SKvz5%eB|6<XNiv)rtLC>INz0JwCh~Vh{qj}}nQdg|?&x%}fpMwKd&U{<AaZVx`enG-'
    'Id&&G$L@#*!F+kmc^VFTy{&JD-qP9MXk)283DB_{DoXzo;5}pLre6z0y=dePe2IU6khuZe!3i8+K*TW+<?j&gkMeg2dkA;1n^<#K'
    'w32u_E7P=>ct}qfn7Dlelf4zo#M#{;JQ(Hg5FQ{5-TpE#bgKDtg$Ab_vR-2AgV7)}y_o;^lT~^viaQhAnpFfHj`DX1hX^Y)NLZnP'
    '=+~A3X5|nM5q}<vmMiz`FhTE7^lQ%jGJB^2l1B-zG(yfS!_k?|%{oRTI_i@HJWggj7M;o5EIZvFz+3%Fl)uw=4vnx}uG7SZr-*(h'
    'qBEPzb%vbiPY1}1ohAC7iOys$S7|QB^IRmnz<GkkxoBnPY+WMAUX1$7*}6>5|Cgebp0j0ld;ccVgXMBvi}JZ#R|$GoqLq`&b%S`}'
    'wP<j;T)z<AZ$v9Gm&@$)1<});D1UeF7GZC0mWdg=O?Jkuif6`3vnK(odjzXHfiqo<ExAw5X!oX_NAh-i|1F%~KVw@%=HSaHf5-0$'
    '8eutPg(#mxHcD`KFynlhl}mg`BrF8Pm^~&lKb$tkOyz6gQ?T7L!o55tXU``U#dlfH<If4&&wMjQ>`vDUg2VG@khcf@@KN#^`+X1<'
    'yhFOMDlM-G8}o`F`LY7}B`fpxhMc%xmo3NZEy3qa#pZaG=06D0!v`cet7tz#eEVIX{1V$i?+IcPQNOnbJ#Y~Uv6q$4`A9gH4`s{H'
    'VmV=-h(CWU1B0Z1q0g_9)^+=VJE%k75w=4_5l17J0Qpdi|5~ZVcw2mq2F*(O&7ZRJL*W>I(g3Y|<Q+xHjNw?h`62l}e(4y`_f!*k'
    '<FV<kU1jBaGDM<u%xhICc9zb?_|s}876gMN%l8aRM*?49uQeihud^zsF`gf&Cn(j$X0jGlX|52+JC`8d5DOynidAx&PjsIf^U5qq'
    'us%M%s<H1X3z57GpQadpUT=&ASBr{y$O3{=Q*0&~Bs(5yG4YdyvEX>5B?N)Ru}Z%aX!}%vI{inGHWz>i*n&o`!h5?d#@``a731#^'
    'E{pMZ2%BR(_p&thwcH_GPGnyeE6*Lmm1L#mv9IS2;hGrF|E!Mjk^ib#W!)icArh{M1#^cmPiAh3Rqh?ahp>}7WBeV$_889#ttEQ3'
    '#VYp>VF!`6Jr>Lz!gXZkj##DNA!MA-Mq<+qF`ftLj8#(YDr+CUO)>s-yfGGh6)MJtZ6<4Nid9~2l3X9Yy)nKI-;NmHhp#)v_u<=0'
    'd}B+jQfpdS`|xceJG46%Ox3FGgoW4^`#P&u+1(V_732Hx?IgQkN9^n2qpW@SdWh|I#mdDXG5%u@IV1GMDy<J+UyQ%gx1aDh`-mQU'
    'V>8=_?*Nf#f6QMWzFsopfmr4A;Tw$ccl!Ft>9#KxTpzvxf<}L=68i8B5v>Pf!S&%gOlBX7Rc;@?((Eg;ko|#VXLtS1#`wE_Cu00v'
    'zmXV!*Ke4xM@M3n-&gM_@z;@<zrK3Mh%X$CReoQ+Q!zfL?<7IyM65FV>YXMW$f;O)`s$q_K7Km(HTKnGcl|EM_`7}=$k(&;1lzN*'
    '%I>Rok;L#9V!`y)yF_Nb7^}p-dhD*>^%#HG?+TIsa?EdEJ%-FRGV>MRn5%ZGYnEX4Z;+Ge^;nSI^%xqz5HxPYymsC5ibiKx?YzGr'
    '0U2mW@(=LlzaQgkeBUAG{aXapo3S9e?gi1qPm~SLc%i$*Qg>p0yX&#K=l96@_iik>u6wRoQXV?zxp9D_gadp)(7PY=+I7#>)=GW#'
    '>}>szc<E>?$nJV<FFYccJdAnmy62-4n^Y7fws^7M>R4h7>B8PAPYKWSgm5E|V?lS_lk;}9n9D9}>lxAIX{=n`^%#0D$coQmL3iDw'
    '=&`rS6c<sNaU{~;r1v*|pN=xFEEnoOo$WvUeRo)EDY9hEN%v<(0sQ1O(rYcNs)|OoYNmG$O`Vgb<SEH95@zd{<hvBn8W+`RQ<_Ke'
    '_kR_9A7ZTQD}wJ!v}#@og^?)~wBFF)zWyIID;9K@1~s!CzB^g=D$=V<GZ8mdUn@ehS?h0ZwxBtG3e9vRADWCW1$e$?xt_#|Z^~-L'
    '9)#&u3yU(67--T5CTC9$oX!rM{(dCER-2r?D?It@kvJPKt@<U>-+l+{dRw2I&n@F!?rFJW9YnnGDQsH)7`}+1k)?kFa)i*xcoH)6'
    '&`7bm*jVB-!uS^KruS&1nq}dlk%O99b-_Stn-!^&9ZHB9_85sWgf1nRJtmQBj!$ZY5qs&=N~Y(hjI|RbpJ;2=+M1h7Rx0`8m-xWs'
    'E<jewhXqzL`8UAh1HxmUW@4r))9Gy6BraH{IysrF-wQqxX+F41L#+h6)eAxryNBDGrBzEh^SkFrq#xFC@&@t#=zx=ihCF>W;PeII'
    'G@_ZlZ%BN=l(-m)jm#Qs(g!CcE?F(!emdJeDS7qa>FnU-pDA<ycNV>PB+14ny}Jdh80p`6$AfPl*2EGS7)CgWN|>gY#6?VlkjN?*'
    'JBx)7rbjgs<)Nu3gN?i;4~rOx#s`|Ufk{s*$z9F#F#SLI<D|!d)RX=<=?TTxl_~e6q)2W-7gbhun8+G(m({><3gf|MZLplO9?`@y'
    'anFmg<L9=o&cpj6hj3+GHj-#$1FL8p=XY8(?(Wxyeo4-+(X#^lI&Hp3x(vTQ;AN+sMaYks{B{jItym;Hk{WH&M~fCHH0gz+WX9g-'
    'Eimg)lYR(ESh7gUlyLJs(;~%v_)@_h=C>JmH>VM@7c>)n7d@DK?s_nNgVv*@!7lKP4ACI%pn)N=X$eE4X|{xn&y*xJBup3*&xp_1'
    'evbzKX+Y>Rd(;to<P_{-c$QF0hQ>_T!;nzg_sb)xRo=~j_#A}z7R|H@cM3Pp%)j?`W;SbDvAY3i&Fz{g1-E9KWz8T?R9kE~l)RK?'
    'DyLP4t}<z;r;D_|0bJ8!G;#`dMiUwtW495|NVjI5r^=#DN#1T7yw-}W;^BPF-6R2jTu6MQX<B@P-Hcs?R`1nJdAQZLTKM;JoW@I1'
    '_1aiqn|1ZFop2p)KY))eMOd+0<x2>9i(Szx$0@la=YGw{>YmTT92W=3G!tZ&$|F;T({VGqsX?S_cK7x&oSsWk9ksES8K3`tCQia`'
    'J7FzU`^Y04_p&=aXk;B=y%LR_(9HLMi?-8y$}VYj%*GA}?IoMG^ECHG8=gR`<NOVpRdH#_r~P!z{9p}{d9{Sh(|!6@*^$$GVs^;P'
    'g}k1%2;UCyl2$ZwMKkv+r<ED8|Gtt=-DX7!@SQfINvnb;m2vLAsJTmA8Ru+UHWxgqo!DV*Twbf0J(F8Ks)K0K9#^-|%$~btJgSn;'
    '-;$k2AV0YeM-32bY)2zWc;anFBP^eFL!8e~ULPlY8seqQjPBy`!_3d<o~N;B4RTw%ztgn7-!UfR8<wLH7vChFoNJb4F5PCXdG>SJ'
    'oyIm2sW(hXJ<qbzcb1iO8L1gEo5&g)16)Ih%siX9zH>sxHj@>eMqPw6+e&oW9QSV_J{NnDgwIsD*qP;?bR&5;X{JsFm)2tD+2T`C'
    'cci$=R31n%1B9*2G_;rf9=m-;*6Zfi6W>^vm4{rD*5Z1gH?yAodh0dCdFQnndf3nF<`F&cMA(D$d(ZBup^;zMjkGwQ+q^x_<u=a}'
    '$_iO|hLrO_O5IL-lG81o5pv56Jby!Hw0k=2#yJO?sikd>KK99&(6bpbJp`HEw#c|;Eq4DF^q41w%slapj;YKrIgco<u@#;U2aq=G'
    'p66cT{d;V^Kjz}4z2CJ7WU}5H*hlc(8@J2#kBKwNAeYQ(C2~W?<$j3R$Ly*l9*mP)ZgHvGAVMGOC72wH`?@6(_jT{YE(bBL+B1DM'
    'WKkc-{svE@!*Rar=|G&XchXPZSbcGicT3`d-z^b7hZu`CL~J<__jOCeMgx{teJD;kB}~27e`|TK|8eP!jB{<f|0X;Ie`DS~_>J9K'
    '>om9c$1>+{xjE;_J)PJM&0(Yw)A0z=@o-#Dp2JQ0;YoR>;<De1V;ET-W#+WIOFu%i7>>I|f;KCD=d8sIcIS?)H4+cbf_!fJBBA8Q'
    'Y*TOA-&aY*vRq~lJTcDVH#_*rNi_0=-N%dbS)j*lPOfI`_<R4c<7Q1TzxXDGRIF%SrJdbKB-)*fdtBWmqO|4=pN{i6!>8hcoa|Y`'
    'btR)iVP?O0W~nIA4%MUJMHi5E%K+zdXk@Ks`kv#B1?=JCSd!s+p5S@T5l=rcrSnY*zp-U$l~&dTgZSqKNB{I6OR_rymk6F0<4(5}'
    '{KS;P8y7A&WaK>4_5JuA<R>LiY>|Om69|EqaAW-*VT67`BN_1gYjOVG+SNF@wHQ~rs}nEVT^$#;;5zYvYw<vC-3Yzz26@9?kNdoh'
    'qk^8=eH*Fg;d4OpHqz@lyUj?j{UsjAog4=qX@S<AfG8znyq!}<T+x^0tA?a{9IKbziSyM5ZcFiA7RD<js$F@P%zlUL7*lrGH$}ZB'
    '-xLB39QZVaS==mr1HMN;Lb9`rgi$ndn%!UIp9qnAOuwcD5HV?v^112e1%K;YY1TD^us)+=)(7OY)Jw6Ek@3I}$qBT;pFrmc*((-7'
    'mSV@0L<JAR1Dcq^jCPnh+&cqgo)8}RG12K!+)a+DTf_rJouq6lV94ijJh1Mzf1eR~pTzBW9k<xfx{|e0@pHoEJc~=!Jdv@gY>k&x'
    'k0Q6y3EzG`#`#*ZZ{vJznwP{2#>jK)Mcl4FkDc63_P6)xn36BqRjPhPyx?VAdZmb)*Rq;LZwMx@;>s0fY-V?;S%i5(sa^dH&=@E7'
    'd`IwkYr9Kol>E@S(oT)=sps^>X6)$%k#}5P-g)gHZ--D`hRJ)f#)SMD)~W#hFtPCsH#_f!m_3x>d(C_%G5e=De~bU464S$?({ISL'
    'm~uQ)vth=_#Rt9+$v?;4_#`3sW+OSP$)F|pRlWqe%2XW^)p*F^PBWa(suO&#nJCc(JjAzktQ8yL37-FmCS3WCsi^Ar;;2e^dY&g_'
    'cZ5-tm}gBU_>)<6La;93$=o9@E6<uHYbB-El8>s^Iz&|#E6n3~R$V@-;QEjNuaHODZGmWG5gLiZGiojx`3U&eC-{C?bp)kM!ih)m'
    '7R$+21d6$w8<`h15Si-}KI_#8y=V^E*9{4$3O}k*nQ-5Uc{rEoOnd{k3F*SLn@^COn^2Y~BD+UC)UHW6cSc)~;90Szgc2(zwEIGW'
    '%mPOr^A^21Bcm3@In>UCr@?Zh(K~kkBf)>oTTHZGq^`AV4Cu_%s>OU<Eg*J#gY4NQ31yreP7RD-T9)9?B+UtBhAbHf2a}X}1}uii'
    'WfhW|Re)GQ^jMxyX1HwhU@X;2GW&`^W><{ul06a?_tp?uS0((|!s;(A37!dClTcv7k`gC+S;i}=%4ak}gs~ZEa3A=Lb!ddKT5SnF'
    'm$fy)pY`$ykL+5~3sWa}Zzi2tjkUxV+7inASyIGmbr4L}COk4{NhMYTGh|75R%3mFXEi#B2I~?Y*|ns^3ErLYN;;otHxPN(Cp_|D'
    'NfE2Dk*u*H;gJbT%CZ`c(Nj`BMpy|k!Zxy>x1tf|yIT@GBfB{v#iAu;8QB^opRu!c7umgA6UsbUQuOVio7lN4;gKQphlw>RlG@Mh'
    '5C!Z)8Z-c6I|yRi63Q%EQp8*ABoWz;gl8r!87LFx5*aXm+D+u&mGI0|B}IH#4_Re*psNHEGpREc7yfcmm(+j%Eoj$W)NapzUL2`I'
    'BjbNm9C?_S8hH#I`pzIsmOvD82#uuSsnwg{`~2)DJjXtQ?VdysK2y>$uX*6%gikS+?R0>g#`Y(CvUEvN4d8=htpk3Uxuh!F;U#Jl'
    'vmFD3?dT&u(3|kg-X&GfwQ8}P9osQT*p7jO60epNu^mIi`h$KMwWI>u;m({XL^2vY6OIw?^9W%(4il{pC491R$v_ysh}=nqdBq6v'
    '>LUryd|Oh~Defroy%9C0Eg1+8<Prtiq4Wk&IzgTW#|du75}w((V6+p)hSr&LpwUU<y(bbrc{L%6bDCgv(mSK3c4C$8({6{<VaT|='
    'j<Yg>x44wx`+=QH@cqEfl5@_PgxAjYUiGu~13OP7I+swL*V+N=0-5oAV!C_R+v$4_Y;q;R_iVpR<h_*e+S%Sq&vsEaR@SZTDv|C='
    'LbboWHSgsbnel33CVSM2EjAb4x_6MgH^GKCi4A`tC(Y}LAUfMG*Hk;$+i}3R$l3m8!he5zEBkkwtZ^$5T<>~W910oteaLR}JV@}}'
    'dF~P$-bwiBZ*TSb`(*aJi6DB~yFH<3UsQ1)uh9g5i||1rsQ&iW`?v+N(rBV`d&|o`Ej|~|_NijEz0zqv2WR^?NLSXm^En!M%<^Uv'
    '{N4CR1fhqCpgY);JE@*K)!X#}drG3~Cy8MCv_B&=KTXVZk9s>CZi8*d5`49-7exN&zL8Otzt1rX`W2CI%s0Y}4}48#ewC=CUi4yX'
    'u7POa1CoCfuzE-A`<CeVCgHb(y{vs{tYpXij+3*`yF?Iu?5(zbPgWUER8o(6JABqdbnuzvLVhGC(+`Pqb+G?L*7}&J)DHGsjxDkH'
    '=R}a5=b2xHs!5J*B8ZOks(Z~jwi07i?Atb$`h+5dN5!}xHI7CWfgi?^rtCIvw3@#i2NB0t)yLj?m$JH=_x5;o@SW-zdP#y_b#>4k'
    '?ERo86J^;U34BlLJ@OymLQ)fG1kT#b$A;RwCw)6<uHI$lQFI&GNfBZHch_IGIPpEH4@9E(o+V;Bek3z~D7%h*(ow@x*x6C^RqzDZ'
    'O8b_#)fb}2r)pKiW%V$=)kT_}xSv!A$p~jwCiM^-F~4$jJ9Yq#2s+iL!r$`xhQ5`Pdf2nRowD6~Q)wg}oM%#Tf=1K>8Uj`<l_ayr'
    'J<Q&zjEwOWEh3Rin93j-f#YE)88Vuze7D4xw1|L5O6ABJ8Ga32xQ3Paj}$zkQSebUVOz1&T<X8Vc>u+p3#nE#avCClCExN9KqDFf'
    'W*{{OjX=(2s-AdC9q%a)RxrL-M1=kAm1c3wSW3+$JA96Khr?>dceRM1W?5=Jnh{tLw#LxZ8jv;6EnVj!BCOOUGoxJvhltGk`UT*#'
    '0BHlfSgMJ5f1|DUOH_A|(d;`ntSnU>BBD4h3EC_owpk!=8@qZ9HX6YBI<*+B1m|nEHt{Qn*i$HH;0N)Wf3>DILyL3-a0zzyN^EPu'
    's~L?jy_OQamQ1@|87EFJwTwvEtSF(NgMDfRnR(f_UM-@kyC@p6jpx92tC6&DCQYqEBXA~V76<Pyt%ly?Kd8n`s=5q2KAG1Lv{!$t'
    'Hh-smR%EJ$;IPIA4#Hmao@VP*Jf|;%xAbPD5!^vctwSSlPdc?0jR1#}Y9k1@N+L`nGA{eVqPrP&{h$_g*<{_M+L6p~5@&kZt*8rE'
    'bdAB-e(50iv@7CMkoOG-d}ur*_6MjOn%Y42{(9o`>%R3aNspJk5A)LK$%b!9ZA8)n2f{Ssq&45yKlq8IpmtSi6IpSi`id^Gmg^qT'
    '#kz>%CO3ab!khgEe3A!*yU+;mPN^*ffz2WWzH`G|6q9khlM=Sh(U*1pGa&!(4UJs5iEuHVz`fkYQr&XDte*O%^9n7FC)aMU$aaK3'
    'lYg6}6fH#lKU3D+T~9I2|D|V~cLa=cpW@qdW3j(_st+N5uGncX_4m-o0eGVBMk7sNum2j2Fl}~9YSX9eHCDWLdG?F{#^slBNxz5-'
    '{K6{jD!{3S;Pl_RNMXcp;bs>pjQ>~NY@c17`nzalNp>pSg)rL<v+PlyrMgQ_^6;?48$AtA@co#l09^k*!F8`3uGPbm(sc@O-6y$D'
    'C&Kao{PG`ou*fi)MHc^IN55oe+kc2;c?i<|xd-X6j)O4ELBf6gxjIW)&13J#1%^d2GmC9{UF>DdQr$yz`A0|>CGIqg=TiD*wfv2P'
    'kz#N2)L|s!C_Jlw#4Hckx*v@&&Hgd3nJi-)F7TSk{<6AY|1CZB7jpKotjwNG1Co|4@O#LeHw_mY_s~|r^)K;z5+oYr_mKNao}}v$'
    '#PNs7?)yu1=DC{A&YrM;CB_?b!{Kr96Bhr!Y8f8(96bO3DbnjGV1ERSjDU1Mb6mC}&y1w@^!sWW=d<sr|3qFcyAzZ}F7{n+*x!uR'
    '<F<QP;^Y-}&QXOfLaC!jI)=cA?bAkLJ&UBw%KwblU5z29R#y9cwdl+>0n+`of@N$@bQbBL|7+?v;q3p~A7@YeREoO|XMB8bo6`Yb'
    'hLTg7d}%6<+(o(#z**#f#$Vy#Eb?#A$Q5|MokAnf2O;$@@Eu>k=!ET)N~oRSge69!MGzaFR9qLIQJCcaQf-E?qU0`T7KZ0(g6F@Q'
    'HmR(5{%gf``v{(A6fM%{*%QR5-Uq)uPyF`Z5}eO^_8;f}A1Axmit{<ib>n2elqCNjBxi6w-3tGIb+ZJAbOGUc2&DQS%@O5q5$G(e'
    '{M+g-0nY!EB1*#q=Zk7H2u{1=6+5NR9}nRC@dt$YVu;nQ61Me!K_k#XK6Ob^i%##h2-7cAEO+X%ci*VSc41#f|5qQLhELHxzMfUf'
    '<WBX0MXr%2&;KTA5q##B@hg0~wzI<jZiAcB7c<LQ`xwl5-S3=;3-I_=EiCi3Y5?}jO=OF`V4eR1$3>vg4UtB&@}N_uoPFtOov}o}'
    'sQHQIbjzN}|EFlDxPN&=9Dwp~tDR5uP`xAde<9@GfVBVKhqTl)Z<Ftk|K9s|NV2D-zCDITCm5#h9e4ZU*(@hC#?SxXHi&unR*B9+'
    'zUHY`&Hdj}U)16qvQ)9M#aQYQ$p!rXNXF1T@)hg<QAfjt1@JYG4NLI><otgfpD?oAfc2et-|w8&Lao)l!MgAk8pP-Sf!OYW$aZS0'
    'S9`IYh#lZELc!|_<lFUs_%@I)%+-S4*r|tTMd%L9WH49>v!fe)iyQf|f1;{?{NH81DXlpY>F?M3`+iMFOZPSM<9|_=2=!^1q@Xvp'
    '&v{#tvQh0xU>#l{{Z@l_JV7H2gU1AeM-`1hCTaiN-v~bRlxXuL5N-O1HZNfI=VZO7-v(=Gvv&eQZ<GD^C*$7G$j_y9Mt&Tas2YI3'
    'CEEJ+w!U9WEB1z3Cs*nXm)2`;bdU4$@V0n`zrq0KV`!vDGyTq4R^vX^$WNw(CORXDfqs2JENd6JbM+BceM#gP`?j2z4L44&jXE2h'
    'p8lu67Ox2gugYqRVPXrYBA$9n<ak|HIXa0P{m2$Q=6X01otoXW$}Befludd=?UO5v{M0s4)dq4H>zCwV67)t}4LN!m)uOb^z!!%R'
    'r+gFmh))Q=I@os;Xk-y!JdQ?&G&9<B*7@hbiK;=X&V&8>;G{-B^E#W@M-0Do)j1gKOIVlWFulPA`$D7rn_-mQStMvpd^-~!QXptC'
    'YknZ|y?2+-#Kx4bv`<Vs_l5?PtXc44%`(W*Bk@K$3_Ifseg^}VpYaVS&D>8zQ|L~8!6i@TpV}v?+S${mW1_0V{^>JdK7B@h9-XKf'
    'h5z+aVWO%4e@hvAs-#=At@!`rCEe&9-V>U<eCB$R@|pU0kk2Y*J;ab&l1KN8Cv;6|B+)gsRYsS2MTp1^nv_XyQ`#wemDMZE^^|cn'
    'HB<Bo@xFWnr;iN6`!IM;H5!4+*{L|ONjT|6XH%Q9?SztUn{AkFGtU1Z*waiBp#z=A8G?bWPEQ$6*lk;~ZZcUOt)~Z7+m0^q?r1=o'
    '?gq?rME6Xfy3>;+`+`tU*3FgK)_ZI)-(>%dCh(J`_0%#4>Aqhx?II^zpeIRo|9mcyXHIfDu%ai*>9J8~qxY<sFN+{M74IWpp4Xv~'
    'D4cRuppj#6%2|v?*d3PzXoT6Kk=SDXwD<-+*(%r~kdv%+b$0)6AwpwVGZEvYGNbe#rtiFK_CjHIw27Px<>j1~GwLBN2;71?tJ+z7'
    '7wm|o2uX(R5`yjG8TEmJA8gBdg0(xnEF<VGP0pmW)H8R0m6s>^+n>v9<TNAXA1dc8dqz{2bNbJ;4wd=f^pZ#TZ-kw=3XL!utt2*D'
    ';mbzTcOv#;qv<>WTcs_qS_lN~RUXiu&U11}{%VlFg~-3!m;BRr=50kh#4^h_t&)7XAM+Dc`SHKiTvhrKn+Q*y!z8kYo&z>*2%C$n'
    'iUAsF*UTO1K?<7X9F#uRS{G}H#BE8x>y%btn6#4>)_Po_FEC766!TKrtKn8O(&P-(y4Zw9mcpBQeUiW3-kIbx1lA$_^NzRjjCc2>'
    '^hOLc`M1fpFsps2H9OpHcb)m?(tIO7woX*FvYCyVl$xmPK`Z#o2BOjWfHb1{q71{0WW@~ut=L&M3}tTEZUmp%inM#oDk2blHzk9S'
    'it4)+>DyuZrNkM@Vl~qoi@PWPU0g$SCzNH1cOl)jX{P>i68yC(!A}so7A2@|FG}!pX`d(JSORP2LpNEwOMdO2ODkgS+d%sg&PDAD'
    '(|~Y6I#c`*#DzWh`~W_;6OAxzwi9f&dBMiiptpLE*u@t%l52>(Zv?z=7t(UCW+Guou*IIcH?0G43|I#u6w^8*KSP`XvO$CcvX%B6'
    '&E(QRmfb{_U7lnyS0u8SQaZ@8Ta#bYoSEovO5>=%L)T&O%KZotX0JU2qn>0C@|L8W!qMGcdx<Q2Jjr6NXvk8MP0n{z>}6_6)|B%R'
    'J4-DAEDj|3yOH~C&IQXX%)e^<$f{Z%Br6^8xl)Tm?MJ_|t3;K1a&Q+0>Gu@k%wuTeEX0|I(8xmADg9`K;nYWP>J8i?esL1@)#w19'
    '8YCL@2X5(SFz-;3uV6B0vr^vi?vHA0zC}}BK`BPJ!?g>1<p|Q2>3^8$e<)!6hl9{xGIF=BvmJbCm}qz;87%%(!&k7*QL^%Iz$?=j'
    'e!C5}9ky(+-&kJkYYp&q><rR=2)yqE8ew0JkE4-Yn)$?2li%}6zynswk-v4t1K^P-iPk5Q<+55qaO3Y3k>O<02O5g8zAxmJVt(7V'
    'E%4#z5ds&$E@#omLCy4GPR=d%3}@gc1D1(=j>vS@mrVXn2>UekwSzn<m|f-BO>=_H`DBptshtd%y)F`&F8Gqk-wDBsy@EU`h%I;k'
    'Y6jm$Xtlwvyn#kox0b6(z5~dWBwsK8a#E@TNX&C5lbCb2mTN?!tDYrdI$kF;UMstfeG<=3)|KTJvB^y$?~SA?vWi_wV$NMzZYTLF'
    'T(^?SHSl7ht}J(mzPFQdQhV;o5|ghAQ4eRuhe*czV7CWJzDveEg3?_NC=I)J$&i?()2Y{DYLp=UASu<QBt|2@%j~vflJ6ohn)KMG'
    '#b%8*&0{~7m`v3I_KoRjlJCCrh@kXP5+xd?F%Nl6JmgVQxtd)pkUlCg=k7b~JLWTjz|*8uH<g&Eo62*-Mm$UU>ZTG4yqijFJglAr'
    '>E>hWeiPEh=Dp5=_G3$m-w@_}Q@oQ`Glj>ezk=@rX>>35zktX&h3<qkLjC|6ISW02(`e)}!~-7@(pMoKc#FSIfPG&k`ED>{WFNms'
    'dh7-h3%nal%()xPYvNlklfEj;#YEj;-X!@>0<V)wokL>2yQais>U6Oh4&zC_>&rVL|J!Mo-?{6{1d(uDQ9@DImk(s-iKJKLJ$6co'
    'HA_by&td0=(e7s5U_O%!qEAV_63fS==gLbl-`!wh&fQ?X5G#C6s?9Iz2BW2T9KQI#A<%9xF`0T+EW10N;=8*<Q#@ke74qFnVrA&='
    '5_9hEQk~+vyTnsIySv0h-CdFdpK3*X0`2Y+D=41gAH!RFA<|+T_Wm3+!n(oKrTD#{BR-!_d6(RGH<*}nH<<bqpNCVI3ZxrMOw<jg'
    'fvi}c3ZxrMtPI^?VlrR$*-iGw6rUG2muNaC6-d{YSlPP12)%{zK}{+C4APjAVnd=LK4<}%u}N~q7O#9zG$Z}SzX!X1S&Hx8yEw)3'
    'M2m<X3q2zvt4E(BPqdUswAeGUtVeA#nQ>`Kis6Yi2f?F6WxfYz;HkVa#eb1oPGnyuDZ8j+?+P;Ga>*Gx13|;N4@ZdQ=BId$V`WNx'
    'rA|Sw-Zcb))hQ`XCMv-y$ud;Y9#5GmpEHnYg*5m8@BB?@<T3324m5HdP;Esc42gV-KdHB*JhEg_&s~e71;<ld8}WtKlrmFgBOTif'
    '?PT^g53~2E=#DwAsLXqsRpRSR@p(n-Qao4Dk@CfZMFZ!-qN4ZmLh#7-#Q!=|9+{%3h%MYeP+Fhz#US}a$tHS<%J=RI!Iy;Y6klU='
    'ON!@bHj}f=rj!y#5%tZ_L|Ytp_EsX{7T*#w-Mh%lTc=(3KIyLpJ5&5E_3cFd?vz*LttZ?aWajNDCC<bqCi1~%2x24am!@4r=ADW%'
    '4-3%PO=jMuICE#9XbdZ!_g}{$XA)__o(~68e5c=i<h;L^ocDWD-X-t!ykBT+Wu2!H<lj$NpnWNyypzpao3UgE$XfgTGEO$}hblfY'
    'Um?G+&Spq{#%J~tTOah!?L-6RxP*3R+3W*khxVtGcqE&*HDfsj3Cl4M41*L6hUJinrW_amcn%yzI@ZCv<}eyDx}y<qA4>UTpHvV~'
    'V~~XLWHZYxCN@2s3WQ&>(dats;)Pc1)Jz$SSa7AaVsE5BulKk7!OV=0<h%8J*RLoq{u>&1v}=Cmllj7TjAa8OO;~h(jOcbWVBHvo'
    '$H_X!Dhk6s#~6imlRQOqIFSm*ZdNAqG+Jl7X0ALm^=x;zf0`J`>jN!+D6K#F?{0mdt9aADTkr4s)y&}khQ@eZn)E6uWA=!#TB5C6'
    'Z?jva%SZRLw~L_$Bg%8=m<>5Z2%q$~koShqe{kpWQi|{7d@jXz=Q~SqK2rvqhyCCzy^1K0Yd?7Id7|mLRPeT@n!ab9o5<?t%dk3)'
    'PJ0l}TkWgR8n~LP8MBVeDy=q{*9Ry6Otp9G?Ong-60O~OYjIU02lpG9-1i&ce^>DLIk3uQG_p@Ky;e!$oNh=wg->2@1CN36+$=-l'
    '`g~F1IxKMjIHe4HN`9Ie?A8bEa1!x<$63BHLE=iP{I;VpF0;!uBF$AFb}{TRwUY&QDFk2_^;P9>7@dOW>K%m5BG$zTjj#yq7xD$_'
    '2EuQz^R3y)p}c;mDEVk!ADxoieDcle$m<<Ns}}NlVe-#ehr0Dc;ECXQz0u+=Br`|;8yeFMYSOYK3|S(EEZo!AyDV0TSf<V`g4)dh'
    'Q8Oe=84@d_#w>fA$au?xjD`$C84VrEY1zo(ynfgLFTEs-A@i(`ZoNa^vUXP91aE=+DL#An9>MfZO5H;ZOo@jY`gz_h>ut_-E3Fk}'
    'm7;aKJdXz{z9Y*0R1mAS2zvO8lJy>>g4MFT=(%}XBh*fPjkH_=&+cb94g+s|oZ@@?JS5l@0>P%QOxTFNKCo_&PmngdHB)15)pgFd'
    'fqk5)Sp55xNby8n3J)hPvpS?!KAmOiEV1s@FAxe0m*)hRXJxcbXArn}I15?VJk9dyiRLfL=n+(NmRtKO#doKDX(Po}`?{t9o}A3H'
    's^)cdKc^tMZolslRv*Ei-(ubs@O(q?eC;1k4<{`Dc=|a@ae0-1%sYb2+mwG>dp}t%2B{{9RPUxyD(e47Z0xny`Q~uhPD>7VMc~x;'
    '31P=N$bLX0M>TWLsOeL-6PLAb<VPawhg9&``#p2{@rR(#SazOpj@>XJSbp+=Wx38{)<{fC^Rj;S;iKg`bLG)Fw%NX}Y9!yJ=NrHG'
    'a!TMjb=5+?DZ*tx^!#l=BT4wqm_{Ry!1B>FpKlOGBWpF2y;s(yrA(NVW=pfXGep{G+TSYH%#&&|f85jjeF32%^PO-G#5Or3`5o5L'
    '290dgOn)$BSmX8;qe&lV{C;wWH0k|~-#eX{IyLE8Q*5@8NNbbcTAZ~_@Xg8EXQGa1k_$i+`t5_^R!>%|3t+X*vfwr>9TTquK4AgU'
    'Z58;<{4}{|LiBG)`<ImJzX|Ez=3L2?pb8b75^YU-TjTe3-*ilj*<Bi>(N@jWT5j!G#@dO&CVg;nZB{cY#rA3<ZWk3kVmD97s*Uoi'
    'rr2sz8bkH01Vh#S><}cLGFeR@z<-utEm`*(qW1!Iy$uPC+EoZ`s`nVXjY3vk7~rZ-Rnb@$jT7U`qLh(Hdz0Q?LVGgSXwnPCHAkED'
    '(c+qN5ge<HwlvMxC0mkKm&aI{lgE(KA=+VgV48^xOBG}=R^u=+By+&T3;y<Nu{BC)$epNca~>f2YDZ}7gy?Gx8d=Wn5v9pJB7)&E'
    '4;UI67<w@+gT~N6i(AXxXYB45tV;7)IV;mNrf;^dTPhXJu?(iwWSv#M)@gCbVDcxoLzPJIoIKKm>DEGYTN5yb{&W-FCd{)=AVm6n'
    'z?Na};I-tf&}OsF8aKXLIu_ofDbFq)6N`Oh8^m@Sk*@9FHS6&CkKIHfc(ezI$8ZpMNJP+feSbTNX6w?y*<x5w7kL9&wKKp~J00@S'
    're<$*t_Z3eJKNq20)N_)=6hppO7nSQ8`H`XdWf)DHsEHm`X=?&Jw)2&utLEx>e~lsZzcL}@vg5zggwFTI+4}4mSOcChx+|ft88%L'
    '`+|tLRbs%p7C3RBieJm1n%5nKSq|<9kD!sya7Xw68rcGoV-Fg+3_EWJ8ezQ^wx{{t3ft1&aq@Z+@M0UUk-uGclAQ#F9qFJXaz7tf'
    'yIt%evh4IBi`SUmi$(m!_IB1`HEH*z`8=sTY5tCXPg<&qM96bpi;#0o+I>W#y`CjvI_@Vk?kl^FebTXFKYR-uO!GBJ`iQN1i5>^i'
    's)#GrZVfrts_jqnRRQ|a%JnBgqFS{BMBo0joYbCc)rMrMhOwHohtqsb+986*pa(PpsYx4hu1R}@AbU71Rf8fVs!2PX<|`B&NqemL'
    '5el#-ZAi5;*hh!}E?^EG_U9=ya+BTqLL;n3#!-Umh$O0kRGAGG9BqDrc;~US`WiigYP%<i?kCbxl|4efszlh`D-FrK561zMGikmi'
    '>*+LK1>;oOS7i?y{p`J2;=X7|6no8OeISVJXVShZc-Y9!I-;H@E1gaIs_bF2l42c+kbKpzG{p4R(tK@@OKH9~$i*~&tNKD(O{$i_'
    '^|ICmxlAOyl=eEmwKm8VGV^7{nfrX}F7vgWeKq|h&DRFGPUOFqR;pPMY8K=q+(`3P0<Nb$SA+=puKpStmZ&a%lc4d7A{wF^u(t>r'
    'H+`THXbsp<r>A_L5by%;kzQe_AMzCY7(7Ep(|rAqduhIw>|KKVowQO#i%=PA$%dS3$=*-%wGQs3eOC4eiE7C{Ao$!@#3#@?8zGr5'
    '?W{KJBa*xIknDxgw0B8-*M<!_*M@zZ=Bq$FN(WNeBP6N~`-H6cI2}mEk5CzE!-nLmh_K4xuaI`EX6y@+%kzvN@H8Dr#g9<gYQ~0~'
    'YsQX|$p3{;zUC#Faja}ShfMTnvhFMoKh4)bcunMe<r9H7WX9KNRo=-jD`&^|j1#%urB!((YhB3+aw;7Ugh7(!dsHily#Rh7iM}fw'
    'fxWNQ@Kr=V5`N$VLGOK9m6h_t35o7gv0Ad9i6uU!{qRoKTC!h=?w>s~PM&MYhGf31GV6tF_!_XG8lK?-oBL#?6l=hSoNK^FYj_)m'
    'Yy9v?*1cLyW{=hc!5~T2fK_-OFNf&70m;j1!)9vu+OX*wp2<ko1jRlDR2w$roV%4HewnH9&o5bP!`2a$ay3CSOFnDEO0j<REW^5n'
    'uOBd{hChQe)C9w#%q26=shMd8$?nO~NaUO!5CTnP=Ej;z;*s2Z=FT6%w<x5=HRuAi0gb$es9-f3c?eNKa}9qYSX{%O85a?J7S{OX'
    'sr+yzU5;N7mJn$d*LY>CtUSO{GV_uezYLWh9As|gGtOrPvFY*}o(E{I34+D)SQ9nmTr+lM4bS$hs0of=vet}UMb=tb6Fjq|icdj0'
    'vIs+Du@-5;YRTqn_*$}Sh!3o;34)ahg5z?oCEH4NV!p;J?_{kd+g8J~AFVazVw?i1B`XzIyawDlYWSM5?Zn&H)&$2&1za;$7-zDI'
    'Zk@z-9W_DoOI8+SeGPwR?5q)<6v8H#VVgVeaK^CwvPF>(I16w7T}aZc@aFHT;roGas^Rl_HWK|dlwH4!BbT?CNVG{(qCSBQw~`q*'
    '*Qi=TR>vyim(4QubigLtYIu&Oo1AgG_%m);$b!V7E=AO?evqu}!;a_s?F7wjHFEQI3i38~5Pi3M&{ra7Nn#fHKH-btExfOW&&lZ_'
    'tj%tM*e(lV;i4o-1F?|Fw1oP;>1lA~ox(!4qx$a@>k}kFv$*&+EMwmGkQ01Qjq6I)zsnTgzrCUU;!0t-lQAiEq0XMW*-LQPBZ)(y'
    'LC&`JIFxKF^Hr?_PUpQf{FnR##7Fnls7oNqTslaQIpDIVYK%Q4!C}OO97ed9z1ti85$ag{snktV#`p9QE~d9ede!Kkg0~d&iF@PX'
    'oMn~^)ldAg&(<$3D<!Rd`6q^7jyHI~DpQ*4Phc*Po!!ML&e-VX+x|G5-LE0d=D@f8lW61|yupWYGzZ8ZLL)2>YKYikK*1K^0b!8`'
    'D4b=&CfDKchG%b(!z8vpRHHV3i-6}jLS{Z(<5lvYbhpFdHp||u;d8x4i2TEf^7r|czr~SzIZh-zCMh9}jI7+t3366FE;_4*g?xoW'
    '^dpOdC<+o=b0b6o=aKv`0ISo4lQ~7uJE@4C0>31I(y(I&&RJrS(>^THDPUvH5lqg~s35~(5;B>SVwBV<op%uy@)9o5lDHD^CHx!*'
    '+%Aw4_xT!Wd8A`1=1~_3dKVPYD>SNkl$RLG%Jp3#es!tF`-(k+oWQFDnJbceO&nVZS&q1nZBU4@9KHv`34avxdk`Po#&Ifm;|;?9'
    'Tqm5#wHjqDBx5$`eWw<qS!Z6rD$)~OZpiB*8Od3*%x{qufAN5xT$JUNKM~)xyG!_<JLIHsyKG#D9N%+~NOadT1I2W_PiDO5nL!GU'
    'vopWfz|MVwV|}pIL&5_Uh#sRgs_c^=E~Lxx-rXZ2-NPDHe#y!YJSH<f^2{uG(O2ecTNA5+jU;9K$uq(aJgM=+K3OxDo)cuARRDuz'
    '$0LoA^ZJXxd8C&Fjj@X1kyPI5dyW9tnML>de+Thz26cCXiUF+|{>y(o8aWBk!54%|0iH1vXyh4K=Ph~0ydi%3DiB`F?YT)~EIXd*'
    '9pN_K)&#|FS$U>$veLW287=#r=Orq#L+mlj_$1k7?}=s;H9@gn9ymvrSjdhq`a~l6kG@$Q#<zSXGk@~UL<Pwgapz^&)zxU{Gaf0F'
    ';dvx2!|U~B+Ig@(M;<9kBm^ydA<s_4aWZo><CmfG!?AQpL=`MAD^2W}B)U{*ys}tcc`(r}es-rXli|<u=}ZuOl+~tnWR*-NNG8gP'
    'i3;N+w{uxdpCw3(M&JyaGJN&@IcVe-%L2{tY*KwDICjeeW9AyI+4;#_;>mL|et9a!^UNo{F*g$ge-#89Cc`3T;6$-7!{=@-Ac!?('
    'DwV&o-sxME;W?9qnQ}2sjN@8N_Q;}4a7>g3^n89bEUkDG-uNq#c9#I*Wf}e}U^BsdNv6_xDl6}^Jj0*jmSwy$QH=LlL1tW@neJRB'
    '@twUj8UD`RDkAU7jK55$)nvw1nR2mvaYqEKTu}>=YfZ*0lf}-h`3!$<ZOP1Jj+ESfUJtkW_afQZUA`?D{w`l<hQG_VHp8FY+X$+y'
    'nVICvtV~b`vC!H~aE#bGqI*ZCQW!D2yL=lmd{)@{49}ExW`bkNmTRhvnBB>HBeCIzj32(tx`#KD**9ipl6!Ky%eN!L-{tGd@NCQ0'
    '49~V~$pp<<sjw~1QIs9$)=m7fD-&GC6+>woL8&`a>711KF5m79f0u73iQRW(f?=$7k(qa9Duc1IJ~?`boVx=;U=NwOCo|JIQf_{-'
    '0rL9}W%#>!y@bo#PdK1`MBlxV`o?{8d7^A~E0=eGoWS>Ig3R1vI2<H69GGz~OdRbGkn?;WL8&)TrpymV+39#UZ;&8Aknx+L#kj2@'
    'a&8~|D!46&t_u(;9Lw-ExsGJ`T)@Kw)kB#|%G|R0zzFf)BbnfHwvG}^MlxSR&X(B&0OEm@NDIb@9VhI}u`)AaC&<n^{?##J*1LbF'
    '35F-j#&9t<<qSDvp3YRt-9I~=c0rYZFv=&`2Dt(cksix|Z}=s{-xa)^;qMBb&+xfp=LjBWGc$Wv@B)$OyiW%05}ENrrgH8IUL_pR'
    '6>^5YoT;3<g4YO|S2O<Z3SKArUdvSeUBT<H$L?nMyMng}D|C|}_DiPH?h4)}48g5T&^car2oAS1m3CK<<y1W&d-6W<(Yu+-$*CG8'
    '+{=SZd2*@>WTnx}*O60Yhh7fO@NaM?9_;GpXoTfpJt3^%BZ9=k%-5BJ^^`>BPXgj|o{^cKW-2KM%X(*TjPNrri2Tnpm6dDtibyyX'
    'P_ET$GV`m7&9&k(72uryA;Z_kdPnU0mgxAV!g8?2$=Uo}8FH}RlU2qmHV4c6-U{dO&p7XjWyzA$@rN?-PV9c;C$iSZOz^h>RnaRn'
    'y4UOfLM;9{(9A04SD`Gw%9lWyCE2|u|5eZqu{UtiUXFBm04MD^Xyg&Z3mG)B2>dgi<tubYvpm-Ur}{uyEFb)s(pN>sfK_MtT@cR('
    '&qp!zk_5f#Y`Ja;dO^?Y*G9(6)Ma^ICYR;UN}23*^Hf$|rk+Stm-Tn2uYt^1Uv?ek`{zA{oxL#2_s?r2wwh1$n3J7ue#x4f)s*E='
    'tBu(p7$m0e0-|qI*6S@nS$$=`(y@DdOSAl!`$Yteh1nqZCB_UaA+s;a29Xmbo9)xn;PlpKr-kM$&+aVE`sb0X*;~uV8qL|6&wX<9'
    '84VbK4)R8C$?^=qsx04^aRssb@@x>9R9?8P9>>$fYO-TjWxdv-V(iD7EYE(d&Q^L(lx^PyR+%)*_v_0OZ*Iv}ZjGwayh)Z-N^H}b'
    '4Z3<1J4d%?`E&Hz>~!-a^0)L^f4)swzCT}Qmgfi75xqLHGhK7a%H6Fe5_V?&W=t{NH<FpxXQzw1Q~7$v`txng@>Tsdle6chZ19;&'
    'TL?;<vz3v#WPS2?5j3`DgXfX9kyW~~U&CEKhx)tgAd<_W?BIp))dy*M2Ka%aI4%Hw;9!=&6SybK-wE8A<?jUUAgAf=*{|<T;4ZQ+'
    'c4mXQ6S$lB*sko?cPDUPmd_#FOAy<W{W|Uh?kAkgzHE6jpbn5dvOoKu!kxhFaON1w@^=FJv;3XFK7#qd><ruqbnJ0w<&6f&*`q(}'
    'wd)?^9|p;c16i+q@q+B*$M~TmgdaLY<Q>XRch@~DKQv4vI+FF*Z*PR0g@?11-*4|?mcOHSI?LbDJD%lpL5>mhj%F*T-`+`LiR0Pe'
    '`t6+}x}VHea=*Q^Sw0)<3_01K&Q@B#y>rBdXS2ce+q*z!KbNiKetXxm{2jf^Sw0)*65%{9X1}g}dsm2GUd{&HZ|^EW=}PwN?YDQ6'
    'F#R`3EPXv2Ot-mT$jmpgmDq3Z7LoI2KnUC>GvCTqcE3II9a|6CAV~fT!1_PS@^|+NSw45@ewM%EbC2L~H(R-V^&Svu?`MPQt2at!'
    'evth-`szI<Hho06g+jJ+`|3R*r{Krga`n}FO4fRk{hIpf-GB(<b(Zg|H%54v=fnq|WxtNTdN0XN9LomNSML>J8(wDrQ|POA3gU<H'
    'EPto(4e|EZ+2H%?F>K!wY~N&q?ziU$Tlv_mv`QW@oFEvEqZo6wdH(zctvV9vZ_@i4zfVUQpOy>tpU(E5{=Pe`wG^4O<|MCCf#t8F'
    'wYF;J>O)g!o2j)*Ym9{1+@-ZIMYP66b=s8Xk^KE%1$oRHP;8r*(qv>x6RkJ&x3B+4&8m;wQ*3_<sxYFj5j!K0XNgAkflq(JF%8R1'
    'C4TlH8?+WBIX5GG){4+?*7}>9E$GjmLO&hJhbCiC#~i0YmdQ$N|Ea9DuZC4MjJRgXF*GH|6uUB#7--T5CRa@koX!rM{(dCEq?lZ_'
    'D?B;tNSuwAr1=u*Z@+_)xUEmlXD`h@g!DG+swG`Zs~b9xMA>SW5=`ewDVpPxv*FcWIwIjvrx<)Mim+k#d&2}R@K{^4Oy5fxawkeQ'
    'Yiripnwv{#l|1H4d|=WK5nB1M5Un1~!>XsVZIh_sRqNzd<-T445^;h=)Ex<GN!UAnkYEvHl1LL5O2hA+k~AemcrQK@>4)`Y_S9iy'
    'mjmXi#aL)$)?kx9IJs)cF7fu$+4jlRs|QbK2PgkbnR}_T=*1&RHa_XyEnufe|IRzUe4FFVS>`vwtpiSsxf~xuWYEZnW<IwCS{m3!'
    'I4w(9rx*%Ftb@?f%sNK6AGDXK<Z}_j4)K9zZD7*(N|IGGNzHwc{BhC;L9R)Uob-X>tHP9QQWhkcWBw}3hejA4)l8h7B{r~{!g8=#'
    '8!U&!)~}%TMAkY7S-Gc7+0m8RX`C!c&Ii$c2OmtE?~yLU2M^o{<SjA?XSGIz=W=+j%ta#?G;<#gP3^HMet9Iq;@gqbXp=r#M7q$V'
    '7m8XL&kY{wS%;eRLrA+4@+nih&G$^?i~H@R67IXeN9Gd^=1OS5By-n*X<9A~&T3*w4arQb4auh&Yuhge;5khM_r{#NHii}nL#r9}'
    'oCQRKrkuPz3=a}&z%-o+&oLyF_VMyas?H@3E`kgMWR<JHE^kC5Ta%C>jYihOX>A!A*$n=<1dTjpRj<*=7R}5-<Ie8pDf$P0r|2#l'
    'UZBk~x1W=fb**mj=cP!$Zq3AilOZpqpX{l0jNL{cD=#hk%H1~jt`*_y`CM#=b^-irWsd(swgQc8*G#W0n-7=_h7A&1Eqr=8PRm>c'
    '3wDnKAuynsC~>lFv&vSsGc|Wl1IgB_nbJDqR?c&?yVc5feir-o$0*!AKv=DWvsfz{VR*I>JlDwMS%%ZM#4aeqY1=A86rK!i2$>U_'
    'i5@4Lc~bacCeGw$&N92zLL_dJka%X!*T-z^e9&I9X+CG$dBhpmJ?jv@ovhk>j=vYvo|D#V+E3#$m{0fV+wM%Vp7`-P1wWpiGkQtl'
    'gRIUylK6^d>cB~CM)*He;yL`HCNJ^Kp1bAVfh()wP6V>dAe=F}(MTWc>&<9{*>e-I=SB&8R>oOh#h#UMp0~?D*+ML^*@FdU_H<v*'
    '?w1iwwn%7F8K-|f4|$Q+T|7dVITPLUG!|Jw4r}*!n%4I_#$kNJ@+RUkxdyKRr|k%*%k0ivj?ee(&Y5z|vdE#^$T81e4jY~3S?2oA'
    'GMDbIQ)$LIpvMj(_4b_ql}c+cWOkA@c8HLfXS2q4(#Uv5+0Euhfyv&F^hm<He@~9TXWo<JbFp{l_}m?_A65yqT#vZ77BdSMpKrP&'
    '#d)UkJ&KtgY;J~&lP|0UU)YOe-=vxP;Z?;q4QAybv!u1SD(J_oXRpm|cDszMw^wz&d98+)&g+pJ=2^mdA%o7CaURU5%RLu%f=Bcr'
    'o!AaLnB#M__vfUgfs8Q&&)-mKN^3JFxfiX}qM2*kX7FRLiwV8X9yhoA!|vaLr1M0$m1bYY?!*y%`f_#|=k}S1Q@LX9{x(4Tt>4z)'
    'VlMvH`(2yMdIY!c#PhB<bG__lREZ&rw*kgd*O8WAATRn9er~~&Yy^#rffWwt_<J>n$WwbTCx5>O{J_CuCGVERo$pv2A-;1s=j)b8'
    'TvR7_n5=Xp=j--JT%t~{?EMg_=M#Hl9nbMMZH^MnMsmLHki-MOLn8D7_5?YRBYhO6;)~x}VuC*|y?Jr&Z1>-UXW?(mn+d<M(}CUU'
    'KS|a);TkVl*7_~C);znl)@gEc9&XYPPtG|Ni~XP;+dP6N!Ud!kyNz=u$5%8sO>{q%3r<cO-376s&79vk>28g3&Jiunl)-}Re*5_x'
    'pM!qRAsV!-GWCA`K^zrswmCJM(cuq%qeD9kPqX`agj>9bM!Gc9qwHi8-?&hUAz3!;C9>{Cuj@+2lEU2US;F}hVoK|i?P`wC^}U=^'
    'UR^SVyums(;IG`8DTCwP1MI8fSkf6czcHm4$>R_M74Ua>c;ek5PrP4pe6IBkg8%iLQ|7&&7*)8JBjTB5Vp6-f=_b+Zmz>jG1uv1S'
    '_1@8K^3=VVQ@`Wn7F9~zJHq#5q@H-J{_njUU;p<m!SGHlkh?VTvfZVLJJ)}?Pi%BA=kvBqTy$IJ0YUG6E|A+Y@v_~PQHZJL!xQEy'
    '((x`J{3yrQoP0?5qC!rFy|gfIsUBe+3TIZ#!iS|qx6)Yd|6?NQBR6J?a)dULo@TcY$?T5<nSHfs`(gw%i9_6&D`m{pQhYjeC*YY9'
    'p%{oO)s5x&N_EeP4o`D_tYGb`^n$QE&xLPhrk$l$NlKz#$2=hq#p1<Mq$ohin)~vS@CRc&e?Zth(<-p4omH%i*DJEdOV>4~?)MH9'
    'b#hpvg}hBT4tyTR-0IH$qt57@tNunCn>VKcv>aP9InppVspY&spEWgd>37AE3$;@tYrlj1iduBL40_r(pphGJ|3O0|tpC+}glK_v'
    '+aS!)TY~y)TV}{D8nxo3SaBugTp@Ry$oMYju{w>=`zFYKAJ5rU=CNDD$?wR%6tj{-9~S%6eZc1v$wU4?5PP4KmLnp&mlP_}q?|jP'
    'ea`Wfi$3L~I7Oj7zYqjI+xkq6C!euLphoz#6+dTfYqP=bP1f=~ZNs(vcgj#LuO&PM<g}dE4qA2ywY0ARRpVYoKxpj-cHgd+-)rGo'
    'X*_K_%36!Ex|Zi@;<YNA5Q~SuA@2abR)FMem|K$C)2!-srk1aPkS2O1Yu)%KAy?<9m!H|Vs?MNGu9mBT5Xmsfo75vY>q)epV3Mm1'
    '!aC-ydDk;2TgAfdNyiPPRYri-SX#?hrd@zWs@ZL;TAs(9Q_G+88fpdSym>-aNf;5jR;DF9oO{$~S0!UU(PD0`?27U+AY;WEiO<Zh'
    '6~~6Wtt~vRu7s5otLGMXnt9fM+ajb3+Yt--y~eyqzJ80cMru))o%I(Ji!7>js_>&4gRz~mg!tHEM<0uM@-gR~q84wt`M?HvO025o'
    '>sK$Y<!dM{BM2|8^<42L)#I0|bMc22#8S&^ojlN649A`ZD+w|y9FdWY@#OZ7T3jafgjRSv<dH7(*_{=F<SKO}g|QvZ_Z&;L5F}Tt'
    'BkAB{Et)cymUQMe7}L{AqS1V<GSib3F+FW$_SRZuE-Wd<XDG~~5}n)vzTp7UBM$LO7iJ*f#Iga6JOFIhp%KOnwv$+Jty(OY41^y|'
    'I!COXwLCw!u2zAcvyqXV*VdEsT4$|C-YzN2HAqBfNttI1V~{r0@?674qSJ<2kGx$n5Z+E`Tejb~5P3J%dStwkqJCRjYk59nORW?W'
    'mJF~Gb5cH%Xog5)7m}JWOWTOGyUFvct5%sOO9sf3C7qe2?Zn#KYCSSxHd3>i%{vJu+iR5>vZUvl%~HE}Ez5DP<!@o`Civ{C^~jSY'
    'MO<7D!Dn}^GJlrz#ZOsdDwnu`-JaM>kl9n~kq=9XVy68BnZ4>vSkgB~g&D7;DtmDPqJd$gNeG@MgM`2AC7jkl5;Gp~&fg>h<+PH{'
    '-z55o<h`{)tYxj^+fSmUKHt%j5B^f>NyBQm9wN3Ls^znh25UXAYe|JOmMr6ybUu$BCa0)FwLbZ<r06_)gsgSgFB2xWFJu`ng{a~H'
    'JO@r9jTmcnjIdTmiPpolK3TM+Czb*;VJ=>AoXC8v)+bLU^okSYX>;5=LzWDLwQ`BV>~Px#G053k{#MN?g5=3spDdd2iF$@0dCEHz'
    'mh{bpxkMt&)6Nlm&iduUgr0Vu;B(G9AC@cwAC~lzm0>>j<`?rTs_UlmD>g%)z^C}z3uIH=Mk9NH-MEHEegV5&#taC{S0<La;FoW6'
    'czS!_)r8M9)(`9oIk#S}_18!KDw*+0ZMpidi@LLl`+?o4<@<qMC-Ppao$kK()_!0&i9|O%BgoFHx5$h)YgIejJNLtu?c3^RCD!+A'
    '6v=xI>~@#f?GDlDcI|Zcy|;FIxkt`+cWZ;|Z2y4Fey?`sJKNi3Cp{!tD+O}09<2?o<2_*oJao3Vv*#n?VGnCn``%l>4Ll|`d{kR0'
    'J?h<TI~Pv<<CyV>z4{W3u<8oWYxz9sX9UTowO%{kEA*jP>Y~c-R=lX??^8an4XW?G^-k&-*%L2nE4Qb;9bzmi{!K0474<d2@MUe#'
    '9q)tf-~N{5P`s)2+hv{A=z2$Hep@@!z3UzBt-<;IGm`l>*!V*&UwdqV=rvyJx8uF4UM-GaeLfNiKh%2ddv85aej+EPkF`Pev{&ss'
    'FVkylJ)FeDb^O<WF9fB}wO;$)TeC8?Iv%AjwL$i}ckU1_8wH8`dPVDaWB@%+eebP#N%1=V%owfv8hXpiJwpoV;)#1My5j)dedmSH'
    '2-LBdSC3BR?0Z4Fj?ZIC5-U{K`R!our?-5;u@_v9_<Xu9h(7k#omEFL$<<YAk9ynZbMaX;Zw|6PyKmo6$KNWfuPavvd*|Ju7IRr='
    'Uhob0KW3a*-fmscee5k?7UyZk{+dE>E?V(Hll~y^Ui6dN9m$w8^d(EV4S!~I2#v@`9@mOz2|dkpxLri;ND)UpibmkvuZN8h^DLpm'
    'lVzwl;w+7jU%IWThlNAa<48s(QFNB-ycP~kuO>RiC3WoctYeGB&V`(Gy$<OMjFp}t2&7#QF!H7%f)4h24k6GswZ;$|F~58KnPczI'
    'NS87iCAo&(yZh?(MC&?9tvl^=2lWP`b-f3zheiAVNGdx^ry@V_uviCNUxqM&JBj*2G;$O6bR!yp>?wUd@%Ond{%(A+iwM~unBC;v'
    '|IGfY&I9~~B;uG?q&Fd{;k?fDz$@v(m1aG_41Yw>3tnG9aA=amq2O+F2ONxV1(AZpGvFDZu>_&PWM52tcOmb)5)$;N>{yu3_^uXl'
    '<aP9=NM7J1m<B^ryBBf?{!F^gLqx#q=*<WRw$f6BgUd>Gbsr+*?mn)IWq*JxIz;5FAbf^r{og~lLA_$V2aP}tGJQGGcp0zpcW&5P'
    'sz5}9te=dv?5aNqz2gkX`*%&99N&@Q;`<tR6B*O@$o;Z<>X*(dv^c(Zplgf14_Sc8zgJR<79#)OSJvEJPchE_z%$PK1ID?}$2aAU'
    'wxUD_>Zh!*wW&Dr0@)>0>^h|X6Ew1}SP@+R3p8>7c33YOX#)HHcW8uZe?U_EK4mYn+UKBWKl+C*zl=-zQC#3hTn!JvsgL0Fk6ffM'
    ';;(SCixkHHt8TW>nb7|+T3Irl3U?vQcEc?F>a$dL$w?lT;RLUN{|(_N7I6KM;5s0OYxS_Cbe#fR2PN0(L|7hxU;d>BiwvV#Wbt=C'
    '7i<Om4wEzMPv{LPD;?I+L;PMX`c@4blK!&`(neev?m<%Qg<l?#`(-u$rBWOomd`gl24{|cf$)9-K7AC8YyzA7Q#3LNdJLlxCHbgk'
    'vT=X7V9)63BfKoKGgcSKllY%WTDIV_S4(y*IC}g}K=&AatAP}M&F@F|*gst0_oMr7stfj&CG~&qVSQ{@<|8N2ENxTss-3E;`7@2<'
    'IVLQ_pdN>l^=TwsKiJ`45<8p}djnpzdK~HQ;WQMc5&Iih{}jiOD9&q<3;H+f|4M#FyVF!yK~uZmS36h!gnVcH-yj*EgVg`pc85!x'
    '*evq0x5*i=b5Sd+oy)@GPG8aWv%F>0X17Sk_^^M=@ga(*J_~j}PmtB#s=BYK2ksJ`6<&W^9QlB-x?B7jroTZW3*asG5{=vgJjM_n'
    'Py?TxIgFFGS#K2L^pPL?C#w3#|6S%A)I+ad@9+Dy)Hky?lpp_#szj(y%OnLID`0K!^R^@%Dpu;R@LO6lHTJzK)rO(>nxOZpqS5P1'
    'y1xkqz*EL?1O%GBBf7o`MAsIg>rSNWCi~db_?|WLb7`HC9|tC?2H<arwtl^>@7L0by`k30m3qUa^_m;)J!lX-XaecoqnSuJOJjV`'
    '8~MqU!PI{wG0?9Mh^6Twc~&1`)%OT(CdULqJ9t!v8>iO_osF^)c{m1N<k0i(C3xs(WGRN(M}pZ0cg%d)Zn(h%W<J*I6nq~Z1<(D0'
    '@EFoegodVkc`6Dwccr<uY0Ft`?I}z4hT13BANi?mqN)v~G^8s@%jD~gwi;5>9F;{NpH@F*9VXuwWF3KgKMzh+4O-<J?AHe;SO1xp'
    '&qOg|c%HO;{hA+~O1PBdFzxDsQ$Zph5^llj)yVgmt;6-atzmymyR8cXTStkl!}YGVHjy*sEA0o<3wlEXO13U|v2_{b=xKDkD-O@I'
    'B(mvg&9wW_l$EE>SL6x&Q~N|!JA0Zun5cSS|1=pepC%(ek4{vL!vFfIFi};2zom?wRnj5aR{a0*k`6RWgz+G0WNRjO64}~KZc~mQ'
    'J0_|++~qd)^da{N%?qyPdXl)Bc951&p);u7g}mi0JS8^N^PE*(J<nO?h^;aTwo=8ywCI$T%W5kVab;VXnkm}K%2{=i9b8xMMS4@N'
    'vhM`Q^U~KNuV~jyO$@JCW{K=ea_4@`PgLc{|5kGq>b<Ga?4wp>Kb4tea);gl>YEViOrMQJpA9pvkLW8V<o4;Ckq%7aP4(W^q1jsO'
    'i~3fA$!3q3w1_f2LDszEw*=$eIys{ejZFS+@-4}-0<~somVPOG`P_w2TMAFSZD<7gO6c84Z^&U}PfkN`7ioVk$vE<3>qJ#6lh()p'
    ')w;@t!?3_tTESPgBORGW+v<Z^x6{5ihrWYgxIG{Yhy7saICH1O^J5HrW)H%XWkc*nBil67(}t!pwP@7njBqh`ILD&u$$uB+qghFe'
    'W$8g!v$c04tX<arYjf?NAW|)^UEN+>`{&Y5PQ>lj-l|FK_j74xtX~`GSF%D;zk)>8$zFo<p1^S~2yos<aNaAA^ArZA6us4h1m{99'
    'I6JQ4r;<V8KP&3Jb~cI|Yk&bpc3Duoqp9CRBgY`x96%$NS=I>}(ZIe35ytFG?*WAI7W;U}v@b-DU|)!IO#6=f4Dk*i1CbISQ`-0R'
    'tI=+Rx!al$gTb2S%w$bd8k;q_n%pd>1mVI^=&hHR$Xu78V9F|m0<%azu}GhSMZ~g{B$%>VP!^e5v!rin&5{hx`is5)9w2fXSqJWn'
    '=(h+)0}2?KNc?Cbq2xh|IrcH<djxmt`F!%*^>XvJ2<{Qwt>^QJ@6=1(BZy@J(@|{G9{7s=2x$#9I`q+cK7Zyu(c_+^9-i+*#9Ewc'
    'bm#?QtI>L?-2a&9#>2yUK7YDUublfI^L*nWCX+FC9qjX@p3nV$OziW>#XhA~JA=5Z5F2*P+<#WjXK_5KS6`#kzVfU7oap|nUMgol'
    '7U125m})hLQ}CUp8ATJ1VK=@-STSqAtmkiQj3JHLO^6rBQ{D2HEVYhe1!aFNp;vIsMR-MQ{<2;<b0;Rcr}2jD)mQb(cO7D$?>fX}'
    '-k2KuGF;DR>%Xh#v-RKBOW#kh%h8GX%htEav57g~<(R1FZ{m#Cd%O=}BRfOsJwa)r-q)RmSm1XWV)A!6F2LSiHJiU(xqLSNrd>9h'
    'f11HF!u?Gf^&BxoTO6aJ6|?y_?ef`j^NMa)t|U6HD7%h*vUODT{A~Vq<r;#(s@bZ@TAyDn1c5cPrQX-k<{;kJ(Jn{6foa`Jw9e0#'
    'ie#dK3R-#_(YjSq>p-HE=&+{@vSQ7tG5rccqYqB`U1;PA?C%Y;`J0yOX7iC+$87%1wRX00lo{>x`qqv*R_fO~XY)_?b+bK2L{UMd'
    'etrFHK6>e#?J;_ZdX8SAGB+(Bv#$*Z6P6XZk=Ss<Y~|=98pw^&sAJ7+eGA#cn`cW!I8o7idFyQcy}V_%ujnNjc=QsLe=lDKcJ3@f'
    '=`-NA4UMo{rQO79yKKEyqN}%z#%i%mR1~kV{F2kN`MbB<X8VeKY&5veGNTbnotn9}fznEA)?=hUulKk7!Tf#}$#?7du3ypDGn?95'
    '?FcFL`DDJ69)r030>X?%z30#f)9vhRKeA*57@j8>o~tMf`y6A3^?=nSg4KoD!Pw0jn_fm(ZP(0|4XoBVe-TRz<n@7;Ka|#={CBrL'
    '&{fPI=+^tYel@@J+0-HHLI}F7k}_tG7^@}Py7e}@Rk{=zgyoROejo2`_|AKCHh;tQ8X94^T_w0(DFbf9esGgsMRd<@KX~GGq&w5}'
    '+U($MM>Ty9YyCoSzAlfm^y)Mk>_Iqhwa?o#a5YymW*wPTT5T||4^IA>YVX$DyME0jTD$eu;;N;ZPBQi9Z-D>ZMm7k8Rc;|%_GzZq'
    '8o0<woYM`7r|`+^ZQwC5o||PzTo3iU>g?)y`M@b<;8XI`)L^$hXor)CCp!*E+(FndByP_xzwK!3$?S5M*yWB7yBPME+Q|aD6auh|'
    '`l|A`T<^eh^%1hvA~^4jqLF66?*YQk_;P~q+w1%_EOIEXA1X>dn%76CBsZUYvpVv6N71T<yk406bJn45{SbH}cwTR`9jb<jYpx9<'
    'R9$3A7_vkRS-7X~$gBr>{ec%*tP(v1)Cz<J8=WmJsVi!RgegN}Wz?8u9}>$JJXqGSpio9bhjLmrV&EXcOE1Y{$UN&oxBfuhvUXPP'
    'W%;!YC{h7TGY!1mAI(<x(2_p9hZ_2M-Yw@@9khliyRX$usSUd~+h+ns@=bca@q6beJdbQ9KaX>L8tA2|*CSk+%ykW3*2)MlX&{)?'
    '&nPBdYRTAs4<CRUV1Hu@y@uaGMuUz{GmQ`}BZNO>AXfy9bR>YuM<ZK+XIO|vlCUQl8+e{!KEZa5Cv547sS{zl#x3@4(gzy9pWI7L'
    'dVk~hb|)b&%brzeL)vWAO#S56OtG~_BCSn&YjMpsaxOC8$E;QxLW-@{gpl&8;c!`SlgY1K1|G2lVaW7cMD$!Jucr`IUwR5>6`jR8'
    'Sq(U(+g8ogc4+D=u|tL*!4|R?6Kzd;TjTfE^GIpcN9_9<!jG-G6yfKx>MUc`#9)&?IJqjz4^6TCW?%PtlP0ZGip@Hu6J&-a7^-$>'
    '2Zyf|@Pt`|5e9!+fkqe}%LyLK<neH|LLmq|j8%*bPK37TEVT>#YZdXY6%E0yO)bs7ldVR0?$S&-3_LfuL@}%q@kpe-NpCOVIT^Dw'
    '>4l;!qfPo~Q5JEOvK^u8wic^FJQ>roS-G_g36vtcjo@SX2L6j_3&CWK0w#t;93}=*0b^pn7F(l)nEN?qE%;w6!hva>Z%~)SSksV%'
    '$t9!pO_rfbkZ)B$-q1V3u$K1_#jo+9j3U>07_y~~;}Zm&z>hTW85M)%Ofk^Fe|7F}kjgd)wFIW0m9-vf;J?ZZHmJ^P&8Rp;bR3e@'
    '(Q|%gNakA#^bXTU8u+i^!$jUA4N{o^p+NE<LS2rzrALW<MjE6tA3~zchhs$FqmudtlKBuCmX0IlvM-_yd?v#wV#AXS{8#Yf4a%7e'
    'A<vl%A?Hkn(+zwk!>I<3nG7LOCc~Kq{+saW29KExA<vl%A(>2u7I;rzM3}HF&2tTWmgd<8<s5{NC`<DK@sM*3%6SqY&smxw=SpGh'
    'tL~)+{@eJ)248ilL!!FWmmB!ZiAxQ>>QaXStV<p8R$Xf~+<=;k_>lvw{tOz~2XE>R<cTugz-Pu@B?w(<@Rjo!3OwgCH17CjpCE6J'
    'ai4GY_vFnnG40Wdu$!y?i9}l;iM$^q<@KD~8FK9As(&Fi`P85q;aHz*n$GL^Wk#bHv6Wu2t}bXdvWP6IlddjAC)mRhIt_ch@e*?E'
    '=Bmea{@oPS{X{-i8zy!B-4xenGJ3JYp^1GrK{&A3CZqGQO<E5+w#n&yY?IL|CAQ(Zzz{#F(}Rm)<`6%r*JnP45o2-|-oHB$CKuru'
    '(1k|W&6Gx+fB(+c`S<T!-B)gBDDd3Qkn_!yCbBacb^j5OH3N15L8(cv^eDx)(>Kd>C2xXm@+RmKzX`(T`_ic&yPcO?e(8JzWxLM5'
    '!MEvh^NOOX9Yn|NW!JG!`mOyGcI-Z#zn9xXY_*%{u~Sly7G*tXS5~`dYY%xE_wY~Su<*U=(36$vyO-#@$3<V)p7XByc1pjgdv*SN'
    'y`P}5&jT8w80H{(H|^)&O%k)a#V|&PPlim$d^=nEtBQG;KJrBF<)6r5;rr9I$100e`bn(P$Hyvk4cDHls%R7%z1J4GFduHl%t8HY'
    ';AH(4q1OU$_D5*s4m>A@(FnV-a!BWItPB!Q8L;&fkA3esZ&vGjZ@sZ{m^|wbxjgH|JyqHJ`UrVnALifJapBw5rN^r9eJ!5Rr9Y}e'
    '{TaaLsLp4Mj1cc1w)K8ree9hyQ|e=Hjok}6&%Pbi<&l)@mCD{656PROFzr!|L*E+M$uD&NYt|F;#(zxocvN;hoWEv0B|G+st{M?p'
    'ZS|b!_;lK%8asWjuzCzS|0QIMJY8RScn^1ZmVMZ{5(BZ%OI<bcv37-cP4s=`LEmA?w~3cd@^0tj&>X%?>Ia?h(>h;w;~nwKw-&#Y'
    'iIjv)y@x2suGY!~iMPhx<1Oh}i23__g2RL)4z$9wmk2_>OX_E`S3eQo{oo-I>QUaSG)l4KFTRlX;b-~xp=7MWq6Tda9~FI(kBTIF'
    'yxaS@m)`DTJCDNdZJWdI-j+E$yA>uH!&AUnW5rJJDsiB5^kVm>&ClVV<Sldj@gS{p_??`eQ?56yD4MX-cLHqKF^9jmxRxOB|F?HP'
    'AaY#yqM%FNJ);@Dk*_Q)KhM9cES%s7CvR?Eo=Jjn<_><w7{|;CMfjR*(3>^h5P}iLm|%>UJ5h|TafBFrP1bmg5GI%qjPZJnugM0j'
    'R!?h$FnY!qCuEHoObEdQtzQTs1m|^ERd-j{>8h@t8CjEk-xr)2x2LOq=XXxkIbC(?^qm{bz}-Ox?y8u9<xL(J_FhN1Hz?^n14=qp'
    'SkmOow-}W4-l=NWPUbeHr#`%{JIqhUpM&4XWaH)J3U}s}6Y)9V+f(_wT!*IeqvwM`4h~Fx+SiYIM`!m<<*yJOn%cZ8MBkdq_jdP9'
    'UHvOWz1zAF*VR(ChLfw#Q~A%e-<}$HRj2ZmqYC4%fuo{+_4z<>+%8QGd;O?)wEbXEhYw6`m1{R8-$NA7BYPy1jo&7#MNj3gO?@vo'
    'Cciu2m@K~HGerM8V6@b4barGaKRSD8YO}8U^p4IR4%+^asjYiWr+6)`SEuq<#9t0__{h|ix#IIm(5_ydx;j^UdPi}u1!ss?H#mlQ'
    'Jt*mGQ&<0PR_<DC+-tv`Df>#?YoDLW-{m?J^xD4&%J;_9)xFDgHt4m_Ol{s>u5&?o&rWTHyIe_6eK9zLzZvvU=cl&H^`PFnQEvsu'
    '-o>e5M>3tYqmrx0!I}E4EjdaVG~@gI;1l$_Q~7Hr?*#4g?WwDI-KV#1e-#{)?@n!Ggws0;`*l$EUu~IDO7V>E52y00SbY%mzwck6'
    'G0a+UWPGsY$1uHP`MuNmTzz<j#wz=!^Q|l1_f@_-HK>h!?LWr%S7*9eTKH_d>QN?d7q5vwWoKUbay$~aE%Qop_iJuCfA{O=>HJ9G'
    'b3vYNn!dVszxGe(dz71}H+J{yi$NLpPj8*OUtgZi_X=N{&iDRv(_826*R4VQe0h3fcfY<8l=s%@t$X*Yv$kMzoqRgDPClK#%XNFu'
    '{%)JzYInI7rt^2X=BGFNF4rAF9u}sz=3TCPf@AXTppD)+y>;$#-5d0)_e@`zyIhOY`FlS1PX8_4<?7v2@@&=V>HM=*&jd&H$?5#v'
    'uY*A*4ov@T-Thh(&g3VjH}-7R)4>tGI=ywCt$H>X{rotH_nGOd`)t+oL7hB1y|HJjP6cIretIiETlLa({;tzcf_i%)DAVcbtNU!#'
    'i_`hf%0HRjyl1O^7W6(ZPH)X;t6rVXKU?*3FtT`Qdb6LcdSyEQ$@t~zt@&)#Ye74Cb$aujt$HJ9C$CL!#b>K>>ls}if9}kD>iuK<'
    '9pgJPuPnyb)S{XEGgoJVe)$(czx?y*zpZDk&IU)!nd!}b=IUIKrL)t2i_csoYrHiw?czc*6KSSfzJpPx?WE<qt?#OT?KQZr8BIoM'
    'yK5__u3b6x)ul!>-x{CIO;lTnD_w&<S<$VLY@@x8mqwz!H(wWZOFpu2;g_ZNNA6CZFP_PN>vChJ-!~PPm1nhEp5_SjA71}2QU6lC'
    'ojkoelmFJ`(V2eVy1W^Cyg!r2yNdES7p=_A_2lt0-8^11vQTS|$_8G0>D}+~(fIk(Om1I{+taShD<37#1JC5wc-t}4Z;iK&)_wVU'
    '&8_~uvtr!Du~XL`JN4Do@nmn!tsibQ-@Q7Pyx!jHCnGC&pUdXy>|}F$Wi9UcxW(<x<lynBla=G$?@P|a)Gl#5wzTA{qe(0;jVC2<'
    '#yB_D+)FmL4=d#(Sxx)8nfz+nyJz~Xrkx!Jt?q2EIM}Y0JLjT1=jPgZYPY0M#*Q`HXC_YzjUZ2hYo}zdr>?!TnUU;XudBA#;`Vzs'
    '9x;C=Q&X?TdAeaHzXtmCGXo<I>o7jzHj<~kaWpeQt=&*qYx!fR9Zfr5`PO}6WF_8zl{WNLrq&+oS-Ws`Pr6oNyVl0;K6UNg&Asn<'
    ';?%WIG=J{w9Ak^E_PaWfyxwfr^KmVXtbF&}5UslJ=f5~tdowk+8g**7AnNw2p}DBrxl31IY~^k<qV9YOOr8wS)auhwC-$^fAMYP&'
    'XSK^T-($z-qGQcA){b~bQi9IWG4aD@TZ`juw!CItw>pwe#LXBp5%-VvM5fLQV(P3J+Row=bI}u5BBpA6(jD=)kUWxU2QSCH)LiD3'
    'lksuCKl94%ah-fFsFRyY>LhoD`qb*A>^RKDGLdW1nX^IMqOa-nFNf0>{n+rwVdqm$vR-f|t3Qo8c|P7fCcB?`+G|U8*SAbpc1(}7'
    'AeVcd+&B4TCjNGAcXr~x|IJQrTgT^zLuEEuwe^dcR*;n7mP{+immpmQbY~LT;1VPyy;3E3Au7&w8d+{F(N8<q#Yb)}J}SSQX+KGQ'
    'd?~1pxsv*5m$G+t)~nT`hN+LV1r<h`)Yp}%kKXSnIuabiUoJU@)A%bN0avCRy|bVmo(blwcG^s9J&~w$C1z<hO2$9&^_Zm_qiFf-'
    'N$IvFS7pY^?yxNF>Dks~pKZ<d-`1d`;nDbt&2pwD*5bPP{!D&e`lCTvAL*8LwkN(Dd*YiMvaIXgR=?-!ADhWvrTP9$K~`t`?CHkx'
    'sFPNEG|0?j-OQ}J=EAG_gWFQQLj8AYKJG`K2u3F>nOE+MI;|r;D(5>_h_atbmPT4JbgvV&t`H@0CFSp5vNw|z88X>R_P3Hb@6MNB'
    'HQ%!kUyHh<wZAwkNxk*o-+?GsjzQa<y(2A0|Lyk6>QtP=<1_g?y-&>KuCnbZ+;@B(J>BbUyw}O%w)fOb{tDsoncNk^;yuOJlGD6>'
    'ws=opE4;3pZF}1*pL<GH0Qw)|=Urwq>w(1IGV+H^K7SYA4Spf>%0zq)dp7gRXxz3}XYyB_PX^gK(KlQDue{&Wxy!Ni`8Zp%{j$~n'
    'dTRfB8r|#7#qF!T-CL4%FoL6Vb*5jd-aepJAHDI;g1z?6BzPvs*wZupu0U@uz5*RzdoJ5kFq2@w-H(24wYW_s&)+;hlb^l)+)V!N'
    '<g+t{cPF#=PsTQM4ZYvJi?Q-M4X1*$$@4QCy0cMO+oyw`?9|LUzwLKy)4%O^h*8a%c#QwsnfwYtYr&}IgP?uCFjIYX;y(97N_+6K'
    'F=5ZBW@q^--yhE8?@zAHR2eJwj5T%^&H4V#O#c4lhryB2ceJ#peCq>8GNoH7uI-C)PJW-s$*DN%-(||tx)ZWC^4p{w`)-OyEX^#9'
    'rE%;`<Ct&V4_O+I&o3k8Wmr$1`+aNK<xJf3QKuyR``b8QJ!8E-F(xhh<KS4noIjRl3r7aY2(CSL+gafWjbJR*$!WaBemSjnEdM#~'
    '?<Z#SE0;u>SCTcN{uF$k{9}-VKjd>zG9%+yD+iU@Lcyn%+1$u{a?o-8m*CUNpJw{?je|yWy?g4Nh4D$y@BL+_d{$06bD~Nss5(ca'
    '(s7+Uch#89*J^Dxe}0PFLNL#!UmRui*}qM1AF6Hio3%SSo3GWzY~?+T3~GhRoRS?uPDW>ko>Q`O-E&HIR)0eJrg*fzn8`^pn|D`G'
    '&)3Z6kKT#d+|gV3oj%#odT)CxoF!Mht@f;=o#kuz?GEaB*KEJzqwhXu?~dcWSQu}Tlk0+<?5>`Z-Z@ko%SoR$Q(Wi!<IiJ<X7jVo'
    '4$S7qF^jW9kCi5h#xVzjW8%PUmFqG+z4yeXjAJH_lwLJR?wj8iWaH56M)uU+dNLZie>OiFx^H%<(a^-EjD{wTtZVk!8}WK5=QA1l'
    'ARZSyGMir)^gFZpQUB6x{<GiVOfHf!*SBYj`oKP8u89hLN7b>_MEN=8f#967G`r4`*F@1d<-y>b^1$pmM@bW#GD@1La!yIcd=Jg$'
    'pX2#nP@3=bJwsL)Lrol6?<~^+wR$9|)rV%+Ig%=@)rW(#-;v=*NfVnmN}8xXM))K?l9w}CO2&eZ1!IIqgW7(iZ`-XfwwkEgAC``x'
    'Cd$WxkI&|x9C&QD(g>@to{t6@cznI1q=`)#B~?0luTSO$XR?tT87sk&vAo_fRAI)B1sPje?-*)gQ^rsOMhD4rKxc!Nb7pp9>!+NX'
    '4c6P3y_&1w6|bN2{%roK>9=R|>!)0p%|CzgW>CKKv!C|*Ful(Wy%p5qh1p@BTJQbbcPS|2TeDkbb-Uhg!+bZWpLc@T-=4j?tJ1v}'
    'jKJTW-Mm%lejW74@6B$NRq1jqA^wd1yP*GFn+>j?2j|lFXSe=pbsq-D;o9uRR;&9>P`4k>ZpGE=I?qJJ{qN<V|NSV)%<pD5_B{l@'
    'pUvN4`DpfU<9i5t@4|f?j7%=iZu|-8-dz15$koTQSLSKu3kA8FNOLt2=jwdC#s3^<|Np753eQIVKZ)<ezgfQV3#}M-p5J#v(o%mB'
    'MI--k-AHuq<LHy|m5=`^dVbHj<MrlyUiwkA_d8?FpZ^@~y}9}Glbsj7`%(18mFB-qj5YuE+}d*V(hsA(AB{A(JAQs)qPe~2N6xNA'
    '=W5Z~_;a;Zt``<=X_kENnOpB~W_$d>ZSB|go;mUP`1hr4_2z&5yZHCr^;)xD#*)9;*8KfTjrjL{Q7u{dulf5*eOuDoxBjN}`}dOH'
    '_qBfCALo9hR^N7_(P@`^<5^}mE{}wxj`Z*M_5b^#Z;wj%xRlxB!jOAh8ua)5_WQ?VziXLNpU%Xv(tn%FMKPQnuG9}Fd#ttUBHhAT'
    '|1E?gpSiSNqFVd!kA8l!IX3US>$A%vRYp29Nt-&`is3J5Ewp}5v$2qgZC`g^+1O4NWn-cL-xrN%zMt%IrM1VjbW3HWJ6V*Im9lp&'
    'HU@nYQmaN<M@kycS|$T$`<Eyj1>Bm}W>h=+h1MPSPCS3#6VK<f@9mq7eXU5+tu>=MI(ss^wHps+w>G;xa;flm+}1bpOO>y0j3wud'
    'm0B(7iCdXz#db}SvD2B1Ep6-8;6iu5N57D-i%Uf{xK#G8qKq9)_I`F-x4usIFLl@(-<H;IGsBYy;~5;Q**t&tP&S6i>=ybyJDTKV'
    'Un^HnrpI{e_jE67t$I8Ze<m-f&B=aowp&6iXbFdMEum<B&dKz+&cxG<vpsv|P<ETMJ@M=*$=gCJo;Yul>&aX0lSh)hv#khUOwY-!'
    '-|vclUs<j7tJ6m7JfHT*;eXu`_8RHdUg^KJ`O>WwozLG(&ls6#-`<>PlOt>8<3U^N?6+306>Yh2zl~v6ioH0Rj4`6-cw@94|GwH9'
    'Z#<OL;DLI#2ESDA=44<0*p^FUn=h)th5lPBslhKK8S7V~my&27&P2P^XZv3ml*zEazBk$0O8;o*f~^HTSL1N$IcGV^`P;3?(^9<B'
    '`aRw6>3VUWxZ`kXSxy#Z{%rrUoGjg1QSbjo67$EInAiGmf3ZTY!k7=H$3;{x&cn$HTduPD?n}wB@Jj2rcsZ$;hg-j2Ov-qm_50!W'
    '_^RIN^>&xVmcNG5FSkdEO1;$GayFAkI^`WON@*1JxoL@3yCrIlzUl+Emfdgpc&2fws6?lmdnteKj!UKOuzXFG-z2s6ajRTu%Y3`_'
    'd)hM3_RnXy$6)kQT%xs1?dRWBY0G8z?^<WzZQWM4Z(Fz3eO$KRBNbX*I4XE9Ju`3Xo2AQ{-YWT&v2tKrz0$a=(S2{Fzu&RGbz_om'
    'BwE-v-Fnjen)I`9Gh?4L(y?5<^V#`yE0Z6lpIlnMrzLv0S)wXqyljc8{QZtF+v#z)x~)E7OxUxp(!bnsx#W&uJjU*p^p)m*tBfAA'
    'd$02MeM)*X9aFVRT4A)=$hNd}q+0d8J1Wi7uce=fn%P)Pufw!{e=a@BTE8!}N9^_0A1;1eU%dRk@7lIHva&L{vi!>vqv_sjE0=#z'
    'zozl^xp?oj<>t%zvM;p9>O*a3eyo2zrV%b>B3#&{2$$Boosv<_S|+QfGcm6Wx3A@*m``s`R@2_F);d?*pMKV>b<csjzP>kJyQaIR'
    'A07C(ejxsBJlW^!$oZAY^UJ?HT07U==h4PO^Z#3WoZH)fWt(OKy4#;fxBt(bt#<b`er{#*Tx<Kue)8KtT=`qvc8n)woN9gENya&6'
    '>)mnAQoTFQS;*vJUwu>ZaIz>53!Ah3#l599yOJr<(&l9T<P8NSTG^cKFWyjgeC=wT!QO0+y6c^*e`}NNE0bd@Ya^K~w&&Wl_tcDP'
    'eqy41e60TP;K%iYaYWrH)4y!Tm_&7S^jsR-rJ(E&r$^0X*?xER?6<qOA9W%aNpmuu)^dKoCEs)$Uk$EzB5AhmD;Y_+4s$yL^-M+w'
    '?6=#x|G9e(OZHck`6}P`H8qm7`Kk0f3R*|>R5wfern=EK&j#JnpO|Pzo9w&UP7e2PC;2n((CuX3mEG@=8;YN6Y@O>`8F(^1|4c<2'
    'J^y4{%|9RdxPB=9ZD+0?N6)wZeykl~c&{vtXQ^L2o$XhQrxX7=;_17pRC=#rs++^pnH;Y4iMd->KkUR%a>mQ%uv5nM=J50;#M6!9'
    'UpkTPY@ZV@tV~`QoWsuOHysOQGIq9Kgxx-3*o<|`Hgv{*osN8_yRog6$JW_vX>1#5fxXXyuQX#zkH~*NS8tzDkB+uxAhhO<x6Tyf'
    'qs{T?x;`<EO|<UC-k!M^`(kqT+;_vay=R_D+WqNPcIMJ^$8>wWqUPUEcca`_Ez0?VC*D^U)>q1&6_lFi{7ghk!)`Gb(Mq-VFPC1A'
    'xi@Y5t+<{^@AG70JiXqm-4VaPwXNNq_ouD2wWS^HEuBlYv^bHht`Zfk5_2j&4qCN-M|vDIx82!dCd&4wiydi{$)}6v?}v+`Y;JY9'
    'C{I@S4EyJ_ZMGs_O50}Z_p~Gn-IBE0@^JfKEGWrJbF0JUr0APNewwz|Oum<f-S%StYxT{R+uBn5{kxO%WNS<5S#9-yZSSRh-Qehs'
    'i^;sO=tz}o^=qxDUrk$c>-TiOr?dM_&y<-Gq`h~t-?_2Qtd~~Cj}(=qx&3Y~y7}pDv%Qyan?>K{l}28h>_)z}{)}BJioCh~-9IXB'
    'b=~~5TV6V=Y%GktxJDLQE8&eF$eh2QY0cRkzbo^~Tdg@&<9B3Uxzw8PG`^6&(peEW=?9vv{N|{7<YPUNhxPdF^vJoT=NfFhnsA?t'
    'cQc)i0-C=ixjuSLdmlyD_&$isaA&4e4@8}kHzT;IEP_s%x~+8eUpf&av$J+wNL$wBjh3=gwr+Wo93H*qVnHc$=a0Bf@5$6@Qu@1t'
    '(%)5F`aZ{1x6Ium>*(l(xb)}ORr>apGo|nDqZ2`r+rf4Gv$#x)K`HMkF6EE<l`^b};t2AygKp_}H(`5~Z{0Z2nh837f2P*rbqU4~'
    'WnTGyT%LoO63#`PV>~Efd++lbj5d3}er^1|VDE=Y_r7b$y_b)fmg1Zo4s!DCAgcQ}H79c=_X^j>moo9(8g(M<*;;V-bNk`GGa}Z;'
    '9|+2_R9cpkLzZQ+vC(hddvdN7RaEPi`cF5sUU@Z>hr3(fN-+LZ=9TM5TCY5odF8utn?I6yC7$Cu{=LjA$KnipCzF#T!w&{I2{T+c'
    'o36B8itgqokvtUC&i6`dr*Ix!Gll{8l(!!lJRf@ekswzOXCk~U>SQ>MaKQcL?U#mZOP5M>^=MFQkA$_BzdyVEQk7Z@-gTt%Id&zJ'
    'v3RY$@uQhno{ZysJgDWzN^7}z7TGP;?&@wY>eZf!_r9EoCw^)?i8-y)3invIUoLBh<#$fE51tvgHhw&l!{_1%j|DNWbYre^x3oN~'
    'Rql8eW;Hp}J{i>V@v>ST9kMSQov%DrPtJ|cXL1;SgYNh<!Fb?g(D$7PO7YaDmZE$-uo~?BWa-|QHzkKX&vB1Go5{)1IEEhwQ9V-{'
    ')!ce|iqXTRnRzaV;n~s{hU~{jtIXPZJ#IxW20iQxL9cNtI9ESExQ88GR}VW{-oySR$lD90dD}n_J6hhuJ`(5ZXF;xh8uYL)R_$R&'
    'hwNcTi+b4jduPU93Pzqk+cvPT>=Q$B)Vvb3ftLpN*M0I|UZVBQUpm?PCg<_@GUdHFzP@ojd+j1_?LW`FvKZIk>p|c2TF^JW+O5GV'
    '{q<;h-&CPT9xd<j-w4{+>xFGB*I$>%R;A}1y<Fi_*x5{0<F#$Z&jeZhc_!ux{q<<ks*SD4S4S2XCKu=bb#-KAX>#T8FAJ}U7k+1U'
    '{EX=MxlEMtGondJ;%i%j_t8lAF@HrO?fX6F@m0G^nQT8A=l??Hm84{E1|>Vcj*{)#l#(r%Twz@se=CUe!lu;0Vqv7K;|CTd56u5-'
    '=j!nIxuwZ-hkx0<HheC9va<Y}XX2;m$KT21{#+dY+nEv_iaIrxlqlWz>d3LB$z!cplGwVjB(Ha4xg(9`@D(Xx(Vd5+B<}_#d8e>$'
    '!hIH%WU;Iyo%|#bhxw^mlHz*1d#qKGk23XkIX<q|GOxtzRE@u%dF7qB{J#z|^4=!Y?PC8~uSvhznH`gCt$k$W^S-+0;KJm==Fgo;'
    'hIWr%Sem?W_?MkK9fjXy9<OFH{z0Z>4@RBR$0h3*LwwbAJdI&zyX5T{&M!@#Km5yfjQwI*M@e_4TW^;*-OKK@O?3A%;2TBby8TV2'
    'Zj%gr7-V2=U<Qh7A*t)I7A~zL1D!m#^E=tjK>PKJOOqGNGSImn8kg&LK}mm8y{;?A5Z3jhg?9itXOngvr+M8yp0=cR3!6N&FnOqz'
    '=l1LEz4qLF*j8nJ^KGp)HOBvty#^GI8ZT#F*%h~y-)Hg_f2Ut^_DJ%TFUffOyx4B7>Dgc;cdQIul1<3so^+q>81^Ksvwb8D%3^0;'
    'Wt^3dgRERG&PqG7&N;Gu+@#s*M3zQgIkE~_>6|Z;ZSNjwpCR*ENn;!`E4llNac=&cX+z29vp)sd`a|K}sBS$bk#~>1c3Wv5gX?WW'
    'U&)Rg_DwGC{p#>z=y(OC@xNq`pQuyzirWsyZSnW7jenBK*6rQ>v_~EVTP+^9Zlt`!d^UaL-?n1CH*-Jalh*grjejol%I)!|)$1~^'
    '{3<^0?8v-wC~ifgnOBm$)N1*>#P?n*=4E+9d6_T$EHzfkkK^O$k1w?538dR@9*O%V4>b4DnNxE|I;W=id!4$UICiJ+?nGKN=Ve>@'
    'v!oBkxxJ>A|I9QIlwij?N^r8E1g$+4ZzVUksBl%RB+^|$q}SBi=aTAKI=Lyiu5#`1&Uk!1lgaoKaUI-{c_sNYczvd1_eP!LBrRDI'
    '%kG^A_e~yb#?+p7GnvF1%)03_0=X+w!n7_%(yg^e={q}H>zyf7IDSqdp9&(sp%ZyKi|wp-_m%8B+}EWFkyp<{`FQwrTo?O-y7){`'
    'qM6RQX7|qiExDb|V9rl@i7ITZXYNyBT_kgsZpuXdt*BGF{xd&v*=%QVb>z^#$wPa;nwwYDr!PHJJg=p_?X(>2w$&VQB-`$tF|@7v'
    '_o<wY?-G3_Q)j=6`;fWJE5C^Ab$=~CqwD4%JD;nboir=$Eam1S4VRtVQPIvy`>3co8cj-dOHiu)C8bLC*eO+e&uK)tSw6#+YG=Mw'
    'y_qZCcHuXYjDNY7zti`nTK>++T&?8JNNvbFeYN@0`&qXJd;jvL?!C&j&}ZZJzL3dGatHACAXi@tqWwx~w9A{6tK?3~e6aW1OZUF6'
    '`;WEq5zlwx%-k7d=8hn?h0@rDyf0Z>EWKlOS1o_X>dxBWlAbKMV|7n0f5+;s+Q7S(wZ$Pzw7#|S?~6YJJen!*eewDGaORbjxIG`r'
    'yb^!E-1vdaD<_kAjkWy!pnE$d9dMVkc4UaTAG!OLwM(V#{9w?Q4wSZ~b<ORmm5*e;5@+mNwfr1_`-8S|s5bC!W^Ks3nYE(+DY?)1'
    '?OOhh*tcp!-Dj+A_&#Ipa^-mf->v0mMm>;uCAlxT6tu&`wTky8Ya6~VS(xo)*4B4|Y(G#N>i%Qx@}~4z?e~5w&f!DB8Tfm_QS;r>'
    'qh@}CQMKQ7KA8=ei6`0nL$zvK>m3g~9F*e7742aMwc)k+?0P(V^(1c9M}xELW5K!N`$1VA{S^A^?D}<U<BtbN)??|Fh-T{@X>F_h'
    'H1N^!1Id=-XMx8@`t^^ucCJ4RdT;sak$1-#I~Mdu%R#h9yT{siPk*$tClBMr(Z=V20q<QbJ>NbNoB@vIa+q#^S9|;E8D_bijUxr;'
    's3emI`)pyca0|s*or|xHtOnQqo~q?%syrE#=y;|FIT`mL2Yb%C2Xg1MOQj{Ml9NlNIX@9Z_*8CWa`f+eBK!|Mb^3+k2)i@525q5y'
    '9@o#~+&&Yu;irS6ezo+d4||7&O#gMT^S!I3{a{HimVEB}aVE~YqE6)LT;jOL-!rh@_w<YQ#bg#@rqs#yf1GJi+3g=F9#`xckd1G|'
    'dH5gWt$nj6&VTHwyKj__Plh@Fzx+SPvo7l0>^=0w_)}`;l@G3u?}TPDd`~<|Kbw6e?nhn@M(IDvypoJLPY0u;Q$cQ@>*hAiN!(7p'
    'x!9AFLxnjB`<MO47F#PMk9OMUT>C2YuF`pxF9hS^)1BCgw>iHlk@Wcv?eU-1^7ATR3?lqVg$Q@8E5hZ{k>pE3BtKnOuDbo&{wG@R'
    '+JF2&t<QSPqeZiha!<I$?eO(rl>TaPW_u;*onP+8e>{%liK0jjZ=e(>OGh}b1yQ})jcUM_7t5j=P@<EitudJ+`itOL{&^7X>y>l3'
    'Skj}V?|riM-u+J<?6-xIYu!nodnV{}f6<NY$!;e1KXI@i!m@Er(!zVTu%oku&fTi&Pa-EH^LH{C{%zcnFJ@jzJ}aFM#y{tRlAg`i'
    '!hlScjV{t$#r3%Vcu}s3#y_W%nTtV$=ks+jVEac(deU?YPsLj}(b~fPlZX0kXUCwc$`8dEzLd#uG9Gv<=(8?%<3Ewv`;%4o-lr5v'
    'O`Yi0)cz+A71USJ=qQQy?I7Aq`Ey97J?uYzs37O1(Vob({~@F87x}N_*8YAle)v^z&Ur5=-8=cZ$d+!1y4d*m;nzW*_^Yclen{>k'
    'uLa|W4}u8a|J271$*jWP1XsD&YJ;~K<|^qoe;f2fzp31B&TXLIJiM;!-jBv3>Rp*p_b=k}|6ejWc_ls~{t%30ejkivJ_^eIyUJxh'
    'xq*?)V(CccauC(;D~}CMZlFfWuhk^i5dIYOp??f|s6PzZhaMT+hgKeM^c&CoIf(F2omn{Lqmf218d>j%>r#a?`S0U)JDO?R$+IxE'
    'dOqi$1SR^*kfVZ)k6VtE_N0w^zORW(k&ST3QAc4<I^_7Fc=WQPo*%u81*I6R=i2s=qmDkMSl76sU(P3jXm`|e{rm9^N4u_Z!oWN4'
    '@i}~NCjUp`W8sE+{@K#&>iK?ocRk-P@2X#^etEuh40C-D$#qvOk}B6gW`bNz1rgp*A;RTN%~f&@<TF7eGnq&ZRnFDsUIUqkubkgp'
    '&yO5#s^>=z`|9~VdT;&eUjzAE5Y<iftA7pT<v535tmi+E+!924bN%XH1Nlob_bC%?(!+kSzTPoO?`Y&p^?ctQ?`zA9Mg|=tN8<VD'
    'E1CSf5|7F6&%Ck{pU>~gypoJ<ZV$#bUkk=Iw+8w7a(!!!ZEg$t*{^N+vCTp-wwVt~ar+h?+uRXEyRc=)Hl5F^ahqQZ#xVB;{qo&G'
    'Z+O>L8pGThL~_qn8p9+j{~QW(bs&gv@lzkeB)#o@LH~8AzBR6#w70oCelF;H_58Jw2Z9mKw}TPRw}R5$U%&d-Mh*v2eY?I@u8n*r'
    '=*u1q`mzV=TkG1$cY_GOQ{Rf$Mi%0c`J=)3;o%_X4+SOq-WD4_JQDO}4{zb|!`Wn3TQGk3eo%@>x8(RC8P7jn&(C{#tiG{3GPyPM'
    'f^0lqzk2sps`U=1;&J;=v%Nz+Zht!S%Hwf=@nkTDc_QeSj|KhmO8wKigVQ^PIUYpvME%pcQ`2wu_{n;H1;`UYgiqE#-5DUgz3OVv'
    'tDd|nS2OxWctd>Ve?F7LJCd1f!HDIVpcGGEm8&1UXNKp3sD6AEuX6Nm?X_g4S<r``3i{CJ>sNaQNbmXlh2Z+k>H2y{9lax>p9E!p'
    ';i``x1|1`p;`8>;GdX!TK5xI0ov#?z^-DoN{<EOx`stP$jr5M4UJjytX-kbd`ps{DJ;?d1K`CC@Qdcv2`_ngq-s<(vXN1n$4kPKz'
    '+hk>kk$z8h%yrHH;k(+i!RIT_csU=8NzMdgl3xUo|NM$YUOpx{8$@!ZLL|$Zn8WrKew?iD7xbQQ2L06edetXH<~H!mMbUFBze{F|'
    'W#UYtx=^qB?8(W3882@ICB0a=q>CFU>B+`M*T%o;Kg6He8{M2t%*J=qGOv93@8Ve*nY_If_YNNhSAl+2&#z_rZg7w0ogi12>Q$e_'
    'S={imA?4RD-V1u_cQf@k+|xAuR#qSG`ImliCL`7NgYng`gUEkXAMQz_jX%|Lsr3HrS`gv;_2Hho+32&b{bKthZnqx=qnh6aJ?w9S'
    '9`?g-{K?Za@pClEGc{G7rs?w>O7aBCKgQYkM$a=B-#j?rIh5W}&F_L}f7^{VetzTV{}k`#KlSANn>{)I<`7TK{Nr%Z=DtfbS*xv{'
    'U+w5}P>PT0oAZ3i?cthI>F49!wUtxXuAKVnHKWPr<fTS5KVEBo-ks>5@0XJqYW4g&G#}UVYhJB3k}bFU*_TG5y*FPMb^7O{BMTRP'
    'S+K&?9fk3(=HfkC`-j*6ODpQAU)05QaMyS|KPhwG|4IBgIm*29T(WLl_Pn3We#?~p?x@pS^sFm1Y`mQjZ&31P9_ON!xw)P^ekSUS'
    'Sgsjas5M7VeOJfr{U)4Gf?E6Yrq<fw?3%I3N-K?Xr>;GB>Z_~inl-JhjWz#zbw~1gdoQ1itlWPwTcWd*&20@{@Asp)h8meVOGZ7l'
    'Mz^Hji#qk%ThdO9Nr_iSkDa>q*r~6+G@g{W8S7jt*7jJY8ROj_cE&Ol^Uz*hsJ*gP<NRE7er~Q^{&rn{vg1EDTSYq?&GH|Zh`Kdg'
    'R<p^B=Fvue_0UGQykQKdu07u@?~b&*X$^m}<A=Ez8d1022bMI<YTRl!Uedmw3E~mi?o7Sk7WZt|WL}BlwlNW8W~@=v=G(EiGt$mb'
    'JK7T?D?K?WYXgsGGLu_rYAoGbyB>Dtj*V-Q*PHEd{+3p~jI2C%v8NS&RN4xA<M>RRg<Y8}tVEqm^=6?kz9jyB@!i}vzG_Fw(eP|B'
    'c5W^@*K9MLjOFTQN4n>Bi=Ak-r8rN`mes7CrB++&eD)Yw$Yg5pxnzHQ{=Yucg7zjeCNsH9XG~^tmqt34w)XZ)Wu3?`p1Ss8zsP@>'
    'Mt*Za<R2D9-Y0wQ`fJCKZ*Ny9d%fr2sZ8FI7IuB3Tfe>Q`Zeo0=@mxP$aZ#)ySdFc0@{(?lg#4G)ZepFC)VEjn@A(ct)<q<X}ccx'
    '<omG;r>?!wjC5yoIF0oFH#_y({I~CZ6rHH$YIRrf`Sj_qRx3xAJ4*XRcCl02VPqc_L^jN)>o<1BGmSDW;r{LM{JhL73-JoiH)mdX'
    'Ek1Ma%e<1*+uoqwK2uz8<Gm{cu8tj>i;gw3({5qidYik#_12DLB5mWjwdPjGF3d$2hKp?d_11eN+!SPVUr9#W$814HCv(T_j-(xa'
    '3P-|tdu71R*(B*ThKOvVM?&x1z*`#mPtW@s`A>2;H@csmTc4YkS_9n9XSk)=C>dA8pW&8njH2bQH$Od(m3|(LKYuUn>DkWYpzZYg'
    '^!&vj+FSC`&i3r(#-6=QR*H6A+bRDR@wM@<HS$+7ZVl?<OF`-8x~2PUpStLcYBr8)^3$q|uLRNFnyZV>=l;p;wX`I&!?c`&?d&Pq'
    'PI3FcJ;?cOK`Fl0Eyd@1R{4r!>FoWpnZ3^rDn-wgr#(H}iR-YqMfK)<K8W`AZnU{I$@=W2Vhb6#ozI7*uJ$eBhcfwJi;s(Yg5%<@'
    'ppNbgN_|JJrRA>e^{n?+v883M6c)6%ipRy>L9};uqy76<ZjXMp=c?Ejp3d$i$?azcMEiw!JAeOlPfaZj*iP|$#sfjl?+r?EPp+jU'
    'Eu;UsJ{4P9=1O7zE1gUK7;onr#W_#z^Bimh>qj<9R$!{!5(Zo|u5|uS<})4++WGxK&hHCyeyE%C>Q|u4OIQ6G^MH2#tsvU_8~JO%'
    '6|O*6ZXpA%B@bxl$^4fG8u|M(OO5>9kGQ5X_h**I<GwPzKeMzm?JL{&XLgpZ^cLTTS{muu!g%o(`ptiNu#unt@<5~f&TtZAYd_6n'
    'r*DKw*}oH%{lP}@o$9elTke)UE%jI~Z%KrGwlMssxIf3wC%vBSQ{s7!CmZ>Bjz=@ET!{OfM;iGx^Ns{<<Dnow-|e=IA#1kizG(mZ'
    '&q=n*+C~!L!$E{c8iVfH#`QQ7Za<80*w$6tzkEN)?V~~Dk968znwj?AcOJ;Lz=3VAXYI_O2hWUx2IThfAj0o=b31U1)EpgEsQm%='
    'es@+`12SpPPXz6GCCK@5P@<!aq3)trY0qQ1vJ5!hdvks)h;U^STSdM%?>l0t)SjOTa{FWu`4f$y?xJ6T){<LaGl=l1O|Si<<A>JW'
    'p8Gw|bUHY1KO403r-Qm!4N7{lk)LzX8|Q(FCGCDbO2&fSGeB;=^8t17;~>JPH@&qC7`IGRY3I)exqU8({Mq69#EA{}I1}Z$JrzXw'
    '{BWb1i4BixCaRpble;)S3)=IGLC${?l<4#(=DgB4WI)b;8btWwaO03G&?@?k|6dMr`%)13&xY%9CN?|{nJ6FszZ#7HUv5;tR?|Ee'
    'O%#p)Ukl3qYGbImX%ib><$7X$--+?(c%1)1CNt;aasGv%zc?ElUq27pz#BmxUN39|2Zw3{{l-NH`i+YQ9ACc(BK&#gYD|SuO=&Bw'
    ')Z<j@FU|+KJr_iN_NuqB-rT+!M0kF{XkoYrD~vZP^%u!p_;(ul=eaKhIlmZ`=tAz3%Yf0#6=*HJbL8J{<mbp=YJ6I&AoOlwInLpG'
    'jr{Wj?*<XR)A+PjM`*wI{basyBfkdZdyQe9R_vYa`+iWaUp21Yiqw6d0*pugA7@IPtXKWppyhwq$UoVz*2vFc|DbX8*J}Dr5Y>l`'
    't+HPA?;H8&06q$${cU5btXF+GIJ5n}v6a@VZg2D6cx?ZdMt)uDKL+ROKLjQExUsd?rT%je;U61Yab4<n;tWS4`MWBg1otWa(%6dY'
    'QYYWqQ5(sxUJ#dP15YdFR_h!IR_h$u%;yo$#?K>Oir@Qoyq$OAtiGFWXCmFsMCFwutN;He|MA294@C$5rS;un(V0vC-=F{b_VumT'
    '55)iVc(i_J{#^tB0000000000003-pUyP#p+OF1b+gr=CckCI7qP^+QDB2h8Y5vFST0gf((M_$N&DZB!KX*jY2itFo_SB>3VC&y&'
    'QFJ){8AUTuG<xnoHUCp<A@H^{vJL<M0000000000000000000000000000000000000000000000000000000000000000000000'
    '000000000000000000000000000000000000000000000Y)SvRE!xxi`Fi>@ioTxyvoTL}wg&(J0000000000000000000000000'
    '000000000009#&d$Bsv%ndUEtqxq5fzr_+<6V2D7=+g3zXiuv=&40E9f3y7cPd~2gKCj09udE+LyGsB2w&nT%U$w8fA9UK+wn+Qh'
    'LhbAP_A{*-xglEIw#)ha({|Sr$#D^@*EXdFTGjba(Z){}e{E7j000000000000000000000000000000000000Kl+jqxt)m$D=*p'
    'I2lDdqcgjr=ts3^+i{5j00000000000000000000000000000000000007{>EB|k_94+sN_WW<rt~0Hlv(fUK@z34S2iu}(&o}<h'
    'U3+&<%>UE2=ttY5ZTCgB=qu6knKR4Vy6-={lDvQK50dxa{DYz1fB6487QgTC{1dI8qtU5a=Y7kckD?#dqix3v<B$I?n%~v@yBnL^'
    '|F5;^xJm^8000000000000000000000000000000000000AOfi=|73(ugeGk0000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000001zwZBhUL00000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000K-O|p+Z9D;qOr_twTbp`jpjf9M-**~'
    'YR%vNZtwQyzh2Y%*>rdFkDLE%`e1wOpTGWfTl4pSNVnXwH(GAUG5`Po000000000000000000000000000000000000000000000'
    '000000000000000000000000000000000000000000000000000Px?TiTMAQyDu!yXZ|^pzV>yA0ssI200000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0001BBgSrf<G*fe{;WmO|K0lcQx7ixto846-~Ts%YW-Y%=$Ex^C4c|I|C0Ru;oRTvy1o6rzy9^V0Zp=(ga'
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
        cap_out=ResourceCreateOut(gpu_va=0x102784000, gpu_va2=0x1027700c0, slot_index=1, heap_size=0x10000, cookie=0x70100683, type_tag=0x8fa1e, out_heap_flags=0x10000),
    ),
    CallOp(  # op 2: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(alloc_size=1072, heap_flags=0x10000, stride_or_count=0x8000000, create_info=24),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid_tag=21, gpu_va=0x1027b4000, gpu_va2=0x102770180, slot_index=2, heap_size=0x10000, cookie=0x70100697, type_tag=0x8fa1f, out_heap_flags=0x10000),
    ),
    CallOp(  # op 3: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(alloc_size=1136, suballoc_flag=1, heap_flags=0x20000, backing_ptr=0x10d4d4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x18000, rid_tag=21, gpu_va=0x1027c4000, gpu_va2=0x102770240, slot_index=3, heap_size=0x20000, cookie=0x70100698, type_tag=0x8fa20, out_heap_flags=0x20000),
    ),
    CallOp(  # op 4: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027c4000, parent_gpu_va2=0x1027c4000, heap_flags=0x20000, heap_lane=3, backing_ptr=0x10d4d4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x18000, rid_tag=21, gpu_va2=0x102770300, slot_index=4, heap_size=0x20000, cookie=0x70100699, type_tag=0x8fa20, out_heap_flags=0x20000),
    ),
    CallOp(  # op 5: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027c4100, parent_gpu_va2=0x1027c4000, heap_flags=0x20000, heap_lane=3, create_info=24, backing_ptr=0x10d4d54a0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x18100, rid_tag=21, gpu_va2=0x1027703c0, slot_index=5, heap_size=0x20000, cookie=0x7010069a, type_tag=0x8fa20, out_heap_flags=0x1ff00),
    ),
    CallOp(  # op 6: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027c4300, parent_gpu_va2=0x1027c4000, heap_flags=0x20000, heap_lane=3, create_info=24, backing_ptr=0x10d4d54a0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x18300, rid_tag=21, gpu_va2=0x102770480, slot_index=6, heap_size=0x20000, cookie=0x7010069b, type_tag=0x8fa20, out_heap_flags=0x1fd00),
    ),
    CallOp(  # op 7: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027c4500, parent_gpu_va2=0x1027c4000, heap_flags=0x20000, heap_lane=3, create_info=24, backing_ptr=0x10d4d54a0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x18500, rid_tag=21, gpu_va2=0x102770540, slot_index=7, heap_size=0x20000, cookie=0x7010069c, type_tag=0x8fa20, out_heap_flags=0x1fb00),
    ),
    CallOp(  # op 8: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027c4600, parent_gpu_va2=0x1027c4000, heap_flags=0x20000, heap_lane=3, backing_ptr=0x10d4d4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x18600, rid_tag=21, gpu_va2=0x102770600, slot_index=8, heap_size=0x20000, cookie=0x7010069d, type_tag=0x8fa20, out_heap_flags=0x1fa00),
    ),
# ── queue setup (sel QUEUE_CREATE / NOTIF_QUEUE / FINALIZE) ─────

    CallOp(  # op 9: QUEUE_CREATE
        selector=sel.QUEUE_CREATE,
        scalars=[],
        struct_in=QueueCreateIn(exe_path='metal_tri'),
        struct_out_sz=16,
        cap_out=QueueCreateOut(queue_id=1, cookie=0x7010069e),
    ),
    CallOp(  # op 10: NOTIF_QUEUE
        selector=sel.NOTIF_QUEUE,
        scalars=NotifQueueIn().as_scalars(),
        struct_in=None,
        struct_out_sz=16,
        cap_out=NotifQueueOut(ring_address=0x1027e4000, queue_id=1),
    ),
    CallOp(  # op 11: QUEUE_FINALIZE
        selector=sel.QUEUE_FINALIZE,
        scalars=QueueFinalizeIn().as_scalars(),
        struct_in=None,
        struct_out_sz=0,
    ),
# ── resource setup (sel NEW_RESOURCE) ───────────────────────────

    CallOp(  # op 12: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027c4700, parent_gpu_va2=0x1027c4000, heap_flags=0x20000, heap_lane=3, create_info=24, backing_ptr=0x8090a6210),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x18700, rid_tag=21, gpu_va2=0x1027706c0, slot_index=9, heap_size=0x20000, cookie=0x701006a2, type_tag=0x8fa20, out_heap_flags=0x1f900),
    ),
    CallOp(  # op 13: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027c6700, parent_gpu_va2=0x1027c4000, heap_flags=0x20000, heap_lane=3, create_info=24, backing_ptr=0x8090a6298),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x1a700, rid_tag=21, gpu_va2=0x102770780, slot_index=10, heap_size=0x20000, cookie=0x701006a3, type_tag=0x8fa20, out_heap_flags=0x1d900),
    ),
    CallOp(  # op 14: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027c6800, parent_gpu_va2=0x1027c4000, heap_flags=0x20000, heap_lane=3, create_info=24, backing_ptr=0x8090a65b8),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x1a800, rid_tag=21, gpu_va2=0x102770840, slot_index=11, heap_size=0x20000, cookie=0x701006a4, type_tag=0x8fa20, out_heap_flags=0x1d800),
    ),
    CallOp(  # op 15: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027c7800, parent_gpu_va2=0x1027c4000, heap_flags=0x20000, heap_lane=3, create_info=24, backing_ptr=0x8090a68d8),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x1b800, rid_tag=21, gpu_va2=0x102770900, slot_index=12, heap_size=0x20000, cookie=0x701006a5, type_tag=0x8fa20, out_heap_flags=0x1c800),
    ),
    CallOp(  # op 16: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027c7900, parent_gpu_va2=0x1027c4000, heap_flags=0x20000, heap_lane=3, create_info=24, backing_ptr=0x8090a6be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x1b900, rid_tag=21, gpu_va2=0x1027709c0, slot_index=13, heap_size=0x20000, cookie=0x701006a6, type_tag=0x8fa20, out_heap_flags=0x1c700),
    ),
    CallOp(  # op 17: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027c7a00, parent_gpu_va2=0x1027c4000, heap_flags=0x20000, heap_lane=3, create_info=24, backing_ptr=0x8090a6ee8),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x1ba00, rid_tag=21, gpu_va2=0x102770a80, slot_index=14, heap_size=0x20000, cookie=0x701006a7, type_tag=0x8fa20, out_heap_flags=0x1c600),
    ),
    CallOp(  # op 18: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027c7b00, parent_gpu_va2=0x1027c4000, heap_flags=0x20000, heap_lane=3, create_info=24, backing_ptr=0x10d4d4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x1bb00, rid_tag=21, gpu_va2=0x102770b40, slot_index=15, heap_size=0x20000, cookie=0x701006a8, type_tag=0x8fa20, out_heap_flags=0x1c500),
    ),
    CallOp(  # op 19: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(alloc_size=1136, suballoc_flag=1, heap_flags=0x20000, backing_ptr=0x10d4d4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x40000, rid_tag=21, gpu_va=0x1027e8000, gpu_va2=0x102770c00, slot_index=16, heap_size=0x20000, cookie=0x701006a9, type_tag=0x8fa24, out_heap_flags=0x20000),
    ),
    CallOp(  # op 20: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, alloc_size=3120, parent_gpu_va=0x1027e8000, parent_gpu_va2=0x1027e8000, heap_flags=0x20000, heap_lane=16, create_info=24, backing_ptr=0x8090a4000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x40000, rid_tag=21, gpu_va2=0x102770cc0, slot_index=17, heap_size=0x20000, cookie=0x701006aa, type_tag=0x8fa24, out_heap_flags=0x20000),
    ),
# ── shared memory (sel SHMEM) ───────────────────────────────────

    CallOp(  # op 21: SHMEM
        selector=sel.SHMEM,
        scalars=ShmemIn().as_scalars(),
        struct_in=None,
        struct_out_sz=16,
        cap_out=ShmemOut(gpu_va=0x102808000, size=16384, shmem_id=1),
    ),
    CallOp(  # op 22: SHMEM
        selector=sel.SHMEM,
        scalars=ShmemIn(map_flags=1).as_scalars(),
        struct_in=None,
        struct_out_sz=16,
        cap_out=ShmemOut(gpu_va=0x10280c000, size=16384, shmem_id=2),
    ),
# ── resource setup (sel NEW_RESOURCE) ───────────────────────────

    CallOp(  # op 23: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(alloc_size=33840, heap_flags=0x54000, stride_or_count=0x38000000, create_info=24),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x18000, gpu_va=0x1072e4000, gpu_va2=0x102770d80, slot_index=18, heap_size=0x54000, cookie=0x711006ab, type_tag=0x8fa25, out_heap_flags=0x54000),
    ),
    CallOp(  # op 24: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x68000, rid_tag=21, gpu_va=0x102810000, gpu_va2=0x102770e40, slot_index=19, heap_size=32768, cookie=0x711006ac, type_tag=0x8fa26, out_heap_flags=32768),
    ),
    CallOp(  # op 25: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x78000, rid_tag=21, gpu_va=0x102818000, gpu_va2=0x102770f00, slot_index=20, heap_size=32768, cookie=0x711006ad, type_tag=0x8fa27, out_heap_flags=32768),
    ),
    CallOp(  # op 26: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x88000, rid_tag=21, gpu_va=0x102820000, gpu_va2=0x102770fc0, slot_index=21, heap_size=32768, cookie=0x711006ae, type_tag=0x8fa28, out_heap_flags=32768),
    ),
    CallOp(  # op 27: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000, create_info=72),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x98000, rid_tag=21, gpu_va=0x102828000, gpu_va2=0x102771080, slot_index=22, heap_size=32768, cookie=0x711006af, type_tag=0x8fa29, out_heap_flags=32768),
    ),
    CallOp(  # op 28: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0xa8000, rid_tag=21, gpu_va=0x102b1c000, gpu_va2=0x102771140, slot_index=23, heap_size=32768, cookie=0x711006b0, type_tag=0x8fa2a, out_heap_flags=32768),
    ),
    CallOp(  # op 29: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=50224, heap_flags=32768, stride_or_count=0x48000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x70000, gpu_va=0x102b24000, gpu_va2=0x102771200, slot_index=24, heap_size=32768, cookie=0x711006b1, type_tag=0x8fa2b, out_heap_flags=32768),
    ),
    CallOp(  # op 30: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=50224, heap_flags=32768, stride_or_count=0x48000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x80000, gpu_va=0x102b2c000, gpu_va2=0x1027712c0, slot_index=25, heap_size=32768, cookie=0x711006b2, type_tag=0x8fa2c, out_heap_flags=32768),
    ),
    CallOp(  # op 31: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x10000, alloc_size=17456, heap_flags=0x100000, stride_or_count=0x18000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0xb8000, rid_tag=21, gpu_va=0x107338000, gpu_va2=0x102771380, slot_index=26, heap_size=0x100000, cookie=0x711006b3, type_tag=0x8fa2d, out_heap_flags=0x100000),
    ),
    CallOp(  # op 32: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x1c0000, rid_tag=21, gpu_va=0x102b34000, gpu_va2=0x102771440, slot_index=27, heap_size=32768, cookie=0x711006b4, type_tag=0x8fa2e, out_heap_flags=32768),
    ),
    CallOp(  # op 33: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x18000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x1d0000, rid_tag=21, gpu_va=0x102b3c000, gpu_va2=0x102771500, slot_index=28, heap_size=32768, cookie=0x711006b5, type_tag=0x8fa2f, out_heap_flags=32768),
    ),
    CallOp(  # op 34: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x1e0000, rid_tag=21, gpu_va=0x102b44000, gpu_va2=0x1027715c0, slot_index=29, heap_size=32768, cookie=0x711006b6, type_tag=0x8fa30, out_heap_flags=32768),
    ),
    CallOp(  # op 35: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x1f0000, rid_tag=21, gpu_va=0x102b4c000, gpu_va2=0x102771680, slot_index=30, heap_size=32768, cookie=0x711006b7, type_tag=0x8fa31, out_heap_flags=32768),
    ),
    CallOp(  # op 36: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x200000, rid_tag=21, gpu_va=0x102b54000, gpu_va2=0x102771740, slot_index=31, heap_size=32768, cookie=0x711006b8, type_tag=0x8fa32, out_heap_flags=32768),
    ),
    CallOp(  # op 37: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x210000, rid_tag=21, gpu_va=0x102b5c000, gpu_va2=0x102771800, slot_index=32, heap_size=32768, cookie=0x711006b9, type_tag=0x8fa33, out_heap_flags=32768),
    ),
    CallOp(  # op 38: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x220000, rid_tag=21, gpu_va=0x107438000, gpu_va2=0x1027718c0, slot_index=33, heap_size=32768, cookie=0x711006ba, type_tag=0x8fa34, out_heap_flags=32768),
    ),
    CallOp(  # op 39: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x187c0, alloc_size=17456, heap_flags=34752, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x230000, rid_tag=21, gpu_va=0x107440000, gpu_va2=0x102771980, slot_index=34, heap_size=49152, cookie=0x711006bb, type_tag=0x8fa35, out_heap_flags=49152),
    ),
    CallOp(  # op 40: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x1ff80, alloc_size=17456, heap_flags=65408, stride_or_count=0x18000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x240000, rid_tag=21, gpu_va=0x10744c000, gpu_va2=0x102771a40, slot_index=35, heap_size=0x10000, cookie=0x711006bc, type_tag=0x8fa36, out_heap_flags=0x10000),
    ),
    CallOp(  # op 41: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x10000, alloc_size=17456, heap_flags=0xc0000, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x258000, rid_tag=21, gpu_va=0x10745c000, gpu_va2=0x102771b00, slot_index=36, heap_size=0xc0000, cookie=0x711006bd, type_tag=0x8fa37, out_heap_flags=0xc0000),
    ),
    MemoryOp(  # op 42
        kind=MEMORY_RESOURCE,
        address=0x102784000,
        offset=0x0,
        size=0x10000,
    ),
    MemoryOp(  # op 43
        kind=MEMORY_RESOURCE,
        address=0x1027b4000,
        offset=0x10000,
        size=0x10000,
    ),
    MemoryOp(  # op 44
        kind=MEMORY_RESOURCE,
        address=0x1027c4000,
        offset=0x20000,
        size=0x20000,
    ),
    MemoryOp(  # op 45
        kind=MEMORY_RESOURCE,
        address=0x1027e4000,
        offset=0x40000,
        size=0x4000,
    ),
    MemoryOp(  # op 46
        kind=MEMORY_RESOURCE,
        address=0x1027e8000,
        offset=0x44000,
        size=0x20000,
    ),
    MemoryOp(  # op 47
        kind=MEMORY_RESOURCE,
        address=0x102808000,
        offset=0x64000,
        size=0x4000,
    ),
    MemoryOp(  # op 48
        kind=MEMORY_RESOURCE,
        address=0x10280c000,
        offset=0x68000,
        size=0x4000,
    ),
    MemoryOp(  # op 49
        kind=MEMORY_RESOURCE,
        address=0x1072e4000,
        offset=0x6c000,
        size=0x54000,
    ),
    MemoryOp(  # op 50
        kind=MEMORY_RESOURCE,
        address=0x102810000,
        offset=0xc0000,
        size=0x8000,
    ),
    MemoryOp(  # op 51
        kind=MEMORY_RESOURCE,
        address=0x102818000,
        offset=0xc8000,
        size=0x8000,
    ),
    MemoryOp(  # op 52
        kind=MEMORY_RESOURCE,
        address=0x102820000,
        offset=0xd0000,
        size=0x8000,
    ),
    MemoryOp(  # op 53
        kind=MEMORY_RESOURCE,
        address=0x102828000,
        offset=0xd8000,
        size=0x8000,
    ),
    MemoryOp(  # op 54
        kind=MEMORY_RESOURCE,
        address=0x102b1c000,
        offset=0xe0000,
        size=0x8000,
    ),
    MemoryOp(  # op 55
        kind=MEMORY_RESOURCE,
        address=0x102b24000,
        offset=0xe8000,
        size=0x8000,
    ),
    MemoryOp(  # op 56
        kind=MEMORY_RESOURCE,
        address=0x102b2c000,
        offset=0xf0000,
        size=0x8000,
    ),
    MemoryOp(  # op 57
        kind=MEMORY_RESOURCE,
        address=0x107338000,
        offset=0xf8000,
        size=0x100000,
    ),
    MemoryOp(  # op 58
        kind=MEMORY_RESOURCE,
        address=0x102b34000,
        offset=0x1f8000,
        size=0x8000,
    ),
    MemoryOp(  # op 59
        kind=MEMORY_RESOURCE,
        address=0x102b3c000,
        offset=0x200000,
        size=0x8000,
    ),
    MemoryOp(  # op 60
        kind=MEMORY_RESOURCE,
        address=0x102b44000,
        offset=0x208000,
        size=0x8000,
    ),
    MemoryOp(  # op 61
        kind=MEMORY_RESOURCE,
        address=0x102b4c000,
        offset=0x210000,
        size=0x8000,
    ),
    MemoryOp(  # op 62
        kind=MEMORY_RESOURCE,
        address=0x102b54000,
        offset=0x218000,
        size=0x8000,
    ),
    MemoryOp(  # op 63
        kind=MEMORY_RESOURCE,
        address=0x102b5c000,
        offset=0x220000,
        size=0x8000,
    ),
    MemoryOp(  # op 64
        kind=MEMORY_RESOURCE,
        address=0x107438000,
        offset=0x228000,
        size=0x8000,
    ),
    MemoryOp(  # op 65
        kind=MEMORY_RESOURCE,
        address=0x107440000,
        offset=0x230000,
        size=0xc000,
    ),
    MemoryOp(  # op 66
        kind=MEMORY_RESOURCE,
        address=0x10744c000,
        offset=0x23c000,
        size=0x10000,
    ),
    MemoryOp(  # op 67
        kind=MEMORY_RESOURCE,
        address=0x10745c000,
        offset=0x24c000,
        size=0xc0000,
    ),
# ── submit (trap0) ──────────────────────────────────────────────

    MemoryOp(  # op 68
        kind=MEMORY_TRAP_AUX,
        address=0x808c44cc0,
        offset=0x30c000,
        size=0x30,
    ),
    MemoryOp(  # op 69
        kind=MEMORY_TRAP_AUX,
        address=0x808c44cf0,
        offset=0x30c030,
        size=0x30,
    ),
    TrapOp(  # op 70
        trap_idx=0,
        p1=1,
        p2=64,
        p4_offset=132,
        snap=Trap0SubmitSnap(record_type=2, submit_flags=1, callback_0=0x808c44cc0, callback_1=0x808c44cf0),
    ),
# ── GPU result validation ───────────────────────────────────────

    MemoryOp(  # op 71
        kind=MEMORY_EXPECTED,
        address=0x1027c4090,
        offset=0x30c060,
        size=0x4,
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
        print(f"expected={list(EXPECTED_CENTER_BGRA)}")
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
