# Scroll recovery working notes

Owned newmodule: source/recovered/scroll_graphics_services.py; new analyze/verify
scripts and thisdirectory. Do not alter battle_graphics_services.py (frozen
368c052e350d0e42b0c411e5e80a4ede88889935553d7c425c143d58c610dac0).
Audio sourcefinal d6d476419a177ef096aa51ad3b78304b51589d1b954a2b78cd8034d6a71fcab4;
15857CPU=15856full+1prefix,4guards,0fail,663/663 instructionaddress observed.

- physical23A00C JMP A387: tile_scroll comparesnormalizedcameraX(8E FE/FF+2
 wrap,>>3) against93, cachesbeforechild evenifbusy. ThenY90>>3 vs92 similarly.
 9Cbit7:columnleft(A465 addsF8 low+carryhigh) elsecurrent(A3C9).
 9Cbit5:rowback(A51C) elsecurrent(A485). Columnbusy7E bit80,rowbusybit40.
 Both branchescopycamera into0C..0F beforebusyreturn.
- Fulltilecolumn: A604 computesY=(0F*2+0D)&FF andreadsdescriptor($A8),Y;
 store1A Y, directA61F loadsprimarytilepointer0/1, fixedmetaptr2/3=F477,
 mapsE1/E000=data.chunk_selectors[id]. Neighbor descriptor Y+2 store10.
 A93Fbuildsunitlookup0680..06BF usingAB26 worldtile18/19; scan19..0, lower
 duplicateunitwins becauseoverwriting. m19incrementspermetatile,extra+1 at
 verticalchunkseam(packedindex+10>=F0); nexttilechunk10 load, index&0F.
 16metatiles. _tilecol: unitat0680[19]!=FF ->sharedunit_tiles(slot),ptr8/9=1B0
 elseterraintile*4+fixedmetaptr2/3. Choosecolumnquadby0Cbit8 (offset0/2 or1/3).
 Firstmetatile skipsfirsttileif0Ebit8. Write0142+X. Endaddrheader0140/141 via
 A89A, 7E|80. A89A alwaysX20 bothbranches, Y0, C/V0 afterhighADC.
- Fulltilerow: A604 primary,neighborY+1 store10,A961unitlookupbyY;17metatiles.
 Startpackedtileindex=(0E&F0)+(0C>>4). x++ each, nibbleF seamloadneighbor and
 packedidx&F0. Choosequadrowby0Ebit8 (offset0/1 or2/3), first skipif0Cbit8.
 Write0166+X. Endheader0164/165 viaA89A,7E|40. Do not fabricatetail tiles.
- A89Aheader:ptrtarget=0140/0164;high=20 regardless0Dparity;low=0C>>3;
 0F=((0E&F8)*4)>>8, addlowpartthenhigh20+0F, carryfromlowignoredbyCLC.
- A51Crowback:0F=91+1;low=90+F0. Ifcarry0 low-=10 and0F--; store0E.
- Attribute_scrollA00F JMPAB53: ((8E-6)&FF)>>3 vs95;updatecacheandcolumn
 THENimmediateRTS, neverrowthatcall. Ifunchanged:90>>4 vs94,updateandrow.
 9Cbit6 choosescolumncurrentAB94 vsrightAD69;9Cbit4 choosesrowADA9 vsAEB5.
 No7Ebusycheck forattributes. OR7E20(column)/10(row),notack/consume.
- AttrcolumnAB94 copiescamera0C..0F, neighbor1C..1F with1D++ (rightchunk).
 AD69 swapswhichcameraXhighis+1. A604primary/A610neighbor getdescriptorY.
 AEF3 loadsattrprimarypointer0/1 ANDmapsE1/E000;AF0C loadssecondary10/11
 withoutmapping. Neighbordesc+2 stored0A/1A, nextverticalseamindex+8>=40:
 primaryAEF3(0A), secondaryAF0C(1A), index&7. Initialindex=(0C>>5)+(0E&E0)>>2.
 AFF9 builds4unitcolumns in0680/6A0/6C0/6E0 usingB08F anddescending20slots.
 for8+(0Ebit10) attributes:readbytesprimary->02,secondary->03;AF1B overlays
 unitpalette2 pairs,17/19 +=2, AC80 combinesseams; buffer018A+X exceptlast
 ninth maymergehalfintoFIRST018A. Header0188/189 viaA8D3 then7E|20.
- AF1B computes((0C+8)&10):iftrue AF30(primary02) ANDAF71(secondary03),
 elseonlyAF30. AF30 uses0680/6A0 current19/+1 quadrants; AF71uses6C0/6E0
 anddecrements17 evenwhennooverlays. Eachpresentbytehasbit7clear (notIDsFF).
- AC80 columnmerge:reverse9Cbit6 andx0Cbit10 determinewhetherprimaryalone,
 (02&CC)|(03&33), or(02&33)|(03&CC). Specialiteration06==8 reuses018A,
 keepingtopF0 andmergeslowquad02lowF/02lowC+03low3/02low3+03lowC asoriginal.
 Must preservetemporary02 masks and oldfirstbyte, not reorderbuffer writes.
- AttrrowADA9 cameraXword+4,Ysame; AEB5 X+4,Ylow+ A0; ifcarryORlow>=F0
 low+=10,0F=91+1 else0F=91. PrimaryA604/AEF3 neighborY+1->0A. indexsame,
 B055builds2unitrows0680/6A0 viaB08F;8+(0Cbit10) attrs, AF B5 overlays02,
 increments16/18 by2; AE58 copybyteorlastninthreusesFIRST019E maskedCC plus
 (02&33). horizontalchunkseamlow3==7 loadsnext0A andpackedidx&F8.
 Header019C/19D A8D3 then7E|10.
- B08F:18=((word0C>>5)&15)*2,19=((word0E>>5)&15)*2,
 16=((word1C>>5)&15)*2,17=SAME0Ewordtransform (not1E).
- A8D3 attrheader:target188/19C, high23 regardless0Dparity, low=C0+(0C>>5)
 +(0E&E0)>>2;Y1, X23, C/V0, finalA lowaddress thenpublicA=7E|flag.
- ProposedAPI ScrollGraphicsServices(memory,GraphicsData.from_rom(rom)),
 tile_scroll(registers=None),attribute_scroll(registers=None). Return source
 AXYP atbodyendifverified; actualcallerRTS/freeCPUstack outsidecontract.
 Queued fulltile finalX20/Y0/CV0; queuedattrX23/Y1/CV0. Topnochange endsCMP
 equality(C1/Z1/N0), propagatesV. BusybrancheskeepactualASL/ADCflag semantics.
 AllnonstackRAMPLUS0140..01B3 are data tocompare. Portswrites onlyE000.
