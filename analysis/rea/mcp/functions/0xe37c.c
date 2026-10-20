
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

