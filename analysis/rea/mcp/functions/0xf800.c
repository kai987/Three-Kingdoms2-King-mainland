
/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 nmi(undefined1 param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  undefined1 uVar2;
  char cVar3;
  undefined1 uStack0000;
  undefined2 uStack_4;
  undefined1 uStack_2;
  undefined1 uStack_1;
  
  DAT_5000 = DAT_0068;
  DAT_0062 = DAT_0069;
  DAT_5800 = DAT_0069;
  DAT_0060 = DAT_0061;
  DAT_c000 = 0xe0;
  DAT_c800 = 0xe1;
  DAT_d000 = 0xe0;
  DAT_d800 = 0xe1;
  uStack0000 = param_1;
  uStack_2 = param_3;
  uStack_1 = param_2;
  if (DAT_007b != '\0') {
    uVar2 = FUN_fad5();
    return uVar2;
  }
  reset_dispatch = DAT_00e1;
  bRAMe800 = DAT_00e2 | 0xc0;
                    /* WARNING (jumptable): Read-only address (RAM,0xe800) is written */
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  uRAMf000 = DAT_00e3;
                    /* WARNING (jumptable): Read-only address (RAM,0xf000) is written */
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  DAT_2003 = 0;
  DAT_007b = '\x01';
  DAT_4014 = 2;
  DAT_2001 = DAT_008c;
  DAT_007c = 0;
  bVar1 = (DAT_0078 & 0xf) << 1;
  _DAT_0000 = CONCAT11((&BYTE_f87c)[bVar1],(&switchD_f878::switchdataD_f87b)[bVar1]);
  switch(DAT_0078 & 0xf) {
  default:
    uStack_4 = 0xfa9a;
    FUN_fb0b();
    uStack_4 = 0xfa9d;
    FUN_f206();
    uStack_4 = 0xfaa0;
    FUN_e6c6();
    uStack_4 = 0xfaa3;
    FUN_ff62();
    uStack_4 = 0xfaa6;
    FUN_fb28();
    break;
  case 2:
    uStack_4 = 0xf8b8;
    FUN_ee53();
    uStack_4 = 0xf8bb;
    FUN_f206();
    uStack_4 = 0xf8be;
    FUN_fb0b();
    uStack_4 = 0xf8c1;
    FUN_ec67();
    uStack_4 = 0xf8c4;
    FUN_e6c6();
    uStack_4 = 0xf8c9;
    FUN_f237(0x2e);
    uStack_4 = 0xf8cc;
    func_0xa003();
    DAT_00a5 = 0x4c;
    nmi = (code)0x4c;
    uStack_4 = 0xf8d6;
    FUN_ff9b();
    uStack_4 = 0xf8d9;
    FUN_faa9();
    uStack_4 = 0xf8de;
    FUN_f237(0x3d);
    uStack_4 = 0xf8e1;
    func_0xa003();
    uStack_4 = 0xf8e4;
    func_0xa009();
    uStack_4 = 0xf8e7;
    func_0xa00f();
    uStack_4 = 0xf8ea;
    func_0xa03f();
    uStack_4 = 0xf8ef;
    FUN_f237(0x3b);
    uStack_4 = 0xf8f2;
    func_0xa000();
    uStack_4 = 0xf8f5;
    FUN_fabf();
    uStack_4 = 0xf8f8;
    FUN_e830();
    uStack_4 = 0xf8fb;
    FUN_fb28();
    break;
  case 3:
    uStack_4 = 0xf901;
    FUN_ee53();
    uStack_4 = 0xf904;
    FUN_f206();
    uStack_4 = 0xf907;
    FUN_fb0b();
    DAT_007c = 0;
    uStack_4 = 0xf90e;
    FUN_ec67();
    uStack_4 = 0xf911;
    FUN_e6c6();
    uStack_4 = 0xf916;
    FUN_f237(0x2e);
    uStack_4 = 0xf919;
    func_0xa003();
    DAT_00a5 = 0x4c;
    nmi = (code)0x4c;
    uStack_4 = 0xf923;
    FUN_ff62();
    if ((DAT_0500 < 0xc) && (DAT_008f == '\0')) {
      uStack_4 = 0xf932;
      FUN_f077();
      uStack_4 = 0xf937;
      FUN_f237(0x37);
      uStack_4 = 0xf93a;
      func_0xa00c();
      uStack_4 = 0xf93d;
      func_0xa00f();
    }
    uStack_4 = 0xf940;
    FUN_faa9();
    uStack_4 = 0xf945;
    FUN_f237(0x39);
    uStack_4 = 0xf948;
    func_0xa00f();
    uStack_4 = 0xf94d;
    FUN_f237(0x2c);
    uStack_4 = 0xf950;
    func_0xa000();
    uStack_4 = 0xf955;
    FUN_f237(0x3d);
    uStack_4 = 0xf958;
    func_0xa003();
    uStack_4 = 0xf95b;
    FUN_fabf();
    uStack_4 = 0xf95e;
    FUN_e830();
    DAT_009d = DAT_009c;
    uStack_4 = 0xf967;
    FUN_fb28();
    break;
  case 4:
    uStack_4 = 0xf96d;
    FUN_ee53();
    uStack_4 = 0xf970;
    FUN_f206();
    uStack_4 = 0xf973;
    FUN_fb0b();
    DAT_007c = 0;
    uStack_4 = 0xf97a;
    FUN_ec67();
    uStack_4 = 0xf97d;
    FUN_e6c6();
    uStack_4 = 0xf982;
    FUN_f237(0x2e);
    uStack_4 = 0xf985;
    func_0xa003();
    DAT_00a5 = 0x4c;
    nmi = (code)0x4c;
    uStack_4 = 0xf98f;
    FUN_ff62();
    uStack_4 = 0xf994;
    FUN_f237(0x2e);
    uStack_4 = 0xf997;
    func_0xa000();
    uStack_4 = 0xf99a;
    FUN_e830();
    uStack_4 = 0xf99d;
    FUN_fb28();
    break;
  case 5:
    uStack_4 = 0xf9a3;
    FUN_ee53();
    uStack_4 = 0xf9a6;
    FUN_f206();
    uStack_4 = 0xf9a9;
    FUN_fb0b();
    DAT_007c = 0;
    uStack_4 = 0xf9b0;
    FUN_ec67();
    uStack_4 = 0xf9b3;
    FUN_e6c6();
    uStack_4 = 0xf9b8;
    FUN_f237(0x2e);
    uStack_4 = 0xf9bb;
    func_0xa003();
    DAT_00a5 = 0x4c;
    nmi = (code)0x4c;
    uStack_4 = 0xf9c5;
    FUN_ff62();
    uStack_4 = 0xf9c8;
    FUN_faa9();
    uStack_4 = 0xf9cd;
    FUN_f237(0x37);
    uStack_4 = 0xf9d0;
    func_0xa01b();
    uStack_4 = 0xf9d5;
    FUN_f237(0x3d);
    uStack_4 = 0xf9d8;
    func_0xa003();
    uStack_4 = 0xf9db;
    FUN_fabf();
    uStack_4 = 0xf9de;
    FUN_e830();
    uStack_4 = 0xf9e1;
    FUN_fb28();
    break;
  case 6:
    uStack_4 = 0xf9e7;
    FUN_ee53();
    uStack_4 = 0xf9ea;
    FUN_f206();
    uStack_4 = 0xf9ed;
    FUN_fb0b();
    uStack_4 = 0xf9f0;
    FUN_e6c6();
    uStack_4 = 0xf9f5;
    FUN_f237(0x2e);
    uStack_4 = 0xf9f8;
    func_0xa003();
    DAT_00a5 = 0x4c;
    nmi = (code)0x4c;
    uStack_4 = 0xfa04;
    FUN_f237(0x2a);
    uStack_4 = 0xfa07;
    func_0xa003();
    uStack_4 = 0xfa0a;
    FUN_ff62();
    uStack_4 = 0xfa0d;
    FUN_e830();
    uStack_4 = 0xfa10;
    FUN_fb28();
    break;
  case 7:
    uStack_4 = 0xfa16;
    FUN_ee53();
    uStack_4 = 0xfa19;
    FUN_f206();
    uStack_4 = 0xfa1c;
    FUN_fb0b();
    uStack_4 = 0xfa1f;
    FUN_ec67();
    uStack_4 = 0xfa22;
    FUN_e6c6();
    uStack_4 = 0xfa27;
    FUN_f237(0x2e);
    uStack_4 = 0xfa2a;
    func_0xa003();
    uStack_4 = 0xfa2d;
    FUN_ff9b();
    DAT_00a5 = 0x4c;
    nmi = (code)0x4c;
    uStack_4 = 0xfa37;
    FUN_faa9();
    uStack_4 = 0xfa3c;
    FUN_f237(0x3d);
    uStack_4 = 0xfa3f;
    func_0xa003();
    uStack_4 = 0xfa44;
    FUN_f237(0x28);
    uStack_4 = 0xfa47;
    func_0xa024();
    uStack_4 = 0xfa4a;
    FUN_fabf();
    uStack_4 = 0xfa4d;
    FUN_e830();
    uStack_4 = 0xfa50;
    FUN_fb28();
    break;
  case 8:
    uStack_4 = 0xfa56;
    FUN_ee53();
    uStack_4 = 0xfa59;
    FUN_f206();
    uStack_4 = 0xfa5c;
    FUN_fb0b();
    uStack_4 = 0xfa5f;
    FUN_ec67();
    uStack_4 = 0xfa64;
    FUN_f237(0x2e);
    uStack_4 = 0xfa67;
    func_0xa003();
    DAT_0081 = 0;
    uStack_4 = 0xfa70;
    FUN_f237(0x3d);
    uStack_4 = 0xfa73;
    func_0xa003();
    DAT_00a5 = 0x4c;
    nmi = (code)0x4c;
    uStack_4 = 0xfa7d;
    FUN_e6c6();
    uStack_4 = 0xfa80;
    FUN_faa9();
    uStack_4 = 0xfa85;
    FUN_f237(0x37);
    uStack_4 = 0xfa88;
    func_0xa01e();
    uStack_4 = 0xfa8b;
    FUN_fabf();
    uStack_4 = 0xfa8e;
    FUN_ff62();
    uStack_4 = 0xfa91;
    FUN_e830();
    uStack_4 = 0xfa94;
    FUN_fb28();
    break;
  case 9:
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  case 10:
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  case 0xb:
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  case 0xc:
    cVar3 = '\x02';
    do {
      do {
      } while (-1 < DAT_2002);
      do {
      } while (DAT_2002 < '\0');
      cVar3 = cVar3 + -1;
    } while (-1 < cVar3);
    DAT_4010 = 0;
    DAT_4015 = 0xf;
    DAT_4017 = 0xc0;
    DAT_2000 = 0;
    DAT_2001 = 0;
    cVar3 = '\x04';
    do {
      do {
      } while (-1 < DAT_2002);
      do {
      } while (DAT_2002 < '\0');
      cVar3 = cVar3 + -1;
    } while (-1 < cVar3);
    _DAT_0000 = CONCAT11(4,(&switchD_f878::switchdataD_f87b)[bVar1]);
    _DAT_0000 = (uint3)_DAT_0000;
    DAT_5800 = DAT_0062;
    do {
      do {
        *_DAT_0001 = 0;
        cVar3 = DAT_0001 + '\x01';
        _DAT_0000 = CONCAT11(cVar3,DAT_0000);
      } while (cVar3 != '\0');
      bVar1 = DAT_0002 + 1;
      _DAT_0000 = CONCAT12(bVar1,_DAT_0000);
    } while (bVar1 < 8);
    *(undefined2 *)(CONCAT11((char)((ushort)((short)&uStack_4 + 1) >> 8),0xff) + -1) = 0xe061;
    FUN_f3bd();
    DAT_007a = 0;
    DAT_004e = (code *)CONCAT11(DAT_e07d,DAT_e07c);
                    /* WARNING: Could not recover jumptable at 0xe079. Too many branches */
                    /* WARNING: Treating indirect jump as call */
    uVar2 = (*DAT_004e)();
    return uVar2;
  case 0xd:
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  case 0xe:
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
  DAT_007b = DAT_007b + -1;
  reset_dispatch = cRAM00de;
                    /* WARNING (jumptable): Read-only address (RAM,0xe800) is written */
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  bRAMe800 = DAT_00df | 0xc0;
                    /* WARNING (jumptable): Read-only address (RAM,0xf000) is written */
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  uRAMf000 = DAT_00e0;
  DAT_0050 = DAT_0050 + '\x01';
  cRAM0052 = cRAM0052 + '\x01';
  cRAM0054 = cRAM0054 + '\x01';
  cRAM0055 = cRAM0055 + '\x01';
  DAT_005e = DAT_005e + '\x01';
  if (DAT_005e == '\0') {
    DAT_005f = DAT_005f + '\x01';
  }
  return uStack0000;
}

