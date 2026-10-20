// Ghidra-generated fixed-bank-pair pseudocode. Bank switching and inline pointer dispatch need manual correction. Not original source.

/* 0xa000 bank29_entry_00 */

void bank29_entry_00(void)

{
  ushort uVar1;
  char cVar2;
  byte bVar3;
  
  if ((DAT_007e & 4) != 0) {
    return;
  }
  if ((DAT_0303 == '\0') && (DAT_0308 == '\0')) {
    if ((DAT_005e & DAT_0305) != 0) {
      FUN_ee72();
      return;
    }
    if (*(char *)(DAT_0304 + 0x34e) != -0x80) {
      DAT_2007 = *(undefined1 *)(DAT_0304 + 0x31e);
      cVar2 = DAT_031c;
      if (DAT_030c == '\0') {
        DAT_2007 = *(undefined1 *)(DAT_0304 + 0x34e);
        cVar2 = DAT_034c;
      }
      DAT_2006 = cVar2 + DAT_0304;
      DAT_0304 = DAT_0304 + 1;
      return;
    }
  }
  else {
    DAT_2006 = DAT_031c;
    for (bVar3 = 0; uVar1 = (ushort)bVar3, *(char *)(uVar1 + 0x31e) != -0x80; bVar3 = bVar3 + 1) {
      DAT_2007 = *(char *)(uVar1 + 0x31e);
    }
    if (DAT_030c == '\0') {
      DAT_2006 = DAT_034c;
      for (bVar3 = 0; uVar1 = (ushort)bVar3, *(char *)(uVar1 + 0x34e) != -0x80; bVar3 = bVar3 + 1) {
        DAT_2007 = *(char *)(uVar1 + 0x34e);
      }
    }
  }
  DAT_0304 = 0xff;
  DAT_007e = DAT_007e & 0xfe;
  return;
}



/* 0xa003 thunk_FUN_a154 */

void thunk_FUN_a154(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa1;
  FUN_a158();
  return;
}



/* 0xa006 thunk_FUN_a11b */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_a11b(void)

{
  char cVar1;
  byte bVar2;
  
  DAT_2000 = DAT_008b & 0xfb;
  _DAT_0000 = 0x380;
  bVar2 = 0;
  while (cVar1 = *(char *)(bVar2 + 0x380), cVar1 != -1) {
    DAT_2006 = *(undefined1 *)((byte)(bVar2 + 2) + 0x380);
    bVar2 = bVar2 + 3;
    do {
      DAT_2007 = *(undefined1 *)(bVar2 + 0x380);
      bVar2 = bVar2 + 1;
      cVar1 = cVar1 + -1;
    } while (cVar1 != '\0');
  }
  return;
}



/* 0xa009 thunk_FUN_abd2 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_abd2(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  if (DAT_037c != '\0') {
    uStack0000 = 0xab;
    FUN_f25f(0x31);
    if (DAT_037d != -1) {
      uStack0000 = 0xab;
      FUN_b14c(1);
    }
    if (DAT_037e != -1) {
      uStack0000 = 0xab;
      FUN_b14c(2);
    }
  }
  if (DAT_0140 == 0) {
    return;
  }
  if (-1 < (char)DAT_0140) {
    if ((DAT_0140 & 0xf) == 1) {
      if ((DAT_0150 & 0xf) == 0) {
        DAT_0420 = 0;
      }
      if ((DAT_0150 & 0xf) == 1) {
        DAT_037c = -1;
      }
      DAT_0150 = DAT_0150 & 0x80;
      DAT_0140 = 0;
      return;
    }
    if ((DAT_007e & 8) != 0) {
      return;
    }
    if ((DAT_0150 & 0xf) == 0) goto LAB_aec9;
    goto LAB_adf3;
  }
  DAT_037c = '\0';
  DAT_0140 = 5;
  DAT_0143 = 0;
  DAT_0144 = -0x80;
  DAT_0154 = 0x38;
  if ((DAT_0150 & 0xf) == 0) {
    DAT_0142 = '\"';
    DAT_0148 = '#';
    DAT_037c = '\0';
    if ((char)DAT_0150 < '\0') {
      DAT_0145 = 0xe4;
      DAT_0147 = 0xec;
      DAT_0141 = 0x90;
      DAT_0143 = 0x10;
    }
    else {
      DAT_0145 = 0xe0;
      DAT_0147 = 0xe8;
      DAT_0141 = 0x82;
      DAT_0143 = 2;
    }
    DAT_0146 = -0x7d;
    DAT_0144 = -0x7e;
LAB_aec9:
    DAT_0140 = DAT_0140 - 1;
    uStack0000 = 0xae;
    FUN_f25f(0x30);
    DAT_0010 = (byte *)CONCAT11(DAT_0144,DAT_0143);
    bVar1 = 0;
    do {
      bVar2 = 0;
      do {
        (&DAT_0160)[bVar1] = *(undefined1 *)((short)DAT_0010 + (ushort)bVar2);
        bVar2 = bVar2 + 1;
        bVar1 = bVar1 + 1;
      } while (bVar2 < 0xe);
      DAT_0010 = (byte *)CONCAT11(DAT_0010._1_1_ + (0xdf < (byte)DAT_0010),(byte)DAT_0010 + 0x20);
    } while (bVar1 < 0x38);
    bVar1 = DAT_0143 + 0x80;
    DAT_0144 = DAT_0144 -
               (((~DAT_0143 & 0x80) == 0 && (bVar1 & 0x80) == 0) && (bVar1 & ~DAT_0143 & 0x80) == 0)
    ;
    DAT_0010 = (byte *)CONCAT11(DAT_0146,DAT_0145);
    bVar2 = 0;
    DAT_0143 = bVar1;
    do {
      (&DAT_014b)[bVar2] = *(undefined1 *)((short)DAT_0010 + (ushort)bVar2);
      bVar2 = bVar2 + 1;
    } while (bVar2 < 4);
    bVar2 = DAT_0145 - 8;
    bVar1 = ~DAT_0145;
    DAT_0145 = bVar2;
    DAT_0146 = DAT_0146 - ((bVar2 & bVar1 & 0x80) == 0);
    bVar2 = DAT_0147 - 8;
    bVar1 = ~DAT_0147;
    DAT_0147 = bVar2;
    DAT_0148 = DAT_0148 - ((bVar2 & bVar1 & 0x80) == 0);
    bVar2 = DAT_0141 + 0x80;
    bVar1 = ~DAT_0141;
    DAT_0141 = bVar2;
    DAT_0142 = DAT_0142 -
               (((bVar1 & 0x80) == 0 && (bVar2 & 0x80) == 0) && (bVar2 & bVar1 & 0x80) == 0);
    DAT_007e = DAT_007e | 8;
    return;
  }
  DAT_0152 = 0x83;
  DAT_0153 = 0xb6;
  DAT_00b4 = 9;
  DAT_00c4 = 9;
  DAT_00cc = 9;
  DAT_00d4 = 9;
  DAT_00dc = 9;
  DAT_0420 = 0x80;
  if ((char)DAT_0150 < '\0') {
    DAT_0420 = 0x40;
  }
  bVar1 = DAT_0150 & 0xf;
  if (bVar1 == 1) {
    DAT_0149 = 5;
    DAT_014a = 0xb3;
    uStack0000 = 0xac;
    region_address(DAT_0402);
    DAT_037e = _DAT_0000[0x11];
    if (*_DAT_0000 == '\a') {
      DAT_037d = -1;
    }
    else {
      bVar1 = *_DAT_0000 << 1;
      _DAT_0000 = (char *)CONCAT11((&DAT_ad85)[bVar1],(&DAT_ad84)[bVar1]);
      DAT_037d = *_DAT_0000;
    }
    DAT_00b4 = 8;
    DAT_00c4 = 8;
    DAT_00cc = 8;
    DAT_00d4 = 8;
    DAT_00d3 = 1;
    DAT_00cb = DAT_00d3;
  }
  else if (bVar1 == 2) {
LAB_ac95:
    DAT_0149 = 0xe5;
    DAT_014a = 0xb3;
    DAT_00cb = 1;
    DAT_00d3 = 5;
  }
  else if (bVar1 == 3) {
    DAT_0149 = 0xc1;
    DAT_014a = 0xb4;
    DAT_00d3 = 5;
    DAT_00cb = DAT_00d3;
  }
  else {
    if (bVar1 != 4) goto LAB_ac95;
    DAT_0149 = 0x9c;
    DAT_014a = 0xb5;
    DAT_00d3 = 5;
    DAT_00cb = DAT_00d3;
  }
  DAT_00c2 = 0;
  DAT_00ca = 0;
  DAT_00d2 = 0;
  DAT_00da = 0;
  DAT_0142 = ' ';
  DAT_0148 = '#';
  if ((char)DAT_0150 < '\0') {
    DAT_0147 = 0xc4;
    DAT_0145 = 0x7f;
    DAT_0141 = 0x10;
    bVar1 = 0xcc;
  }
  else {
    DAT_0147 = 0xc0;
    DAT_0145 = 0x7b;
    DAT_0141 = 2;
    bVar1 = 200;
  }
  DAT_0146 = -0x4a;
  bVar3 = CARRY1(bVar1,DAT_0143);
  DAT_0143 = bVar1 + DAT_0143;
  DAT_0144 = DAT_0144 + '\x03' + bVar3;
  DAT_00b3 = DAT_00cb;
  DAT_00c3 = DAT_00cb;
  DAT_00db = DAT_00d3;
LAB_adf3:
  DAT_0140 = DAT_0140 - 1;
  uStack0000 = 0xad;
  FUN_f25f(0x30);
  DAT_0010 = (byte *)CONCAT11(DAT_014a,DAT_0149);
  bVar2 = 0;
  bVar1 = 0;
  do {
    if (*(byte *)((short)DAT_0010 + (ushort)bVar2) < 0xf0) {
      (&DAT_0160)[bVar1] = *(byte *)((short)DAT_0010 + (ushort)bVar2);
      bVar2 = bVar2 + 1;
      bVar1 = bVar1 + 1;
    }
    else {
      uStack0000 = 0xae;
      FUN_af77();
    }
  } while (bVar1 < 0x38);
  uStack0000 = 0xae;
  FUN_af66(bVar2,9);
  DAT_0010 = (byte *)CONCAT11(DAT_0146,DAT_0145);
  _DAT_0012 = (byte *)CONCAT11(DAT_0144,DAT_0143);
  DAT_014b = *_DAT_0012 & 0x33 | *DAT_0010;
  bVar1 = 1;
  do {
    (&DAT_014b)[bVar1] = DAT_0010[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < 3);
  (&DAT_014b)[bVar1] = _DAT_0012[bVar1] & 0xcc | DAT_0010[bVar1];
  uStack0000 = 0xae;
  FUN_af66(8,7);
  uStack0000 = 0xae;
  FUN_af66(8,3);
  uStack0000 = 0xae;
  FUN_af66(0x80,1);
  if ((DAT_0150 & 0xf) == 1) {
    if (DAT_0140 == '\x04') {
      uStack0000 = 0xae;
      FUN_b0ab();
    }
    uStack0000 = 0xae;
    region_address(DAT_0402);
    if (*_DAT_0000 != '\a') {
      if (DAT_0140 == '\x04') {
        uStack0000 = 0xae;
        FUN_b23a(0);
      }
      else if (DAT_0140 == '\x03') {
        uStack0000 = 0xae;
        FUN_b23a(1);
        uStack0000 = 0xae;
        FUN_b27a();
      }
      else if (DAT_0140 == '\x02') {
        DAT_000f = 2;
        uStack0000 = 0xae;
        FUN_b27a();
      }
    }
  }
  DAT_007e = DAT_007e | 8;
  return;
}



/* 0xa00c thunk_FUN_b29f */

void thunk_FUN_b29f(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_0001 = DAT_0142;
  DAT_0000 = DAT_0141;
  bVar1 = 0;
  do {
    bVar2 = 0;
    do {
      bVar2 = bVar2 + 1;
      bVar1 = bVar1 + 1;
    } while (bVar2 < 0xe);
    bVar3 = 0xdf < DAT_0000;
    DAT_0000 = DAT_0000 + 0x20;
    DAT_0001 = DAT_0001 + bVar3;
  } while (bVar1 < DAT_0154);
  DAT_2006 = DAT_0147;
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_014b)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < 4);
  return;
}



/* 0xa00f thunk_FUN_b989 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_b989(void)

{
  undefined1 uVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  bool bVar5;
  undefined1 uStack0000;
  
  if (((DAT_0140 == '\0') && ((DAT_007e & 2) == 0)) && (DAT_0478 != 0)) {
    if ((char)DAT_0478 < '\0') {
      DAT_0479 = DAT_0478 & 0xf;
      DAT_0478 = 0;
      DAT_047a = 0;
      DAT_047b = '\0';
      DAT_0486 = '\0';
      DAT_0480 = 0xc0;
      DAT_0481 = '#';
      uStack0000 = 0xba;
      FUN_f25f(0x30);
      if (DAT_047c == -1) {
        DAT_047c = '\x0f';
        bVar3 = 0;
        do {
          if ((&DAT_0151)[bVar3] != -1) {
            DAT_047b = DAT_047b + '\x01';
          }
          bVar3 = bVar3 + 1;
        } while (bVar3 < 10);
      }
      else {
        uVar1 = DAT_0402;
        if (DAT_0479 == 2) {
          DAT_0479 = 0;
          uVar1 = DAT_040c;
        }
        uStack0000 = 0xba;
        region_address(uVar1);
        bVar4 = 0x11;
        bVar3 = 0;
        do {
          cVar2 = *(char *)(_DAT_0000 + (ushort)bVar4);
          (&DAT_0151)[bVar3] = cVar2;
          if (cVar2 != -1) {
            DAT_047b = DAT_047b + '\x01';
          }
          bVar3 = bVar3 + 1;
          bVar4 = bVar4 + 1;
        } while (bVar3 < 10);
      }
      if (DAT_0479 == 0) {
        DAT_0482 = 0xc9;
        DAT_0483 = -0x48;
      }
      else {
        DAT_0482 = 9;
        DAT_0483 = -0x48;
      }
    }
    else {
      if (DAT_0478 == 0x10) {
        DAT_0478 = 0;
        DAT_047a = 0;
        DAT_0480 = 0;
        DAT_0424 = 0;
        DAT_0425 = 0;
        if (DAT_047c == '\x0f') {
          DAT_047b = DAT_047b + -1;
        }
        DAT_0061 = 6;
        DAT_00b2 = 8;
        DAT_00b3 = 9;
        DAT_00b4 = 6;
        bVar3 = 1;
        DAT_008f = 1;
        do {
          (&DAT_0480)[bVar3] = 0xff;
          bVar3 = bVar3 + 1;
        } while (bVar3 < 0xb);
        return;
      }
      if ((1 < DAT_0478) && (DAT_0478 < 0xc)) {
        bVar3 = DAT_047a + 1;
        cVar2 = (&DAT_0151)[DAT_047a];
        DAT_047a = bVar3;
        if (cVar2 != -1) {
          uStack0000 = 0xb9;
          officer_address(cVar2);
          DAT_001c = _DAT_0000;
          bVar3 = 0;
          do {
            (&DAT_0160)[bVar3] = 1;
            bVar3 = bVar3 + 1;
          } while (bVar3 < 0x40);
          uStack0000 = 0xbb;
          FUN_f308(cVar2);
          bVar3 = 0;
          for (bVar4 = 0; cVar2 = *(char *)(_DAT_0000 + (ushort)bVar4), cVar2 != '\0';
              bVar4 = bVar4 + 1) {
            if ((cVar2 == '9') || (cVar2 == ':')) {
              bVar3 = bVar3 - 1;
              (&DAT_0163)[bVar3] = cVar2;
            }
            else {
              (&DAT_0183)[bVar3] = cVar2;
            }
            bVar3 = bVar3 + 1;
          }
          DAT_0017 = 0x76;
          DAT_0013 = 2;
          DAT_0014 = 0x2b;
          bVar3 = 0;
          do {
            bVar4 = DAT_0014;
            DAT_0002 = 0;
            DAT_0003 = 0;
            _DAT_0000 = CONCAT11(*(char *)(DAT_001c + (ushort)bVar3),DAT_0000);
            if ((*(char *)(DAT_001c + (ushort)bVar3) == 'd') && (bVar3 == 3)) {
              (&DAT_0160)[DAT_0014] = 0x32;
              (&DAT_0160)[(byte)(bVar4 + 1)] = 0x32;
            }
            else {
              uStack0000 = 0xbb;
              FUN_e9ba();
              uStack0000 = 0xbb;
              FUN_b040(DAT_0014);
            }
            DAT_0014 = DAT_0014 + 3;
            bVar3 = bVar3 + 1;
          } while (bVar3 < 4);
          if (DAT_0479 == 0) {
            DAT_0002 = 0;
            DAT_0003 = 0;
            _DAT_0000 = CONCAT11(*(undefined1 *)(DAT_001c + 4),DAT_0000);
            uStack0000 = 0xbb;
            FUN_e9ba();
            uStack0000 = 0xbb;
            FUN_b040(0x37);
          }
          _DAT_0000 = CONCAT11(*(byte *)(DAT_001c + 6) << 1,DAT_0000);
          DAT_0003 = *(byte *)(DAT_001c + 7) >> 7;
          DAT_0002 = *(byte *)(DAT_001c + 7) << 1 | *(byte *)(DAT_001c + 6) >> 7;
          uStack0000 = 0xbb;
          FUN_e9ba();
          DAT_0007 = DAT_0008;
          DAT_0008 = DAT_0009;
          DAT_0013 = 3;
          if (DAT_0479 == 0) {
            uStack0000 = 0xbb;
            FUN_b040(0x3a);
          }
          else {
            uStack0000 = 0xbb;
            FUN_b040(0x37);
            _DAT_0000 = CONCAT11(*(undefined1 *)(DAT_001c + 8),DAT_0000);
            DAT_0002 = *(byte *)(DAT_001c + 9) & 3;
            DAT_0003 = 0;
            uStack0000 = 0xbc;
            FUN_e9ba();
            DAT_0013 = 4;
            uStack0000 = 0xbc;
            FUN_b040(0x3b);
          }
          bVar5 = 0xbf < DAT_0480;
          DAT_0480 = DAT_0480 + 0x40;
          DAT_0481 = DAT_0481 + bVar5;
          DAT_0478 = DAT_0478 + 1;
          DAT_007e = DAT_007e | 2;
          return;
        }
      }
    }
    if (DAT_0478 == 0xf) {
      bVar3 = 0;
      do {
        (&DAT_0160)[bVar3] = 0xaa;
        bVar3 = bVar3 + 1;
      } while (bVar3 < 0x40);
      DAT_0480 = -0x40;
      DAT_0481 = '\'';
    }
    else {
      if ((DAT_0478 < 2) || ((DAT_0486 == '\0' && (DAT_0486 = '\x01', DAT_047c != '\x0f')))) {
        DAT_001a = CONCAT11(DAT_0483,DAT_0482);
        bVar3 = 0;
        do {
          (&DAT_0160)[bVar3] = *(undefined1 *)(DAT_001a + (ushort)bVar3);
          bVar3 = bVar3 + 1;
        } while (bVar3 < 0x40);
        bVar5 = 0xbf < DAT_0482;
        DAT_0482 = DAT_0482 + 0x40;
        DAT_0483 = DAT_0483 + bVar5;
      }
      else {
        bVar3 = 0;
        do {
          (&DAT_0160)[bVar3] = 1;
          bVar3 = bVar3 + 1;
        } while (bVar3 < 0x40);
      }
      bVar5 = 0xbf < DAT_0480;
      DAT_0480 = DAT_0480 + 0x40;
      DAT_0481 = DAT_0481 + bVar5;
    }
    DAT_0478 = DAT_0478 + 1;
    DAT_007e = DAT_007e | 2;
    return;
  }
  return;
}



/* 0xa012 thunk_FUN_bc41 */

void thunk_FUN_bc41(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_2006 = DAT_0480;
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_0160)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x40);
  return;
}



/* 0xa015 thunk_FUN_dbb1 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_dbb1(void)

{
  byte bVar1;
  
  _DAT_000a = CONCAT11((&DAT_dbd0)[(byte)(DAT_0000 << 1)],(&DAT_dbcf)[(byte)(DAT_0000 << 1)]);
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x100) = *(undefined1 *)(_DAT_000a + (ushort)bVar1);
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x20);
  return;
}



/* 0xa018 thunk_FUN_dd8b */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_dd8b(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  _DAT_0000 = (undefined1 *)0x6000;
  bVar2 = 0;
  do {
    do {
      *(undefined1 *)((short)_DAT_0000 + (ushort)bVar2) = 0;
      bVar2 = bVar2 + 1;
    } while (bVar2 != 0);
    bVar1 = DAT_0001 + 1;
    _DAT_0000 = (undefined1 *)CONCAT11(bVar1,DAT_0000);
  } while (bVar1 < 0x70);
  do {
    uStack0000 = 0xdd;
    bVar2 = FUN_e87a();
  } while (4 < (bVar2 & 7));
  DAT_6f04 = 0xff;
  DAT_6fe2 = 0xff;
  DAT_0400 = 0xb;
  DAT_0401 = 0;
  uStack0000 = 0xdd;
  DAT_6f45 = bVar2 & 7;
  FUN_f25f(0x30);
  _DAT_0000 = (undefined1 *)0x8c00;
  _DAT_0002 = (undefined1 *)0x6000;
  bVar2 = 0;
  DAT_0004 = 0;
  do {
    *_DAT_0002 = *_DAT_0000;
    if ((char)(DAT_0000 + '\x01') == '\0') {
      DAT_0001 = DAT_0001 + '\x01';
    }
    _DAT_0000 = (undefined1 *)CONCAT11(DAT_0001,DAT_0000 + '\x01');
    if ((char)(DAT_0002 + '\x01') == '\0') {
      DAT_0003 = DAT_0003 + '\x01';
    }
    _DAT_0002 = (undefined1 *)CONCAT11(DAT_0003,DAT_0002 + '\x01');
    bVar2 = bVar2 + 1;
    if (bVar2 == 0) {
      DAT_0004 = DAT_0004 + 1;
    }
  } while ((DAT_0004 < 3) || (bVar2 < 0xc0));
  uStack0000 = 0xde;
  FUN_f25f(0x31);
  _DAT_0000 = &DAT_8000;
  _DAT_0002 = (undefined1 *)0x63c0;
  bVar2 = 0;
  DAT_0004 = 0;
  do {
    *_DAT_0002 = *_DAT_0000;
    if ((char)(DAT_0000 + '\x01') == '\0') {
      DAT_0001 = DAT_0001 + '\x01';
    }
    _DAT_0000 = (undefined1 *)CONCAT11(DAT_0001,DAT_0000 + '\x01');
    if ((char)(DAT_0002 + '\x01') == '\0') {
      DAT_0003 = DAT_0003 + '\x01';
    }
    _DAT_0002 = (undefined1 *)CONCAT11(DAT_0003,DAT_0002 + '\x01');
    bVar2 = bVar2 + 1;
    if (bVar2 == 0) {
      DAT_0004 = DAT_0004 + 1;
    }
  } while ((DAT_0004 < 0xb) || (bVar2 < 0x40));
  DAT_6f00 = 0x59;
  DAT_6f01 = 0;
  DAT_6f83 = 0xff;
  DAT_6f84 = 0xff;
  DAT_6f85 = 0xff;
  DAT_6f86 = 0xff;
  DAT_6f87 = 0xff;
  DAT_6f88 = 0xff;
  DAT_6f89 = 0xff;
  DAT_6f8a = 0;
  return;
}



/* 0xa01b thunk_FUN_de7e */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_de7e(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xde;
  DAT_0000 = FUN_f25f(0x21);
  bVar2 = 0;
  bVar1 = DAT_0000 * '\x03';
  DAT_0001 = (((bVar1 >> 7) << 1 | (bVar1 & 0x7f) >> 6) << 1 | (bVar1 & 0x3f) >> 5) << 1 |
             (bVar1 & 0x1f) >> 4;
  _DAT_0002 = CONCAT11(DAT_0001 + 0x94 + (0x93 < (byte)(DAT_0000 * '0')),DAT_0000 * '0' + 0x6c);
  do {
    *(undefined1 *)(bVar2 + 0xae) = *(undefined1 *)(_DAT_0002 + (ushort)bVar2);
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0x30);
  return;
}



/* 0xa01e thunk_FUN_a6b6 */

void thunk_FUN_a6b6(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0002 = 0x9b < DAT_6f00;
  DAT_0001 = DAT_6f00 + 100;
  DAT_0003 = 0;
  uStack0000 = 0xa6;
  FUN_e9ba();
  DAT_0383 = (DAT_0008 & 0xf) + 4;
  DAT_038d = (DAT_0008 & 0xf) + 0x14;
  DAT_0384 = (DAT_0007 >> 4) + 4;
  DAT_038e = (DAT_0007 >> 4) + 0x14;
  DAT_0385 = (DAT_0007 & 0xf) + 4;
  DAT_038f = (DAT_0007 & 0xf) + 0x14;
  DAT_0001 = DAT_6f01 + '\x01';
  DAT_0002 = 0;
  DAT_0003 = 0;
  uStack0000 = 0xa7;
  FUN_e9ba();
  bVar1 = DAT_0007 >> 4;
  if (bVar1 == 0) {
    bVar1 = 0xe;
  }
  DAT_0388 = bVar1 + 4;
  DAT_0392 = bVar1 + 0x14;
  DAT_0389 = (DAT_0007 & 0xf) + 4;
  DAT_0393 = (DAT_0007 & 0xf) + 0x14;
  DAT_0380 = 7;
  DAT_0381 = 0x20;
  DAT_0382 = 0x43;
  DAT_038a = 7;
  DAT_038b = 0x20;
  DAT_038c = 99;
  DAT_0387 = 0x12;
  DAT_0391 = 0x22;
  DAT_0386 = 0xe;
  DAT_0390 = 0x1e;
  DAT_0394 = 0xff;
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa021 thunk_FUN_a77f */

void thunk_FUN_a77f(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  if ((DAT_005e + 5U & 0xf) != 0) {
    return;
  }
  DAT_0001 = DAT_6f05;
  DAT_0002 = 0;
  DAT_0003 = 0;
  uStack0000 = 0xa7;
  FUN_e9ba();
  bVar1 = 0x3a;
  do {
    *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa7f6);
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  if (DAT_0007 >> 4 != 0) {
    DAT_03aa = (DAT_0007 >> 4) + 0x76;
  }
  DAT_03ab = (DAT_0007 & 0xf) + 0x76;
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa024 bank29_entry_24 */

void bank29_entry_24(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0001 = DAT_6f05;
  DAT_0002 = 0;
  DAT_0003 = 0;
  uStack0000 = 0xa7;
  FUN_e9ba();
  bVar1 = 0x3a;
  do {
    *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa7f6);
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  if (DAT_0007 >> 4 != 0) {
    DAT_03aa = (DAT_0007 >> 4) + 0x76;
  }
  DAT_03ab = (DAT_0007 & 0xf) + 0x76;
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa027 thunk_FUN_a830 */

void thunk_FUN_a830(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0x3a;
  do {
    *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa856);
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  uStack0000 = 0xa8;
  FUN_a957(*(undefined1 *)(DAT_0509 + 0x664));
  uStack0000 = 0xa8;
  FUN_a976(*(undefined1 *)(DAT_0509 + 0x664));
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa02a thunk_FUN_a890 */

void thunk_FUN_a890(void)

{
  undefined1 uVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = DAT_0000;
  DAT_0000 = 0;
  far_call_inline_word(0x3d);
  DAT_0000 = uStack0000;
  bVar2 = 0x3a;
  do {
    *(undefined1 *)(bVar2 + 0x380) = *(undefined1 *)(bVar2 + 0xa8c3);
    bVar2 = bVar2 - 1;
  } while (-1 < (char)bVar2);
  uStack0000 = DAT_0000;
  FUN_a957();
  uVar1 = uStack0000;
  uStack0000 = 0xa8;
  FUN_a976(uVar1);
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa02d thunk_FUN_a78a */

void thunk_FUN_a78a(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  if ((DAT_005e + 1U & 3) == 0) {
    if ((DAT_005e + 1U & 4) != 0) {
      DAT_0001 = DAT_6f05;
      DAT_0002 = 0;
      DAT_0003 = 0;
      uStack0000 = 0xa7;
      FUN_e9ba();
      bVar1 = 0x3a;
      do {
        *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa7f6);
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      if (DAT_0007 >> 4 != 0) {
        DAT_03aa = (DAT_0007 >> 4) + 0x76;
      }
      DAT_03ab = (DAT_0007 & 0xf) + 0x76;
      DAT_007e = DAT_007e | 4;
      return;
    }
    bVar1 = 0x3a;
    do {
      *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa7f6);
      bVar1 = bVar1 - 1;
    } while (-1 < (char)bVar1);
    DAT_007e = DAT_007e | 4;
  }
  return;
}



/* 0xa030 thunk_FUN_a8a4 */

void thunk_FUN_a8a4(void)

{
  undefined1 uVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  bVar2 = 0x3a;
  do {
    *(undefined1 *)(bVar2 + 0x380) = *(undefined1 *)(bVar2 + 0xa8c3);
    bVar2 = bVar2 - 1;
  } while (-1 < (char)bVar2);
  uStack0000 = DAT_0000;
  FUN_a957();
  uVar1 = uStack0000;
  uStack0000 = 0xa8;
  FUN_a976(uVar1);
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa033 thunk_FUN_a8fd */

void thunk_FUN_a8fd(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0x3a;
  do {
    *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa91d);
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  uStack0000 = 0xa9;
  FUN_a957(DAT_04ae);
  uStack0000 = 0xa9;
  FUN_a976(DAT_04ae);
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa036 thunk_FUN_bc66 */

void thunk_FUN_bc66(void)

{
  byte bVar1;
  
  bVar1 = 0x3f;
  do {
    (&DAT_0140)[bVar1] = 0;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  return;
}



/* 0xa039 thunk_FUN_bc71 */

void thunk_FUN_bc71(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xbc;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xa03c thunk_FUN_a991 */

void thunk_FUN_a991(void)

{
  undefined1 uVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  if (DAT_0001 == '\0') {
    bVar2 = 0x3a;
    do {
      *(undefined1 *)(bVar2 + 0x380) = (&DAT_a9fd)[bVar2];
      bVar2 = bVar2 - 1;
    } while (-1 < (char)bVar2);
  }
  else {
    bVar2 = 0x3a;
    do {
      *(undefined1 *)(bVar2 + 0x380) = *(undefined1 *)(bVar2 + 0xa9c3);
      bVar2 = bVar2 - 1;
    } while (-1 < (char)bVar2);
  }
  uStack0000 = DAT_0000;
  FUN_a957();
  uVar1 = uStack0000;
  uStack0000 = 0xa9;
  FUN_a976(uVar1);
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa03f thunk_FUN_be36 */

void thunk_FUN_be36(void)

{
  undefined1 uStack0000;
  
  if (DAT_04a0 == 0) {
    return;
  }
  if ((char)DAT_04a0 < '\0') {
    if ((DAT_04a0 & 0xf) != 0) {
      DAT_04a3 = DAT_04a3 + '\x01';
      DAT_04d0 = DAT_04d0 + '\x01';
      uStack0000 = 0xbe;
      FUN_f25f(0x36);
      uStack0000 = 0xbe;
                    /* WARNING: Subroutine does not return */
      tail_dispatch_inline_table(DAT_04a2);
    }
  }
  else {
    DAT_04a2 = DAT_04a0 - 1;
    DAT_04a1 = 0;
    DAT_0420 = 0x40;
    if (-1 < DAT_0150) {
      DAT_0420 = 0x80;
    }
    DAT_04a0 = 0x80;
  }
  uStack0000 = 0xc9;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_04a1);
}



/* 0xa042 thunk_FUN_aa37 */

void thunk_FUN_aa37(void)

{
  char cVar1;
  char cVar2;
  byte bVar3;
  char cStack0000;
  
  cVar2 = DAT_000c;
  cVar1 = DAT_000b;
  cStack0000 = DAT_000a;
  if (DAT_000b != -1) {
    FUN_ab38();
  }
  DAT_000c = cVar2;
  DAT_000b = cVar1;
  DAT_000a = cStack0000;
  if (cVar2 == '\0') {
    bVar3 = 0x30;
    do {
      *(undefined1 *)(bVar3 + 0x380) = 1;
      bVar3 = bVar3 - 1;
    } while (-1 < (char)bVar3);
    if (DAT_000a != -1) {
      bVar3 = DAT_000a * '\f';
      DAT_038d = (&DAT_ab08)[bVar3];
      DAT_038e = (&DAT_ab09)[bVar3];
      DAT_038f = (&DAT_ab0a)[bVar3];
      DAT_0390 = (&DAT_ab0b)[bVar3];
      DAT_0391 = (&DAT_ab0c)[bVar3];
      DAT_0392 = (&DAT_ab0d)[bVar3];
      DAT_03a0 = (&DAT_ab0e)[bVar3];
      DAT_03a1 = (&DAT_ab0f)[bVar3];
      DAT_03a2 = (&DAT_ab10)[bVar3];
      DAT_03a3 = (&DAT_ab11)[bVar3];
      DAT_03a4 = (&DAT_ab12)[bVar3];
      DAT_03a5 = (&DAT_ab13)[bVar3];
      DAT_00bd = 0x76;
      DAT_0389 = 0xc0;
      DAT_038a = 0xc1;
      DAT_039c = 0xd0;
      DAT_039d = 0xd1;
    }
    DAT_0380 = 0x10;
    DAT_0393 = 0x10;
    DAT_0381 = 0x22;
    DAT_0382 = 200;
    DAT_0394 = 0x22;
    DAT_0395 = 0xe8;
    DAT_03a6 = 0xff;
    DAT_007e = DAT_007e | 4;
    return;
  }
  return;
}



/* 0xa045 thunk_FUN_deb9 */

void thunk_FUN_deb9(byte param_1)

{
  byte bVar1;
  
  DAT_0000 = param_1;
  bVar1 = param_1 * '\n';
  DAT_0068 = (&DAT_df1a)[bVar1];
  DAT_0069 = (&DAT_df1b)[bVar1];
  DAT_006a = (&DAT_df1c)[bVar1];
  DAT_006b = (&DAT_df1d)[bVar1];
  DAT_006c = (&DAT_df1e)[bVar1];
  DAT_006d = (&DAT_df1f)[bVar1];
  DAT_006e = (&DAT_df20)[bVar1];
  DAT_006f = (&DAT_df21)[bVar1];
  DAT_0070 = (&DAT_df22)[bVar1];
  DAT_0071 = (&DAT_df23)[bVar1];
  DAT_0072 = (&DAT_df56)[param_1];
  DAT_0073 = (&DAT_df5c)[param_1];
  DAT_0074 = (&DAT_df62)[param_1];
  DAT_0061 = (&DAT_df68)[param_1];
  return;
}



/* 0xa048 FUN_a048 */

void FUN_a048(void)

{
  ushort uVar1;
  char cVar2;
  byte bVar3;
  
  if ((DAT_007e & 4) != 0) {
    return;
  }
  if ((DAT_0303 == '\0') && (DAT_0308 == '\0')) {
    if ((DAT_005e & DAT_0305) != 0) {
      FUN_ee72();
      return;
    }
    if (*(char *)(DAT_0304 + 0x34e) != -0x80) {
      DAT_2007 = *(undefined1 *)(DAT_0304 + 0x31e);
      cVar2 = DAT_031c;
      if (DAT_030c == '\0') {
        DAT_2007 = *(undefined1 *)(DAT_0304 + 0x34e);
        cVar2 = DAT_034c;
      }
      DAT_2006 = cVar2 + DAT_0304;
      DAT_0304 = DAT_0304 + 1;
      return;
    }
  }
  else {
    DAT_2006 = DAT_031c;
    for (bVar3 = 0; uVar1 = (ushort)bVar3, *(char *)(uVar1 + 0x31e) != -0x80; bVar3 = bVar3 + 1) {
      DAT_2007 = *(char *)(uVar1 + 0x31e);
    }
    if (DAT_030c == '\0') {
      DAT_2006 = DAT_034c;
      for (bVar3 = 0; uVar1 = (ushort)bVar3, *(char *)(uVar1 + 0x34e) != -0x80; bVar3 = bVar3 + 1) {
        DAT_2007 = *(char *)(uVar1 + 0x34e);
      }
    }
  }
  DAT_0304 = 0xff;
  DAT_007e = DAT_007e & 0xfe;
  return;
}



/* 0xa11b FUN_a11b */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a11b(void)

{
  char cVar1;
  byte bVar2;
  
  DAT_2000 = DAT_008b & 0xfb;
  _DAT_0000 = 0x380;
  bVar2 = 0;
  while (cVar1 = *(char *)(bVar2 + 0x380), cVar1 != -1) {
    DAT_2006 = *(undefined1 *)((byte)(bVar2 + 2) + 0x380);
    bVar2 = bVar2 + 3;
    do {
      DAT_2007 = *(undefined1 *)(bVar2 + 0x380);
      bVar2 = bVar2 + 1;
      cVar1 = cVar1 + -1;
    } while (cVar1 != '\0');
  }
  return;
}



/* 0xa154 FUN_a154 */

void FUN_a154(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa1;
  FUN_a158();
  return;
}



/* 0xa158 FUN_a158 */

void FUN_a158(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  if ((DAT_0081 & 1) != 0) {
    DAT_0308 = 1;
  }
  if ((DAT_0300 != -1) && ((DAT_007e & 1) == 0)) {
    DAT_0304 = 0;
    uStack0000 = 0xa1;
    FUN_a690();
    if (DAT_0300 == '\0') {
      uStack0000 = 0xa1;
      FUN_a61d();
      bVar1 = 0;
      DAT_0306 = *DAT_00a6;
      uStack0000 = 0xa1;
      FUN_a1df();
      DAT_0307 = DAT_00a6[bVar1];
      uStack0000 = 0xa1;
      FUN_a1df();
      DAT_0300 = '\x01';
      DAT_0303 = 0;
      DAT_0308 = 0;
      DAT_030c = 0;
      DAT_030f = 0;
      DAT_0305 = 3;
    }
    uStack0000 = 0xa1;
    FUN_a60f();
    DAT_031c = DAT_0306;
    DAT_034c = DAT_0306 - 0x20;
    DAT_031d = DAT_0307;
    DAT_034d = DAT_0307 - ((DAT_034c & ~DAT_0306 & 0x80) == 0);
    while( true ) {
      uStack0000 = 0xa1;
      DAT_0012 = FUN_a1df(*DAT_00a6);
      if (((char)DAT_0012 < '\0') && (DAT_0012 < 0xc0)) break;
      uStack0000 = 0xa1;
      FUN_a1e8();
    }
    uStack0000 = 0xa2;
                    /* WARNING: Subroutine does not return */
    tail_dispatch_inline_table(DAT_0012 + 0x80);
  }
  return;
}



/* 0xa1df FUN_a1df */

void FUN_a1df(void)

{
  DAT_00a6._0_1_ = (char)DAT_00a6 + '\x01';
  if ((char)DAT_00a6 == '\0') {
    DAT_00a6._1_1_ = DAT_00a6._1_1_ + '\x01';
  }
  return;
}



/* 0xa1e8 FUN_a1e8 */

void FUN_a1e8(char param_1,byte param_2)

{
  if ((DAT_030c == '\0') && ((param_1 == '9' || (param_1 == ':')))) {
    *(char *)(param_2 + 0x34b) = param_1;
    return;
  }
  (&DAT_031c)[param_2] = param_1 + DAT_030f;
  return;
}



/* 0xa60f FUN_a60f */

void FUN_a60f(void)

{
  byte bVar1;
  
  bVar1 = 0x28;
  do {
    (&DAT_031c)[bVar1] = 1;
    (&DAT_034c)[bVar1] = 1;
    bVar1 = bVar1 - 1;
  } while (bVar1 != 0);
  return;
}



/* 0xa61d FUN_a61d */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a61d(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0001 = DAT_0310 >> 7;
  DAT_0000 = DAT_0310 << 1;
  uStack0000 = 0xa6;
  bVar1 = FUN_a690();
  _DAT_0000 = (undefined1 *)
              CONCAT11(DAT_0001 + (&DAT_a673)[(byte)(bVar1 << 1)] +
                       CARRY1(DAT_0000,(&DAT_a672)[(byte)(bVar1 << 1)]),
                       DAT_0000 + (&DAT_a672)[(byte)(bVar1 << 1)]);
  if ((bVar1 < 9) && (2 < bVar1)) {
    DAT_00a6._0_1_ = *_DAT_0000;
    DAT_00a6._1_1_ = _DAT_0000[1] + '@';
    return;
  }
  DAT_00a6._0_1_ = *_DAT_0000;
  DAT_00a6._1_1_ = _DAT_0000[1] + ' ';
  return;
}



/* 0xa690 FUN_a690 */

byte FUN_a690(void)

{
  byte bStack0000;
  
  bStack0000 = 0;
  if (0x1f < DAT_0310) {
    bStack0000 = DAT_007a;
  }
  FUN_f25f((&DAT_a6a7)[bStack0000]);
  return bStack0000;
}



/* 0xa6b6 FUN_a6b6 */

void FUN_a6b6(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0002 = 0x9b < DAT_6f00;
  DAT_0001 = DAT_6f00 + 100;
  DAT_0003 = 0;
  uStack0000 = 0xa6;
  FUN_e9ba();
  DAT_0383 = (DAT_0008 & 0xf) + 4;
  DAT_038d = (DAT_0008 & 0xf) + 0x14;
  DAT_0384 = (DAT_0007 >> 4) + 4;
  DAT_038e = (DAT_0007 >> 4) + 0x14;
  DAT_0385 = (DAT_0007 & 0xf) + 4;
  DAT_038f = (DAT_0007 & 0xf) + 0x14;
  DAT_0001 = DAT_6f01 + '\x01';
  DAT_0002 = 0;
  DAT_0003 = 0;
  uStack0000 = 0xa7;
  FUN_e9ba();
  bVar1 = DAT_0007 >> 4;
  if (bVar1 == 0) {
    bVar1 = 0xe;
  }
  DAT_0388 = bVar1 + 4;
  DAT_0392 = bVar1 + 0x14;
  DAT_0389 = (DAT_0007 & 0xf) + 4;
  DAT_0393 = (DAT_0007 & 0xf) + 0x14;
  DAT_0380 = 7;
  DAT_0381 = 0x20;
  DAT_0382 = 0x43;
  DAT_038a = 7;
  DAT_038b = 0x20;
  DAT_038c = 99;
  DAT_0387 = 0x12;
  DAT_0391 = 0x22;
  DAT_0386 = 0xe;
  DAT_0390 = 0x1e;
  DAT_0394 = 0xff;
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa77f FUN_a77f */

void FUN_a77f(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  if ((DAT_005e + 5U & 0xf) != 0) {
    return;
  }
  DAT_0001 = DAT_6f05;
  DAT_0002 = 0;
  DAT_0003 = 0;
  uStack0000 = 0xa7;
  FUN_e9ba();
  bVar1 = 0x3a;
  do {
    *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa7f6);
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  if (DAT_0007 >> 4 != 0) {
    DAT_03aa = (DAT_0007 >> 4) + 0x76;
  }
  DAT_03ab = (DAT_0007 & 0xf) + 0x76;
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa78a FUN_a78a */

void FUN_a78a(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  if ((DAT_005e + 1U & 3) == 0) {
    if ((DAT_005e + 1U & 4) != 0) {
      DAT_0001 = DAT_6f05;
      DAT_0002 = 0;
      DAT_0003 = 0;
      uStack0000 = 0xa7;
      FUN_e9ba();
      bVar1 = 0x3a;
      do {
        *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa7f6);
        bVar1 = bVar1 - 1;
      } while (-1 < (char)bVar1);
      if (DAT_0007 >> 4 != 0) {
        DAT_03aa = (DAT_0007 >> 4) + 0x76;
      }
      DAT_03ab = (DAT_0007 & 0xf) + 0x76;
      DAT_007e = DAT_007e | 4;
      return;
    }
    bVar1 = 0x3a;
    do {
      *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa7f6);
      bVar1 = bVar1 - 1;
    } while (-1 < (char)bVar1);
    DAT_007e = DAT_007e | 4;
  }
  return;
}



/* 0xa7b2 FUN_a7b2 */

void FUN_a7b2(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0001 = DAT_6f05;
  DAT_0002 = 0;
  DAT_0003 = 0;
  uStack0000 = 0xa7;
  FUN_e9ba();
  bVar1 = 0x3a;
  do {
    *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa7f6);
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  if (DAT_0007 >> 4 != 0) {
    DAT_03aa = (DAT_0007 >> 4) + 0x76;
  }
  DAT_03ab = (DAT_0007 & 0xf) + 0x76;
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa830 FUN_a830 */

void FUN_a830(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0x3a;
  do {
    *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa856);
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  uStack0000 = 0xa8;
  FUN_a957(*(undefined1 *)(DAT_0509 + 0x664));
  uStack0000 = 0xa8;
  FUN_a976(*(undefined1 *)(DAT_0509 + 0x664));
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa890 FUN_a890 */

void FUN_a890(void)

{
  undefined1 uVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = DAT_0000;
  DAT_0000 = 0;
  far_call_inline_word(0x3d);
  DAT_0000 = uStack0000;
  bVar2 = 0x3a;
  do {
    *(undefined1 *)(bVar2 + 0x380) = *(undefined1 *)(bVar2 + 0xa8c3);
    bVar2 = bVar2 - 1;
  } while (-1 < (char)bVar2);
  uStack0000 = DAT_0000;
  FUN_a957();
  uVar1 = uStack0000;
  uStack0000 = 0xa8;
  FUN_a976(uVar1);
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa8a4 FUN_a8a4 */

void FUN_a8a4(void)

{
  undefined1 uVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  bVar2 = 0x3a;
  do {
    *(undefined1 *)(bVar2 + 0x380) = *(undefined1 *)(bVar2 + 0xa8c3);
    bVar2 = bVar2 - 1;
  } while (-1 < (char)bVar2);
  uStack0000 = DAT_0000;
  FUN_a957();
  uVar1 = uStack0000;
  uStack0000 = 0xa8;
  FUN_a976(uVar1);
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa8fd FUN_a8fd */

void FUN_a8fd(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0x3a;
  do {
    *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa91d);
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  uStack0000 = 0xa9;
  FUN_a957(DAT_04ae);
  uStack0000 = 0xa9;
  FUN_a976(DAT_04ae);
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xa957 FUN_a957 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a957(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xa9;
  bVar2 = FUN_f308();
  bVar3 = 0;
  while (cVar1 = *(char *)(_DAT_0000 + (ushort)bVar3), cVar1 != '\0') {
    if ((cVar1 == '9') || (cVar1 == ':')) {
      (&DAT_03a5)[bVar2] = cVar1;
      bVar3 = bVar3 + 1;
    }
    else {
      bVar3 = bVar3 + 1;
      bVar2 = bVar2 + 1;
    }
  }
  return;
}



/* 0xa976 FUN_a976 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a976(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xa9;
  bVar2 = FUN_f308();
  for (bVar3 = 0; cVar1 = *(char *)(_DAT_0000 + (ushort)bVar3), cVar1 != '\0'; bVar3 = bVar3 + 1) {
    if ((cVar1 != '9') && (cVar1 != ':')) {
      *(char *)(bVar2 + 0x3b1) = cVar1;
      bVar2 = bVar2 + 1;
    }
  }
  return;
}



/* 0xa991 FUN_a991 */

void FUN_a991(void)

{
  undefined1 uVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  if (DAT_0001 == '\0') {
    bVar2 = 0x3a;
    do {
      *(undefined1 *)(bVar2 + 0x380) = (&DAT_a9fd)[bVar2];
      bVar2 = bVar2 - 1;
    } while (-1 < (char)bVar2);
  }
  else {
    bVar2 = 0x3a;
    do {
      *(undefined1 *)(bVar2 + 0x380) = *(undefined1 *)(bVar2 + 0xa9c3);
      bVar2 = bVar2 - 1;
    } while (-1 < (char)bVar2);
  }
  uStack0000 = DAT_0000;
  FUN_a957();
  uVar1 = uStack0000;
  uStack0000 = 0xa9;
  FUN_a976(uVar1);
  DAT_007e = DAT_007e | 4;
  return;
}



/* 0xaa37 FUN_aa37 */

void FUN_aa37(void)

{
  char cVar1;
  char cVar2;
  byte bVar3;
  char cStack0000;
  
  cVar2 = DAT_000c;
  cVar1 = DAT_000b;
  cStack0000 = DAT_000a;
  if (DAT_000b != -1) {
    FUN_ab38();
  }
  DAT_000c = cVar2;
  DAT_000b = cVar1;
  DAT_000a = cStack0000;
  if (cVar2 == '\0') {
    bVar3 = 0x30;
    do {
      *(undefined1 *)(bVar3 + 0x380) = 1;
      bVar3 = bVar3 - 1;
    } while (-1 < (char)bVar3);
    if (DAT_000a != -1) {
      bVar3 = DAT_000a * '\f';
      DAT_038d = (&DAT_ab08)[bVar3];
      DAT_038e = (&DAT_ab09)[bVar3];
      DAT_038f = (&DAT_ab0a)[bVar3];
      DAT_0390 = (&DAT_ab0b)[bVar3];
      DAT_0391 = (&DAT_ab0c)[bVar3];
      DAT_0392 = (&DAT_ab0d)[bVar3];
      DAT_03a0 = (&DAT_ab0e)[bVar3];
      DAT_03a1 = (&DAT_ab0f)[bVar3];
      DAT_03a2 = (&DAT_ab10)[bVar3];
      DAT_03a3 = (&DAT_ab11)[bVar3];
      DAT_03a4 = (&DAT_ab12)[bVar3];
      DAT_03a5 = (&DAT_ab13)[bVar3];
      DAT_00bd = 0x76;
      DAT_0389 = 0xc0;
      DAT_038a = 0xc1;
      DAT_039c = 0xd0;
      DAT_039d = 0xd1;
    }
    DAT_0380 = 0x10;
    DAT_0393 = 0x10;
    DAT_0381 = 0x22;
    DAT_0382 = 200;
    DAT_0394 = 0x22;
    DAT_0395 = 0xe8;
    DAT_03a6 = 0xff;
    DAT_007e = DAT_007e | 4;
    return;
  }
  return;
}



/* 0xab38 FUN_ab38 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ab38(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xab;
  FUN_f25f(0x31);
  _DAT_0000 = (undefined1 *)(ushort)DAT_000b;
  DAT_0002 = 0;
  DAT_0003 = 0xd;
  uStack0000 = 0xab;
  FUN_ebe9();
  _DAT_0000 = (undefined1 *)CONCAT11(DAT_0007 + -0x73 + (0x4b < DAT_0006),DAT_0006 + 0xb4);
  DAT_00b9 = *_DAT_0000;
  DAT_0002 = '0';
  bVar1 = 1;
  do {
    if (_DAT_0000[bVar1] == -1) break;
    DAT_0002 = DAT_0002 + -0x10;
    bVar1 = bVar1 + 4;
  } while (bVar1 < 0xd);
  bVar1 = 1;
  do {
    if (_DAT_0000[bVar1] == -1) {
      return;
    }
    *(char *)(DAT_007c + 0x201) = _DAT_0000[bVar1] + -0x40;
    *(undefined1 *)(DAT_007c + 0x200) = *(undefined1 *)(bVar1 + 0xabb8);
    *(char *)(DAT_007c + 0x203) = *(char *)(bVar1 + 0xabc5) + DAT_0002;
    *(undefined1 *)(DAT_007c + 0x202) = 1;
    DAT_007c = DAT_007c + 4;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0xd);
  return;
}



/* 0xabd2 FUN_abd2 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_abd2(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  if (DAT_037c != '\0') {
    uStack0000 = 0xab;
    FUN_f25f(0x31);
    if (DAT_037d != -1) {
      uStack0000 = 0xab;
      FUN_b14c(1);
    }
    if (DAT_037e != -1) {
      uStack0000 = 0xab;
      FUN_b14c(2);
    }
  }
  if (DAT_0140 == 0) {
    return;
  }
  if (-1 < (char)DAT_0140) {
    if ((DAT_0140 & 0xf) == 1) {
      if ((DAT_0150 & 0xf) == 0) {
        DAT_0420 = 0;
      }
      if ((DAT_0150 & 0xf) == 1) {
        DAT_037c = -1;
      }
      DAT_0150 = DAT_0150 & 0x80;
      DAT_0140 = 0;
      return;
    }
    if ((DAT_007e & 8) != 0) {
      return;
    }
    if ((DAT_0150 & 0xf) == 0) goto LAB_aec9;
    goto LAB_adf3;
  }
  DAT_037c = '\0';
  DAT_0140 = 5;
  DAT_0143 = 0;
  DAT_0144 = -0x80;
  DAT_0154 = 0x38;
  if ((DAT_0150 & 0xf) == 0) {
    DAT_0142 = '\"';
    DAT_0148 = '#';
    DAT_037c = '\0';
    if ((char)DAT_0150 < '\0') {
      DAT_0145 = 0xe4;
      DAT_0147 = 0xec;
      DAT_0141 = 0x90;
      DAT_0143 = 0x10;
    }
    else {
      DAT_0145 = 0xe0;
      DAT_0147 = 0xe8;
      DAT_0141 = 0x82;
      DAT_0143 = 2;
    }
    DAT_0146 = -0x7d;
    DAT_0144 = -0x7e;
LAB_aec9:
    DAT_0140 = DAT_0140 - 1;
    uStack0000 = 0xae;
    FUN_f25f(0x30);
    DAT_0010 = (byte *)CONCAT11(DAT_0144,DAT_0143);
    bVar1 = 0;
    do {
      bVar2 = 0;
      do {
        (&DAT_0160)[bVar1] = *(undefined1 *)((short)DAT_0010 + (ushort)bVar2);
        bVar2 = bVar2 + 1;
        bVar1 = bVar1 + 1;
      } while (bVar2 < 0xe);
      DAT_0010 = (byte *)CONCAT11(DAT_0010._1_1_ + (0xdf < (byte)DAT_0010),(byte)DAT_0010 + 0x20);
    } while (bVar1 < 0x38);
    bVar1 = DAT_0143 + 0x80;
    DAT_0144 = DAT_0144 -
               (((~DAT_0143 & 0x80) == 0 && (bVar1 & 0x80) == 0) && (bVar1 & ~DAT_0143 & 0x80) == 0)
    ;
    DAT_0010 = (byte *)CONCAT11(DAT_0146,DAT_0145);
    bVar2 = 0;
    DAT_0143 = bVar1;
    do {
      (&DAT_014b)[bVar2] = *(undefined1 *)((short)DAT_0010 + (ushort)bVar2);
      bVar2 = bVar2 + 1;
    } while (bVar2 < 4);
    bVar2 = DAT_0145 - 8;
    bVar1 = ~DAT_0145;
    DAT_0145 = bVar2;
    DAT_0146 = DAT_0146 - ((bVar2 & bVar1 & 0x80) == 0);
    bVar2 = DAT_0147 - 8;
    bVar1 = ~DAT_0147;
    DAT_0147 = bVar2;
    DAT_0148 = DAT_0148 - ((bVar2 & bVar1 & 0x80) == 0);
    bVar2 = DAT_0141 + 0x80;
    bVar1 = ~DAT_0141;
    DAT_0141 = bVar2;
    DAT_0142 = DAT_0142 -
               (((bVar1 & 0x80) == 0 && (bVar2 & 0x80) == 0) && (bVar2 & bVar1 & 0x80) == 0);
    DAT_007e = DAT_007e | 8;
    return;
  }
  DAT_0152 = 0x83;
  DAT_0153 = 0xb6;
  DAT_00b4 = 9;
  DAT_00c4 = 9;
  DAT_00cc = 9;
  DAT_00d4 = 9;
  DAT_00dc = 9;
  DAT_0420 = 0x80;
  if ((char)DAT_0150 < '\0') {
    DAT_0420 = 0x40;
  }
  bVar1 = DAT_0150 & 0xf;
  if (bVar1 == 1) {
    DAT_0149 = 5;
    DAT_014a = 0xb3;
    uStack0000 = 0xac;
    region_address(DAT_0402);
    DAT_037e = _DAT_0000[0x11];
    if (*_DAT_0000 == '\a') {
      DAT_037d = -1;
    }
    else {
      bVar1 = *_DAT_0000 << 1;
      _DAT_0000 = (char *)CONCAT11((&DAT_ad85)[bVar1],(&DAT_ad84)[bVar1]);
      DAT_037d = *_DAT_0000;
    }
    DAT_00b4 = 8;
    DAT_00c4 = 8;
    DAT_00cc = 8;
    DAT_00d4 = 8;
    DAT_00d3 = 1;
    DAT_00cb = DAT_00d3;
  }
  else if (bVar1 == 2) {
LAB_ac95:
    DAT_0149 = 0xe5;
    DAT_014a = 0xb3;
    DAT_00cb = 1;
    DAT_00d3 = 5;
  }
  else if (bVar1 == 3) {
    DAT_0149 = 0xc1;
    DAT_014a = 0xb4;
    DAT_00d3 = 5;
    DAT_00cb = DAT_00d3;
  }
  else {
    if (bVar1 != 4) goto LAB_ac95;
    DAT_0149 = 0x9c;
    DAT_014a = 0xb5;
    DAT_00d3 = 5;
    DAT_00cb = DAT_00d3;
  }
  DAT_00c2 = 0;
  DAT_00ca = 0;
  DAT_00d2 = 0;
  DAT_00da = 0;
  DAT_0142 = ' ';
  DAT_0148 = '#';
  if ((char)DAT_0150 < '\0') {
    DAT_0147 = 0xc4;
    DAT_0145 = 0x7f;
    DAT_0141 = 0x10;
    bVar1 = 0xcc;
  }
  else {
    DAT_0147 = 0xc0;
    DAT_0145 = 0x7b;
    DAT_0141 = 2;
    bVar1 = 200;
  }
  DAT_0146 = -0x4a;
  bVar3 = CARRY1(bVar1,DAT_0143);
  DAT_0143 = bVar1 + DAT_0143;
  DAT_0144 = DAT_0144 + '\x03' + bVar3;
  DAT_00b3 = DAT_00cb;
  DAT_00c3 = DAT_00cb;
  DAT_00db = DAT_00d3;
LAB_adf3:
  DAT_0140 = DAT_0140 - 1;
  uStack0000 = 0xad;
  FUN_f25f(0x30);
  DAT_0010 = (byte *)CONCAT11(DAT_014a,DAT_0149);
  bVar2 = 0;
  bVar1 = 0;
  do {
    if (*(byte *)((short)DAT_0010 + (ushort)bVar2) < 0xf0) {
      (&DAT_0160)[bVar1] = *(byte *)((short)DAT_0010 + (ushort)bVar2);
      bVar2 = bVar2 + 1;
      bVar1 = bVar1 + 1;
    }
    else {
      uStack0000 = 0xae;
      FUN_af77();
    }
  } while (bVar1 < 0x38);
  uStack0000 = 0xae;
  FUN_af66(bVar2,9);
  DAT_0010 = (byte *)CONCAT11(DAT_0146,DAT_0145);
  _DAT_0012 = (byte *)CONCAT11(DAT_0144,DAT_0143);
  DAT_014b = *_DAT_0012 & 0x33 | *DAT_0010;
  bVar1 = 1;
  do {
    (&DAT_014b)[bVar1] = DAT_0010[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < 3);
  (&DAT_014b)[bVar1] = _DAT_0012[bVar1] & 0xcc | DAT_0010[bVar1];
  uStack0000 = 0xae;
  FUN_af66(8,7);
  uStack0000 = 0xae;
  FUN_af66(8,3);
  uStack0000 = 0xae;
  FUN_af66(0x80,1);
  if ((DAT_0150 & 0xf) == 1) {
    if (DAT_0140 == '\x04') {
      uStack0000 = 0xae;
      FUN_b0ab();
    }
    uStack0000 = 0xae;
    region_address(DAT_0402);
    if (*_DAT_0000 != '\a') {
      if (DAT_0140 == '\x04') {
        uStack0000 = 0xae;
        FUN_b23a(0);
      }
      else if (DAT_0140 == '\x03') {
        uStack0000 = 0xae;
        FUN_b23a(1);
        uStack0000 = 0xae;
        FUN_b27a();
      }
      else if (DAT_0140 == '\x02') {
        DAT_000f = 2;
        uStack0000 = 0xae;
        FUN_b27a();
      }
    }
  }
  DAT_007e = DAT_007e | 8;
  return;
}



/* 0xaf66 FUN_af66 */

void FUN_af66(byte param_1,byte param_2)

{
  byte bVar1;
  
  bVar1 = (&DAT_0140)[param_2];
  (&DAT_0140)[param_2] = param_1 + bVar1;
  (&DAT_0140)[(byte)(param_2 + 1)] = (&DAT_0140)[(byte)(param_2 + 1)] + CARRY1(param_1,bVar1);
  return;
}



/* 0xaf77 FUN_af77 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_af77(char param_1,byte param_2,char param_3)

{
  ushort uVar1;
  char cVar2;
  byte bVar3;
  bool bVar4;
  byte bStack0000;
  
  DAT_0013 = *(char *)(DAT_0010 + (ushort)(byte)(param_3 + 1));
  bStack0000 = param_3 + 2;
  DAT_0012 = param_1;
  region_address(DAT_0402);
  uVar1 = (ushort)bStack0000;
  bStack0000 = bStack0000 + 1;
  _DAT_0017 = (undefined1 *)
              CONCAT11(DAT_0001 + CARRY1(*(byte *)(DAT_0010 + uVar1),DAT_0000),
                       *(byte *)(DAT_0010 + uVar1) + DAT_0000);
  if (DAT_0012 == -0x10) {
    bVar3 = 0;
    DAT_0002 = '\0';
    _DAT_0000 = _DAT_0000 & 0xff;
    do {
      if (_DAT_0017[bVar3] != -1) {
        _DAT_0000 = CONCAT11(DAT_0001 + '\x01',DAT_0000);
      }
      bVar3 = bVar3 + 1;
    } while (bVar3 < 10);
  }
  else if (DAT_0012 == -0xf) {
    _DAT_0000 = CONCAT11(*_DAT_0017,DAT_0000);
    DAT_0002 = _DAT_0017[1];
  }
  else if (DAT_0012 == -0xd) {
    DAT_0002 = 0;
    DAT_0003 = '\0';
    DAT_0004 = 0;
    do {
      if (_DAT_0017[DAT_0004] == -1) break;
      officer_address();
      bVar4 = CARRY1(*(byte *)(_DAT_0000 + 8),DAT_0002);
      DAT_0002 = *(byte *)(_DAT_0000 + 8) + DAT_0002;
      DAT_0003 = *(char *)(_DAT_0000 + 9) + DAT_0003 + bVar4;
      DAT_0004 = DAT_0004 + 1;
    } while (DAT_0004 < 10);
    _DAT_0000 = CONCAT11(DAT_0002,DAT_0000);
    DAT_0002 = DAT_0003;
  }
  else {
    _DAT_0000 = CONCAT11(*_DAT_0017,DAT_0000);
    DAT_0002 = '\0';
  }
  DAT_0003 = 0;
  FUN_e9ba();
  cVar2 = bStack0000;
  _DAT_0017 = (undefined1 *)CONCAT11(DAT_0018,0xb6);
  DAT_0016 = 1;
  if (DAT_0013 != '\x02') {
    if (DAT_0013 != '\x03') {
      if (DAT_0013 != '\x04') {
        if (DAT_0013 != '\x05') {
          bStack0000 = 0xb0;
          FUN_b091(DAT_0009 >> 4,cVar2);
        }
        bStack0000 = 0xb0;
        FUN_b091(DAT_0009 & 0xf);
      }
      bStack0000 = 0xb0;
      FUN_b091(DAT_0008 >> 4);
    }
    bStack0000 = 0xb0;
    FUN_b091(DAT_0008 & 0xf);
  }
  bStack0000 = 0xb0;
  FUN_b091(DAT_0007 >> 4);
  DAT_0016 = DAT_0017;
  if ((DAT_0007 & 0xf) == 0) {
    (&DAT_0160)[param_2] = DAT_0017;
  }
  else {
    (&DAT_0160)[param_2] = (DAT_0007 & 0xf) + DAT_0017;
    DAT_0016 = DAT_0017;
  }
  return;
}



/* 0xb040 FUN_b040 */

void FUN_b040(byte param_1)

{
  undefined1 uStack0000;
  
  DAT_0016 = 1;
  if (DAT_0013 != '\x02') {
    if (DAT_0013 != '\x03') {
      if (DAT_0013 != '\x04') {
        if (DAT_0013 != '\x05') {
          uStack0000 = 0xb0;
          FUN_b091(DAT_0009 >> 4);
        }
        uStack0000 = 0xb0;
        FUN_b091(DAT_0009 & 0xf);
      }
      uStack0000 = 0xb0;
      FUN_b091(DAT_0008 >> 4);
    }
    uStack0000 = 0xb0;
    FUN_b091(DAT_0008 & 0xf);
  }
  uStack0000 = 0xb0;
  FUN_b091(DAT_0007 >> 4);
  DAT_0016 = DAT_0017;
  if ((DAT_0007 & 0xf) == 0) {
    (&DAT_0160)[param_1] = DAT_0017;
  }
  else {
    (&DAT_0160)[param_1] = (DAT_0007 & 0xf) + DAT_0017;
    DAT_0016 = DAT_0017;
  }
  return;
}



/* 0xb091 FUN_b091 */

void FUN_b091(char param_1,byte param_2)

{
  char in_Z;
  
  if (in_Z == '\0') {
    (&DAT_0160)[param_2] = param_1 + DAT_0017;
    DAT_0016 = DAT_0017;
  }
  else {
    (&DAT_0160)[param_2] = DAT_0016;
  }
  return;
}



/* 0xb0ab FUN_b0ab */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b0ab(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  _DAT_0000 = (undefined1 *)
              CONCAT11(((DAT_0402 * '\x03' & 0x7f) >> 6) + CARRY1(DAT_0402 * '\f',DAT_0402) +
                       DAT_0153 + CARRY1(DAT_0402 * '\r',DAT_0152),DAT_0402 * '\r' + DAT_0152);
  DAT_00b2 = *_DAT_0000;
  bVar3 = 1;
  bVar2 = 0;
  DAT_00c2 = DAT_00b2;
  DAT_00ca = DAT_00b2;
  DAT_00d2 = DAT_00b2;
  DAT_00da = DAT_00b2;
  do {
    (&DAT_016f)[bVar2] = _DAT_0000[bVar3];
    bVar3 = bVar3 + 1;
    bVar2 = bVar2 + 1;
  } while (bVar3 < 7);
  bVar2 = 0;
  do {
    (&DAT_017d)[bVar2] = _DAT_0000[bVar3];
    bVar3 = bVar3 + 1;
    bVar2 = bVar2 + 1;
  } while (bVar3 < 0xd);
  uStack0000 = 0xb1;
  FUN_f25f(0x30);
  _DAT_0000 = (undefined1 *)
              CONCAT11((0xe5 < (byte)(DAT_0402 * '\b')) + -0x66,DAT_0402 * '\b' + 0x1a);
  bVar3 = 0;
  bVar2 = 0;
  do {
    if (*(char *)((short)_DAT_0000 + (ushort)bVar3) == '\0') {
      return;
    }
    cVar1 = *(char *)((short)_DAT_0000 + (ushort)bVar3) + -0x80;
    if ((cVar1 == -0x47) || (cVar1 == -0x46)) {
      bVar2 = bVar2 - 1;
      (&DAT_0175)[bVar2] = cVar1;
    }
    else {
      (&DAT_0183)[bVar2] = cVar1;
    }
    bVar3 = bVar3 + 1;
    bVar2 = bVar2 + 1;
  } while (bVar3 < 8);
  return;
}



/* 0xb14c FUN_b14c */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b14c(byte param_1)

{
  undefined1 uVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  
  DAT_0005 = '\0';
  if (DAT_0150 < '\0') {
    DAT_0005 = 'p';
  }
  DAT_0007 = '@';
  DAT_0006 = '\0';
  if (param_1 != 1) {
    DAT_0007 = -0x80;
    DAT_0006 = ' ';
  }
  bVar3 = (&DAT_037c)[param_1] * '\x02';
  bVar4 = bVar3 + (&DAT_037c)[param_1];
  bVar2 = bVar4 * '\x04' + (&DAT_037c)[param_1];
  _DAT_0000 = (undefined1 *)
              CONCAT11((((CARRY1(bVar3,(&DAT_037c)[param_1]) - ((char)(&DAT_037c)[param_1] >> 7)) *
                         '\x02' | bVar4 >> 7) << 1 | (bVar4 & 0x7f) >> 6) +
                       CARRY1(bVar4 * '\x04',(&DAT_037c)[param_1]) + -0x73 + (0x4b < bVar2),
                       bVar2 + 0xb4);
  _DAT_0002 = &DAT_b222;
  bVar4 = 0;
  DAT_0004 = 0;
  uVar1 = *_DAT_0000;
  *(undefined1 *)(param_1 + 0xae) = uVar1;
  *(undefined1 *)(param_1 + 0xbe) = uVar1;
  *(undefined1 *)(param_1 + 0xc6) = uVar1;
  *(undefined1 *)(param_1 + 0xce) = uVar1;
  *(undefined1 *)(param_1 + 0xd6) = uVar1;
  do {
    bVar4 = bVar4 + 1;
    if (_DAT_0000[bVar4] == -1) {
      return;
    }
    *(char *)(DAT_007c + 0x201) = _DAT_0000[bVar4] + DAT_0007;
    *(undefined1 *)(DAT_007c + 0x202) = 1;
    *(char *)(DAT_007c + 0x203) = _DAT_0002[DAT_0004] + DAT_0005;
    *(char *)(DAT_007c + 0x200) = _DAT_0002[(byte)(DAT_0004 + 1)] + DAT_0006;
    DAT_0004 = DAT_0004 + 2;
    DAT_007c = DAT_007c + 4;
  } while (bVar4 < 0xc);
  return;
}



/* 0xb23a FUN_b23a */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b23a(char param_1)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xb2;
  DAT_000f = param_1;
  region_address(DAT_0402);
  if (*_DAT_0000 != '\a') {
    bVar2 = 1;
    if (DAT_000f != '\0') {
      bVar2 = 2;
    }
    uStack0000 = 0xb2;
    FUN_f308((&DAT_037c)[bVar2]);
    bVar2 = 0;
    for (bVar3 = 0; cVar1 = _DAT_0000[bVar3], cVar1 != '\0'; bVar3 = bVar3 + 1) {
      if ((cVar1 == '9') || (cVar1 == ':')) {
        bVar2 = bVar2 - 1;
        (&DAT_0190)[bVar2] = cVar1 + -0x80;
      }
      bVar2 = bVar2 + 1;
    }
  }
  return;
}



/* 0xb27a FUN_b27a */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b27a(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xb2;
  FUN_f308((&DAT_037c)[DAT_000f]);
  bVar2 = 0;
  for (bVar3 = 0; cVar1 = *(char *)(_DAT_0000 + (ushort)bVar3), cVar1 != '\0'; bVar3 = bVar3 + 1) {
    if ((cVar1 != '9') && (cVar1 != ':')) {
      (&DAT_0166)[bVar2] = cVar1 + -0x80;
      bVar2 = bVar2 + 1;
    }
  }
  return;
}



/* 0xb29f FUN_b29f */

void FUN_b29f(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_0001 = DAT_0142;
  DAT_0000 = DAT_0141;
  bVar1 = 0;
  do {
    bVar2 = 0;
    do {
      bVar2 = bVar2 + 1;
      bVar1 = bVar1 + 1;
    } while (bVar2 < 0xe);
    bVar3 = 0xdf < DAT_0000;
    DAT_0000 = DAT_0000 + 0x20;
    DAT_0001 = DAT_0001 + bVar3;
  } while (bVar1 < DAT_0154);
  DAT_2006 = DAT_0147;
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_014b)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < 4);
  return;
}



/* 0xb989 FUN_b989 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b989(void)

{
  undefined1 uVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  bool bVar5;
  undefined1 uStack0000;
  
  if (((DAT_0140 == '\0') && ((DAT_007e & 2) == 0)) && (DAT_0478 != 0)) {
    if ((char)DAT_0478 < '\0') {
      DAT_0479 = DAT_0478 & 0xf;
      DAT_0478 = 0;
      DAT_047a = 0;
      DAT_047b = '\0';
      DAT_0486 = '\0';
      DAT_0480 = 0xc0;
      DAT_0481 = '#';
      uStack0000 = 0xba;
      FUN_f25f(0x30);
      if (DAT_047c == -1) {
        DAT_047c = '\x0f';
        bVar3 = 0;
        do {
          if ((&DAT_0151)[bVar3] != -1) {
            DAT_047b = DAT_047b + '\x01';
          }
          bVar3 = bVar3 + 1;
        } while (bVar3 < 10);
      }
      else {
        uVar1 = DAT_0402;
        if (DAT_0479 == 2) {
          DAT_0479 = 0;
          uVar1 = DAT_040c;
        }
        uStack0000 = 0xba;
        region_address(uVar1);
        bVar4 = 0x11;
        bVar3 = 0;
        do {
          cVar2 = *(char *)(_DAT_0000 + (ushort)bVar4);
          (&DAT_0151)[bVar3] = cVar2;
          if (cVar2 != -1) {
            DAT_047b = DAT_047b + '\x01';
          }
          bVar3 = bVar3 + 1;
          bVar4 = bVar4 + 1;
        } while (bVar3 < 10);
      }
      if (DAT_0479 == 0) {
        DAT_0482 = 0xc9;
        DAT_0483 = -0x48;
      }
      else {
        DAT_0482 = 9;
        DAT_0483 = -0x48;
      }
    }
    else {
      if (DAT_0478 == 0x10) {
        DAT_0478 = 0;
        DAT_047a = 0;
        DAT_0480 = 0;
        DAT_0424 = 0;
        DAT_0425 = 0;
        if (DAT_047c == '\x0f') {
          DAT_047b = DAT_047b + -1;
        }
        DAT_0061 = 6;
        DAT_00b2 = 8;
        DAT_00b3 = 9;
        DAT_00b4 = 6;
        bVar3 = 1;
        DAT_008f = 1;
        do {
          (&DAT_0480)[bVar3] = 0xff;
          bVar3 = bVar3 + 1;
        } while (bVar3 < 0xb);
        return;
      }
      if ((1 < DAT_0478) && (DAT_0478 < 0xc)) {
        bVar3 = DAT_047a + 1;
        cVar2 = (&DAT_0151)[DAT_047a];
        DAT_047a = bVar3;
        if (cVar2 != -1) {
          uStack0000 = 0xb9;
          officer_address(cVar2);
          DAT_001c = _DAT_0000;
          bVar3 = 0;
          do {
            (&DAT_0160)[bVar3] = 1;
            bVar3 = bVar3 + 1;
          } while (bVar3 < 0x40);
          uStack0000 = 0xbb;
          FUN_f308(cVar2);
          bVar3 = 0;
          for (bVar4 = 0; cVar2 = *(char *)(_DAT_0000 + (ushort)bVar4), cVar2 != '\0';
              bVar4 = bVar4 + 1) {
            if ((cVar2 == '9') || (cVar2 == ':')) {
              bVar3 = bVar3 - 1;
              (&DAT_0163)[bVar3] = cVar2;
            }
            else {
              (&DAT_0183)[bVar3] = cVar2;
            }
            bVar3 = bVar3 + 1;
          }
          DAT_0017 = 0x76;
          DAT_0013 = 2;
          DAT_0014 = 0x2b;
          bVar3 = 0;
          do {
            bVar4 = DAT_0014;
            DAT_0002 = 0;
            DAT_0003 = 0;
            _DAT_0000 = CONCAT11(*(char *)(DAT_001c + (ushort)bVar3),DAT_0000);
            if ((*(char *)(DAT_001c + (ushort)bVar3) == 'd') && (bVar3 == 3)) {
              (&DAT_0160)[DAT_0014] = 0x32;
              (&DAT_0160)[(byte)(bVar4 + 1)] = 0x32;
            }
            else {
              uStack0000 = 0xbb;
              FUN_e9ba();
              uStack0000 = 0xbb;
              FUN_b040(DAT_0014);
            }
            DAT_0014 = DAT_0014 + 3;
            bVar3 = bVar3 + 1;
          } while (bVar3 < 4);
          if (DAT_0479 == 0) {
            DAT_0002 = 0;
            DAT_0003 = 0;
            _DAT_0000 = CONCAT11(*(undefined1 *)(DAT_001c + 4),DAT_0000);
            uStack0000 = 0xbb;
            FUN_e9ba();
            uStack0000 = 0xbb;
            FUN_b040(0x37);
          }
          _DAT_0000 = CONCAT11(*(byte *)(DAT_001c + 6) << 1,DAT_0000);
          DAT_0003 = *(byte *)(DAT_001c + 7) >> 7;
          DAT_0002 = *(byte *)(DAT_001c + 7) << 1 | *(byte *)(DAT_001c + 6) >> 7;
          uStack0000 = 0xbb;
          FUN_e9ba();
          DAT_0007 = DAT_0008;
          DAT_0008 = DAT_0009;
          DAT_0013 = 3;
          if (DAT_0479 == 0) {
            uStack0000 = 0xbb;
            FUN_b040(0x3a);
          }
          else {
            uStack0000 = 0xbb;
            FUN_b040(0x37);
            _DAT_0000 = CONCAT11(*(undefined1 *)(DAT_001c + 8),DAT_0000);
            DAT_0002 = *(byte *)(DAT_001c + 9) & 3;
            DAT_0003 = 0;
            uStack0000 = 0xbc;
            FUN_e9ba();
            DAT_0013 = 4;
            uStack0000 = 0xbc;
            FUN_b040(0x3b);
          }
          bVar5 = 0xbf < DAT_0480;
          DAT_0480 = DAT_0480 + 0x40;
          DAT_0481 = DAT_0481 + bVar5;
          DAT_0478 = DAT_0478 + 1;
          DAT_007e = DAT_007e | 2;
          return;
        }
      }
    }
    if (DAT_0478 == 0xf) {
      bVar3 = 0;
      do {
        (&DAT_0160)[bVar3] = 0xaa;
        bVar3 = bVar3 + 1;
      } while (bVar3 < 0x40);
      DAT_0480 = -0x40;
      DAT_0481 = '\'';
    }
    else {
      if ((DAT_0478 < 2) || ((DAT_0486 == '\0' && (DAT_0486 = '\x01', DAT_047c != '\x0f')))) {
        DAT_001a = CONCAT11(DAT_0483,DAT_0482);
        bVar3 = 0;
        do {
          (&DAT_0160)[bVar3] = *(undefined1 *)(DAT_001a + (ushort)bVar3);
          bVar3 = bVar3 + 1;
        } while (bVar3 < 0x40);
        bVar5 = 0xbf < DAT_0482;
        DAT_0482 = DAT_0482 + 0x40;
        DAT_0483 = DAT_0483 + bVar5;
      }
      else {
        bVar3 = 0;
        do {
          (&DAT_0160)[bVar3] = 1;
          bVar3 = bVar3 + 1;
        } while (bVar3 < 0x40);
      }
      bVar5 = 0xbf < DAT_0480;
      DAT_0480 = DAT_0480 + 0x40;
      DAT_0481 = DAT_0481 + bVar5;
    }
    DAT_0478 = DAT_0478 + 1;
    DAT_007e = DAT_007e | 2;
    return;
  }
  return;
}



/* 0xbc41 FUN_bc41 */

void FUN_bc41(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_2006 = DAT_0480;
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_0160)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x40);
  return;
}



/* 0xbc66 FUN_bc66 */

void FUN_bc66(void)

{
  byte bVar1;
  
  bVar1 = 0x3f;
  do {
    (&DAT_0140)[bVar1] = 0;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  return;
}



/* 0xbc71 FUN_bc71 */

void FUN_bc71(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xbc;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xbe36 FUN_be36 */

void FUN_be36(void)

{
  undefined1 uStack0000;
  
  if (DAT_04a0 == 0) {
    return;
  }
  if ((char)DAT_04a0 < '\0') {
    if ((DAT_04a0 & 0xf) != 0) {
      DAT_04a3 = DAT_04a3 + '\x01';
      DAT_04d0 = DAT_04d0 + '\x01';
      uStack0000 = 0xbe;
      FUN_f25f(0x36);
      uStack0000 = 0xbe;
                    /* WARNING: Subroutine does not return */
      tail_dispatch_inline_table(DAT_04a2);
    }
  }
  else {
    DAT_04a2 = DAT_04a0 - 1;
    DAT_04a1 = 0;
    DAT_0420 = 0x40;
    if (-1 < DAT_0150) {
      DAT_0420 = 0x80;
    }
    DAT_04a0 = 0x80;
  }
  uStack0000 = 0xc9;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_04a1);
}



/* 0xdbb1 FUN_dbb1 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_dbb1(void)

{
  byte bVar1;
  
  _DAT_000a = CONCAT11((&DAT_dbd0)[(byte)(DAT_0000 << 1)],(&DAT_dbcf)[(byte)(DAT_0000 << 1)]);
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x100) = *(undefined1 *)(_DAT_000a + (ushort)bVar1);
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x20);
  return;
}



/* 0xdd8b FUN_dd8b */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_dd8b(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  _DAT_0000 = (undefined1 *)0x6000;
  bVar2 = 0;
  do {
    do {
      *(undefined1 *)((short)_DAT_0000 + (ushort)bVar2) = 0;
      bVar2 = bVar2 + 1;
    } while (bVar2 != 0);
    bVar1 = DAT_0001 + 1;
    _DAT_0000 = (undefined1 *)CONCAT11(bVar1,DAT_0000);
  } while (bVar1 < 0x70);
  do {
    uStack0000 = 0xdd;
    bVar2 = FUN_e87a();
  } while (4 < (bVar2 & 7));
  DAT_6f04 = 0xff;
  DAT_6fe2 = 0xff;
  DAT_0400 = 0xb;
  DAT_0401 = 0;
  uStack0000 = 0xdd;
  DAT_6f45 = bVar2 & 7;
  FUN_f25f(0x30);
  _DAT_0000 = (undefined1 *)0x8c00;
  _DAT_0002 = (undefined1 *)0x6000;
  bVar2 = 0;
  DAT_0004 = 0;
  do {
    *_DAT_0002 = *_DAT_0000;
    if ((char)(DAT_0000 + '\x01') == '\0') {
      DAT_0001 = DAT_0001 + '\x01';
    }
    _DAT_0000 = (undefined1 *)CONCAT11(DAT_0001,DAT_0000 + '\x01');
    if ((char)(DAT_0002 + '\x01') == '\0') {
      DAT_0003 = DAT_0003 + '\x01';
    }
    _DAT_0002 = (undefined1 *)CONCAT11(DAT_0003,DAT_0002 + '\x01');
    bVar2 = bVar2 + 1;
    if (bVar2 == 0) {
      DAT_0004 = DAT_0004 + 1;
    }
  } while ((DAT_0004 < 3) || (bVar2 < 0xc0));
  uStack0000 = 0xde;
  FUN_f25f(0x31);
  _DAT_0000 = &DAT_8000;
  _DAT_0002 = (undefined1 *)0x63c0;
  bVar2 = 0;
  DAT_0004 = 0;
  do {
    *_DAT_0002 = *_DAT_0000;
    if ((char)(DAT_0000 + '\x01') == '\0') {
      DAT_0001 = DAT_0001 + '\x01';
    }
    _DAT_0000 = (undefined1 *)CONCAT11(DAT_0001,DAT_0000 + '\x01');
    if ((char)(DAT_0002 + '\x01') == '\0') {
      DAT_0003 = DAT_0003 + '\x01';
    }
    _DAT_0002 = (undefined1 *)CONCAT11(DAT_0003,DAT_0002 + '\x01');
    bVar2 = bVar2 + 1;
    if (bVar2 == 0) {
      DAT_0004 = DAT_0004 + 1;
    }
  } while ((DAT_0004 < 0xb) || (bVar2 < 0x40));
  DAT_6f00 = 0x59;
  DAT_6f01 = 0;
  DAT_6f83 = 0xff;
  DAT_6f84 = 0xff;
  DAT_6f85 = 0xff;
  DAT_6f86 = 0xff;
  DAT_6f87 = 0xff;
  DAT_6f88 = 0xff;
  DAT_6f89 = 0xff;
  DAT_6f8a = 0;
  return;
}



/* 0xde7e FUN_de7e */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_de7e(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xde;
  DAT_0000 = FUN_f25f(0x21);
  bVar2 = 0;
  bVar1 = DAT_0000 * '\x03';
  DAT_0001 = (((bVar1 >> 7) << 1 | (bVar1 & 0x7f) >> 6) << 1 | (bVar1 & 0x3f) >> 5) << 1 |
             (bVar1 & 0x1f) >> 4;
  _DAT_0002 = CONCAT11(DAT_0001 + 0x94 + (0x93 < (byte)(DAT_0000 * '0')),DAT_0000 * '0' + 0x6c);
  do {
    *(undefined1 *)(bVar2 + 0xae) = *(undefined1 *)(_DAT_0002 + (ushort)bVar2);
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0x30);
  return;
}



/* 0xdeb9 FUN_deb9 */

void FUN_deb9(byte param_1)

{
  byte bVar1;
  
  DAT_0000 = param_1;
  bVar1 = param_1 * '\n';
  DAT_0068 = (&DAT_df1a)[bVar1];
  DAT_0069 = (&DAT_df1b)[bVar1];
  DAT_006a = (&DAT_df1c)[bVar1];
  DAT_006b = (&DAT_df1d)[bVar1];
  DAT_006c = (&DAT_df1e)[bVar1];
  DAT_006d = (&DAT_df1f)[bVar1];
  DAT_006e = (&DAT_df20)[bVar1];
  DAT_006f = (&DAT_df21)[bVar1];
  DAT_0070 = (&DAT_df22)[bVar1];
  DAT_0071 = (&DAT_df23)[bVar1];
  DAT_0072 = (&DAT_df56)[param_1];
  DAT_0073 = (&DAT_df5c)[param_1];
  DAT_0074 = (&DAT_df62)[param_1];
  DAT_0061 = (&DAT_df68)[param_1];
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
  thunk_FUN_de7e();
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
      bVar1 = thunk_FUN_b29f();
      return bVar1;
    }
    if ((char)(DAT_007e << 5) < '\0') {
      DAT_007e = DAT_007e & 0xfb;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = thunk_FUN_a11b();
      return bVar1;
    }
    if ((char)(DAT_007e << 6) < '\0') {
      DAT_007e = DAT_007e & 0xfd;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = thunk_FUN_bc41();
      return bVar1;
    }
    if ((char)(DAT_007e << 7) < '\0') {
      bStack0000 = 0xee;
      FUN_f237(DAT_007e << 7,0x3d);
      bVar1 = bank29_entry_00();
      return bVar1;
    }
  }
  DAT_2000 = DAT_008b & 0xfb;
  bVar1 = 0;
  DAT_007d = 0;
  do {
    DAT_2007 = (&DAT_0101)[bVar1];
    bVar1 = bVar1 + 2;
  } while (bVar1 < 0x20);
  DAT_2006 = 0;
  return 0;
}



/* 0xee72 FUN_ee72 */

void FUN_ee72(void)

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
  bank29_entry_00 = DAT_00b2;
  DAT_a800 = DAT_00b3;
                    /* WARNING: Read-only address (RAM,0xb000) is written */
  uRAMb000 = DAT_00b4;
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



/* 0xf308 FUN_f308 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 FUN_f308(byte param_1)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xf3;
  DAT_0002 = param_1;
  FUN_f25f(0x30);
  _DAT_0000 = CONCAT11(((((DAT_0002 >> 7) << 1 | (DAT_0002 & 0x7f) >> 6) +
                        CARRY1(DAT_0002 * '\x04',DAT_0002)) * '\x02' |
                       (byte)(DAT_0002 * '\x05') >> 7) + 0x90 + (0xe5 < (byte)(DAT_0002 * '\n')),
                       DAT_0002 * '\n' + 0x1a);
  bVar3 = 0;
  bVar2 = 0;
  while (cVar1 = *(char *)(_DAT_0000 + (ushort)bVar3), cVar1 != '\0') {
    bVar3 = bVar3 + 1;
    if ((cVar1 != '9') && (cVar1 != ':')) {
      bVar2 = bVar2 + 1;
    }
  }
  return *(undefined1 *)(bVar2 - 0xca1);
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
  thunk_FUN_a154();
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


