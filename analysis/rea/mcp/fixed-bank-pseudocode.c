// Ghidra-generated 6502 pseudocode. Not original source or compilable game code.

/* 0xe000 reset_dispatch */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void reset_dispatch(void)

{
  byte bVar1;
  char cVar2;
  
  cVar2 = '\x02';
  do {
    do {
    } while (-1 < DAT_2002);
    do {
    } while (DAT_2002 < '\0');
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  DAT_4010 = 0;
  DAT_4015 = 0xf;
  DAT_4017 = 0xc0;
  DAT_2000 = 0;
  DAT_2001 = 0;
  cVar2 = '\x04';
  do {
    do {
    } while (-1 < DAT_2002);
    do {
    } while (DAT_2002 < '\0');
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  _DAT_0001 = &DAT_0004;
  do {
    do {
      *_DAT_0001 = 0;
      cVar2 = DAT_0001 + '\x01';
      _DAT_0001 = (undefined1 *)CONCAT11(DAT_0002,cVar2);
    } while (cVar2 != '\0');
    bVar1 = DAT_0002 + 1;
    _DAT_0001 = (undefined1 *)((ushort)bVar1 << 8);
  } while (bVar1 < 8);
  *(undefined2 *)(CONCAT11((char)((ushort)&stack0x0000 >> 8),0xff) + -1) = 0xe061;
  FUN_f3bd();
  DAT_007a = 0;
  DAT_004e = (code *)CONCAT11(DAT_e07d,DAT_e07c);
                    /* WARNING: Could not recover jumptable at 0xe079. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*DAT_004e)();
  return;
}



/* 0xe09a state_or_entry_e09a */

void state_or_entry_e09a(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xe0;
  FUN_e768();
  uStack0000 = 0xe0;
  DAT_2001 = FUN_e74d();
  uStack0000 = 0xe0;
  FUN_e57f();
  bVar1 = 0x1f;
  do {
    *(undefined1 *)(bVar1 + 0x100) = 0xf;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  do {
  } while (-1 < DAT_2002);
  DAT_00a5 = 0x4c;
  nmi = (code)0x4c;
  uStack0000 = 0xe0;
  FUN_e51f(0);
  DAT_008b = 0x10;
  DAT_2000 = 0x10;
  DAT_008c = 0;
  DAT_2001 = 0;
  DAT_007a = 9;
  DAT_004e = (code *)CONCAT11(uRAMe08f,uRAMe08e);
                    /* WARNING: Could not recover jumptable at 0xe079. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*DAT_004e)();
  return;
}



/* 0xe0da state_or_entry_e0da */

/* WARNING: Control flow encountered bad instruction data */

undefined1 state_or_entry_e0da(void)

{
  byte bVar1;
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
code_r0xe0da:
  uStack0000 = 0xe0;
  FUN_e4da();
  DAT_0078 = 2;
  uStack0000 = 0xe0;
  FUN_e370(0);
  uStack0000 = 0xe0;
  select_data_bank(0x30);
  DAT_000a = 0;
  DAT_000b = 0x80;
  DAT_0001 = 0x20;
  DAT_0000 = 0;
  DAT_0004 = 0;
  DAT_0005 = 0;
  DAT_0006 = 0;
  DAT_0007 = 4;
  uStack0000 = 0xe1;
  FUN_f237(0x37);
  uStack0000 = 0xe1;
  func_0xa003();
  uStack0000 = 0xe1;
  FUN_f237(0x3d);
  DAT_0000 = '\0';
  uStack0000 = 0xe1;
  func_0xa015();
  uStack0000 = 0xe1;
  FUN_eaf7();
  if (DAT_0400 != '\r') {
    DAT_6f8b = 0xff;
  }
  uStack0000 = 0xe1;
  FUN_f237(0x3d);
  uStack0000 = 0xe1;
  func_0xa036();
  uStack0000 = 0xe1;
  FUN_ecbf();
  uStack0000 = 0xe1;
  FUN_f237(0x3d);
  uStack0000 = 0xe1;
  func_0xa045(0);
  DAT_0098 = 0xa0;
  DAT_0420 = 0;
  DAT_04e0 = 0;
  DAT_04e1 = 0;
  DAT_04e2 = 0;
  DAT_04e3 = 0;
  DAT_6f41 = 0xf0;
  DAT_6f3f = 0x80;
  uStack0000 = 0xe1;
  FUN_e51f(0);
  DAT_007a = DAT_007a + 1;
  uStack0000 = 0xe1;
  FUN_e673(0x81);
  uStack0000 = 0xe1;
  FUN_e749();
  uStack0000 = 0xe1;
  FUN_e753();
  do {
    bVar1 = (DAT_007a & 0x1f) << 1;
    DAT_004e = CONCAT11((&DAT_e07d)[bVar1],(&DAT_e07c)[bVar1]);
    switch(DAT_007a & 0x1f) {
    case 0:
      uStack0000 = 0xe0;
      FUN_e768();
      uStack0000 = 0xe0;
      DAT_2001 = FUN_e74d();
      uStack0000 = 0xe0;
      FUN_e57f();
      bVar1 = 0x1f;
      do {
        *(undefined1 *)(bVar1 + 0x100) = 0xf;
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      do {
      } while (-1 < DAT_2002);
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      uStack0000 = 0xe0;
      FUN_e51f(0);
      DAT_008b = 0x10;
      DAT_2000 = 0x10;
      DAT_008c = 0;
      DAT_2001 = 0;
      DAT_007a = 9;
      break;
    case 1:
      goto code_r0xe0da;
    case 2:
      uStack0000 = 0xe1;
      FUN_e87a();
      uStack0000 = 0xe1;
      FUN_f24b(0x2a);
      uStack0000 = 0xe1;
      func_0xa000();
      break;
    case 3:
      uStack0000 = 0xe1;
      FUN_e4da();
      DAT_0078 = 3;
      uStack0000 = 0xe1;
      FUN_e370(1);
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa027();
      if (DAT_0500 == '\v') {
        uStack0000 = 0xe1;
        FUN_f237(0x2c);
        uStack0000 = 0xe1;
        func_0xa006();
      }
      else {
        uStack0000 = 0xe1;
        FUN_f237(0x28);
        uStack0000 = 0xe1;
        func_0xa003();
      }
      DAT_0090 = DAT_0510;
      DAT_0091 = DAT_0511;
      DAT_008e = DAT_0512;
      DAT_008f = DAT_0513;
      DAT_0518 = 0xff;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa009();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\x01';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      DAT_0508 = 0;
      DAT_0068 = 0x70;
      DAT_0069 = 0xaf;
      uStack0000 = 0xe2;
      FUN_e51f(1);
      DAT_0097 = 1;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_0061 = 5;
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e673(0x1d);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 4:
      uStack0000 = 0xe2;
      FUN_e87a();
      uStack0000 = 0xe2;
      FUN_f24b(0x28);
      uStack0000 = 0xe2;
      func_0xa000();
      break;
    case 5:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 4;
      uStack0000 = 0xe2;
      FUN_e370(DAT_0544 + '\x02');
      uStack0000 = 0xe2;
      FUN_e51f(2);
      uStack0000 = 0xe2;
      FUN_f237(0x37);
      uStack0000 = 0xe2;
      func_0xa024();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      DAT_0000 = DAT_0544 + '\x02';
      uStack0000 = 0xe2;
      func_0xa015();
      DAT_0107 = (&DAT_e2de)[DAT_0563];
      DAT_010f = (&DAT_e2de)[DAT_0562];
      uStack0000 = 0xe2;
      DAT_0113 = DAT_0107;
      DAT_0117 = DAT_010f;
      FUN_eaf7();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      uStack0000 = 0xe2;
      func_0xa045(1);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e683(0xd);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 6:
      uStack0000 = 0xe2;
      FUN_e87a();
      break;
    case 7:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 5;
      uStack0000 = 0xe2;
      FUN_e370(10);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x84;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\n';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      if (DAT_04ab == '\x01') {
        DAT_0106 = 0;
        DAT_0116 = 0;
      }
      if (DAT_04ac == '\x01') {
        DAT_010e = 0;
        DAT_011a = 0;
      }
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(2);
      uStack0000 = 0xe3;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e67b(0x12);
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    case 8:
      uStack0000 = 0xe3;
      FUN_e87a();
      break;
    case 9:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 6;
      uStack0000 = 0xe3;
      FUN_e370(0xb);
      uStack0000 = 0xe3;
      select_data_bank(0x35);
      DAT_000a = 0x90;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\v';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(3);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe3;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    default:
      break;
    case 0xb:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 7;
      uStack0000 = 0xe3;
      FUN_e370(0xc);
      uStack0000 = 0xe4;
      select_data_bank(0x32);
      DAT_000a = 0xe3;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa018();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\f';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_ecbf();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(4);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe4;
      FUN_e683(8);
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xd:
      uStack0000 = 0xe4;
      FUN_e4da();
      DAT_0078 = 8;
      uStack0000 = 0xe4;
      FUN_e370(0xd);
      uStack0000 = 0xe4;
      select_data_bank(0x36);
      DAT_000a = 0x92;
      DAT_000b = 0x9b;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\r';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(5);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      if (DAT_0541 == '\0') {
        uStack0000 = 0xe4;
        FUN_e673(0x98);
      }
      else {
        uStack0000 = 0xe4;
        FUN_e67b(0xaa);
      }
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x10:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x11:
      DAT_008c = 0;
      return 0;
    case 0x12:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x13:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x14:
      uStack0000 = 0xe5;
      FUN_e673(0);
      uStack0000 = 0xe5;
      FUN_e590();
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      return 0x4c;
    case 0x15:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x16:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x17:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x18:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x19:
      DAT_007b = DAT_007b + -1;
      reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
      bRAMe800 = DAT_00df | 0xc0;
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
      return in_stack_00000003;
    case 0x1a:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1b:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1c:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1d:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1e:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1f:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  } while( true );
}



/* 0xe17d state_or_entry_e17d */

/* WARNING: Control flow encountered bad instruction data */

undefined1 state_or_entry_e17d(void)

{
  byte bVar1;
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
code_r0xe17d:
  uStack0000 = 0xe1;
  FUN_e87a();
  uStack0000 = 0xe1;
  FUN_f24b(0x2a);
  uStack0000 = 0xe1;
  func_0xa000();
  do {
    bVar1 = (DAT_007a & 0x1f) << 1;
    DAT_004e = CONCAT11((&DAT_e07d)[bVar1],(&DAT_e07c)[bVar1]);
    switch(DAT_007a & 0x1f) {
    case 0:
      uStack0000 = 0xe0;
      FUN_e768();
      uStack0000 = 0xe0;
      DAT_2001 = FUN_e74d();
      uStack0000 = 0xe0;
      FUN_e57f();
      bVar1 = 0x1f;
      do {
        *(undefined1 *)(bVar1 + 0x100) = 0xf;
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      do {
      } while (-1 < DAT_2002);
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      uStack0000 = 0xe0;
      FUN_e51f(0);
      DAT_008b = 0x10;
      DAT_2000 = 0x10;
      DAT_008c = 0;
      DAT_2001 = 0;
      DAT_007a = 9;
      break;
    case 1:
      uStack0000 = 0xe0;
      FUN_e4da();
      DAT_0078 = 2;
      uStack0000 = 0xe0;
      FUN_e370(0);
      uStack0000 = 0xe0;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x80;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa003();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\0';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      if (DAT_0400 != '\r') {
        DAT_6f8b = 0xff;
      }
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa036();
      uStack0000 = 0xe1;
      FUN_ecbf();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa045(0);
      DAT_0098 = 0xa0;
      DAT_0420 = 0;
      DAT_04e0 = 0;
      DAT_04e1 = 0;
      DAT_04e2 = 0;
      DAT_04e3 = 0;
      DAT_6f41 = 0xf0;
      DAT_6f3f = 0x80;
      uStack0000 = 0xe1;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe1;
      FUN_e673(0x81);
      uStack0000 = 0xe1;
      FUN_e749();
      uStack0000 = 0xe1;
      FUN_e753();
      break;
    case 2:
      goto code_r0xe17d;
    case 3:
      uStack0000 = 0xe1;
      FUN_e4da();
      DAT_0078 = 3;
      uStack0000 = 0xe1;
      FUN_e370(1);
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa027();
      if (DAT_0500 == '\v') {
        uStack0000 = 0xe1;
        FUN_f237(0x2c);
        uStack0000 = 0xe1;
        func_0xa006();
      }
      else {
        uStack0000 = 0xe1;
        FUN_f237(0x28);
        uStack0000 = 0xe1;
        func_0xa003();
      }
      DAT_0090 = DAT_0510;
      DAT_0091 = DAT_0511;
      DAT_008e = DAT_0512;
      DAT_008f = DAT_0513;
      DAT_0518 = 0xff;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa009();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\x01';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      DAT_0508 = 0;
      DAT_0068 = 0x70;
      DAT_0069 = 0xaf;
      uStack0000 = 0xe2;
      FUN_e51f(1);
      DAT_0097 = 1;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_0061 = 5;
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e673(0x1d);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 4:
      uStack0000 = 0xe2;
      FUN_e87a();
      uStack0000 = 0xe2;
      FUN_f24b(0x28);
      uStack0000 = 0xe2;
      func_0xa000();
      break;
    case 5:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 4;
      uStack0000 = 0xe2;
      FUN_e370(DAT_0544 + '\x02');
      uStack0000 = 0xe2;
      FUN_e51f(2);
      uStack0000 = 0xe2;
      FUN_f237(0x37);
      uStack0000 = 0xe2;
      func_0xa024();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      DAT_0000 = DAT_0544 + '\x02';
      uStack0000 = 0xe2;
      func_0xa015();
      DAT_0107 = (&DAT_e2de)[DAT_0563];
      DAT_010f = (&DAT_e2de)[DAT_0562];
      uStack0000 = 0xe2;
      DAT_0113 = DAT_0107;
      DAT_0117 = DAT_010f;
      FUN_eaf7();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      uStack0000 = 0xe2;
      func_0xa045(1);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e683(0xd);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 6:
      uStack0000 = 0xe2;
      FUN_e87a();
      break;
    case 7:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 5;
      uStack0000 = 0xe2;
      FUN_e370(10);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x84;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\n';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      if (DAT_04ab == '\x01') {
        DAT_0106 = 0;
        DAT_0116 = 0;
      }
      if (DAT_04ac == '\x01') {
        DAT_010e = 0;
        DAT_011a = 0;
      }
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(2);
      uStack0000 = 0xe3;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e67b(0x12);
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    case 8:
      uStack0000 = 0xe3;
      FUN_e87a();
      break;
    case 9:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 6;
      uStack0000 = 0xe3;
      FUN_e370(0xb);
      uStack0000 = 0xe3;
      select_data_bank(0x35);
      DAT_000a = 0x90;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\v';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(3);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe3;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    default:
      break;
    case 0xb:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 7;
      uStack0000 = 0xe3;
      FUN_e370(0xc);
      uStack0000 = 0xe4;
      select_data_bank(0x32);
      DAT_000a = 0xe3;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa018();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\f';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_ecbf();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(4);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe4;
      FUN_e683(8);
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xd:
      uStack0000 = 0xe4;
      FUN_e4da();
      DAT_0078 = 8;
      uStack0000 = 0xe4;
      FUN_e370(0xd);
      uStack0000 = 0xe4;
      select_data_bank(0x36);
      DAT_000a = 0x92;
      DAT_000b = 0x9b;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\r';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(5);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      if (DAT_0541 == '\0') {
        uStack0000 = 0xe4;
        FUN_e673(0x98);
      }
      else {
        uStack0000 = 0xe4;
        FUN_e67b(0xaa);
      }
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x10:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x11:
      DAT_008c = 0;
      return 0;
    case 0x12:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x13:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x14:
      uStack0000 = 0xe5;
      FUN_e673(0);
      uStack0000 = 0xe5;
      FUN_e590();
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      return 0x4c;
    case 0x15:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x16:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x17:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x18:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x19:
      DAT_007b = DAT_007b + -1;
      reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
      bRAMe800 = DAT_00df | 0xc0;
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
      return in_stack_00000003;
    case 0x1a:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1b:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1c:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1d:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1e:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1f:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  } while( true );
}



/* 0xe18b state_or_entry_e18b */

/* WARNING: Control flow encountered bad instruction data */

undefined1 state_or_entry_e18b(void)

{
  byte bVar1;
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
code_r0xe18b:
  uStack0000 = 0xe1;
  FUN_e4da();
  DAT_0078 = 3;
  uStack0000 = 0xe1;
  FUN_e370(1);
  uStack0000 = 0xe1;
  FUN_f237(0x37);
  uStack0000 = 0xe1;
  func_0xa027();
  if (DAT_0500 == '\v') {
    uStack0000 = 0xe1;
    FUN_f237(0x2c);
    uStack0000 = 0xe1;
    func_0xa006();
  }
  else {
    uStack0000 = 0xe1;
    FUN_f237(0x28);
    uStack0000 = 0xe1;
    func_0xa003();
  }
  DAT_0090 = DAT_0510;
  DAT_0091 = DAT_0511;
  DAT_008e = DAT_0512;
  DAT_008f = DAT_0513;
  DAT_0518 = 0xff;
  uStack0000 = 0xe1;
  FUN_f237(0x37);
  uStack0000 = 0xe1;
  func_0xa009();
  uStack0000 = 0xe1;
  FUN_f237(0x3d);
  DAT_0000 = '\x01';
  uStack0000 = 0xe1;
  func_0xa015();
  uStack0000 = 0xe1;
  FUN_eaf7();
  DAT_0508 = 0;
  DAT_0068 = 0x70;
  DAT_0069 = 0xaf;
  uStack0000 = 0xe2;
  FUN_e51f(1);
  DAT_0097 = 1;
  uStack0000 = 0xe2;
  FUN_ecbf();
  DAT_0061 = 5;
  DAT_007a = DAT_007a + 1;
  uStack0000 = 0xe2;
  FUN_e673(0x1d);
  uStack0000 = 0xe2;
  FUN_e749();
  uStack0000 = 0xe2;
  FUN_e753();
  do {
    bVar1 = (DAT_007a & 0x1f) << 1;
    DAT_004e = CONCAT11((&DAT_e07d)[bVar1],(&DAT_e07c)[bVar1]);
    switch(DAT_007a & 0x1f) {
    case 0:
      uStack0000 = 0xe0;
      FUN_e768();
      uStack0000 = 0xe0;
      DAT_2001 = FUN_e74d();
      uStack0000 = 0xe0;
      FUN_e57f();
      bVar1 = 0x1f;
      do {
        *(undefined1 *)(bVar1 + 0x100) = 0xf;
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      do {
      } while (-1 < DAT_2002);
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      uStack0000 = 0xe0;
      FUN_e51f(0);
      DAT_008b = 0x10;
      DAT_2000 = 0x10;
      DAT_008c = 0;
      DAT_2001 = 0;
      DAT_007a = 9;
      break;
    case 1:
      uStack0000 = 0xe0;
      FUN_e4da();
      DAT_0078 = 2;
      uStack0000 = 0xe0;
      FUN_e370(0);
      uStack0000 = 0xe0;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x80;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa003();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\0';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      if (DAT_0400 != '\r') {
        DAT_6f8b = 0xff;
      }
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa036();
      uStack0000 = 0xe1;
      FUN_ecbf();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa045(0);
      DAT_0098 = 0xa0;
      DAT_0420 = 0;
      DAT_04e0 = 0;
      DAT_04e1 = 0;
      DAT_04e2 = 0;
      DAT_04e3 = 0;
      DAT_6f41 = 0xf0;
      DAT_6f3f = 0x80;
      uStack0000 = 0xe1;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe1;
      FUN_e673(0x81);
      uStack0000 = 0xe1;
      FUN_e749();
      uStack0000 = 0xe1;
      FUN_e753();
      break;
    case 2:
      uStack0000 = 0xe1;
      FUN_e87a();
      uStack0000 = 0xe1;
      FUN_f24b(0x2a);
      uStack0000 = 0xe1;
      func_0xa000();
      break;
    case 3:
      goto code_r0xe18b;
    case 4:
      uStack0000 = 0xe2;
      FUN_e87a();
      uStack0000 = 0xe2;
      FUN_f24b(0x28);
      uStack0000 = 0xe2;
      func_0xa000();
      break;
    case 5:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 4;
      uStack0000 = 0xe2;
      FUN_e370(DAT_0544 + '\x02');
      uStack0000 = 0xe2;
      FUN_e51f(2);
      uStack0000 = 0xe2;
      FUN_f237(0x37);
      uStack0000 = 0xe2;
      func_0xa024();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      DAT_0000 = DAT_0544 + '\x02';
      uStack0000 = 0xe2;
      func_0xa015();
      DAT_0107 = (&DAT_e2de)[DAT_0563];
      DAT_010f = (&DAT_e2de)[DAT_0562];
      uStack0000 = 0xe2;
      DAT_0113 = DAT_0107;
      DAT_0117 = DAT_010f;
      FUN_eaf7();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      uStack0000 = 0xe2;
      func_0xa045(1);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e683(0xd);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 6:
      uStack0000 = 0xe2;
      FUN_e87a();
      break;
    case 7:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 5;
      uStack0000 = 0xe2;
      FUN_e370(10);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x84;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\n';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      if (DAT_04ab == '\x01') {
        DAT_0106 = 0;
        DAT_0116 = 0;
      }
      if (DAT_04ac == '\x01') {
        DAT_010e = 0;
        DAT_011a = 0;
      }
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(2);
      uStack0000 = 0xe3;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e67b(0x12);
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    case 8:
      uStack0000 = 0xe3;
      FUN_e87a();
      break;
    case 9:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 6;
      uStack0000 = 0xe3;
      FUN_e370(0xb);
      uStack0000 = 0xe3;
      select_data_bank(0x35);
      DAT_000a = 0x90;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\v';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(3);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe3;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    default:
      break;
    case 0xb:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 7;
      uStack0000 = 0xe3;
      FUN_e370(0xc);
      uStack0000 = 0xe4;
      select_data_bank(0x32);
      DAT_000a = 0xe3;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa018();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\f';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_ecbf();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(4);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe4;
      FUN_e683(8);
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xd:
      uStack0000 = 0xe4;
      FUN_e4da();
      DAT_0078 = 8;
      uStack0000 = 0xe4;
      FUN_e370(0xd);
      uStack0000 = 0xe4;
      select_data_bank(0x36);
      DAT_000a = 0x92;
      DAT_000b = 0x9b;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\r';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(5);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      if (DAT_0541 == '\0') {
        uStack0000 = 0xe4;
        FUN_e673(0x98);
      }
      else {
        uStack0000 = 0xe4;
        FUN_e67b(0xaa);
      }
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x10:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x11:
      DAT_008c = 0;
      return 0;
    case 0x12:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x13:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x14:
      uStack0000 = 0xe5;
      FUN_e673(0);
      uStack0000 = 0xe5;
      FUN_e590();
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      return 0x4c;
    case 0x15:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x16:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x17:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x18:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x19:
      DAT_007b = DAT_007b + -1;
      reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
      bRAMe800 = DAT_00df | 0xc0;
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
      return in_stack_00000003;
    case 0x1a:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1b:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1c:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1d:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1e:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1f:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  } while( true );
}



/* 0xe221 state_or_entry_e221 */

/* WARNING: Control flow encountered bad instruction data */

undefined1 state_or_entry_e221(void)

{
  byte bVar1;
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
code_r0xe221:
  uStack0000 = 0xe2;
  FUN_e87a();
  uStack0000 = 0xe2;
  FUN_f24b(0x28);
  uStack0000 = 0xe2;
  func_0xa000();
  do {
    bVar1 = (DAT_007a & 0x1f) << 1;
    DAT_004e = CONCAT11((&DAT_e07d)[bVar1],(&DAT_e07c)[bVar1]);
    switch(DAT_007a & 0x1f) {
    case 0:
      uStack0000 = 0xe0;
      FUN_e768();
      uStack0000 = 0xe0;
      DAT_2001 = FUN_e74d();
      uStack0000 = 0xe0;
      FUN_e57f();
      bVar1 = 0x1f;
      do {
        *(undefined1 *)(bVar1 + 0x100) = 0xf;
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      do {
      } while (-1 < DAT_2002);
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      uStack0000 = 0xe0;
      FUN_e51f(0);
      DAT_008b = 0x10;
      DAT_2000 = 0x10;
      DAT_008c = 0;
      DAT_2001 = 0;
      DAT_007a = 9;
      break;
    case 1:
      uStack0000 = 0xe0;
      FUN_e4da();
      DAT_0078 = 2;
      uStack0000 = 0xe0;
      FUN_e370(0);
      uStack0000 = 0xe0;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x80;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa003();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\0';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      if (DAT_0400 != '\r') {
        DAT_6f8b = 0xff;
      }
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa036();
      uStack0000 = 0xe1;
      FUN_ecbf();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa045(0);
      DAT_0098 = 0xa0;
      DAT_0420 = 0;
      DAT_04e0 = 0;
      DAT_04e1 = 0;
      DAT_04e2 = 0;
      DAT_04e3 = 0;
      DAT_6f41 = 0xf0;
      DAT_6f3f = 0x80;
      uStack0000 = 0xe1;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe1;
      FUN_e673(0x81);
      uStack0000 = 0xe1;
      FUN_e749();
      uStack0000 = 0xe1;
      FUN_e753();
      break;
    case 2:
      uStack0000 = 0xe1;
      FUN_e87a();
      uStack0000 = 0xe1;
      FUN_f24b(0x2a);
      uStack0000 = 0xe1;
      func_0xa000();
      break;
    case 3:
      uStack0000 = 0xe1;
      FUN_e4da();
      DAT_0078 = 3;
      uStack0000 = 0xe1;
      FUN_e370(1);
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa027();
      if (DAT_0500 == '\v') {
        uStack0000 = 0xe1;
        FUN_f237(0x2c);
        uStack0000 = 0xe1;
        func_0xa006();
      }
      else {
        uStack0000 = 0xe1;
        FUN_f237(0x28);
        uStack0000 = 0xe1;
        func_0xa003();
      }
      DAT_0090 = DAT_0510;
      DAT_0091 = DAT_0511;
      DAT_008e = DAT_0512;
      DAT_008f = DAT_0513;
      DAT_0518 = 0xff;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa009();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\x01';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      DAT_0508 = 0;
      DAT_0068 = 0x70;
      DAT_0069 = 0xaf;
      uStack0000 = 0xe2;
      FUN_e51f(1);
      DAT_0097 = 1;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_0061 = 5;
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e673(0x1d);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 4:
      goto code_r0xe221;
    case 5:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 4;
      uStack0000 = 0xe2;
      FUN_e370(DAT_0544 + '\x02');
      uStack0000 = 0xe2;
      FUN_e51f(2);
      uStack0000 = 0xe2;
      FUN_f237(0x37);
      uStack0000 = 0xe2;
      func_0xa024();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      DAT_0000 = DAT_0544 + '\x02';
      uStack0000 = 0xe2;
      func_0xa015();
      DAT_0107 = (&DAT_e2de)[DAT_0563];
      DAT_010f = (&DAT_e2de)[DAT_0562];
      uStack0000 = 0xe2;
      DAT_0113 = DAT_0107;
      DAT_0117 = DAT_010f;
      FUN_eaf7();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      uStack0000 = 0xe2;
      func_0xa045(1);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e683(0xd);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 6:
      uStack0000 = 0xe2;
      FUN_e87a();
      break;
    case 7:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 5;
      uStack0000 = 0xe2;
      FUN_e370(10);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x84;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\n';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      if (DAT_04ab == '\x01') {
        DAT_0106 = 0;
        DAT_0116 = 0;
      }
      if (DAT_04ac == '\x01') {
        DAT_010e = 0;
        DAT_011a = 0;
      }
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(2);
      uStack0000 = 0xe3;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e67b(0x12);
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    case 8:
      uStack0000 = 0xe3;
      FUN_e87a();
      break;
    case 9:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 6;
      uStack0000 = 0xe3;
      FUN_e370(0xb);
      uStack0000 = 0xe3;
      select_data_bank(0x35);
      DAT_000a = 0x90;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\v';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(3);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe3;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    default:
      break;
    case 0xb:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 7;
      uStack0000 = 0xe3;
      FUN_e370(0xc);
      uStack0000 = 0xe4;
      select_data_bank(0x32);
      DAT_000a = 0xe3;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa018();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\f';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_ecbf();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(4);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe4;
      FUN_e683(8);
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xd:
      uStack0000 = 0xe4;
      FUN_e4da();
      DAT_0078 = 8;
      uStack0000 = 0xe4;
      FUN_e370(0xd);
      uStack0000 = 0xe4;
      select_data_bank(0x36);
      DAT_000a = 0x92;
      DAT_000b = 0x9b;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\r';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(5);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      if (DAT_0541 == '\0') {
        uStack0000 = 0xe4;
        FUN_e673(0x98);
      }
      else {
        uStack0000 = 0xe4;
        FUN_e67b(0xaa);
      }
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x10:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x11:
      DAT_008c = 0;
      return 0;
    case 0x12:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x13:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x14:
      uStack0000 = 0xe5;
      FUN_e673(0);
      uStack0000 = 0xe5;
      FUN_e590();
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      return 0x4c;
    case 0x15:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x16:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x17:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x18:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x19:
      DAT_007b = DAT_007b + -1;
      reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
      bRAMe800 = DAT_00df | 0xc0;
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
      return in_stack_00000003;
    case 0x1a:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1b:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1c:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1d:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1e:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1f:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  } while( true );
}



/* 0xe22f state_or_entry_e22f */

/* WARNING: Control flow encountered bad instruction data */

undefined1 state_or_entry_e22f(void)

{
  byte bVar1;
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
code_r0xe22f:
  uStack0000 = 0xe2;
  FUN_e4da();
  DAT_0078 = 4;
  uStack0000 = 0xe2;
  FUN_e370(DAT_0544 + '\x02');
  uStack0000 = 0xe2;
  FUN_e51f(2);
  uStack0000 = 0xe2;
  FUN_f237(0x37);
  uStack0000 = 0xe2;
  func_0xa024();
  uStack0000 = 0xe2;
  FUN_f237(0x3d);
  DAT_0000 = DAT_0544 + '\x02';
  uStack0000 = 0xe2;
  func_0xa015();
  DAT_0107 = (&DAT_e2de)[DAT_0563];
  DAT_010f = (&DAT_e2de)[DAT_0562];
  uStack0000 = 0xe2;
  DAT_0113 = DAT_0107;
  DAT_0117 = DAT_010f;
  FUN_eaf7();
  uStack0000 = 0xe2;
  FUN_f237(0x3d);
  uStack0000 = 0xe2;
  func_0xa045(1);
  DAT_0098 = 0xa0;
  uStack0000 = 0xe2;
  FUN_ecbf();
  DAT_007a = DAT_007a + 1;
  uStack0000 = 0xe2;
  FUN_e683(0xd);
  uStack0000 = 0xe2;
  FUN_e749();
  uStack0000 = 0xe2;
  FUN_e753();
  do {
    bVar1 = (DAT_007a & 0x1f) << 1;
    DAT_004e = CONCAT11((&DAT_e07d)[bVar1],(&DAT_e07c)[bVar1]);
    switch(DAT_007a & 0x1f) {
    case 0:
      uStack0000 = 0xe0;
      FUN_e768();
      uStack0000 = 0xe0;
      DAT_2001 = FUN_e74d();
      uStack0000 = 0xe0;
      FUN_e57f();
      bVar1 = 0x1f;
      do {
        *(undefined1 *)(bVar1 + 0x100) = 0xf;
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      do {
      } while (-1 < DAT_2002);
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      uStack0000 = 0xe0;
      FUN_e51f(0);
      DAT_008b = 0x10;
      DAT_2000 = 0x10;
      DAT_008c = 0;
      DAT_2001 = 0;
      DAT_007a = 9;
      break;
    case 1:
      uStack0000 = 0xe0;
      FUN_e4da();
      DAT_0078 = 2;
      uStack0000 = 0xe0;
      FUN_e370(0);
      uStack0000 = 0xe0;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x80;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa003();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\0';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      if (DAT_0400 != '\r') {
        DAT_6f8b = 0xff;
      }
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa036();
      uStack0000 = 0xe1;
      FUN_ecbf();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa045(0);
      DAT_0098 = 0xa0;
      DAT_0420 = 0;
      DAT_04e0 = 0;
      DAT_04e1 = 0;
      DAT_04e2 = 0;
      DAT_04e3 = 0;
      DAT_6f41 = 0xf0;
      DAT_6f3f = 0x80;
      uStack0000 = 0xe1;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe1;
      FUN_e673(0x81);
      uStack0000 = 0xe1;
      FUN_e749();
      uStack0000 = 0xe1;
      FUN_e753();
      break;
    case 2:
      uStack0000 = 0xe1;
      FUN_e87a();
      uStack0000 = 0xe1;
      FUN_f24b(0x2a);
      uStack0000 = 0xe1;
      func_0xa000();
      break;
    case 3:
      uStack0000 = 0xe1;
      FUN_e4da();
      DAT_0078 = 3;
      uStack0000 = 0xe1;
      FUN_e370(1);
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa027();
      if (DAT_0500 == '\v') {
        uStack0000 = 0xe1;
        FUN_f237(0x2c);
        uStack0000 = 0xe1;
        func_0xa006();
      }
      else {
        uStack0000 = 0xe1;
        FUN_f237(0x28);
        uStack0000 = 0xe1;
        func_0xa003();
      }
      DAT_0090 = DAT_0510;
      DAT_0091 = DAT_0511;
      DAT_008e = DAT_0512;
      DAT_008f = DAT_0513;
      DAT_0518 = 0xff;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa009();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\x01';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      DAT_0508 = 0;
      DAT_0068 = 0x70;
      DAT_0069 = 0xaf;
      uStack0000 = 0xe2;
      FUN_e51f(1);
      DAT_0097 = 1;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_0061 = 5;
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e673(0x1d);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 4:
      uStack0000 = 0xe2;
      FUN_e87a();
      uStack0000 = 0xe2;
      FUN_f24b(0x28);
      uStack0000 = 0xe2;
      func_0xa000();
      break;
    case 5:
      goto code_r0xe22f;
    case 6:
      uStack0000 = 0xe2;
      FUN_e87a();
      break;
    case 7:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 5;
      uStack0000 = 0xe2;
      FUN_e370(10);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x84;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\n';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      if (DAT_04ab == '\x01') {
        DAT_0106 = 0;
        DAT_0116 = 0;
      }
      if (DAT_04ac == '\x01') {
        DAT_010e = 0;
        DAT_011a = 0;
      }
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(2);
      uStack0000 = 0xe3;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e67b(0x12);
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    case 8:
      uStack0000 = 0xe3;
      FUN_e87a();
      break;
    case 9:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 6;
      uStack0000 = 0xe3;
      FUN_e370(0xb);
      uStack0000 = 0xe3;
      select_data_bank(0x35);
      DAT_000a = 0x90;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\v';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(3);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe3;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    default:
      break;
    case 0xb:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 7;
      uStack0000 = 0xe3;
      FUN_e370(0xc);
      uStack0000 = 0xe4;
      select_data_bank(0x32);
      DAT_000a = 0xe3;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa018();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\f';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_ecbf();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(4);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe4;
      FUN_e683(8);
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xd:
      uStack0000 = 0xe4;
      FUN_e4da();
      DAT_0078 = 8;
      uStack0000 = 0xe4;
      FUN_e370(0xd);
      uStack0000 = 0xe4;
      select_data_bank(0x36);
      DAT_000a = 0x92;
      DAT_000b = 0x9b;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\r';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(5);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      if (DAT_0541 == '\0') {
        uStack0000 = 0xe4;
        FUN_e673(0x98);
      }
      else {
        uStack0000 = 0xe4;
        FUN_e67b(0xaa);
      }
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x10:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x11:
      DAT_008c = 0;
      return 0;
    case 0x12:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x13:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x14:
      uStack0000 = 0xe5;
      FUN_e673(0);
      uStack0000 = 0xe5;
      FUN_e590();
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      return 0x4c;
    case 0x15:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x16:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x17:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x18:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x19:
      DAT_007b = DAT_007b + -1;
      reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
      bRAMe800 = DAT_00df | 0xc0;
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
      return in_stack_00000003;
    case 0x1a:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1b:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1c:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1d:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1e:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1f:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  } while( true );
}



/* 0xe2e2 state_or_entry_e2e2 */

/* WARNING: Control flow encountered bad instruction data */

undefined1 state_or_entry_e2e2(void)

{
  byte bVar1;
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
code_r0xe2e2:
  uStack0000 = 0xe2;
  FUN_e87a();
  do {
    bVar1 = (DAT_007a & 0x1f) << 1;
    DAT_004e = CONCAT11((&DAT_e07d)[bVar1],(&DAT_e07c)[bVar1]);
    switch(DAT_007a & 0x1f) {
    case 0:
      uStack0000 = 0xe0;
      FUN_e768();
      uStack0000 = 0xe0;
      DAT_2001 = FUN_e74d();
      uStack0000 = 0xe0;
      FUN_e57f();
      bVar1 = 0x1f;
      do {
        *(undefined1 *)(bVar1 + 0x100) = 0xf;
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      do {
      } while (-1 < DAT_2002);
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      uStack0000 = 0xe0;
      FUN_e51f(0);
      DAT_008b = 0x10;
      DAT_2000 = 0x10;
      DAT_008c = 0;
      DAT_2001 = 0;
      DAT_007a = 9;
      break;
    case 1:
      uStack0000 = 0xe0;
      FUN_e4da();
      DAT_0078 = 2;
      uStack0000 = 0xe0;
      FUN_e370(0);
      uStack0000 = 0xe0;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x80;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa003();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\0';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      if (DAT_0400 != '\r') {
        DAT_6f8b = 0xff;
      }
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa036();
      uStack0000 = 0xe1;
      FUN_ecbf();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa045(0);
      DAT_0098 = 0xa0;
      DAT_0420 = 0;
      DAT_04e0 = 0;
      DAT_04e1 = 0;
      DAT_04e2 = 0;
      DAT_04e3 = 0;
      DAT_6f41 = 0xf0;
      DAT_6f3f = 0x80;
      uStack0000 = 0xe1;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe1;
      FUN_e673(0x81);
      uStack0000 = 0xe1;
      FUN_e749();
      uStack0000 = 0xe1;
      FUN_e753();
      break;
    case 2:
      uStack0000 = 0xe1;
      FUN_e87a();
      uStack0000 = 0xe1;
      FUN_f24b(0x2a);
      uStack0000 = 0xe1;
      func_0xa000();
      break;
    case 3:
      uStack0000 = 0xe1;
      FUN_e4da();
      DAT_0078 = 3;
      uStack0000 = 0xe1;
      FUN_e370(1);
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa027();
      if (DAT_0500 == '\v') {
        uStack0000 = 0xe1;
        FUN_f237(0x2c);
        uStack0000 = 0xe1;
        func_0xa006();
      }
      else {
        uStack0000 = 0xe1;
        FUN_f237(0x28);
        uStack0000 = 0xe1;
        func_0xa003();
      }
      DAT_0090 = DAT_0510;
      DAT_0091 = DAT_0511;
      DAT_008e = DAT_0512;
      DAT_008f = DAT_0513;
      DAT_0518 = 0xff;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa009();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\x01';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      DAT_0508 = 0;
      DAT_0068 = 0x70;
      DAT_0069 = 0xaf;
      uStack0000 = 0xe2;
      FUN_e51f(1);
      DAT_0097 = 1;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_0061 = 5;
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e673(0x1d);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 4:
      uStack0000 = 0xe2;
      FUN_e87a();
      uStack0000 = 0xe2;
      FUN_f24b(0x28);
      uStack0000 = 0xe2;
      func_0xa000();
      break;
    case 5:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 4;
      uStack0000 = 0xe2;
      FUN_e370(DAT_0544 + '\x02');
      uStack0000 = 0xe2;
      FUN_e51f(2);
      uStack0000 = 0xe2;
      FUN_f237(0x37);
      uStack0000 = 0xe2;
      func_0xa024();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      DAT_0000 = DAT_0544 + '\x02';
      uStack0000 = 0xe2;
      func_0xa015();
      DAT_0107 = (&DAT_e2de)[DAT_0563];
      DAT_010f = (&DAT_e2de)[DAT_0562];
      uStack0000 = 0xe2;
      DAT_0113 = DAT_0107;
      DAT_0117 = DAT_010f;
      FUN_eaf7();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      uStack0000 = 0xe2;
      func_0xa045(1);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e683(0xd);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 6:
      goto code_r0xe2e2;
    case 7:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 5;
      uStack0000 = 0xe2;
      FUN_e370(10);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x84;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\n';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      if (DAT_04ab == '\x01') {
        DAT_0106 = 0;
        DAT_0116 = 0;
      }
      if (DAT_04ac == '\x01') {
        DAT_010e = 0;
        DAT_011a = 0;
      }
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(2);
      uStack0000 = 0xe3;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e67b(0x12);
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    case 8:
      uStack0000 = 0xe3;
      FUN_e87a();
      break;
    case 9:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 6;
      uStack0000 = 0xe3;
      FUN_e370(0xb);
      uStack0000 = 0xe3;
      select_data_bank(0x35);
      DAT_000a = 0x90;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\v';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(3);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe3;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    default:
      break;
    case 0xb:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 7;
      uStack0000 = 0xe3;
      FUN_e370(0xc);
      uStack0000 = 0xe4;
      select_data_bank(0x32);
      DAT_000a = 0xe3;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa018();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\f';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_ecbf();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(4);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe4;
      FUN_e683(8);
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xd:
      uStack0000 = 0xe4;
      FUN_e4da();
      DAT_0078 = 8;
      uStack0000 = 0xe4;
      FUN_e370(0xd);
      uStack0000 = 0xe4;
      select_data_bank(0x36);
      DAT_000a = 0x92;
      DAT_000b = 0x9b;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\r';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(5);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      if (DAT_0541 == '\0') {
        uStack0000 = 0xe4;
        FUN_e673(0x98);
      }
      else {
        uStack0000 = 0xe4;
        FUN_e67b(0xaa);
      }
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x10:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x11:
      DAT_008c = 0;
      return 0;
    case 0x12:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x13:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x14:
      uStack0000 = 0xe5;
      FUN_e673(0);
      uStack0000 = 0xe5;
      FUN_e590();
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      return 0x4c;
    case 0x15:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x16:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x17:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x18:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x19:
      DAT_007b = DAT_007b + -1;
      reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
      bRAMe800 = DAT_00df | 0xc0;
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
      return in_stack_00000003;
    case 0x1a:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1b:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1c:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1d:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1e:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1f:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  } while( true );
}



/* 0xe2e8 state_or_entry_e2e8 */

/* WARNING: Control flow encountered bad instruction data */

undefined1 state_or_entry_e2e8(void)

{
  byte bVar1;
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
code_r0xe2e8:
  uStack0000 = 0xe2;
  FUN_e4da();
  DAT_0078 = 5;
  uStack0000 = 0xe2;
  FUN_e370(10);
  DAT_0098 = 0xa0;
  uStack0000 = 0xe2;
  select_data_bank(0x30);
  DAT_000a = 0;
  DAT_000b = 0x84;
  DAT_0000 = 0;
  DAT_0001 = 0x20;
  uStack0000 = 0xe3;
  FUN_f237(0x37);
  uStack0000 = 0xe3;
  func_0xa003();
  uStack0000 = 0xe3;
  FUN_f237(0x3d);
  DAT_0000 = '\n';
  uStack0000 = 0xe3;
  func_0xa015();
  uStack0000 = 0xe3;
  FUN_eaf7();
  if (DAT_04ab == '\x01') {
    DAT_0106 = 0;
    DAT_0116 = 0;
  }
  if (DAT_04ac == '\x01') {
    DAT_010e = 0;
    DAT_011a = 0;
  }
  uStack0000 = 0xe3;
  FUN_ecbf();
  uStack0000 = 0xe3;
  FUN_f237(0x3d);
  uStack0000 = 0xe3;
  func_0xa045(2);
  uStack0000 = 0xe3;
  FUN_e51f(0);
  DAT_007a = DAT_007a + 1;
  uStack0000 = 0xe3;
  FUN_e67b(0x12);
  uStack0000 = 0xe3;
  FUN_e749();
  uStack0000 = 0xe3;
  FUN_e753();
  do {
    bVar1 = (DAT_007a & 0x1f) << 1;
    DAT_004e = CONCAT11((&DAT_e07d)[bVar1],(&DAT_e07c)[bVar1]);
    switch(DAT_007a & 0x1f) {
    case 0:
      uStack0000 = 0xe0;
      FUN_e768();
      uStack0000 = 0xe0;
      DAT_2001 = FUN_e74d();
      uStack0000 = 0xe0;
      FUN_e57f();
      bVar1 = 0x1f;
      do {
        *(undefined1 *)(bVar1 + 0x100) = 0xf;
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      do {
      } while (-1 < DAT_2002);
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      uStack0000 = 0xe0;
      FUN_e51f(0);
      DAT_008b = 0x10;
      DAT_2000 = 0x10;
      DAT_008c = 0;
      DAT_2001 = 0;
      DAT_007a = 9;
      break;
    case 1:
      uStack0000 = 0xe0;
      FUN_e4da();
      DAT_0078 = 2;
      uStack0000 = 0xe0;
      FUN_e370(0);
      uStack0000 = 0xe0;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x80;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa003();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\0';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      if (DAT_0400 != '\r') {
        DAT_6f8b = 0xff;
      }
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa036();
      uStack0000 = 0xe1;
      FUN_ecbf();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa045(0);
      DAT_0098 = 0xa0;
      DAT_0420 = 0;
      DAT_04e0 = 0;
      DAT_04e1 = 0;
      DAT_04e2 = 0;
      DAT_04e3 = 0;
      DAT_6f41 = 0xf0;
      DAT_6f3f = 0x80;
      uStack0000 = 0xe1;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe1;
      FUN_e673(0x81);
      uStack0000 = 0xe1;
      FUN_e749();
      uStack0000 = 0xe1;
      FUN_e753();
      break;
    case 2:
      uStack0000 = 0xe1;
      FUN_e87a();
      uStack0000 = 0xe1;
      FUN_f24b(0x2a);
      uStack0000 = 0xe1;
      func_0xa000();
      break;
    case 3:
      uStack0000 = 0xe1;
      FUN_e4da();
      DAT_0078 = 3;
      uStack0000 = 0xe1;
      FUN_e370(1);
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa027();
      if (DAT_0500 == '\v') {
        uStack0000 = 0xe1;
        FUN_f237(0x2c);
        uStack0000 = 0xe1;
        func_0xa006();
      }
      else {
        uStack0000 = 0xe1;
        FUN_f237(0x28);
        uStack0000 = 0xe1;
        func_0xa003();
      }
      DAT_0090 = DAT_0510;
      DAT_0091 = DAT_0511;
      DAT_008e = DAT_0512;
      DAT_008f = DAT_0513;
      DAT_0518 = 0xff;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa009();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\x01';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      DAT_0508 = 0;
      DAT_0068 = 0x70;
      DAT_0069 = 0xaf;
      uStack0000 = 0xe2;
      FUN_e51f(1);
      DAT_0097 = 1;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_0061 = 5;
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e673(0x1d);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 4:
      uStack0000 = 0xe2;
      FUN_e87a();
      uStack0000 = 0xe2;
      FUN_f24b(0x28);
      uStack0000 = 0xe2;
      func_0xa000();
      break;
    case 5:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 4;
      uStack0000 = 0xe2;
      FUN_e370(DAT_0544 + '\x02');
      uStack0000 = 0xe2;
      FUN_e51f(2);
      uStack0000 = 0xe2;
      FUN_f237(0x37);
      uStack0000 = 0xe2;
      func_0xa024();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      DAT_0000 = DAT_0544 + '\x02';
      uStack0000 = 0xe2;
      func_0xa015();
      DAT_0107 = (&DAT_e2de)[DAT_0563];
      DAT_010f = (&DAT_e2de)[DAT_0562];
      uStack0000 = 0xe2;
      DAT_0113 = DAT_0107;
      DAT_0117 = DAT_010f;
      FUN_eaf7();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      uStack0000 = 0xe2;
      func_0xa045(1);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e683(0xd);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 6:
      uStack0000 = 0xe2;
      FUN_e87a();
      break;
    case 7:
      goto code_r0xe2e8;
    case 8:
      uStack0000 = 0xe3;
      FUN_e87a();
      break;
    case 9:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 6;
      uStack0000 = 0xe3;
      FUN_e370(0xb);
      uStack0000 = 0xe3;
      select_data_bank(0x35);
      DAT_000a = 0x90;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\v';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(3);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe3;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    default:
      break;
    case 0xb:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 7;
      uStack0000 = 0xe3;
      FUN_e370(0xc);
      uStack0000 = 0xe4;
      select_data_bank(0x32);
      DAT_000a = 0xe3;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa018();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\f';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_ecbf();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(4);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe4;
      FUN_e683(8);
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xd:
      uStack0000 = 0xe4;
      FUN_e4da();
      DAT_0078 = 8;
      uStack0000 = 0xe4;
      FUN_e370(0xd);
      uStack0000 = 0xe4;
      select_data_bank(0x36);
      DAT_000a = 0x92;
      DAT_000b = 0x9b;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\r';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(5);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      if (DAT_0541 == '\0') {
        uStack0000 = 0xe4;
        FUN_e673(0x98);
      }
      else {
        uStack0000 = 0xe4;
        FUN_e67b(0xaa);
      }
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x10:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x11:
      DAT_008c = 0;
      return 0;
    case 0x12:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x13:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x14:
      uStack0000 = 0xe5;
      FUN_e673(0);
      uStack0000 = 0xe5;
      FUN_e590();
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      return 0x4c;
    case 0x15:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x16:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x17:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x18:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x19:
      DAT_007b = DAT_007b + -1;
      reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
      bRAMe800 = DAT_00df | 0xc0;
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
      return in_stack_00000003;
    case 0x1a:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1b:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1c:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1d:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1e:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1f:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  } while( true );
}



/* 0xe36a state_or_entry_e36a */

/* WARNING: Control flow encountered bad instruction data */

undefined1 state_or_entry_e36a(void)

{
  byte bVar1;
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
code_r0xe36a:
  uStack0000 = 0xe3;
  FUN_e87a();
  do {
    bVar1 = (DAT_007a & 0x1f) << 1;
    DAT_004e = CONCAT11((&DAT_e07d)[bVar1],(&DAT_e07c)[bVar1]);
    switch(DAT_007a & 0x1f) {
    case 0:
      uStack0000 = 0xe0;
      FUN_e768();
      uStack0000 = 0xe0;
      DAT_2001 = FUN_e74d();
      uStack0000 = 0xe0;
      FUN_e57f();
      bVar1 = 0x1f;
      do {
        *(undefined1 *)(bVar1 + 0x100) = 0xf;
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      do {
      } while (-1 < DAT_2002);
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      uStack0000 = 0xe0;
      FUN_e51f(0);
      DAT_008b = 0x10;
      DAT_2000 = 0x10;
      DAT_008c = 0;
      DAT_2001 = 0;
      DAT_007a = 9;
      break;
    case 1:
      uStack0000 = 0xe0;
      FUN_e4da();
      DAT_0078 = 2;
      uStack0000 = 0xe0;
      FUN_e370(0);
      uStack0000 = 0xe0;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x80;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa003();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\0';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      if (DAT_0400 != '\r') {
        DAT_6f8b = 0xff;
      }
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa036();
      uStack0000 = 0xe1;
      FUN_ecbf();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa045(0);
      DAT_0098 = 0xa0;
      DAT_0420 = 0;
      DAT_04e0 = 0;
      DAT_04e1 = 0;
      DAT_04e2 = 0;
      DAT_04e3 = 0;
      DAT_6f41 = 0xf0;
      DAT_6f3f = 0x80;
      uStack0000 = 0xe1;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe1;
      FUN_e673(0x81);
      uStack0000 = 0xe1;
      FUN_e749();
      uStack0000 = 0xe1;
      FUN_e753();
      break;
    case 2:
      uStack0000 = 0xe1;
      FUN_e87a();
      uStack0000 = 0xe1;
      FUN_f24b(0x2a);
      uStack0000 = 0xe1;
      func_0xa000();
      break;
    case 3:
      uStack0000 = 0xe1;
      FUN_e4da();
      DAT_0078 = 3;
      uStack0000 = 0xe1;
      FUN_e370(1);
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa027();
      if (DAT_0500 == '\v') {
        uStack0000 = 0xe1;
        FUN_f237(0x2c);
        uStack0000 = 0xe1;
        func_0xa006();
      }
      else {
        uStack0000 = 0xe1;
        FUN_f237(0x28);
        uStack0000 = 0xe1;
        func_0xa003();
      }
      DAT_0090 = DAT_0510;
      DAT_0091 = DAT_0511;
      DAT_008e = DAT_0512;
      DAT_008f = DAT_0513;
      DAT_0518 = 0xff;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa009();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\x01';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      DAT_0508 = 0;
      DAT_0068 = 0x70;
      DAT_0069 = 0xaf;
      uStack0000 = 0xe2;
      FUN_e51f(1);
      DAT_0097 = 1;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_0061 = 5;
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e673(0x1d);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 4:
      uStack0000 = 0xe2;
      FUN_e87a();
      uStack0000 = 0xe2;
      FUN_f24b(0x28);
      uStack0000 = 0xe2;
      func_0xa000();
      break;
    case 5:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 4;
      uStack0000 = 0xe2;
      FUN_e370(DAT_0544 + '\x02');
      uStack0000 = 0xe2;
      FUN_e51f(2);
      uStack0000 = 0xe2;
      FUN_f237(0x37);
      uStack0000 = 0xe2;
      func_0xa024();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      DAT_0000 = DAT_0544 + '\x02';
      uStack0000 = 0xe2;
      func_0xa015();
      DAT_0107 = (&DAT_e2de)[DAT_0563];
      DAT_010f = (&DAT_e2de)[DAT_0562];
      uStack0000 = 0xe2;
      DAT_0113 = DAT_0107;
      DAT_0117 = DAT_010f;
      FUN_eaf7();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      uStack0000 = 0xe2;
      func_0xa045(1);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e683(0xd);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 6:
      uStack0000 = 0xe2;
      FUN_e87a();
      break;
    case 7:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 5;
      uStack0000 = 0xe2;
      FUN_e370(10);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x84;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\n';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      if (DAT_04ab == '\x01') {
        DAT_0106 = 0;
        DAT_0116 = 0;
      }
      if (DAT_04ac == '\x01') {
        DAT_010e = 0;
        DAT_011a = 0;
      }
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(2);
      uStack0000 = 0xe3;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e67b(0x12);
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    case 8:
      goto code_r0xe36a;
    case 9:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 6;
      uStack0000 = 0xe3;
      FUN_e370(0xb);
      uStack0000 = 0xe3;
      select_data_bank(0x35);
      DAT_000a = 0x90;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\v';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(3);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe3;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    default:
      break;
    case 0xb:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 7;
      uStack0000 = 0xe3;
      FUN_e370(0xc);
      uStack0000 = 0xe4;
      select_data_bank(0x32);
      DAT_000a = 0xe3;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa018();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\f';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_ecbf();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(4);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe4;
      FUN_e683(8);
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xd:
      uStack0000 = 0xe4;
      FUN_e4da();
      DAT_0078 = 8;
      uStack0000 = 0xe4;
      FUN_e370(0xd);
      uStack0000 = 0xe4;
      select_data_bank(0x36);
      DAT_000a = 0x92;
      DAT_000b = 0x9b;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\r';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(5);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      if (DAT_0541 == '\0') {
        uStack0000 = 0xe4;
        FUN_e673(0x98);
      }
      else {
        uStack0000 = 0xe4;
        FUN_e67b(0xaa);
      }
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x10:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x11:
      DAT_008c = 0;
      return 0;
    case 0x12:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x13:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x14:
      uStack0000 = 0xe5;
      FUN_e673(0);
      uStack0000 = 0xe5;
      FUN_e590();
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      return 0x4c;
    case 0x15:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x16:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x17:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x18:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x19:
      DAT_007b = DAT_007b + -1;
      reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
      bRAMe800 = DAT_00df | 0xc0;
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
      return in_stack_00000003;
    case 0x1a:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1b:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1c:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1d:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1e:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1f:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  } while( true );
}



/* 0xe370 FUN_e370 */

void FUN_e370(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xe3;
  FUN_f237(0x3d);
  uStack0000 = 0xe3;
  func_0xa01b();
  uStack0000 = 0xe3;
  FUN_f206();
  return;
}



/* 0xe37c state_or_entry_e37c */

/* WARNING: Control flow encountered bad instruction data */

undefined1 state_or_entry_e37c(void)

{
  byte bVar1;
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
code_r0xe37c:
  uStack0000 = 0xe3;
  FUN_e4da();
  DAT_0078 = 6;
  uStack0000 = 0xe3;
  FUN_e370(0xb);
  uStack0000 = 0xe3;
  select_data_bank(0x35);
  DAT_000a = 0x90;
  DAT_000b = 0x9a;
  DAT_0001 = 0x20;
  DAT_0000 = 0;
  DAT_0004 = 0;
  DAT_0005 = 0;
  DAT_0006 = 0;
  DAT_0007 = 4;
  uStack0000 = 0xe3;
  FUN_f237(0x37);
  uStack0000 = 0xe3;
  func_0xa003();
  uStack0000 = 0xe3;
  FUN_f237(0x3d);
  DAT_0000 = '\v';
  uStack0000 = 0xe3;
  func_0xa015();
  uStack0000 = 0xe3;
  FUN_eaf7();
  uStack0000 = 0xe3;
  FUN_ecbf();
  uStack0000 = 0xe3;
  FUN_f237(0x3d);
  uStack0000 = 0xe3;
  func_0xa045(3);
  DAT_0098 = 0xa0;
  uStack0000 = 0xe3;
  FUN_e51f(2);
  DAT_007a = DAT_007a + 1;
  uStack0000 = 0xe3;
  FUN_e749();
  uStack0000 = 0xe3;
  FUN_e753();
  do {
    bVar1 = (DAT_007a & 0x1f) << 1;
    DAT_004e = CONCAT11((&DAT_e07d)[bVar1],(&DAT_e07c)[bVar1]);
    switch(DAT_007a & 0x1f) {
    case 0:
      uStack0000 = 0xe0;
      FUN_e768();
      uStack0000 = 0xe0;
      DAT_2001 = FUN_e74d();
      uStack0000 = 0xe0;
      FUN_e57f();
      bVar1 = 0x1f;
      do {
        *(undefined1 *)(bVar1 + 0x100) = 0xf;
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      do {
      } while (-1 < DAT_2002);
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      uStack0000 = 0xe0;
      FUN_e51f(0);
      DAT_008b = 0x10;
      DAT_2000 = 0x10;
      DAT_008c = 0;
      DAT_2001 = 0;
      DAT_007a = 9;
      break;
    case 1:
      uStack0000 = 0xe0;
      FUN_e4da();
      DAT_0078 = 2;
      uStack0000 = 0xe0;
      FUN_e370(0);
      uStack0000 = 0xe0;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x80;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa003();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\0';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      if (DAT_0400 != '\r') {
        DAT_6f8b = 0xff;
      }
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa036();
      uStack0000 = 0xe1;
      FUN_ecbf();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa045(0);
      DAT_0098 = 0xa0;
      DAT_0420 = 0;
      DAT_04e0 = 0;
      DAT_04e1 = 0;
      DAT_04e2 = 0;
      DAT_04e3 = 0;
      DAT_6f41 = 0xf0;
      DAT_6f3f = 0x80;
      uStack0000 = 0xe1;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe1;
      FUN_e673(0x81);
      uStack0000 = 0xe1;
      FUN_e749();
      uStack0000 = 0xe1;
      FUN_e753();
      break;
    case 2:
      uStack0000 = 0xe1;
      FUN_e87a();
      uStack0000 = 0xe1;
      FUN_f24b(0x2a);
      uStack0000 = 0xe1;
      func_0xa000();
      break;
    case 3:
      uStack0000 = 0xe1;
      FUN_e4da();
      DAT_0078 = 3;
      uStack0000 = 0xe1;
      FUN_e370(1);
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa027();
      if (DAT_0500 == '\v') {
        uStack0000 = 0xe1;
        FUN_f237(0x2c);
        uStack0000 = 0xe1;
        func_0xa006();
      }
      else {
        uStack0000 = 0xe1;
        FUN_f237(0x28);
        uStack0000 = 0xe1;
        func_0xa003();
      }
      DAT_0090 = DAT_0510;
      DAT_0091 = DAT_0511;
      DAT_008e = DAT_0512;
      DAT_008f = DAT_0513;
      DAT_0518 = 0xff;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa009();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\x01';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      DAT_0508 = 0;
      DAT_0068 = 0x70;
      DAT_0069 = 0xaf;
      uStack0000 = 0xe2;
      FUN_e51f(1);
      DAT_0097 = 1;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_0061 = 5;
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e673(0x1d);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 4:
      uStack0000 = 0xe2;
      FUN_e87a();
      uStack0000 = 0xe2;
      FUN_f24b(0x28);
      uStack0000 = 0xe2;
      func_0xa000();
      break;
    case 5:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 4;
      uStack0000 = 0xe2;
      FUN_e370(DAT_0544 + '\x02');
      uStack0000 = 0xe2;
      FUN_e51f(2);
      uStack0000 = 0xe2;
      FUN_f237(0x37);
      uStack0000 = 0xe2;
      func_0xa024();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      DAT_0000 = DAT_0544 + '\x02';
      uStack0000 = 0xe2;
      func_0xa015();
      DAT_0107 = (&DAT_e2de)[DAT_0563];
      DAT_010f = (&DAT_e2de)[DAT_0562];
      uStack0000 = 0xe2;
      DAT_0113 = DAT_0107;
      DAT_0117 = DAT_010f;
      FUN_eaf7();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      uStack0000 = 0xe2;
      func_0xa045(1);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e683(0xd);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 6:
      uStack0000 = 0xe2;
      FUN_e87a();
      break;
    case 7:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 5;
      uStack0000 = 0xe2;
      FUN_e370(10);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x84;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\n';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      if (DAT_04ab == '\x01') {
        DAT_0106 = 0;
        DAT_0116 = 0;
      }
      if (DAT_04ac == '\x01') {
        DAT_010e = 0;
        DAT_011a = 0;
      }
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(2);
      uStack0000 = 0xe3;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e67b(0x12);
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    case 8:
      uStack0000 = 0xe3;
      FUN_e87a();
      break;
    case 9:
      goto code_r0xe37c;
    default:
      break;
    case 0xb:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 7;
      uStack0000 = 0xe3;
      FUN_e370(0xc);
      uStack0000 = 0xe4;
      select_data_bank(0x32);
      DAT_000a = 0xe3;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa018();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\f';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_ecbf();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(4);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe4;
      FUN_e683(8);
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xd:
      uStack0000 = 0xe4;
      FUN_e4da();
      DAT_0078 = 8;
      uStack0000 = 0xe4;
      FUN_e370(0xd);
      uStack0000 = 0xe4;
      select_data_bank(0x36);
      DAT_000a = 0x92;
      DAT_000b = 0x9b;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\r';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(5);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      if (DAT_0541 == '\0') {
        uStack0000 = 0xe4;
        FUN_e673(0x98);
      }
      else {
        uStack0000 = 0xe4;
        FUN_e67b(0xaa);
      }
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x10:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x11:
      DAT_008c = 0;
      return 0;
    case 0x12:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x13:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x14:
      uStack0000 = 0xe5;
      FUN_e673(0);
      uStack0000 = 0xe5;
      FUN_e590();
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      return 0x4c;
    case 0x15:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x16:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x17:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x18:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x19:
      DAT_007b = DAT_007b + -1;
      reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
      bRAMe800 = DAT_00df | 0xc0;
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
      return in_stack_00000003;
    case 0x1a:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1b:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1c:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1d:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1e:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1f:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  } while( true );
}



/* 0xe3eb state_or_entry_e3eb */

/* WARNING: Control flow encountered bad instruction data */

undefined1 state_or_entry_e3eb(void)

{
  byte bVar1;
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
code_r0xe3eb:
  do {
    bVar1 = (DAT_007a & 0x1f) << 1;
    DAT_004e = CONCAT11((&DAT_e07d)[bVar1],(&DAT_e07c)[bVar1]);
    switch(DAT_007a & 0x1f) {
    case 0:
      uStack0000 = 0xe0;
      FUN_e768();
      uStack0000 = 0xe0;
      DAT_2001 = FUN_e74d();
      uStack0000 = 0xe0;
      FUN_e57f();
      bVar1 = 0x1f;
      do {
        *(undefined1 *)(bVar1 + 0x100) = 0xf;
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      do {
      } while (-1 < DAT_2002);
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      uStack0000 = 0xe0;
      FUN_e51f(0);
      DAT_008b = 0x10;
      DAT_2000 = 0x10;
      DAT_008c = 0;
      DAT_2001 = 0;
      DAT_007a = 9;
      break;
    case 1:
      uStack0000 = 0xe0;
      FUN_e4da();
      DAT_0078 = 2;
      uStack0000 = 0xe0;
      FUN_e370(0);
      uStack0000 = 0xe0;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x80;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa003();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\0';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      if (DAT_0400 != '\r') {
        DAT_6f8b = 0xff;
      }
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa036();
      uStack0000 = 0xe1;
      FUN_ecbf();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa045(0);
      DAT_0098 = 0xa0;
      DAT_0420 = 0;
      DAT_04e0 = 0;
      DAT_04e1 = 0;
      DAT_04e2 = 0;
      DAT_04e3 = 0;
      DAT_6f41 = 0xf0;
      DAT_6f3f = 0x80;
      uStack0000 = 0xe1;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe1;
      FUN_e673(0x81);
      uStack0000 = 0xe1;
      FUN_e749();
      uStack0000 = 0xe1;
      FUN_e753();
      break;
    case 2:
      uStack0000 = 0xe1;
      FUN_e87a();
      uStack0000 = 0xe1;
      FUN_f24b(0x2a);
      uStack0000 = 0xe1;
      func_0xa000();
      break;
    case 3:
      uStack0000 = 0xe1;
      FUN_e4da();
      DAT_0078 = 3;
      uStack0000 = 0xe1;
      FUN_e370(1);
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa027();
      if (DAT_0500 == '\v') {
        uStack0000 = 0xe1;
        FUN_f237(0x2c);
        uStack0000 = 0xe1;
        func_0xa006();
      }
      else {
        uStack0000 = 0xe1;
        FUN_f237(0x28);
        uStack0000 = 0xe1;
        func_0xa003();
      }
      DAT_0090 = DAT_0510;
      DAT_0091 = DAT_0511;
      DAT_008e = DAT_0512;
      DAT_008f = DAT_0513;
      DAT_0518 = 0xff;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa009();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\x01';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      DAT_0508 = 0;
      DAT_0068 = 0x70;
      DAT_0069 = 0xaf;
      uStack0000 = 0xe2;
      FUN_e51f(1);
      DAT_0097 = 1;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_0061 = 5;
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e673(0x1d);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 4:
      uStack0000 = 0xe2;
      FUN_e87a();
      uStack0000 = 0xe2;
      FUN_f24b(0x28);
      uStack0000 = 0xe2;
      func_0xa000();
      break;
    case 5:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 4;
      uStack0000 = 0xe2;
      FUN_e370(DAT_0544 + '\x02');
      uStack0000 = 0xe2;
      FUN_e51f(2);
      uStack0000 = 0xe2;
      FUN_f237(0x37);
      uStack0000 = 0xe2;
      func_0xa024();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      DAT_0000 = DAT_0544 + '\x02';
      uStack0000 = 0xe2;
      func_0xa015();
      DAT_0107 = (&DAT_e2de)[DAT_0563];
      DAT_010f = (&DAT_e2de)[DAT_0562];
      uStack0000 = 0xe2;
      DAT_0113 = DAT_0107;
      DAT_0117 = DAT_010f;
      FUN_eaf7();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      uStack0000 = 0xe2;
      func_0xa045(1);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e683(0xd);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 6:
      uStack0000 = 0xe2;
      FUN_e87a();
      break;
    case 7:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 5;
      uStack0000 = 0xe2;
      FUN_e370(10);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x84;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\n';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      if (DAT_04ab == '\x01') {
        DAT_0106 = 0;
        DAT_0116 = 0;
      }
      if (DAT_04ac == '\x01') {
        DAT_010e = 0;
        DAT_011a = 0;
      }
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(2);
      uStack0000 = 0xe3;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e67b(0x12);
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    case 8:
      uStack0000 = 0xe3;
      FUN_e87a();
      break;
    case 9:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 6;
      uStack0000 = 0xe3;
      FUN_e370(0xb);
      uStack0000 = 0xe3;
      select_data_bank(0x35);
      DAT_000a = 0x90;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\v';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(3);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe3;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    default:
      goto code_r0xe3eb;
    case 0xb:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 7;
      uStack0000 = 0xe3;
      FUN_e370(0xc);
      uStack0000 = 0xe4;
      select_data_bank(0x32);
      DAT_000a = 0xe3;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa018();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\f';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_ecbf();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(4);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe4;
      FUN_e683(8);
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xd:
      uStack0000 = 0xe4;
      FUN_e4da();
      DAT_0078 = 8;
      uStack0000 = 0xe4;
      FUN_e370(0xd);
      uStack0000 = 0xe4;
      select_data_bank(0x36);
      DAT_000a = 0x92;
      DAT_000b = 0x9b;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\r';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(5);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      if (DAT_0541 == '\0') {
        uStack0000 = 0xe4;
        FUN_e673(0x98);
      }
      else {
        uStack0000 = 0xe4;
        FUN_e67b(0xaa);
      }
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x10:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x11:
      DAT_008c = 0;
      return 0;
    case 0x12:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x13:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x14:
      uStack0000 = 0xe5;
      FUN_e673(0);
      uStack0000 = 0xe5;
      FUN_e590();
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      return 0x4c;
    case 0x15:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x16:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x17:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x18:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x19:
      DAT_007b = DAT_007b + -1;
      reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
      bRAMe800 = DAT_00df | 0xc0;
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
      return in_stack_00000003;
    case 0x1a:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1b:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1c:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1d:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1e:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1f:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  } while( true );
}



/* 0xe3ee state_or_entry_e3ee */

/* WARNING: Control flow encountered bad instruction data */

undefined1 state_or_entry_e3ee(void)

{
  byte bVar1;
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
code_r0xe3ee:
  uStack0000 = 0xe3;
  FUN_e4da();
  DAT_0078 = 7;
  uStack0000 = 0xe3;
  FUN_e370(0xc);
  uStack0000 = 0xe4;
  select_data_bank(0x32);
  DAT_000a = 0xe3;
  DAT_000b = 0x9a;
  DAT_0001 = 0x20;
  DAT_0000 = 0;
  DAT_0004 = 0;
  DAT_0005 = 0;
  DAT_0006 = 0;
  DAT_0007 = 4;
  uStack0000 = 0xe4;
  FUN_f237(0x37);
  uStack0000 = 0xe4;
  func_0xa003();
  uStack0000 = 0xe4;
  FUN_f237(0x3d);
  uStack0000 = 0xe4;
  func_0xa018();
  uStack0000 = 0xe4;
  FUN_f237(0x3d);
  DAT_0000 = '\f';
  uStack0000 = 0xe4;
  func_0xa015();
  uStack0000 = 0xe4;
  FUN_eaf7();
  uStack0000 = 0xe4;
  FUN_ecbf();
  uStack0000 = 0xe4;
  FUN_f237(0x3d);
  uStack0000 = 0xe4;
  func_0xa045(4);
  DAT_0098 = 0xa0;
  uStack0000 = 0xe4;
  FUN_e51f(2);
  DAT_007a = DAT_007a + 1;
  uStack0000 = 0xe4;
  FUN_e683(8);
  uStack0000 = 0xe4;
  FUN_e749();
  uStack0000 = 0xe4;
  FUN_e753();
  do {
    bVar1 = (DAT_007a & 0x1f) << 1;
    DAT_004e = CONCAT11((&DAT_e07d)[bVar1],(&DAT_e07c)[bVar1]);
    switch(DAT_007a & 0x1f) {
    case 0:
      uStack0000 = 0xe0;
      FUN_e768();
      uStack0000 = 0xe0;
      DAT_2001 = FUN_e74d();
      uStack0000 = 0xe0;
      FUN_e57f();
      bVar1 = 0x1f;
      do {
        *(undefined1 *)(bVar1 + 0x100) = 0xf;
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      do {
      } while (-1 < DAT_2002);
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      uStack0000 = 0xe0;
      FUN_e51f(0);
      DAT_008b = 0x10;
      DAT_2000 = 0x10;
      DAT_008c = 0;
      DAT_2001 = 0;
      DAT_007a = 9;
      break;
    case 1:
      uStack0000 = 0xe0;
      FUN_e4da();
      DAT_0078 = 2;
      uStack0000 = 0xe0;
      FUN_e370(0);
      uStack0000 = 0xe0;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x80;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa003();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\0';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      if (DAT_0400 != '\r') {
        DAT_6f8b = 0xff;
      }
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa036();
      uStack0000 = 0xe1;
      FUN_ecbf();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa045(0);
      DAT_0098 = 0xa0;
      DAT_0420 = 0;
      DAT_04e0 = 0;
      DAT_04e1 = 0;
      DAT_04e2 = 0;
      DAT_04e3 = 0;
      DAT_6f41 = 0xf0;
      DAT_6f3f = 0x80;
      uStack0000 = 0xe1;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe1;
      FUN_e673(0x81);
      uStack0000 = 0xe1;
      FUN_e749();
      uStack0000 = 0xe1;
      FUN_e753();
      break;
    case 2:
      uStack0000 = 0xe1;
      FUN_e87a();
      uStack0000 = 0xe1;
      FUN_f24b(0x2a);
      uStack0000 = 0xe1;
      func_0xa000();
      break;
    case 3:
      uStack0000 = 0xe1;
      FUN_e4da();
      DAT_0078 = 3;
      uStack0000 = 0xe1;
      FUN_e370(1);
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa027();
      if (DAT_0500 == '\v') {
        uStack0000 = 0xe1;
        FUN_f237(0x2c);
        uStack0000 = 0xe1;
        func_0xa006();
      }
      else {
        uStack0000 = 0xe1;
        FUN_f237(0x28);
        uStack0000 = 0xe1;
        func_0xa003();
      }
      DAT_0090 = DAT_0510;
      DAT_0091 = DAT_0511;
      DAT_008e = DAT_0512;
      DAT_008f = DAT_0513;
      DAT_0518 = 0xff;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa009();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\x01';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      DAT_0508 = 0;
      DAT_0068 = 0x70;
      DAT_0069 = 0xaf;
      uStack0000 = 0xe2;
      FUN_e51f(1);
      DAT_0097 = 1;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_0061 = 5;
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e673(0x1d);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 4:
      uStack0000 = 0xe2;
      FUN_e87a();
      uStack0000 = 0xe2;
      FUN_f24b(0x28);
      uStack0000 = 0xe2;
      func_0xa000();
      break;
    case 5:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 4;
      uStack0000 = 0xe2;
      FUN_e370(DAT_0544 + '\x02');
      uStack0000 = 0xe2;
      FUN_e51f(2);
      uStack0000 = 0xe2;
      FUN_f237(0x37);
      uStack0000 = 0xe2;
      func_0xa024();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      DAT_0000 = DAT_0544 + '\x02';
      uStack0000 = 0xe2;
      func_0xa015();
      DAT_0107 = (&DAT_e2de)[DAT_0563];
      DAT_010f = (&DAT_e2de)[DAT_0562];
      uStack0000 = 0xe2;
      DAT_0113 = DAT_0107;
      DAT_0117 = DAT_010f;
      FUN_eaf7();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      uStack0000 = 0xe2;
      func_0xa045(1);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e683(0xd);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 6:
      uStack0000 = 0xe2;
      FUN_e87a();
      break;
    case 7:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 5;
      uStack0000 = 0xe2;
      FUN_e370(10);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x84;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\n';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      if (DAT_04ab == '\x01') {
        DAT_0106 = 0;
        DAT_0116 = 0;
      }
      if (DAT_04ac == '\x01') {
        DAT_010e = 0;
        DAT_011a = 0;
      }
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(2);
      uStack0000 = 0xe3;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e67b(0x12);
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    case 8:
      uStack0000 = 0xe3;
      FUN_e87a();
      break;
    case 9:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 6;
      uStack0000 = 0xe3;
      FUN_e370(0xb);
      uStack0000 = 0xe3;
      select_data_bank(0x35);
      DAT_000a = 0x90;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\v';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(3);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe3;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    default:
      break;
    case 0xb:
      goto code_r0xe3ee;
    case 0xd:
      uStack0000 = 0xe4;
      FUN_e4da();
      DAT_0078 = 8;
      uStack0000 = 0xe4;
      FUN_e370(0xd);
      uStack0000 = 0xe4;
      select_data_bank(0x36);
      DAT_000a = 0x92;
      DAT_000b = 0x9b;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\r';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(5);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      if (DAT_0541 == '\0') {
        uStack0000 = 0xe4;
        FUN_e673(0x98);
      }
      else {
        uStack0000 = 0xe4;
        FUN_e67b(0xaa);
      }
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x10:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x11:
      DAT_008c = 0;
      return 0;
    case 0x12:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x13:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x14:
      uStack0000 = 0xe5;
      FUN_e673(0);
      uStack0000 = 0xe5;
      FUN_e590();
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      return 0x4c;
    case 0x15:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x16:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x17:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x18:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x19:
      DAT_007b = DAT_007b + -1;
      reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
      bRAMe800 = DAT_00df | 0xc0;
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
      return in_stack_00000003;
    case 0x1a:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1b:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1c:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1d:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1e:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1f:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  } while( true );
}



/* 0xe46a state_or_entry_e46a */

/* WARNING: Control flow encountered bad instruction data */

undefined1 state_or_entry_e46a(void)

{
  byte bVar1;
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
code_r0xe46a:
  uStack0000 = 0xe4;
  FUN_e4da();
  DAT_0078 = 8;
  uStack0000 = 0xe4;
  FUN_e370(0xd);
  uStack0000 = 0xe4;
  select_data_bank(0x36);
  DAT_000a = 0x92;
  DAT_000b = 0x9b;
  DAT_0000 = 0;
  DAT_0001 = 0x20;
  uStack0000 = 0xe4;
  FUN_f237(0x37);
  uStack0000 = 0xe4;
  func_0xa003();
  uStack0000 = 0xe4;
  FUN_f237(0x3d);
  DAT_0000 = '\r';
  uStack0000 = 0xe4;
  func_0xa015();
  uStack0000 = 0xe4;
  FUN_eaf7();
  uStack0000 = 0xe4;
  FUN_f237(0x3d);
  uStack0000 = 0xe4;
  func_0xa045(5);
  DAT_0098 = 0xa0;
  uStack0000 = 0xe4;
  FUN_e51f(2);
  DAT_007a = DAT_007a + 1;
  if (DAT_0541 == '\0') {
    uStack0000 = 0xe4;
    FUN_e673(0x98);
  }
  else {
    uStack0000 = 0xe4;
    FUN_e67b(0xaa);
  }
  uStack0000 = 0xe4;
  FUN_e749();
  uStack0000 = 0xe4;
  FUN_e753();
  do {
    bVar1 = (DAT_007a & 0x1f) << 1;
    DAT_004e = CONCAT11((&DAT_e07d)[bVar1],(&DAT_e07c)[bVar1]);
    switch(DAT_007a & 0x1f) {
    case 0:
      uStack0000 = 0xe0;
      FUN_e768();
      uStack0000 = 0xe0;
      DAT_2001 = FUN_e74d();
      uStack0000 = 0xe0;
      FUN_e57f();
      bVar1 = 0x1f;
      do {
        *(undefined1 *)(bVar1 + 0x100) = 0xf;
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      do {
      } while (-1 < DAT_2002);
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      uStack0000 = 0xe0;
      FUN_e51f(0);
      DAT_008b = 0x10;
      DAT_2000 = 0x10;
      DAT_008c = 0;
      DAT_2001 = 0;
      DAT_007a = 9;
      break;
    case 1:
      uStack0000 = 0xe0;
      FUN_e4da();
      DAT_0078 = 2;
      uStack0000 = 0xe0;
      FUN_e370(0);
      uStack0000 = 0xe0;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x80;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa003();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\0';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      if (DAT_0400 != '\r') {
        DAT_6f8b = 0xff;
      }
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa036();
      uStack0000 = 0xe1;
      FUN_ecbf();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      uStack0000 = 0xe1;
      func_0xa045(0);
      DAT_0098 = 0xa0;
      DAT_0420 = 0;
      DAT_04e0 = 0;
      DAT_04e1 = 0;
      DAT_04e2 = 0;
      DAT_04e3 = 0;
      DAT_6f41 = 0xf0;
      DAT_6f3f = 0x80;
      uStack0000 = 0xe1;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe1;
      FUN_e673(0x81);
      uStack0000 = 0xe1;
      FUN_e749();
      uStack0000 = 0xe1;
      FUN_e753();
      break;
    case 2:
      uStack0000 = 0xe1;
      FUN_e87a();
      uStack0000 = 0xe1;
      FUN_f24b(0x2a);
      uStack0000 = 0xe1;
      func_0xa000();
      break;
    case 3:
      uStack0000 = 0xe1;
      FUN_e4da();
      DAT_0078 = 3;
      uStack0000 = 0xe1;
      FUN_e370(1);
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa027();
      if (DAT_0500 == '\v') {
        uStack0000 = 0xe1;
        FUN_f237(0x2c);
        uStack0000 = 0xe1;
        func_0xa006();
      }
      else {
        uStack0000 = 0xe1;
        FUN_f237(0x28);
        uStack0000 = 0xe1;
        func_0xa003();
      }
      DAT_0090 = DAT_0510;
      DAT_0091 = DAT_0511;
      DAT_008e = DAT_0512;
      DAT_008f = DAT_0513;
      DAT_0518 = 0xff;
      uStack0000 = 0xe1;
      FUN_f237(0x37);
      uStack0000 = 0xe1;
      func_0xa009();
      uStack0000 = 0xe1;
      FUN_f237(0x3d);
      DAT_0000 = '\x01';
      uStack0000 = 0xe1;
      func_0xa015();
      uStack0000 = 0xe1;
      FUN_eaf7();
      DAT_0508 = 0;
      DAT_0068 = 0x70;
      DAT_0069 = 0xaf;
      uStack0000 = 0xe2;
      FUN_e51f(1);
      DAT_0097 = 1;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_0061 = 5;
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e673(0x1d);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 4:
      uStack0000 = 0xe2;
      FUN_e87a();
      uStack0000 = 0xe2;
      FUN_f24b(0x28);
      uStack0000 = 0xe2;
      func_0xa000();
      break;
    case 5:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 4;
      uStack0000 = 0xe2;
      FUN_e370(DAT_0544 + '\x02');
      uStack0000 = 0xe2;
      FUN_e51f(2);
      uStack0000 = 0xe2;
      FUN_f237(0x37);
      uStack0000 = 0xe2;
      func_0xa024();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      DAT_0000 = DAT_0544 + '\x02';
      uStack0000 = 0xe2;
      func_0xa015();
      DAT_0107 = (&DAT_e2de)[DAT_0563];
      DAT_010f = (&DAT_e2de)[DAT_0562];
      uStack0000 = 0xe2;
      DAT_0113 = DAT_0107;
      DAT_0117 = DAT_010f;
      FUN_eaf7();
      uStack0000 = 0xe2;
      FUN_f237(0x3d);
      uStack0000 = 0xe2;
      func_0xa045(1);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      FUN_ecbf();
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe2;
      FUN_e683(0xd);
      uStack0000 = 0xe2;
      FUN_e749();
      uStack0000 = 0xe2;
      FUN_e753();
      break;
    case 6:
      uStack0000 = 0xe2;
      FUN_e87a();
      break;
    case 7:
      uStack0000 = 0xe2;
      FUN_e4da();
      DAT_0078 = 5;
      uStack0000 = 0xe2;
      FUN_e370(10);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe2;
      select_data_bank(0x30);
      DAT_000a = 0;
      DAT_000b = 0x84;
      DAT_0000 = 0;
      DAT_0001 = 0x20;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\n';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      if (DAT_04ab == '\x01') {
        DAT_0106 = 0;
        DAT_0116 = 0;
      }
      if (DAT_04ac == '\x01') {
        DAT_010e = 0;
        DAT_011a = 0;
      }
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(2);
      uStack0000 = 0xe3;
      FUN_e51f(0);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e67b(0x12);
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    case 8:
      uStack0000 = 0xe3;
      FUN_e87a();
      break;
    case 9:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 6;
      uStack0000 = 0xe3;
      FUN_e370(0xb);
      uStack0000 = 0xe3;
      select_data_bank(0x35);
      DAT_000a = 0x90;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe3;
      FUN_f237(0x37);
      uStack0000 = 0xe3;
      func_0xa003();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      DAT_0000 = '\v';
      uStack0000 = 0xe3;
      func_0xa015();
      uStack0000 = 0xe3;
      FUN_eaf7();
      uStack0000 = 0xe3;
      FUN_ecbf();
      uStack0000 = 0xe3;
      FUN_f237(0x3d);
      uStack0000 = 0xe3;
      func_0xa045(3);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe3;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe3;
      FUN_e749();
      uStack0000 = 0xe3;
      FUN_e753();
      break;
    default:
      break;
    case 0xb:
      uStack0000 = 0xe3;
      FUN_e4da();
      DAT_0078 = 7;
      uStack0000 = 0xe3;
      FUN_e370(0xc);
      uStack0000 = 0xe4;
      select_data_bank(0x32);
      DAT_000a = 0xe3;
      DAT_000b = 0x9a;
      DAT_0001 = 0x20;
      DAT_0000 = 0;
      DAT_0004 = 0;
      DAT_0005 = 0;
      DAT_0006 = 0;
      DAT_0007 = 4;
      uStack0000 = 0xe4;
      FUN_f237(0x37);
      uStack0000 = 0xe4;
      func_0xa003();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa018();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      DAT_0000 = '\f';
      uStack0000 = 0xe4;
      func_0xa015();
      uStack0000 = 0xe4;
      FUN_eaf7();
      uStack0000 = 0xe4;
      FUN_ecbf();
      uStack0000 = 0xe4;
      FUN_f237(0x3d);
      uStack0000 = 0xe4;
      func_0xa045(4);
      DAT_0098 = 0xa0;
      uStack0000 = 0xe4;
      FUN_e51f(2);
      DAT_007a = DAT_007a + 1;
      uStack0000 = 0xe4;
      FUN_e683(8);
      uStack0000 = 0xe4;
      FUN_e749();
      uStack0000 = 0xe4;
      FUN_e753();
      break;
    case 0xd:
      goto code_r0xe46a;
    case 0xf:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x10:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x11:
      DAT_008c = 0;
      return 0;
    case 0x12:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x13:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x14:
      uStack0000 = 0xe5;
      FUN_e673(0);
      uStack0000 = 0xe5;
      FUN_e590();
      DAT_00a5 = 0x4c;
      nmi = (code)0x4c;
      return 0x4c;
    case 0x15:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x16:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x17:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x18:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x19:
      DAT_007b = DAT_007b + -1;
      reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
      bRAMe800 = DAT_00df | 0xc0;
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
      return in_stack_00000003;
    case 0x1a:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1b:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1c:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1d:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1e:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    case 0x1f:
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  } while( true );
}



/* 0xe4da FUN_e4da */

void FUN_e4da(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xe4;
  FUN_e768();
  uStack0000 = 0xe4;
  DAT_2001 = FUN_e74d();
  uStack0000 = 0xe4;
  FUN_e57f();
  uStack0000 = 0xe4;
  FUN_e7df();
  DAT_0090 = 0;
  DAT_0091 = 0;
  DAT_008e = 0;
  DAT_008f = 0;
  DAT_0098 = 0;
  DAT_0099 = 0;
  DAT_0096 = 0;
  DAT_0097 = 0;
  DAT_007e = 0;
  DAT_005e = 0;
  DAT_005f = 0;
  switchD_f878::caseD_f = 0;
  DAT_00a4 = 0;
  DAT_0300 = 0xff;
  DAT_0304 = 0xff;
  FUN_e823();
  return;
}



/* 0xe51f FUN_e51f */

void FUN_e51f(char param_1)

{
  byte bVar1;
  
  bVar1 = param_1 * '\b';
  DAT_00e6 = (&DAT_e567)[bVar1];
  DAT_c000 = (&DAT_e567)[bVar1];
  DAT_00e7 = (&DAT_e567)[(byte)(bVar1 + 1)];
  DAT_c800 = (&DAT_e567)[(byte)(bVar1 + 1)];
  DAT_00e8 = (&DAT_e567)[(byte)(bVar1 + 2)];
  DAT_d000 = (&DAT_e567)[(byte)(bVar1 + 2)];
  DAT_00e9 = (&DAT_e567)[(byte)(bVar1 + 3)];
  DAT_d800 = (&DAT_e567)[(byte)(bVar1 + 3)];
  DAT_00ea = (&DAT_e567)[(byte)(bVar1 + 4)];
  DAT_00eb = (&DAT_e567)[(byte)(bVar1 + 5)];
  DAT_00ec = (&DAT_e567)[(byte)(bVar1 + 6)];
  DAT_00ed = (&DAT_e567)[(byte)(bVar1 + 7)];
  return;
}



/* 0xe57f FUN_e57f */

void FUN_e57f(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xe5;
  FUN_e673(0);
  uStack0000 = 0xe5;
  FUN_e590();
  DAT_00a5 = 0x4c;
  nmi = (code)0x4c;
  return;
}



/* 0xe590 FUN_e590 */

void FUN_e590(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  DAT_4015 = 0;
  DAT_07f6 = 0;
  DAT_4000 = 0x10;
  DAT_4004 = 0x10;
  DAT_400c = 0x10;
  DAT_4001 = 8;
  DAT_4005 = 8;
  DAT_4008 = 0;
  DAT_07f2 = 0;
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x700) = 0xff;
    *(undefined1 *)(bVar1 + 0x706) = 0;
    bVar1 = bVar1 + 0x16;
  } while (bVar1 != 0xf2);
  cVar2 = '?';
  do {
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  nmi = (code)0x80;
  bVar1 = 0;
  do {
    DAT_4800 = (&DAT_e6a6)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x20);
  uStack0000 = 0xe5;
  FUN_e5fa(0xf0,100);
  nmi = (code)0x7f;
  DAT_4800 = 0x30;
  return;
}



/* 0xe5f3 FUN_e5f3 */

void FUN_e5f3(undefined1 param_1,code param_2)

{
  nmi = param_2;
  DAT_4800 = param_1;
  return;
}



/* 0xe5fa FUN_e5fa */

undefined1 FUN_e5fa(undefined1 param_1,char param_2)

{
  undefined1 uVar1;
  undefined1 uStack0000;
  
  uStack0000 = param_1;
  do {
    uVar1 = uStack0000;
    uStack0000 = 0xe5;
    uStack0000 = FUN_e5f3(uVar1);
    param_2 = param_2 + '\b';
  } while (-1 < param_2);
  return uStack0000;
}



/* 0xe609 FUN_e609 */

undefined1 FUN_e609(undefined1 param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xe6;
  bVar1 = select_data_bank(0x22);
  DAT_00f0 = (byte *)CONCAT11(((bVar1 >> 7) << 1 | (bVar1 & 0x7f) >> 6) + 0x80,bVar1 * '\x04');
  bVar1 = *DAT_00f0;
  if ((*(char *)(bVar1 + 0x700) != -1) && (*(byte *)(bVar1 + 0x701) < 4)) {
    DAT_07f6 = (&DAT_e667)[*(byte *)(bVar1 + 0x701)] & DAT_07f6;
    DAT_4015 = DAT_07f6;
  }
  *(byte *)(bVar1 + 0x701) = DAT_00f0[1];
  *(byte *)(bVar1 + 0x702) = DAT_00f0[2];
  *(byte *)(bVar1 + 0x703) = DAT_00f0[3] + 0x40;
  *(undefined1 *)(bVar1 + 0x700) = 0;
  return param_1;
}



/* 0xe673 FUN_e673 */

void FUN_e673(char param_1)

{
  char cStack0000;
  
  cStack0000 = param_1;
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  FUN_e609(cStack0000 + '\x01');
  return;
}



/* 0xe67b FUN_e67b */

void FUN_e67b(char param_1)

{
  char cStack0000;
  
  cStack0000 = param_1;
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  FUN_e609(cStack0000 + '\x01');
  return;
}



/* 0xe683 FUN_e683 */

void FUN_e683(char param_1)

{
  char cStack0000;
  
  cStack0000 = param_1;
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  FUN_e609(cStack0000 + '\x01');
  return;
}



/* 0xe6c6 FUN_e6c6 */

void FUN_e6c6(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  
  bVar2 = DAT_0085;
  bVar1 = DAT_0083;
  DAT_0084 = DAT_0083;
  DAT_0086 = DAT_0085;
  DAT_4016 = 0;
  cVar3 = '\a';
  do {
    DAT_0083 = DAT_0083 >> 1;
    DAT_0085 = DAT_0085 >> 1 | ((DAT_4017 & 3) != 0) << 7;
    cVar3 = cVar3 + -1;
  } while (-1 < cVar3);
  DAT_0081 = (DAT_0083 ^ bVar1) & DAT_0083;
  DAT_0082 = (DAT_0085 ^ bVar2) & DAT_0085;
  return;
}



/* 0xe70e FUN_e70e */

void FUN_e70e(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  bVar1 = 0;
  DAT_007d = 0;
  do {
    DAT_2007 = (&DAT_0101)[bVar1];
    bVar1 = bVar1 + 2;
  } while (bVar1 < 0x20);
  DAT_2006 = 0;
  return;
}



/* 0xe749 FUN_e749 */

/* WARNING: Removing unreachable block (RAM,0xe74d) */

void FUN_e749(void)

{
  DAT_008c = 0x1e;
  return;
}



/* 0xe74d FUN_e74d */

void FUN_e74d(void)

{
  DAT_008c = 0;
  return;
}



/* 0xe753 FUN_e753 */

void FUN_e753(void)

{
  DAT_007b = 0;
  DAT_007e = 0;
  DAT_2000 = DAT_008b | 0x80;
  if (DAT_2000 == 0) {
    DAT_2000 = DAT_008b & 0x7f;
  }
  DAT_008b = DAT_2000;
  return;
}



/* 0xe768 FUN_e768 */

void FUN_e768(void)

{
  DAT_008b = DAT_008b & 0x7f;
  DAT_2000 = DAT_008b;
  return;
}



/* 0xe7b5 FUN_e7b5 */

void FUN_e7b5(void)

{
  char cVar1;
  byte bVar2;
  
  DAT_2006 = 0;
  cVar1 = '\0';
  DAT_0001 = '\x03';
  do {
    do {
      cVar1 = cVar1 + -1;
    } while (cVar1 != '\0');
    DAT_0001 = DAT_0001 + -1;
    bVar2 = 0;
  } while (DAT_0001 != '\0');
  do {
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0xc0);
  do {
    DAT_2007 = DAT_0003;
    bVar2 = bVar2 + 1;
  } while (bVar2 != 0);
  return;
}



/* 0xe7df FUN_e7df */

void FUN_e7df(void)

{
  undefined1 uStack0000;
  
  DAT_c000 = 0xe0;
  DAT_c800 = 0xe1;
  DAT_d000 = 0xe0;
  DAT_d800 = 0xe1;
  DAT_0002 = 1;
  DAT_0003 = 0xaa;
  uStack0000 = 0xe8;
  FUN_e7b5(0x20);
  DAT_0002 = 1;
  DAT_0003 = 0xaa;
  uStack0000 = 0xe8;
  FUN_e7b5(0x24);
  DAT_0002 = 1;
  DAT_0003 = 0xaa;
  FUN_e7b5(0x28);
  return;
}



/* 0xe823 FUN_e823 */

void FUN_e823(void)

{
  byte bVar1;
  
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x200) = 0xf0;
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



/* 0xe830 FUN_e830 */

void FUN_e830(void)

{
  byte bVar1;
  
  bVar1 = DAT_007c;
  if (DAT_007c != 0xff) {
    do {
      *(undefined1 *)(bVar1 + 0x200) = 0xf0;
      bVar1 = bVar1 + 4;
    } while (bVar1 != 0);
  }
  return;
}



/* 0xe87a FUN_e87a */

undefined1 FUN_e87a(undefined1 param_1)

{
  ushort uVar1;
  
  DAT_0051 = param_1;
  uVar1 = (ushort)DAT_0050;
  DAT_0050 = DAT_0050 + 1;
  return (&DAT_e8ba)[uVar1];
}



/* 0xeaf7 FUN_eaf7 */

void FUN_eaf7(void)

{
  DAT_2005 = DAT_0090;
  DAT_008b = DAT_008f & 1 | DAT_008b & 0xfe;
  DAT_2000 = DAT_008b;
  return;
}



/* 0xec67 FUN_ec67 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ec67(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  
  if (DAT_0087 < '\0') {
    return;
  }
  if (-1 < (char)(DAT_008a + -1)) {
    DAT_008a = DAT_008a + -1;
    return;
  }
  DAT_008a = DAT_0089;
  DAT_007d = 1;
  if (DAT_0087 == '\0') {
    DAT_0088 = DAT_0088 - 1;
    if (DAT_0088 != 0) goto LAB_ec98;
  }
  else {
    DAT_0088 = DAT_0088 + 1;
    if (DAT_0088 < 4) goto LAB_ec98;
  }
  DAT_0087 = -1;
LAB_ec98:
  _DAT_0000 = 0x100;
  _DAT_0002 = &DAT_0120;
  bVar3 = 0x1f;
  do {
    cVar1 = _DAT_0002[bVar3];
    bVar2 = DAT_0088;
    do {
      bVar2 = bVar2 - 1;
      if ((char)bVar2 < '\0') goto LAB_ecb9;
      cVar1 = cVar1 + -0x10;
    } while (-1 < cVar1);
    cVar1 = '\x0f';
LAB_ecb9:
    *(char *)(_DAT_0000 + (ushort)bVar3) = cVar1;
    bVar3 = bVar3 - 1;
    if ((char)bVar3 < '\0') {
      return;
    }
  } while( true );
}



/* 0xecbf FUN_ecbf */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ecbf(void)

{
  byte bVar1;
  
  DAT_0087 = 0;
  DAT_0088 = 4;
  DAT_0089 = 4;
  _DAT_0000 = 0x100;
  _DAT_0002 = &DAT_0120;
  bVar1 = 0;
  do {
    _DAT_0002[bVar1] = *(undefined1 *)(_DAT_0000 + (ushort)bVar1);
    *(undefined1 *)(_DAT_0000 + (ushort)bVar1) = 0xf;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x20);
  return;
}



/* 0xee53 FUN_ee53 */

/* WARNING: Control flow encountered bad instruction data */

byte FUN_ee53(void)

{
  byte bVar1;
  byte bStack0000;
  
  if (DAT_007d == '\0') {
    if ((char)DAT_007e < '\0') {
      bStack0000 = DAT_007e;
      DAT_007e = DAT_007e & 0x7f;
      FUN_ef0b();
      return bStack0000;
    }
    bStack0000 = DAT_007e << 1;
    if ((char)bStack0000 < '\0') {
      DAT_007e = DAT_007e & 0xbf;
      FUN_ef71();
      return bStack0000;
    }
    if ((char)(DAT_007e << 2) < '\0') {
      DAT_007e = DAT_007e & 0xdf;
      bVar1 = FUN_efc0();
      return bVar1;
    }
    if ((char)(DAT_007e << 3) < '\0') {
      DAT_007e = DAT_007e & 0xef;
      bVar1 = FUN_f028();
      return bVar1;
    }
    if ((char)(DAT_007e << 4) < '\0') {
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      DAT_007e = DAT_007e & 0xf7;
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
    if ((char)(DAT_007e << 5) < '\0') {
      DAT_007e = DAT_007e & 0xfb;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
    if ((char)(DAT_007e << 6) < '\0') {
      DAT_007e = DAT_007e & 0xfd;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
    if ((char)(DAT_007e << 7) < '\0') {
      bStack0000 = 0xee;
      FUN_f237(DAT_007e << 7,0x3d);
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  }
  bVar1 = FUN_e70e();
  return bVar1;
}



/* 0xef0b FUN_ef0b */

void FUN_ef0b(void)

{
  byte bVar1;
  
  DAT_0001 = (((DAT_0140 & 3) << 1 | DAT_0141 >> 7) << 1 | (DAT_0141 & 0x7f) >> 6) << 1 |
             (DAT_0141 & 0x3f) >> 5;
  DAT_0000 = 0x1e - DAT_0001;
  DAT_2000 = DAT_008b | 4;
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_0142)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0000);
  DAT_2006 = DAT_0141 & 0x1f;
  do {
    if (0x1d < bVar1) {
      return;
    }
    DAT_2007 = (&DAT_0142)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



/* 0xef71 FUN_ef71 */

void FUN_ef71(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_0000 = 0x20 - (DAT_0165 & 0x1f);
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_0166)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0000);
  DAT_2006 = DAT_0165 & 0xe0;
  do {
    if (0x1f < bVar1) {
      return;
    }
    DAT_2007 = (&DAT_0166)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



/* 0xefc0 FUN_efc0 */

void FUN_efc0(void)

{
  byte bVar1;
  byte bVar2;
  
  DAT_0001 = DAT_0189;
  DAT_0000 = 8 - ((DAT_0189 & 0x38) >> 3);
  bVar2 = 0;
  do {
    DAT_2006 = DAT_0001;
    DAT_2007 = (&DAT_018a)[bVar2];
    DAT_0001 = DAT_0001 + 8;
    bVar2 = bVar2 + 1;
  } while (bVar2 < DAT_0000);
  bVar1 = DAT_0189 & 199;
  do {
    DAT_0001 = bVar1;
    if (7 < bVar2) {
      return;
    }
    DAT_2006 = DAT_0001;
    DAT_2007 = (&DAT_018a)[bVar2];
    bVar2 = bVar2 + 1;
    bVar1 = DAT_0001 + 8;
  } while (bVar2 != 0);
  DAT_0001 = DAT_0001 + 8;
  return;
}



/* 0xf028 FUN_f028 */

void FUN_f028(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_0000 = 8 - (DAT_019d & 7);
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_019e)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0000);
  DAT_2006 = DAT_019d & 0xf8;
  do {
    if (7 < bVar1) {
      return;
    }
    DAT_2007 = (&DAT_019e)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



/* 0xf077 FUN_f077 */

void FUN_f077(void)

{
  if (((DAT_009c ^ DAT_009d) & 0xc0) != 0) {
    DAT_0095 = 0xff;
  }
  if (((DAT_009c ^ DAT_009d) & 0x30) != 0) {
    DAT_0094 = 0xff;
  }
  return;
}



/* 0xf206 FUN_f206 */

void FUN_f206(void)

{
  DAT_8000 = DAT_00ae;
  DAT_8800 = DAT_00af;
  DAT_9000 = DAT_00b0;
  DAT_9800 = DAT_00b1;
  SUB_a000 = DAT_00b2;
  DAT_a800 = DAT_00b3;
  DAT_b000 = DAT_00b4;
  DAT_b800 = DAT_00b5;
  return;
}



/* 0xf237 FUN_f237 */

undefined1 FUN_f237(undefined1 param_1,byte param_2)

{
  DAT_00e2 = param_2;
  DAT_00e3 = param_2 + 1;
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  cRAMf000 = param_2 + 1;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  bRAMe800 = param_2 | 0xc0;
  return param_1;
}



/* 0xf24b FUN_f24b */

undefined1 FUN_f24b(undefined1 param_1,byte param_2)

{
  DAT_00df = param_2;
  DAT_00e0 = param_2 + 1;
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  cRAMf000 = param_2 + 1;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  bRAMe800 = param_2 | 0xc0;
  return param_1;
}



/* 0xf25f select_data_bank */

void select_data_bank(code param_1)

{
  DAT_00e1 = param_1;
  reset_dispatch = param_1;
  return;
}



/* 0xf2af record32_address */

void record32_address(byte param_1)

{
  DAT_0000 = param_1 * ' ';
  DAT_0001 = (((((param_1 >> 7) << 1 | (param_1 & 0x7f) >> 6) << 1 | (param_1 & 0x3f) >> 5) << 1 |
              (param_1 & 0x1f) >> 4) << 1 | (param_1 & 0xf) >> 3) + 0x60;
  return;
}



/* 0xf2d7 record12_address */

void record12_address(byte param_1)

{
  DAT_0000 = param_1 * '\f' - 0x40;
  DAT_0001 = (((CARRY1(param_1 * '\x02',param_1) - ((char)param_1 >> 7)) * '\x02' |
              (byte)(param_1 * '\x03') >> 7) << 1 | (param_1 * '\x03' & 0x7f) >> 6) + 99 +
             (0x3f < (byte)(param_1 * '\f'));
  return;
}



/* 0xf3bd FUN_f3bd */

void FUN_f3bd(void)

{
  byte bVar1;
  char cVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  DAT_5000 = 0;
  DAT_5800 = 0;
  DAT_c000 = 0xe0;
  DAT_d000 = 0xe0;
  DAT_c800 = 0xe1;
  DAT_d800 = 0xe1;
  bVar1 = 0;
  do {
    DAT_0001 = (byte)FUN_f3bd[bVar1] & 1;
    DAT_4016 = DAT_0001;
    if (((DAT_4017 >> 1 ^ 0xff) & 1) != DAT_0001) {
      return;
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0x46);
  nmi = (code)0x40;
  bVar3 = false;
  uStack0000 = 0xf3;
  FUN_f422();
  if (!bVar3) {
    uStack0000 = 0xf4;
    FUN_f43f();
    uStack0000 = 0xf4;
    FUN_f422();
  }
  cVar2 = '\0';
  do {
    cVar2 = cVar2 + '\x01';
  } while (cVar2 != ' ');
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



/* 0xf422 FUN_f422 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

char FUN_f422(byte param_1)

{
  char cVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xf4;
  FUN_f458();
  do {
    do {
      if (*(char *)(_DAT_0002 + (ushort)param_1) != DAT_0000) {
        return *(char *)(_DAT_0002 + (ushort)param_1);
      }
      uStack0000 = 0xf4;
      FUN_f468();
      param_1 = param_1 + 1;
    } while (param_1 != 0);
    cVar1 = DAT_0003 + '\x01';
    _DAT_0002 = CONCAT11(cVar1,DAT_0002);
  } while (cVar1 != -0x80);
  return '\0';
}



/* 0xf43f FUN_f43f */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_f43f(byte param_1)

{
  char cVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xf4;
  FUN_f458();
  do {
    do {
      *(undefined1 *)(_DAT_0002 + (ushort)param_1) = DAT_0000;
      uStack0000 = 0xf4;
      FUN_f468();
      param_1 = param_1 + 1;
    } while (param_1 != 0);
    cVar1 = DAT_0003 + '\x01';
    _DAT_0002 = CONCAT11(cVar1,DAT_0002);
  } while (cVar1 != -0x80);
  return;
}



/* 0xf458 FUN_f458 */

void FUN_f458(void)

{
  DAT_0002 = 0;
  DAT_0003 = 0x60;
  DAT_0000 = 0xaa;
  return;
}



/* 0xf468 FUN_f468 */

void FUN_f468(void)

{
  do {
    DAT_0000 = DAT_0000 * '\x05' + '\x01';
  } while (DAT_0000 == '\0');
  return;
}



/* 0xf800 nmi */

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



/* 0xf8af FUN_f8af */

undefined1 FUN_f8af(void)

{
  undefined1 in_stack_00000003;
  
  return in_stack_00000003;
}



/* 0xfa97 switchD_f878::caseD_0 */

undefined1 switchD_f878::caseD_0(void)

{
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
  uStack0000 = 0xfa;
  FUN_fb0b();
  uStack0000 = 0xfa;
  FUN_f206();
  uStack0000 = 0xfa;
  FUN_e6c6();
  uStack0000 = 0xfa;
  FUN_ff62();
  uStack0000 = 0xfa;
  FUN_fb28();
  DAT_007b = DAT_007b + -1;
  reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  bRAMe800 = DAT_00df | 0xc0;
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
  return in_stack_00000003;
}



/* 0xfaa9 FUN_faa9 */

void FUN_faa9(void)

{
  undefined1 uVar1;
  undefined1 uVar2;
  
  uVar2 = DAT_0083;
  uVar1 = DAT_0081;
  if (DAT_6f44 != '\0') {
    DAT_0081 = DAT_0082;
    DAT_0082 = uVar1;
    DAT_0083 = DAT_0085;
    DAT_0085 = uVar2;
  }
  return;
}



/* 0xfabf FUN_fabf */

void FUN_fabf(void)

{
  undefined1 uVar1;
  undefined1 uVar2;
  
  uVar2 = DAT_0085;
  uVar1 = DAT_0082;
  if (DAT_6f44 != '\0') {
    DAT_0082 = DAT_0081;
    DAT_0081 = uVar1;
    DAT_0085 = DAT_0083;
    DAT_0083 = uVar2;
  }
  return;
}



/* 0xfad5 FUN_fad5 */

void FUN_fad5(void)

{
  code cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xfa;
  FUN_f206();
  uStack0000 = 0xfa;
  FUN_fb0b();
  bVar2 = DAT_00e2;
  cVar1 = DAT_00e1;
  uStack0000 = DAT_00e3;
  FUN_f237(0x2e);
  func_0xa003();
  nmi = DAT_00a5;
  reset_dispatch = cVar1;
  bRAMe800 = bVar2 | 0xc0;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  DAT_00e3 = uStack0000;
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  uRAMf000 = uStack0000;
  uStack0000 = 0xfb;
  DAT_00e1 = cVar1;
  DAT_00e2 = bVar2;
  FUN_fb28();
  FUN_f8af();
  return;
}



/* 0xfb0b FUN_fb0b */

void FUN_fb0b(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xfb;
  FUN_eaf7();
  DAT_c000 = DAT_00e6;
  DAT_c800 = DAT_00e7;
  DAT_d000 = DAT_00e8;
  DAT_d800 = DAT_00e9;
  do {
  } while ((DAT_2002 & 0x40) == 0x40);
  return;
}



/* 0xfb28 FUN_fb28 */

void FUN_fb28(void)

{
  do {
  } while (DAT_0062 != '\0');
  return;
}



/* 0xfb2d irq */

undefined1 irq(undefined1 param_1)

{
  byte bVar1;
  char cVar2;
  char cVar3;
  
  if ((DAT_5800 & 0x7f) != 0x7f) {
    do {
                    /* WARNING: Do nothing block with infinite loop */
    } while( true );
  }
  if (DAT_0060 == '\0') {
    DAT_0062 = 0;
    DAT_5000 = 0;
    DAT_5800 = 0;
    return param_1;
  }
  if (DAT_0060 != '\x01') {
    if (DAT_0060 == '\x02') {
      cVar2 = '\b';
      do {
        cVar2 = cVar2 + -1;
      } while (-1 < cVar2);
      bVar1 = (DAT_0099 & 7) << 1;
      DAT_0046 = (&DAT_fd1a)[bVar1];
      DAT_0047 = (&DAT_fd1b)[bVar1];
      do {
        DAT_0046 = DAT_0046 + -1;
      } while (DAT_0046 != '\0');
      do {
        DAT_0047 = DAT_0047 + -1;
      } while (DAT_0047 != '\0');
      cVar2 = '\x1b';
      do {
        cVar2 = cVar2 + -1;
      } while (cVar2 != '\0');
      DAT_0046 = 0;
      DAT_0047 = 0;
      DAT_0062 = 0;
      DAT_2005 = DAT_0096;
      DAT_2006 = DAT_009a;
      DAT_5000 = 0;
      DAT_5800 = 0;
      DAT_8000 = DAT_00b6;
      DAT_8800 = DAT_00b7;
      DAT_9000 = DAT_00b8;
      DAT_9800 = DAT_00b9;
      SUB_a000 = DAT_00ba;
      DAT_a800 = DAT_00bb;
      DAT_b000 = DAT_00bc;
      DAT_b800 = DAT_00bd;
      DAT_c700 = DAT_00ea;
      return param_1;
    }
    if (DAT_0060 != '\x03') {
      cVar2 = DAT_0072;
      if (DAT_0060 == '\x04') {
        do {
          cVar2 = cVar2 + -1;
          cVar3 = DAT_0073;
        } while (-1 < cVar2);
        do {
          cVar3 = cVar3 + -1;
          cVar2 = DAT_0074;
        } while (-1 < cVar3);
        do {
          cVar2 = cVar2 + -1;
        } while (-1 < cVar2);
        DAT_0062 = 0;
        DAT_2005 = DAT_0096;
        DAT_2006 = DAT_009a;
        DAT_5000 = 0;
        DAT_5800 = 0;
        DAT_8000 = DAT_00b6;
        DAT_8800 = DAT_00b7;
        DAT_9000 = DAT_00b8;
        DAT_9800 = DAT_00b9;
        SUB_a000 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        DAT_c700 = DAT_00ea;
        return param_1;
      }
      if (DAT_0060 == '\x05') {
LAB_fd95:
        cVar2 = '0';
        do {
          cVar2 = cVar2 + -1;
        } while (-1 < cVar2);
        DAT_0062 = 0;
        DAT_2005 = DAT_0096;
        DAT_2006 = DAT_009a;
        DAT_5000 = 0;
        DAT_5800 = 0;
        DAT_8000 = DAT_00b6;
        DAT_8800 = DAT_00b7;
        DAT_9000 = DAT_00b8;
        DAT_9800 = DAT_00b9;
        SUB_a000 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        DAT_c700 = 0xe1;
        DAT_c800 = 0xe1;
        DAT_d000 = 0xe1;
        DAT_d800 = 0xe1;
        return param_1;
      }
      if (DAT_0060 == '\x06') {
        DAT_0062 = 0;
        DAT_5000 = 0;
        DAT_5800 = 0;
        return param_1;
      }
      if (DAT_0060 == '\a') {
        DAT_5000 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6a);
        DAT_5800 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6b);
        if (DAT_0063 == '\0') {
          DAT_c700 = 0xe1;
          DAT_d000 = 0xe1;
          DAT_c800 = 0xe1;
          DAT_d800 = 0xe1;
          DAT_2006 = 0xb8;
          DAT_2005 = 0;
          goto LAB_fbce;
        }
        if (DAT_0063 == '\x01') goto LAB_fbfc;
        if (DAT_0063 != '\x02') {
          DAT_0063 = '\0';
          goto LAB_fd95;
        }
        goto LAB_fc2a;
      }
      if (DAT_0060 == '\b') {
        DAT_5000 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6a);
        DAT_5800 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6b);
        if (DAT_0063 == '\0') goto LAB_fbce;
        if (DAT_0063 == '\x01') goto LAB_fbfc;
        if (DAT_0063 == '\x02') goto LAB_fc2a;
        goto LAB_fc58;
      }
      if (DAT_0060 == '\t') {
        DAT_0062 = 0;
        DAT_5000 = 0;
        DAT_5800 = 0;
        DAT_8000 = DAT_00b6;
        DAT_8800 = DAT_00b7;
        DAT_9000 = DAT_00b8;
        DAT_9800 = DAT_00b9;
        SUB_a000 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        return param_1;
      }
      if (DAT_0060 == '\n') {
        cVar2 = '\x10';
        do {
          cVar2 = cVar2 + -1;
        } while (-1 < cVar2);
        DAT_0062 = 0;
        DAT_2005 = 0;
        DAT_2006 = DAT_009a;
        DAT_5000 = 0;
        DAT_5800 = 0;
        DAT_8000 = DAT_00b6;
        DAT_8800 = DAT_00b7;
        DAT_9000 = DAT_00b8;
        DAT_9800 = DAT_00b9;
        SUB_a000 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        DAT_c000 = DAT_00ea;
        return param_1;
      }
      if (DAT_0060 == '\v') {
        DAT_5000 = DAT_006a;
        DAT_5800 = DAT_006b;
        DAT_0060 = '\f';
        goto LAB_fbce;
      }
      if (DAT_0060 != '\f') {
        DAT_0062 = 0;
        DAT_5000 = 0;
        DAT_5800 = 0;
        return param_1;
      }
      DAT_5000 = DAT_006c;
      DAT_5800 = DAT_006d;
      DAT_0060 = '\n';
      goto LAB_fbfc;
    }
  }
  DAT_5000 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6a);
  DAT_5800 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6b);
  if (DAT_0063 == '\0') {
LAB_fbce:
    DAT_0063 = DAT_0063 + '\x01';
    DAT_8000 = DAT_00be;
    DAT_8800 = DAT_00bf;
    DAT_9000 = DAT_00c0;
    DAT_9800 = DAT_00c1;
    SUB_a000 = DAT_00c2;
    DAT_a800 = DAT_00c3;
    DAT_b000 = DAT_00c4;
    DAT_b800 = DAT_00c5;
    return param_1;
  }
  if (DAT_0063 != '\x01') {
    if (DAT_0063 != '\x02') {
LAB_fc58:
      DAT_0060 = DAT_0060 + '\x01';
      DAT_0063 = 0;
      DAT_8000 = DAT_00d6;
      DAT_8800 = DAT_00d7;
      DAT_9000 = DAT_00d8;
      DAT_9800 = DAT_00d9;
      SUB_a000 = DAT_00da;
      DAT_a800 = DAT_00db;
      DAT_b000 = DAT_00dc;
      DAT_b800 = DAT_00dd;
      return param_1;
    }
LAB_fc2a:
    DAT_0063 = DAT_0063 + '\x01';
    DAT_8000 = DAT_00ce;
    DAT_8800 = DAT_00cf;
    DAT_9000 = DAT_00d0;
    DAT_9800 = DAT_00d1;
    SUB_a000 = DAT_00d2;
    DAT_a800 = DAT_00d3;
    DAT_b000 = DAT_00d4;
    DAT_b800 = DAT_00d5;
    return param_1;
  }
LAB_fbfc:
  DAT_b800 = DAT_00cd;
  DAT_b000 = DAT_00cc;
  DAT_a800 = DAT_00cb;
  SUB_a000 = DAT_00ca;
  DAT_9800 = DAT_00c9;
  DAT_9000 = DAT_00c8;
  DAT_8800 = DAT_00c7;
  DAT_8000 = DAT_00c6;
  DAT_0063 = DAT_0063 + '\x01';
  return param_1;
}



/* 0xff62 FUN_ff62 */

void FUN_ff62(void)

{
  DAT_0099 = DAT_0098;
  DAT_0047 = (DAT_0098 >> 7) << 1 | (DAT_0098 & 0x78) >> 6;
  DAT_009a = (DAT_0098 & 0xf8) << 2;
  DAT_009b = DAT_0047 + 0x20;
  DAT_00ea = 0xe0;
  DAT_00ec = 0xe0;
  if ((DAT_0097 & 1) != 0) {
    DAT_00ea = 0xe1;
    DAT_00ec = 0xe1;
  }
  return;
}



/* 0xff9b FUN_ff9b */

void FUN_ff9b(void)

{
  DAT_0099 = DAT_0098;
  DAT_0047 = (DAT_0098 >> 7) << 1 | (DAT_0098 & 0x78) >> 6;
  DAT_009a = (DAT_0098 & 0xf8) << 2;
  DAT_009b = DAT_0047 + 0x20;
  DAT_00ea = 0xe0;
  if ((DAT_0097 & 1) != 0) {
    DAT_009b = DAT_0047 + 0x24;
    DAT_00ea = 0xe1;
  }
  return;
}


