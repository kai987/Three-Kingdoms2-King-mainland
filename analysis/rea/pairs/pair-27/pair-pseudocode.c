// Ghidra-generated fixed-bank-pair pseudocode. Bank switching and inline pointer dispatch need manual correction. Not original source.

/* 0xa000 bank27_entry_00 */

/* WARNING: Control flow encountered bad instruction data */

void bank27_entry_00(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_de83();
  uStack0000 = 0xa0;
  FUN_df35();
  uStack0000 = 0xa0;
  far_call_inline_word(0x39);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



/* 0xa003 thunk_FUN_da02 */

void thunk_FUN_da02(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  DAT_001f = 3;
  DAT_0014 = DAT_048e;
  DAT_0015 = DAT_048f;
  cVar3 = -((char)DAT_0081 >> 7);
  bVar1 = DAT_048b;
  if (cVar3 == '\0') {
    if ((char)(DAT_0081 << 1) < '\0') {
      cVar3 = 2 < DAT_048b;
      if (DAT_048b != 3) {
        DAT_048b = DAT_048b + 1;
      }
    }
    else {
      if ((char)(DAT_0081 << 2) < '\0') {
        uStack0000 = 0xda;
        FUN_db09();
        bVar1 = DAT_048e - DAT_0000;
        DAT_048f = (DAT_048f - DAT_0001) -
                   (((DAT_0000 & (~DAT_048e | bVar1) | bVar1 & ~DAT_048e) & 0x80) == 0);
        DAT_048e = bVar1;
      }
      else {
        bVar1 = DAT_0081 << 4;
        cVar3 = '\0';
        if (-1 < (char)(DAT_0081 << 3)) goto LAB_da91;
        uStack0000 = 0xda;
        FUN_db09(bVar1);
        bVar4 = CARRY1(DAT_048e,DAT_0000);
        DAT_048e = DAT_048e + DAT_0000;
        DAT_048f = DAT_048f + DAT_0001 + bVar4;
      }
      DAT_0000 = DAT_048e;
      DAT_0001 = DAT_048f;
      bVar1 = (DAT_0491 - DAT_048f) -
              (((DAT_048e & (~DAT_0490 | DAT_0490 - DAT_048e) | DAT_0490 - DAT_048e & ~DAT_0490) &
               0x80) == 0);
      cVar3 = ((DAT_048f & (~DAT_0491 | bVar1) | bVar1 & ~DAT_0491) & 0x80) != 0;
      if (!(bool)cVar3) {
        DAT_048e = DAT_0014;
        DAT_048f = DAT_0015;
        bVar1 = DAT_0015;
      }
    }
  }
  else if (DAT_048b != 0) {
    DAT_048b = DAT_048b - 1;
  }
LAB_da91:
  uStack0000 = 0xda;
  FUN_ddad(bVar1);
  if (cVar3 != '\0') {
    DAT_0013 = DAT_0081 & 3;
    DAT_0001 = DAT_048e;
    DAT_0002 = DAT_048f;
    DAT_0003 = 0;
    uStack0000 = 0xda;
    FUN_e9ba();
    DAT_048c = DAT_0007;
    DAT_048d = DAT_0008;
    DAT_0011 = '\x03' - DAT_048b;
    DAT_0010 = 1;
    bVar2 = 2;
    bVar1 = 0;
    do {
      uStack0000 = 0xda;
      FUN_db35((byte)(&DAT_048b)[bVar2] >> 4);
      if (bVar2 == 1) {
        DAT_0010 = 0x76;
      }
      uStack0000 = 0xda;
      FUN_db35((&DAT_048b)[bVar2] & 0xf);
      bVar2 = bVar2 - 1;
    } while (bVar2 != 0);
    (&DAT_031e)[bVar1] = 0x80;
    DAT_0303 = 1;
    DAT_030c = 1;
    DAT_046c = DAT_046c + '\x01';
    DAT_007e = DAT_007e | 1;
  }
  return;
}



/* 0xa006 thunk_FUN_d64a */

byte thunk_FUN_d64a(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  char cVar4;
  undefined1 uStack0000;
  
  DAT_0013 = DAT_0425;
  DAT_0010 = 0x4c;
  DAT_0011 = 0xd7;
  DAT_0012 = 0;
  uStack0000 = 0xd6;
  FUN_ed19();
  cVar4 = DAT_047b <= DAT_0012;
  if (((DAT_0012 != DAT_047b) && ((bool)cVar4)) &&
     (DAT_0012 = DAT_047b, DAT_0425 = DAT_047b, DAT_0013 != 0)) {
    DAT_0012 = 0;
    DAT_0425 = DAT_0012;
  }
  DAT_0010 = 0x58;
  DAT_0011 = 0xd7;
  DAT_0000 = 0x6e;
  DAT_0001 = 0xd7;
  DAT_047a = DAT_0012;
  uStack0000 = 0xd6;
  FUN_edf5();
  uStack0000 = 0xd6;
  bVar1 = FUN_ddad();
  if (cVar4 != '\0') {
    if (DAT_047c == '\x10') {
      bVar1 = FUN_d7c5();
      return bVar1;
    }
    if ((bool)(DAT_0081 & 1)) {
      if ((DAT_047c == '\x0f') || (DAT_0012 != DAT_047b)) {
        if (DAT_047c == '\x0f') {
          DAT_0481 = (&DAT_0151)[DAT_0012];
          uStack0000 = 0xd7;
          cVar4 = FUN_dd4f(DAT_0402);
          if (cVar4 == DAT_0481) {
            DAT_047c = 0x81;
            return 0x81;
          }
          DAT_047c = 0x80;
          bVar1 = FUN_d7a8();
          return bVar1;
        }
        if ((&DAT_0481)[DAT_0012] == -1) {
          bVar1 = 0;
          if (DAT_047c != '\0') {
            (&DAT_0481)[DAT_0012] = (&DAT_0151)[DAT_0012];
            DAT_047c = DAT_047c + -1;
            uStack0000 = 0xd7;
            bVar1 = FUN_d773(0x3e);
          }
        }
        else {
          (&DAT_0481)[DAT_0012] = 0xff;
          DAT_047c = DAT_047c + '\x01';
          uStack0000 = 0xd7;
          bVar1 = FUN_d773(1);
        }
      }
      else {
        bVar2 = 0;
        bVar3 = 0;
        do {
          bVar1 = (&DAT_0481)[bVar3];
          if (bVar1 != 0xff) {
            (&DAT_0481)[bVar2] = bVar1;
            DAT_0000 = bVar2;
            if (bVar3 != bVar2) {
              bVar1 = 0xff;
              (&DAT_0481)[bVar3] = 0xff;
            }
            bVar2 = bVar2 + 1;
          }
          bVar3 = bVar3 + 1;
        } while (bVar3 < 10);
        if (bVar2 != 0) {
          DAT_047c = 0x81;
          bVar1 = FUN_d7a8();
          return bVar1;
        }
      }
    }
    else {
      bVar1 = DAT_0081 >> 2;
      if ((DAT_0081 >> 1 & 1) != 0) {
        DAT_047c = 0x90;
        bVar1 = FUN_d7a8();
        return bVar1;
      }
    }
  }
  return bVar1;
}



/* 0xa009 thunk_FUN_df25 */

void thunk_FUN_df25(void)

{
  DAT_000b = (&DAT_dee9)[DAT_000a];
  DAT_000c = (&DAT_df07)[DAT_000a];
  return;
}



/* 0xa00c FUN_a00c */

/* WARNING: Control flow encountered bad instruction data */

void FUN_a00c(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_de83();
  uStack0000 = 0xa0;
  FUN_df35();
  uStack0000 = 0xa0;
  far_call_inline_word(0x39);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



/* 0xa00f FUN_a00f */

/* WARNING: Control flow encountered bad instruction data */

void FUN_a00f(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_df35();
  uStack0000 = 0xa0;
  far_call_inline_word(0x39);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



/* 0xa01b thunk_FUN_fb2d */

void thunk_FUN_fb2d(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
                    /* WARNING: Could not recover jumptable at 0xa01b. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*(code *)IRQ)();
  return;
}



/* 0xa01e FUN_a01e */

void FUN_a01e(void)

{
  return;
}



/* 0xa024 FUN_a024 */

/* WARNING: Control flow encountered bad instruction data */

void FUN_a024(void)

{
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



/* 0xa03f FUN_a03f */

byte FUN_a03f(byte param_1)

{
  char in_C;
  
  thunk_FUN_da02 = (code)((char)thunk_FUN_da02 + '\x01');
  return param_1 + DAT_00a0 + in_C + DAT_75a0 + CARRY1(param_1,DAT_00a0) & DAT_07c0;
}



/* 0xd64a FUN_d64a */

byte FUN_d64a(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  char cVar4;
  undefined1 uStack0000;
  
  DAT_0013 = DAT_0425;
  DAT_0010 = 0x4c;
  DAT_0011 = 0xd7;
  DAT_0012 = 0;
  uStack0000 = 0xd6;
  FUN_ed19();
  cVar4 = DAT_047b <= DAT_0012;
  if (((DAT_0012 != DAT_047b) && ((bool)cVar4)) &&
     (DAT_0012 = DAT_047b, DAT_0425 = DAT_047b, DAT_0013 != 0)) {
    DAT_0012 = 0;
    DAT_0425 = DAT_0012;
  }
  DAT_0010 = 0x58;
  DAT_0011 = 0xd7;
  DAT_0000 = 0x6e;
  DAT_0001 = 0xd7;
  DAT_047a = DAT_0012;
  uStack0000 = 0xd6;
  FUN_edf5();
  uStack0000 = 0xd6;
  bVar1 = FUN_ddad();
  if (cVar4 != '\0') {
    if (DAT_047c == '\x10') {
      bVar1 = FUN_d7c5();
      return bVar1;
    }
    if ((bool)(DAT_0081 & 1)) {
      if ((DAT_047c == '\x0f') || (DAT_0012 != DAT_047b)) {
        if (DAT_047c == '\x0f') {
          DAT_0481 = (&DAT_0151)[DAT_0012];
          uStack0000 = 0xd7;
          cVar4 = FUN_dd4f(DAT_0402);
          if (cVar4 == DAT_0481) {
            DAT_047c = 0x81;
            return 0x81;
          }
          DAT_047c = 0x80;
          bVar1 = FUN_d7a8();
          return bVar1;
        }
        if ((&DAT_0481)[DAT_0012] == -1) {
          bVar1 = 0;
          if (DAT_047c != '\0') {
            (&DAT_0481)[DAT_0012] = (&DAT_0151)[DAT_0012];
            DAT_047c = DAT_047c + -1;
            uStack0000 = 0xd7;
            bVar1 = FUN_d773(0x3e);
          }
        }
        else {
          (&DAT_0481)[DAT_0012] = 0xff;
          DAT_047c = DAT_047c + '\x01';
          uStack0000 = 0xd7;
          bVar1 = FUN_d773(1);
        }
      }
      else {
        bVar2 = 0;
        bVar3 = 0;
        do {
          bVar1 = (&DAT_0481)[bVar3];
          if (bVar1 != 0xff) {
            (&DAT_0481)[bVar2] = bVar1;
            DAT_0000 = bVar2;
            if (bVar3 != bVar2) {
              bVar1 = 0xff;
              (&DAT_0481)[bVar3] = 0xff;
            }
            bVar2 = bVar2 + 1;
          }
          bVar3 = bVar3 + 1;
        } while (bVar3 < 10);
        if (bVar2 != 0) {
          DAT_047c = 0x81;
          bVar1 = FUN_d7a8();
          return bVar1;
        }
      }
    }
    else {
      bVar1 = DAT_0081 >> 2;
      if ((DAT_0081 >> 1 & 1) != 0) {
        DAT_047c = 0x90;
        bVar1 = FUN_d7a8();
        return bVar1;
      }
    }
  }
  return bVar1;
}



/* 0xd773 FUN_d773 */

void FUN_d773(undefined1 param_1,undefined1 param_2)

{
  undefined1 uStack0000;
  
  DAT_031f = 0x80;
  DAT_0000 = 0x40;
  DAT_0001 = 0;
  DAT_0002 = 0;
  uStack0000 = 0xd7;
  DAT_0003 = param_2;
  DAT_031e = param_1;
  FUN_ebe9();
  DAT_031c = DAT_0006 + 0xa2;
  DAT_031d = DAT_0007 + '$' + (0x5d < DAT_0006);
  DAT_007e = DAT_007e | 1;
  return;
}



/* 0xd7a8 FUN_d7a8 */

void FUN_d7a8(void)

{
  DAT_008f = 0;
  DAT_0061 = 3;
  DAT_00b2 = 0;
  DAT_00b3 = 5;
  DAT_00b4 = 9;
  return;
}



/* 0xd7c5 FUN_d7c5 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d7c5(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  if (DAT_0012 == DAT_047b) {
    if ((bool)(DAT_0081 & 1)) {
      DAT_047c = 0x80;
      DAT_0090 = 0;
      DAT_008f = 0;
      DAT_0061 = 3;
      DAT_00b2 = 0;
      DAT_00b3 = 5;
      DAT_00b4 = 9;
      return;
    }
  }
  else if ((DAT_0081 & 0xc0) != 0) {
    uStack0000 = 0xd8;
    region_address(DAT_0402);
    uStack0000 = 0xd8;
    officer_address(*(undefined1 *)(_DAT_0000 + (ushort)(byte)(DAT_0012 + 0x11)));
    DAT_0002 = *(byte *)(_DAT_0000 + 8);
    DAT_0003 = *(byte *)(_DAT_0000 + 9);
    if ((char)DAT_0081 < '\0') {
      bVar2 = ('\x03' - DAT_0003) - ((DAT_0002 & -DAT_0002 - 0x19 & 0x80) == 0);
      if (((DAT_0003 & (bVar2 | 0xfc) | bVar2 & 0xfc) & 0x80) != 0) {
        uStack0000 = 0xd8;
        FUN_d987(bVar2);
        DAT_0002 = 100;
        if ((DAT_042d == 0) && (DAT_042c < 100)) {
          DAT_0002 = DAT_042c;
        }
        bVar3 = CARRY1(*(byte *)(_DAT_0000 + 8),DAT_0002);
        *(byte *)(_DAT_0000 + 8) = *(byte *)(_DAT_0000 + 8) + DAT_0002;
        *(char *)(_DAT_0000 + 9) = *(char *)(_DAT_0000 + 9) + bVar3;
        bVar2 = DAT_042c - DAT_0002;
        DAT_042d = DAT_042d - (((DAT_0002 & (~DAT_042c | bVar2) | bVar2 & ~DAT_042c) & 0x80) == 0);
        DAT_042c = bVar2;
      }
    }
    else if ((DAT_0003 != 0) || (DAT_0002 != 0)) {
      uStack0000 = 0xd8;
      FUN_d987();
      if ((DAT_0005 == '\0') &&
         (((DAT_042d - 0x26) -
           (((~DAT_042c & 0xad | DAT_042c + 0x53 & 0xad | DAT_042c + 0x53 & ~DAT_042c) & 0x80) == 0)
           & ~DAT_042d & 0x80) == 0)) {
        bVar2 = *(byte *)(_DAT_0000 + 8);
        bVar1 = bVar2 + 0x9c;
        *(byte *)(_DAT_0000 + 8) = bVar1;
        *(char *)(_DAT_0000 + 9) = *(char *)(_DAT_0000 + 9) - ((bVar1 & ~bVar2 & 0x80) == 0);
        DAT_042d = DAT_042d + (0x9b < DAT_042c);
        DAT_042c = DAT_042c + 100;
      }
    }
    DAT_0002 = *(undefined1 *)(_DAT_0000 + 9);
    _DAT_0000 = CONCAT11(*(undefined1 *)(_DAT_0000 + 8),DAT_0000);
    DAT_0003 = 0;
    uStack0000 = 0xd8;
    FUN_e9ba();
    DAT_000a = 1;
    bVar2 = 0;
    uStack0000 = 0xd8;
    FUN_d94e();
    (&DAT_031e)[bVar2] = 0x80;
    _DAT_0000 = 0x40;
    DAT_0002 = 0;
    DAT_0003 = DAT_0012;
    uStack0000 = 0xd8;
    FUN_ebe9();
    DAT_031c = DAT_0006 + 0xbb;
    DAT_031d = DAT_0007 + '$' + (0x44 < DAT_0006);
    goto LAB_d93d;
  }
  _DAT_0000 = CONCAT11(DAT_042c,DAT_0000);
  DAT_0002 = DAT_042d;
  DAT_0003 = '\0';
  uStack0000 = 0xd9;
  FUN_e9ba();
  bVar2 = 0;
  DAT_000a = 1;
  uStack0000 = 0xd9;
  FUN_d96f(DAT_0009 & 0xf);
  uStack0000 = 0xd9;
  FUN_d94e();
  (&DAT_031e)[bVar2] = 0x80;
  DAT_031c = ':';
  DAT_031d = '\'';
LAB_d93d:
  DAT_0303 = 1;
  DAT_030c = 1;
  DAT_007e = DAT_007e | 1;
  return;
}



/* 0xd94e FUN_d94e */

void FUN_d94e(byte param_1)

{
  undefined1 uStack0000;
  
  do {
    uStack0000 = 0xd9;
    FUN_d96f(*(byte *)(param_1 + 7) >> 4);
    if (param_1 == 0) {
      DAT_000a = 0x76;
    }
    uStack0000 = 0xd9;
    FUN_d96f(*(byte *)(param_1 + 7) & 0xf);
    param_1 = param_1 - 1;
  } while (param_1 != 0xff);
  return;
}



/* 0xd96f FUN_d96f */

void FUN_d96f(char param_1,byte param_2)

{
  bool in_Z;
  
  if (in_Z) {
    (&DAT_031e)[param_2] = DAT_000a;
  }
  else {
    (&DAT_031e)[param_2] = param_1 + 'v';
    DAT_000a = 0x76;
  }
  return;
}



/* 0xd987 FUN_d987 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d987(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  DAT_0010 = DAT_0000;
  DAT_0011 = DAT_0001;
  _DAT_0000 = CONCAT11(DAT_0002,DAT_0000);
  DAT_0002 = DAT_0003;
  DAT_0003 = 100;
  DAT_0004 = 0;
  uStack0000 = 0xd9;
  FUN_ea7c();
  if (DAT_0005 != 0) {
    bVar4 = CARRY1(DAT_0005,DAT_042c);
    DAT_042c = DAT_0005 + DAT_042c;
    DAT_042d = DAT_042d + bVar4;
    DAT_0006 = DAT_042c - 0x10;
    if (((DAT_042d - 0x27) - ((DAT_0006 & ~DAT_042c & 0x80) == 0) & ~DAT_042d & 0x80) != 0) {
      DAT_042c = 0x10;
      DAT_042d = 0x27;
      DAT_0005 = DAT_0005 - DAT_0006;
    }
  }
  _DAT_0000 = CONCAT11(DAT_0011,DAT_0010);
  bVar3 = *(byte *)(_DAT_0000 + 8) - DAT_0005;
  bVar1 = ~*(byte *)(_DAT_0000 + 8);
  bVar2 = DAT_0005 & (bVar1 | bVar3);
  *(byte *)(_DAT_0000 + 8) = bVar3;
  *(char *)(_DAT_0000 + 9) = *(char *)(_DAT_0000 + 9) - (((bVar2 | bVar3 & bVar1) & 0x80) == 0);
  return;
}



/* 0xda02 FUN_da02 */

void FUN_da02(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  DAT_001f = 3;
  DAT_0014 = DAT_048e;
  DAT_0015 = DAT_048f;
  cVar3 = -((char)DAT_0081 >> 7);
  bVar1 = DAT_048b;
  if (cVar3 == '\0') {
    if ((char)(DAT_0081 << 1) < '\0') {
      cVar3 = 2 < DAT_048b;
      if (DAT_048b != 3) {
        DAT_048b = DAT_048b + 1;
      }
    }
    else {
      if ((char)(DAT_0081 << 2) < '\0') {
        uStack0000 = 0xda;
        FUN_db09();
        bVar1 = DAT_048e - DAT_0000;
        DAT_048f = (DAT_048f - DAT_0001) -
                   (((DAT_0000 & (~DAT_048e | bVar1) | bVar1 & ~DAT_048e) & 0x80) == 0);
        DAT_048e = bVar1;
      }
      else {
        bVar1 = DAT_0081 << 4;
        cVar3 = '\0';
        if (-1 < (char)(DAT_0081 << 3)) goto LAB_da91;
        uStack0000 = 0xda;
        FUN_db09(bVar1);
        bVar4 = CARRY1(DAT_048e,DAT_0000);
        DAT_048e = DAT_048e + DAT_0000;
        DAT_048f = DAT_048f + DAT_0001 + bVar4;
      }
      DAT_0000 = DAT_048e;
      DAT_0001 = DAT_048f;
      bVar1 = (DAT_0491 - DAT_048f) -
              (((DAT_048e & (~DAT_0490 | DAT_0490 - DAT_048e) | DAT_0490 - DAT_048e & ~DAT_0490) &
               0x80) == 0);
      cVar3 = ((DAT_048f & (~DAT_0491 | bVar1) | bVar1 & ~DAT_0491) & 0x80) != 0;
      if (!(bool)cVar3) {
        DAT_048e = DAT_0014;
        DAT_048f = DAT_0015;
        bVar1 = DAT_0015;
      }
    }
  }
  else if (DAT_048b != 0) {
    DAT_048b = DAT_048b - 1;
  }
LAB_da91:
  uStack0000 = 0xda;
  FUN_ddad(bVar1);
  if (cVar3 != '\0') {
    DAT_0013 = DAT_0081 & 3;
    DAT_0001 = DAT_048e;
    DAT_0002 = DAT_048f;
    DAT_0003 = 0;
    uStack0000 = 0xda;
    FUN_e9ba();
    DAT_048c = DAT_0007;
    DAT_048d = DAT_0008;
    DAT_0011 = '\x03' - DAT_048b;
    DAT_0010 = 1;
    bVar2 = 2;
    bVar1 = 0;
    do {
      uStack0000 = 0xda;
      FUN_db35((byte)(&DAT_048b)[bVar2] >> 4);
      if (bVar2 == 1) {
        DAT_0010 = 0x76;
      }
      uStack0000 = 0xda;
      FUN_db35((&DAT_048b)[bVar2] & 0xf);
      bVar2 = bVar2 - 1;
    } while (bVar2 != 0);
    (&DAT_031e)[bVar1] = 0x80;
    DAT_0303 = 1;
    DAT_030c = 1;
    DAT_046c = DAT_046c + '\x01';
    DAT_007e = DAT_007e | 1;
  }
  return;
}



/* 0xdb09 FUN_db09 */

void FUN_db09(void)

{
  DAT_0001 = 0;
  if (DAT_048b == '\0') {
    DAT_0000 = 1;
  }
  else if (DAT_048b == '\x01') {
    DAT_0000 = 10;
  }
  else if (DAT_048b == '\x02') {
    DAT_0000 = 100;
  }
  else {
    DAT_0001 = 3;
    DAT_0000 = 0xe8;
  }
  return;
}



/* 0xdb35 FUN_db35 */

void FUN_db35(char param_1,byte param_2)

{
  bool in_Z;
  
  if (in_Z) {
    if ((DAT_0013 == '\0') && (DAT_0011 <= param_2)) {
      DAT_0010 = 0x76;
    }
    (&DAT_031e)[param_2] = DAT_0010;
  }
  else {
    (&DAT_031e)[param_2] = param_1 + 'v';
    DAT_0010 = 0x76;
  }
  if (((DAT_0013 == '\0') && (param_2 == DAT_0011)) && ((DAT_046c & 8) == 0)) {
    (&DAT_031e)[param_2] = 1;
  }
  return;
}



/* 0xdd4f FUN_dd4f */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 FUN_dd4f(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xdd;
  region_address();
  uStack0000 = 0xdd;
  FUN_f368(*_DAT_0000);
  return *_DAT_0000;
}



/* 0xddad FUN_ddad */

void FUN_ddad(void)

{
  if ((DAT_0304 == -1) && (DAT_0300 == -1)) {
    return;
  }
  return;
}



/* 0xde83 FUN_de83 */

void FUN_de83(void)

{
  if (((DAT_008f == '\0') && (DAT_04e4 == '\0')) && (DAT_04a0 == '\0')) {
    DAT_000a = DAT_6f41;
    DAT_000c = DAT_6f3f;
    DAT_0000 = 0xb1;
    DAT_0001 = 0xde;
    DAT_0002 = 0;
    FUN_f1ad();
    return;
  }
  return;
}



/* 0xdf25 FUN_df25 */

void FUN_df25(void)

{
  DAT_000b = (&DAT_dee9)[DAT_000a];
  DAT_000c = (&DAT_df07)[DAT_000a];
  return;
}



/* 0xdf35 FUN_df35 */

void FUN_df35(void)

{
  undefined1 uVar1;
  undefined1 uStack0000;
  
  DAT_000e = DAT_0420;
  DAT_000f = '\x1d';
  uVar1 = DAT_007c;
  if (DAT_008f == '\0') {
    do {
      uStack0000 = 0xdf;
      FUN_df62();
      DAT_000f = DAT_000f + -1;
    } while (-1 < DAT_000f);
  }
  DAT_007c = uVar1;
  DAT_04e0 = 0;
  DAT_04e1 = 0;
  DAT_04e2 = 0;
  DAT_04e3 = 0;
  return;
}



/* 0xdf62 FUN_df62 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_df62(byte param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  _DAT_0000 = (byte *)CONCAT11(DAT_0001,(&DAT_dfee)[DAT_000f & 7]);
  if (((((&DAT_04e0)[DAT_000f >> 3] & (&DAT_dfee)[DAT_000f & 7]) == 0) || ((DAT_005e & 8) == 0)) &&
     (((&DAT_dfd0)[DAT_000f] & DAT_000e) == 0)) {
    uStack0000 = 0xdf;
    region_address(DAT_000f);
    bVar1 = *_DAT_0000;
    *(undefined *)(param_1 + 0x201) = (&DAT_dfc0)[bVar1 & 7];
    *(undefined *)(param_1 + 0x202) = (&DAT_dfc8)[bVar1 & 7];
    bVar1 = DAT_000f & 0x1f;
    *(undefined *)(param_1 + 0x203) = (&DAT_dee9)[bVar1];
    *(undefined *)(param_1 + 0x200) = (&DAT_df07)[bVar1];
    return;
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
  thunk_FUN_fb2d();
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
                    /* WARNING: Read-only address (RAM,0xd800) is written */
  uRAMd800 = (&DAT_e567)[(byte)(bVar1 + 3)];
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
                    /* WARNING: Read-only address (RAM,0xd800) is written */
  uRAMd800 = 0xe1;
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



/* 0xe9ba FUN_e9ba */

void FUN_e9ba(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  
  DAT_0007 = 0;
  DAT_0008 = '\0';
  DAT_0009 = '\0';
  bVar3 = DAT_0001;
  bVar1 = DAT_0002;
  bVar2 = DAT_0003;
  do {
    DAT_0003 = bVar2;
    DAT_0002 = bVar1;
    DAT_0001 = bVar3;
    bVar1 = (DAT_0002 + 0xbe) - ((DAT_0001 - 0x40 & ~DAT_0001 & 0x80) == 0);
    bVar2 = (DAT_0003 - 0xf) - ((bVar1 & ~DAT_0002 & 0x80) == 0);
    bVar3 = DAT_0001 - 0x40;
  } while ((bVar2 & ~DAT_0003 & 0x80) != 0);
  do {
    bVar1 = DAT_0001 + 0x60;
    bVar2 = (DAT_0002 + 0x7a) -
            (((~DAT_0001 & 0xa0 | bVar1 & 0xa0 | bVar1 & ~DAT_0001) & 0x80) == 0);
    bVar3 = (DAT_0003 - 1) - (((~DAT_0002 & 0x86 | bVar2 & 0x86 | bVar2 & ~DAT_0002) & 0x80) == 0);
    bVar4 = (bVar3 & ~DAT_0003 & 0x80) != 0;
    if (!bVar4) break;
    DAT_0009 = DAT_0009 + '\x0f' + bVar4;
    DAT_0001 = bVar1;
    DAT_0002 = bVar2;
    DAT_0003 = bVar3;
  } while (DAT_0009 != '\0');
  do {
    bVar1 = DAT_0001 - 0x10;
    DAT_0005 = (DAT_0002 - 0x27) - ((bVar1 & ~DAT_0001 & 0x80) == 0);
    bVar2 = DAT_0003 - ((DAT_0005 & ~DAT_0002 & 0x80) == 0);
    if ((bVar2 & ~DAT_0003 & 0x80) == 0) break;
    DAT_0009 = DAT_0009 + '\x01';
    DAT_0001 = bVar1;
    DAT_0002 = DAT_0005;
    DAT_0003 = bVar2;
  } while (DAT_0009 != '\0');
  do {
    bVar1 = DAT_0001 + 0x18;
    bVar2 = (DAT_0002 - 3) - (((~DAT_0001 & 0xe8 | bVar1 & 0xe8 | bVar1 & ~DAT_0001) & 0x80) == 0);
    bVar4 = (bVar2 & ~DAT_0002 & 0x80) != 0;
    if (!bVar4) break;
    DAT_0008 = DAT_0008 + '\x0f' + bVar4;
    DAT_0001 = bVar1;
    DAT_0002 = bVar2;
  } while (DAT_0008 != '\0');
  do {
    bVar1 = DAT_0001 + 0x9c;
    bVar2 = DAT_0002 - ((bVar1 & ~DAT_0001 & 0x80) == 0);
    if ((bVar2 & ~DAT_0002 & 0x80) == 0) break;
    DAT_0008 = DAT_0008 + '\x01';
    DAT_0001 = bVar1;
    DAT_0002 = bVar2;
  } while (DAT_0008 != '\0');
  do {
    DAT_0004 = DAT_0001 - 10;
    bVar1 = DAT_0002 - ((DAT_0004 & ~DAT_0001 & 0x80) == 0);
    bVar4 = (bVar1 & ~DAT_0002 & 0x80) != 0;
    if (!bVar4) break;
    DAT_0007 = DAT_0007 + 0xf + bVar4;
    DAT_0001 = DAT_0004;
    DAT_0002 = bVar1;
  } while (DAT_0007 != 0);
  DAT_0007 = DAT_0001 | DAT_0007;
  return;
}



/* 0xea7c FUN_ea7c */

void FUN_ea7c(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  
  DAT_0005 = 0;
  DAT_0006 = 0;
  cVar1 = '\x0f';
  do {
    bVar2 = DAT_0001 >> 7;
    DAT_0001 = DAT_0001 * '\x02';
    bVar3 = DAT_0002 >> 7;
    DAT_0002 = DAT_0002 << 1 | bVar2;
    bVar3 = DAT_0005 << 1 | bVar3;
    DAT_0006 = DAT_0006 << 1 | DAT_0005 >> 7;
    DAT_0007 = bVar3 - DAT_0003;
    bVar2 = (DAT_0006 - DAT_0004) -
            (((DAT_0003 & (~bVar3 | DAT_0007) | DAT_0007 & ~bVar3) & 0x80) == 0);
    DAT_0005 = bVar3;
    if (((DAT_0004 & (~DAT_0006 | bVar2) | bVar2 & ~DAT_0006) & 0x80) != 0) {
      DAT_0001 = DAT_0001 + 1;
      DAT_0005 = DAT_0007;
      DAT_0006 = bVar2;
    }
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
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



/* 0xebe9 FUN_ebe9 */

void FUN_ebe9(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  bool bVar4;
  byte bVar5;
  
  cVar1 = '\a';
  DAT_0004 = 0;
  DAT_0005 = 0;
  DAT_0006 = 0;
  DAT_0007 = 0;
  DAT_0008 = 0;
  DAT_0009 = '\0';
  do {
    bVar2 = DAT_0003 & 1;
    DAT_0003 = DAT_0003 >> 1;
    if (bVar2 != 0) {
      bVar3 = CARRY1(DAT_0000,DAT_0006);
      DAT_0006 = DAT_0000 + DAT_0006;
      bVar4 = CARRY1(DAT_0001,DAT_0007);
      DAT_0007 = DAT_0001 + DAT_0007 + bVar3;
      bVar3 = CARRY1(DAT_0002,DAT_0008);
      DAT_0008 = DAT_0002 + DAT_0008 + bVar4;
      DAT_0009 = DAT_0004 + DAT_0009 + bVar3;
    }
    bVar2 = DAT_0000 >> 7;
    DAT_0000 = DAT_0000 << 1;
    bVar5 = DAT_0001 >> 7;
    DAT_0001 = DAT_0001 << 1 | bVar2;
    bVar2 = DAT_0002 >> 7;
    DAT_0002 = DAT_0002 << 1 | bVar5;
    DAT_0004 = DAT_0004 << 1 | bVar2;
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
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



/* 0xed19 FUN_ed19 */

void FUN_ed19(void)

{
  undefined1 uStack0000;
  
  DAT_0000 = 1;
  if ((DAT_0081 & 0x80) != 0) {
    uStack0000 = 0xed;
    FUN_ed71();
  }
  if ((DAT_0081 & 0x40) != 0) {
    uStack0000 = 0xed;
    FUN_ed8d();
  }
  if ((DAT_0081 & 0x20) != 0) {
    uStack0000 = 0xed;
    FUN_eda9();
  }
  if ((DAT_0081 & 0x10) != 0) {
    uStack0000 = 0xed;
    FUN_edbe();
  }
  uStack0000 = 0xed;
  DAT_0012 = FUN_eddd();
  return;
}



/* 0xed71 FUN_ed71 */

void FUN_ed71(void)

{
  bool bVar1;
  undefined1 uStack0000;
  
  DAT_0424 = DAT_0424 + 1;
  bVar1 = (char)DAT_0424 < '\0';
  uStack0000 = 0xed;
  FUN_eddd();
  if (((bVar1) || (DAT_0000 <= DAT_0424)) && (DAT_0424 = DAT_0424 - 1, DAT_0012 == '\0')) {
    DAT_0424 = 0;
  }
  return;
}



/* 0xed8d FUN_ed8d */

void FUN_ed8d(void)

{
  char cVar1;
  char cVar2;
  undefined1 uStack0000;
  
  cVar1 = DAT_0424 + -1;
  if (((char)(DAT_0424 + -1) < '\0') && (cVar1 = DAT_0424, DAT_0012 == '\0')) {
    DAT_0424 = DAT_0000;
    do {
      DAT_0424 = DAT_0424 + -1;
      uStack0000 = 0xed;
      cVar2 = FUN_eddd();
      cVar1 = DAT_0424;
    } while (cVar2 == -1);
  }
  DAT_0424 = cVar1;
  return;
}



/* 0xeda9 FUN_eda9 */

void FUN_eda9(void)

{
  char cVar1;
  undefined1 uStack0000;
  
  DAT_0425 = DAT_0425 + '\x01';
  cVar1 = DAT_0425 < '\0';
  uStack0000 = 0xed;
  FUN_eddd();
  if ((cVar1 != '\0') && (DAT_0425 = DAT_0425 + -1, DAT_0012 == '\0')) {
    DAT_0425 = '\0';
  }
  return;
}



/* 0xedbe FUN_edbe */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_edbe(void)

{
  char cVar1;
  byte bVar2;
  
  cVar1 = DAT_0425 + -1;
  if (((char)(DAT_0425 + -1) < '\0') && (cVar1 = DAT_0425, DAT_0012 == '\0')) {
    cVar1 = -1;
    bVar2 = DAT_0424;
    do {
      cVar1 = cVar1 + '\x01';
      bVar2 = bVar2 + DAT_0000;
    } while (-1 < *(char *)(_DAT_0010 + (ushort)bVar2));
  }
  DAT_0425 = cVar1;
  return;
}



/* 0xeddd FUN_eddd */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 FUN_eddd(void)

{
  char cVar1;
  char cVar2;
  
  cVar1 = '\0';
  for (cVar2 = DAT_0425; cVar2 != '\0'; cVar2 = cVar2 + -1) {
    cVar1 = cVar1 + DAT_0000;
  }
  return *(undefined1 *)(_DAT_0010 + (ushort)(byte)(cVar1 + DAT_0424));
}



/* 0xedf5 FUN_edf5 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_edf5(char param_1)

{
  DAT_000a = *(undefined1 *)(_DAT_0010 + (ushort)(byte)(param_1 * '\x02'));
  DAT_000c = *(undefined1 *)(_DAT_0010 + (ushort)(byte)(param_1 * '\x02' + 1));
  DAT_0002 = 0;
  FUN_f1ad();
  return;
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
      bVar1 = FUN_a00c();
      return bVar1;
    }
    if ((char)(DAT_007e << 5) < '\0') {
      DAT_007e = DAT_007e & 0xfb;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = thunk_FUN_d64a();
      return bVar1;
    }
    if ((char)(DAT_007e << 6) < '\0') {
      DAT_007e = DAT_007e & 0xfd;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bStack0000 = 0xa0;
      far_call_inline_word(0x39);
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
    if ((char)(DAT_007e << 7) < '\0') {
      bStack0000 = 0xee;
      FUN_f237(DAT_007e << 7,0x3d);
      bVar1 = bank27_entry_00();
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



/* 0xf1ad FUN_f1ad */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_f1ad(void)

{
  byte bVar1;
  byte bVar2;
  
  DAT_0003 = '\0';
  DAT_0004 = 0;
  bVar2 = 0;
  do {
    if (DAT_007c == 0xff) {
      return;
    }
    while( true ) {
      if (*(char *)(_DAT_0000 + (ushort)bVar2) == -0x80) {
        return;
      }
      bVar1 = *(char *)(_DAT_0000 + (ushort)bVar2) + DAT_000a;
      if (DAT_0004 <= bVar1) break;
      bVar2 = bVar2 + 4;
    }
    *(byte *)(DAT_007c + 0x200) = bVar1;
    *(char *)(DAT_007c + 0x201) = *(char *)(_DAT_0000 + (ushort)(byte)(bVar2 + 1)) + DAT_0003;
    *(byte *)(DAT_007c + 0x202) = *(byte *)(_DAT_0000 + (ushort)(byte)(bVar2 + 2)) ^ DAT_0002;
    *(char *)(DAT_007c + 0x203) = *(char *)(_DAT_0000 + (ushort)(byte)(bVar2 + 3)) + DAT_000c;
    bVar2 = bVar2 + 4;
    DAT_007c = DAT_007c + 4;
  } while (DAT_007c != 0);
  DAT_007c = 0xff;
  return;
}



/* 0xf206 FUN_f206 */

void FUN_f206(void)

{
  DAT_8000 = DAT_00ae;
  DAT_8800 = DAT_00af;
  DAT_9000 = DAT_00b0;
  DAT_9800 = DAT_00b1;
  bank27_entry_00 = DAT_00b2;
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



/* 0xf26d FUN_f26d */

void FUN_f26d(undefined1 param_1)

{
  DAT_0311 = param_1;
  DAT_0310 = 0;
  DAT_0312 = 0xff;
  DAT_0313 = 0xff;
  DAT_0300 = 0;
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



/* 0xf368 FUN_f368 */

void FUN_f368(byte param_1)

{
  byte bVar1;
  
  bVar1 = (param_1 & 0xf) << 1;
  DAT_0000 = (&DAT_f379)[bVar1];
  DAT_0001 = (&DAT_f37a)[bVar1];
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
                    /* WARNING: Read-only address (RAM,0xd800) is written */
  uRAMd800 = 0xe1;
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
  thunk_FUN_da02();
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
                    /* WARNING: Read-only address (RAM,0xd800) is written */
  uRAMd800 = DAT_00e9;
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



/* 0xfb2d FUN_fb2d */

undefined1 FUN_fb2d(undefined1 param_1)

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
    uRAMd800 = 9;
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
      bank27_entry_00 = DAT_00ba;
      DAT_a800 = DAT_00bb;
      DAT_b000 = DAT_00bc;
      DAT_b800 = DAT_00bd;
      DAT_c700 = DAT_00ea;
      uRAMd800 = 9;
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
        bank27_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        DAT_c700 = DAT_00ea;
        uRAMd800 = 9;
        return param_1;
      }
      if (DAT_0060 == '\x05') {
LAB_fd95:
                    /* WARNING: Read-only address (RAM,0xd800) is written */
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
        bank27_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        DAT_c700 = 0xe1;
        DAT_c800 = 0xe1;
        DAT_d000 = 0xe1;
        uRAMd800 = 0xe1;
        return param_1;
      }
      if (DAT_0060 == '\x06') {
        DAT_0062 = 0;
        DAT_5000 = 0;
        DAT_5800 = 0;
        uRAMd800 = 9;
        return param_1;
      }
      if (DAT_0060 == '\a') {
        DAT_5000 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6a);
        DAT_5800 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6b);
        if (DAT_0063 == '\0') {
          DAT_c700 = 0xe1;
          DAT_d000 = 0xe1;
          DAT_c800 = 0xe1;
                    /* WARNING: Read-only address (RAM,0xd800) is written */
          uRAMd800 = 0xe1;
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
        bank27_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        uRAMd800 = 9;
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
        bank27_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        DAT_c000 = DAT_00ea;
        uRAMd800 = 9;
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
        uRAMd800 = 9;
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
    bank27_entry_00 = DAT_00c2;
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
      bank27_entry_00 = DAT_00da;
      DAT_a800 = DAT_00db;
      DAT_b000 = DAT_00dc;
      DAT_b800 = DAT_00dd;
      uRAMd800 = 9;
      return param_1;
    }
LAB_fc2a:
    DAT_0063 = DAT_0063 + '\x01';
    DAT_8000 = DAT_00ce;
    DAT_8800 = DAT_00cf;
    DAT_9000 = DAT_00d0;
    DAT_9800 = DAT_00d1;
    bank27_entry_00 = DAT_00d2;
    DAT_a800 = DAT_00d3;
    DAT_b000 = DAT_00d4;
    DAT_b800 = DAT_00d5;
    uRAMd800 = 9;
    return param_1;
  }
LAB_fbfc:
  uRAMd800 = 9;
  DAT_b800 = DAT_00cd;
  DAT_b000 = DAT_00cc;
  DAT_a800 = DAT_00cb;
  bank27_entry_00 = DAT_00ca;
  DAT_9800 = DAT_00c9;
  DAT_9000 = DAT_00c8;
  DAT_8800 = DAT_00c7;
  DAT_8000 = DAT_00c6;
  DAT_0063 = DAT_0063 + '\x01';
                    /* WARNING: Read-only address (RAM,0xd800) is written */
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


