// Ghidra-generated fixed-bank-pair pseudocode. Bank switching and inline pointer dispatch need manual correction. Not original source.

/* 0xa000 bank12_entry_00 */

void bank12_entry_00(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_df88();
  uStack0000 = 0xa0;
                    /* WARNING: Subroutine does not return */
  far_call_inline_word(0x28);
}



/* 0xa003 thunk_FUN_dc99 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_dc99(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xdc;
  FUN_f25f(0x31);
  bVar1 = DAT_0402 << 2;
  DAT_0512 = *(byte *)(bVar1 + 0x9d5a) + 0x80;
  bVar2 = ~*(byte *)(bVar1 + 0x9d5a);
  DAT_0513 = *(byte *)(bVar1 + 0x9d5b) -
             (((bVar2 & 0x80) == 0 && (DAT_0512 & 0x80) == 0) && (DAT_0512 & bVar2 & 0x80) == 0);
  if ((DAT_0513 & ~*(byte *)(bVar1 + 0x9d5b) & 0x80) == 0) {
    DAT_0512 = 0;
    DAT_0513 = 0;
  }
  if (DAT_0513 != 0) {
    DAT_0512 = 0xfe;
    DAT_0513 = 0;
  }
  DAT_0510 = *(byte *)(bVar1 + 0x9d58) + 0xa0;
  DAT_0511 = *(byte *)(bVar1 + 0x9d59) - ((DAT_0510 & ~*(byte *)(bVar1 + 0x9d58) & 0x80) == 0);
  if ((DAT_0511 & ~*(byte *)(bVar1 + 0x9d59) & 0x80) == 0) {
    DAT_0510 = 0;
    DAT_0511 = 0;
  }
  if (0x8f < DAT_0510) {
    DAT_0510 = 0x8e;
    DAT_0511 = 0;
  }
  DAT_052a = DAT_0402;
  DAT_050c = 0;
  DAT_050d = 0;
  DAT_051a = 0;
  DAT_051b = 0;
  DAT_051c = 0;
  DAT_051d = 0;
  DAT_051e = 0;
  DAT_051f = 0;
  DAT_0520 = 0;
  DAT_0521 = 0;
  DAT_052b = 0xff;
  bVar2 = 0x27;
  do {
    *(undefined1 *)(bVar2 + 0x6f47) = 0xff;
    bVar2 = bVar2 - 1;
  } while (-1 < (char)bVar2);
  bVar2 = 0x13;
  do {
    if (*(char *)(bVar2 + 0x664) == -1) {
      *(undefined1 *)(bVar2 + 0x600) = 0xff;
      *(undefined1 *)(bVar2 + 0x614) = 0xff;
      *(undefined1 *)(bVar2 + 0x628) = 0xff;
      *(undefined1 *)(bVar2 + 0x63c) = 0xff;
      *(undefined1 *)(bVar2 + 0x650) = 0xff;
    }
    else {
      uStack0000 = 0xdd;
      officer_address();
      *(undefined1 *)(bVar2 + 0x600) = 0xff;
      *(undefined1 *)(bVar2 + 0x614) = 0xff;
      bVar1 = *(byte *)(_DAT_0000 + 0xb) >> 2 & 3;
      if (9 < bVar2) {
        bVar1 = bVar1 | 0x80;
      }
      *(byte *)(bVar2 + 0x628) = bVar1;
      *(undefined1 *)(bVar2 + 0x650) = 0;
    }
    bVar2 = bVar2 - 1;
  } while (-1 < (char)bVar2);
  uStack0000 = 0xdd;
  FUN_db03();
  return;
}



/* 0xa006 thunk_FUN_c766 */

void thunk_FUN_c766(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 199;
  FUN_db03();
  uStack0000 = 199;
  FUN_c75b(DAT_0514);
  uStack0000 = 199;
  FUN_c782(DAT_0515);
  uStack0000 = 199;
  FUN_c75b(DAT_0516);
  uStack0000 = 199;
  FUN_c782(DAT_0517);
  return;
}



/* 0xa009 FUN_a009 */

void FUN_a009(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_df88();
  uStack0000 = 0xa0;
                    /* WARNING: Subroutine does not return */
  far_call_inline_word(0x28);
}



/* 0xa00c FUN_a00c */

void FUN_a00c(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
                    /* WARNING: Subroutine does not return */
  far_call_inline_word(0x28);
}



/* 0xa012 FUN_a012 */

void FUN_a012(void)

{
  undefined2 uStack0000;
  
                    /* WARNING: Subroutine does not return */
  uStack0000 = 0xa018;
  far_call_inline_word(0xa0);
}



/* 0xa015 far_call_inline_word */

void far_call_inline_word(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
                    /* WARNING: Subroutine does not return */
  far_call_inline_word();
}



/* 0xa01b FUN_a01b */

void FUN_a01b(byte param_1)

{
  undefined2 uStack0001;
  
                    /* WARNING: Subroutine does not return */
  uStack0001 = 0xa025;
  far_call_inline_word(param_1 & bRAMa0ff);
}



/* 0xa01e FUN_a01e */

void FUN_a01e(byte param_1,byte param_2)

{
  undefined2 uStack0000;
  
                    /* WARNING: Subroutine does not return */
  uStack0000 = 0xa025;
  far_call_inline_word(param_1 & (&DAT_a0df)[param_2]);
}



/* 0xa03f FUN_a03f */

/* WARNING: Control flow encountered bad instruction data */

void FUN_a03f(void)

{
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



/* 0xa1f7 FUN_a1f7 */

void FUN_a1f7(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa1;
  FUN_f293(5);
  DAT_0012 = 1;
  uStack0000 = 0xa2;
  thunk_FUN_d6d0();
  DAT_0424 = 0;
  DAT_0425 = 0;
  return;
}



/* 0xb02b FUN_b02b */

void FUN_b02b(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x42c) = 0;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 9);
  DAT_0544 = 0;
  uStack0000 = 0xb0;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0543 & 0xf);
}



/* 0xc75b FUN_c75b */

void FUN_c75b(char param_1)

{
  byte bVar1;
  
  bVar1 = 0x13;
  do {
    if (param_1 == *(char *)(bVar1 + 0x664)) {
      return;
    }
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  return;
}



/* 0xc766 FUN_c766 */

void FUN_c766(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 199;
  FUN_db03();
  uStack0000 = 199;
  FUN_c75b(DAT_0514);
  uStack0000 = 199;
  FUN_c782(DAT_0515);
  uStack0000 = 199;
  FUN_c75b(DAT_0516);
  uStack0000 = 199;
  FUN_c782(DAT_0517);
  return;
}



/* 0xc782 FUN_c782 */

void FUN_c782(byte param_1)

{
  undefined1 uStack0000;
  
  uStack0000 = 199;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(param_1 & 7);
}



/* 0xd6cc thunk_FUN_d6d0 */

void thunk_FUN_d6d0(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0010 = *(byte *)(DAT_0509 + 0x600);
  DAT_0011 = *(byte *)(DAT_0509 + 0x614);
  DAT_0000 = DAT_0090 >> 4;
  if ((byte)(DAT_0011 - DAT_0000) < 0xf) {
    if (DAT_008e < 0xfc) {
      DAT_0000 = (byte)(DAT_008e + 4) >> 4;
    }
    else {
      DAT_0000 = 0x10;
    }
    if ((byte)(DAT_0010 - DAT_0000) < 0x10) {
      bVar1 = 0xf < DAT_0010;
      if (0xf < DAT_0011) {
        bVar1 = bVar1 | 2;
      }
      DAT_0000 = *(undefined1 *)(DAT_00a8 + (ushort)bVar1);
      uStack0000 = *(undefined1 *)(DAT_00a8 + (ushort)(bVar1 ^ 1));
                    /* WARNING: Subroutine does not return */
      far_call_inline_word(0x37);
    }
  }
  return;
}



/* 0xd6d0 FUN_d6d0 */

void FUN_d6d0(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0010 = *(byte *)(DAT_0509 + 0x600);
  DAT_0011 = *(byte *)(DAT_0509 + 0x614);
  DAT_0000 = DAT_0090 >> 4;
  if ((byte)(DAT_0011 - DAT_0000) < 0xf) {
    if (DAT_008e < 0xfc) {
      DAT_0000 = (byte)(DAT_008e + 4) >> 4;
    }
    else {
      DAT_0000 = 0x10;
    }
    if ((byte)(DAT_0010 - DAT_0000) < 0x10) {
      bVar1 = 0xf < DAT_0010;
      if (0xf < DAT_0011) {
        bVar1 = bVar1 | 2;
      }
      DAT_0000 = *(undefined1 *)(DAT_00a8 + (ushort)bVar1);
      uStack0000 = *(undefined1 *)(DAT_00a8 + (ushort)(bVar1 ^ 1));
                    /* WARNING: Subroutine does not return */
      far_call_inline_word(0x37);
    }
  }
  return;
}



/* 0xdb03 FUN_db03 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_db03(void)

{
  char cVar1;
  byte bVar2;
  byte bStack0000;
  
  bStack0000 = 0xdb;
  FUN_f25f(0x31);
  bVar2 = 0x13;
  do {
    cVar1 = *(char *)(bVar2 + 0x664);
    bStack0000 = bVar2;
    if (*(char *)(bVar2 + 0x664) != -1) {
      bStack0000 = 0xdb;
      officer_address();
      _DAT_0000 = *(ushort *)(_DAT_0000 + 8) & 0x3ff;
      DAT_0002 = 0;
      DAT_0003 = 100;
      DAT_0004 = 0;
      bStack0000 = bVar2;
      FUN_eaa5();
      cVar1 = DAT_0000;
    }
    *(char *)(bStack0000 + 0x63c) = cVar1;
    bVar2 = bStack0000 - 1;
  } while (-1 < (char)bVar2);
  return;
}



/* 0xdc99 FUN_dc99 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_dc99(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xdc;
  FUN_f25f(0x31);
  bVar1 = DAT_0402 << 2;
  DAT_0512 = *(byte *)(bVar1 + 0x9d5a) + 0x80;
  bVar2 = ~*(byte *)(bVar1 + 0x9d5a);
  DAT_0513 = *(byte *)(bVar1 + 0x9d5b) -
             (((bVar2 & 0x80) == 0 && (DAT_0512 & 0x80) == 0) && (DAT_0512 & bVar2 & 0x80) == 0);
  if ((DAT_0513 & ~*(byte *)(bVar1 + 0x9d5b) & 0x80) == 0) {
    DAT_0512 = 0;
    DAT_0513 = 0;
  }
  if (DAT_0513 != 0) {
    DAT_0512 = 0xfe;
    DAT_0513 = 0;
  }
  DAT_0510 = *(byte *)(bVar1 + 0x9d58) + 0xa0;
  DAT_0511 = *(byte *)(bVar1 + 0x9d59) - ((DAT_0510 & ~*(byte *)(bVar1 + 0x9d58) & 0x80) == 0);
  if ((DAT_0511 & ~*(byte *)(bVar1 + 0x9d59) & 0x80) == 0) {
    DAT_0510 = 0;
    DAT_0511 = 0;
  }
  if (0x8f < DAT_0510) {
    DAT_0510 = 0x8e;
    DAT_0511 = 0;
  }
  DAT_052a = DAT_0402;
  DAT_050c = 0;
  DAT_050d = 0;
  DAT_051a = 0;
  DAT_051b = 0;
  DAT_051c = 0;
  DAT_051d = 0;
  DAT_051e = 0;
  DAT_051f = 0;
  DAT_0520 = 0;
  DAT_0521 = 0;
  DAT_052b = 0xff;
  bVar2 = 0x27;
  do {
    *(undefined1 *)(bVar2 + 0x6f47) = 0xff;
    bVar2 = bVar2 - 1;
  } while (-1 < (char)bVar2);
  bVar2 = 0x13;
  do {
    if (*(char *)(bVar2 + 0x664) == -1) {
      *(undefined1 *)(bVar2 + 0x600) = 0xff;
      *(undefined1 *)(bVar2 + 0x614) = 0xff;
      *(undefined1 *)(bVar2 + 0x628) = 0xff;
      *(undefined1 *)(bVar2 + 0x63c) = 0xff;
      *(undefined1 *)(bVar2 + 0x650) = 0xff;
    }
    else {
      uStack0000 = 0xdd;
      officer_address();
      *(undefined1 *)(bVar2 + 0x600) = 0xff;
      *(undefined1 *)(bVar2 + 0x614) = 0xff;
      bVar1 = *(byte *)(_DAT_0000 + 0xb) >> 2 & 3;
      if (9 < bVar2) {
        bVar1 = bVar1 | 0x80;
      }
      *(byte *)(bVar2 + 0x628) = bVar1;
      *(undefined1 *)(bVar2 + 0x650) = 0;
    }
    bVar2 = bVar2 - 1;
  } while (-1 < (char)bVar2);
  uStack0000 = 0xdd;
  FUN_db03();
  return;
}



/* 0xdf88 FUN_df88 */

void FUN_df88(void)

{
  if (DAT_0061 == '\x05') {
    if (DAT_008e < 0x10) {
      DAT_0068 = 0x72;
      return;
    }
    DAT_0068 = 0x74;
  }
  return;
}



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



/* 0xe370 FUN_e370 */

void FUN_e370(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xe3;
  FUN_f237(0x3d);
  uStack0000 = 0xe3;
  FUN_a01b();
  uStack0000 = 0xe3;
  FUN_f206();
  return;
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
  LAB_f800 = 0x4c;
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
  LAB_f800 = 0x80;
  bVar1 = 0;
  do {
    DAT_4800 = (&DAT_e6a6)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x20);
  uStack0000 = 0xe5;
  FUN_e5fa(0xf0,100);
  LAB_f800 = 0x7f;
  DAT_4800 = 0x30;
  return;
}



/* 0xe5f3 FUN_e5f3 */

void FUN_e5f3(undefined1 param_1,undefined1 param_2)

{
  LAB_f800 = param_2;
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
  bVar1 = FUN_f25f(0x22);
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



/* 0xe74d FUN_e74d */

void FUN_e74d(void)

{
  DAT_008c = 0;
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



/* 0xeaa5 FUN_eaa5 */

void FUN_eaa5(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  
  DAT_0005 = 0;
  DAT_0006 = 0;
  DAT_0007 = 0;
  cVar2 = '\x17';
  do {
    bVar3 = DAT_0000 >> 7;
    DAT_0000 = DAT_0000 * '\x02';
    bVar4 = DAT_0001 >> 7;
    DAT_0001 = DAT_0001 << 1 | bVar3;
    bVar3 = DAT_0002 >> 7;
    DAT_0002 = DAT_0002 << 1 | bVar4;
    bVar3 = DAT_0005 << 1 | bVar3;
    bVar4 = DAT_0006 << 1 | DAT_0005 >> 7;
    DAT_0007 = DAT_0007 << 1 | DAT_0006 >> 7;
    DAT_0008 = bVar3 - DAT_0003;
    DAT_0009 = (bVar4 - DAT_0004) -
               (((DAT_0003 & (~bVar3 | DAT_0008) | DAT_0008 & ~bVar3) & 0x80) == 0);
    bVar1 = DAT_0007 - (((DAT_0004 & (~bVar4 | DAT_0009) | DAT_0009 & ~bVar4) & 0x80) == 0);
    DAT_0005 = bVar3;
    DAT_0006 = bVar4;
    if ((bVar1 & ~DAT_0007 & 0x80) != 0) {
      DAT_0000 = DAT_0000 + 1;
      DAT_0005 = DAT_0008;
      DAT_0006 = DAT_0009;
      DAT_0007 = bVar1;
    }
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  return;
}



/* 0xeade tail_dispatch_inline_table */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void tail_dispatch_inline_table(char param_1,undefined1 param_2)

{
  undefined1 unaff_retaddr;
  undefined1 unaff_retaddr_00;
  
  _DAT_0001 = CONCAT11(unaff_retaddr_00,unaff_retaddr);
  _DAT_0003 = (code *)CONCAT11(*(undefined1 *)(_DAT_0001 + (ushort)(byte)(param_1 * '\x02' + 2)),
                               *(undefined1 *)(_DAT_0001 + (ushort)(byte)(param_1 * '\x02' + 1)));
  DAT_0000 = param_2;
                    /* WARNING: Could not recover jumptable at 0xeaf4. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*_DAT_0003)(param_2);
  return;
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
  _DAT_0002 = 0x120;
  bVar3 = 0x1f;
  do {
    cVar1 = *(char *)(_DAT_0002 + (ushort)bVar3);
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



/* 0xee07 far_call_inline_word */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void far_call_inline_word(undefined1 param_1)

{
  undefined1 uStack0000;
  byte bStack0001;
  char cStack0002;
  
  DAT_0058 = DAT_00e2;
  _DAT_0059 = (undefined2 *)CONCAT11(cStack0002 + (0xfe < bStack0001),bStack0001 + 1);
  DAT_005b = (code *)*_DAT_0059;
  DAT_005d = param_1;
  FUN_f237(param_1);
  if ((char)(DAT_0059 + '\x01') == '\0') {
    DAT_005a = DAT_005a + '\x01';
  }
  uStack0000 = DAT_0058;
  DAT_0059 = DAT_0059 + '\x01';
                    /* WARNING: Could not recover jumptable at 0xee4a. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*DAT_005b)();
  return;
}



/* 0xee53 FUN_ee53 */

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
      bVar1 = FUN_a00c();
      return bVar1;
    }
    if ((char)(DAT_007e << 5) < '\0') {
      DAT_007e = DAT_007e & 0xfb;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = thunk_FUN_c766();
      return bVar1;
    }
    if ((char)(DAT_007e << 6) < '\0') {
      DAT_007e = DAT_007e & 0xfd;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = FUN_a012();
      return bVar1;
    }
    if ((char)(DAT_007e << 7) < '\0') {
      bStack0000 = 0xee;
      FUN_f237(DAT_007e << 7,0x3d);
      bVar1 = bank12_entry_00();
      return bVar1;
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
  bank12_entry_00 = DAT_00b2;
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



/* 0xf25f FUN_f25f */

void FUN_f25f(code param_1)

{
  DAT_00e1 = param_1;
  reset_dispatch = param_1;
  return;
}



/* 0xf272 FUN_f272 */

void FUN_f272(undefined1 param_1)

{
  DAT_0310 = param_1;
  DAT_0312 = 0xff;
  DAT_0313 = 0xff;
  DAT_0300 = 0;
  return;
}



/* 0xf293 FUN_f293 */

void FUN_f293(undefined1 param_1)

{
  DAT_0311 = param_1;
  FUN_f272(5);
  return;
}



/* 0xf2af region_address */

void region_address(byte param_1)

{
  DAT_0000 = param_1 * ' ';
  DAT_0001 = (((((param_1 >> 7) << 1 | (param_1 & 0x7f) >> 6) << 1 | (param_1 & 0x3f) >> 5) << 1 |
              (param_1 & 0x1f) >> 4) << 1 | (param_1 & 0xf) >> 3) + 0x60;
  return;
}



/* 0xf2d7 officer_address */

void officer_address(byte param_1)

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
  LAB_f800 = 0x40;
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
  bRAMe800 = bRAM00df | 0xc0;
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  uRAMf000 = uRAM00e0;
  cRAM0050 = cRAM0050 + '\x01';
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
  thunk_FUN_dc99();
  LAB_f800 = DAT_00a5;
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


