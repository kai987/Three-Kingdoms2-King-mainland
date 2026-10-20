
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

