
void FUN_c983(byte param_1)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  undefined1 uStack0000;
  
code_r0xc983:
  bVar4 = false;
  DAT_0010 = 0;
  DAT_0011 = 0;
  bVar2 = 0;
  do {
    uStack0000 = 0xc9;
    FUN_cc92();
    if (!bVar4) {
      bVar1 = (&DAT_6fa1)[bVar2] & 0xf;
      if (bVar1 == 7) {
        (&DAT_6fa1)[bVar2] = (byte)(&DAT_6fa1)[bVar2] >> 4;
      }
      else if (4 < bVar1) {
        if (bVar1 == 5) {
          bVar1 = 100;
        }
        else {
          bVar1 = 0x32;
        }
        bVar4 = CARRY1(bVar1,DAT_0010);
        DAT_0010 = bVar1 + DAT_0010;
        DAT_0011 = DAT_0011 + bVar4;
      }
    }
    bVar1 = bVar2 + 1;
    bVar4 = (char)(bVar2 - 0x13) < '\0';
    bVar2 = bVar1;
  } while (bVar1 < 0x14);
  uStack0000 = 0xc9;
  FUN_c93e();
  bVar1 = *(byte *)(param_1 + 0x526) - DAT_0010;
  bVar2 = ~*(byte *)(param_1 + 0x526);
  bVar1 = (*(byte *)(param_1 + 0x527) - DAT_0011) -
          (((DAT_0010 & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
  bVar2 = ~*(byte *)(param_1 + 0x527);
  if (((DAT_0011 & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
    DAT_0010 = 6;
    do {
      bVar4 = false;
      bVar2 = 0;
      do {
        uStack0000 = 0xc9;
        FUN_cc92();
        if ((!bVar4) && (((&DAT_6fa1)[bVar2] & 0xf) == DAT_0010)) {
          (&DAT_6fa1)[bVar2] = (byte)(&DAT_6fa1)[bVar2] >> 4;
          goto code_r0xc983;
        }
        bVar1 = bVar2 + 1;
        bVar4 = (char)(bVar2 - 0x13) < '\0';
        bVar2 = bVar1;
      } while (bVar1 < 0x14);
      bVar1 = DAT_0010 - 1;
      DAT_0010 = bVar1;
    } while (4 < bVar1);
  }
  uStack0000 = 0xca;
  FUN_cd00(bVar1);
  uStack0000 = 0xca;
  FUN_c93e();
  bVar1 = (&DAT_0522)[param_1] - DAT_001a;
  bVar2 = ~(&DAT_0522)[param_1];
  bVar1 = ((&DAT_0523)[param_1] - DAT_001b) -
          (((DAT_001a & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
  bVar2 = ~(&DAT_0523)[param_1];
  if (((DAT_001b & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
    uStack0000 = 0xca;
    FUN_f25f(0x31);
    DAT_0000 = DAT_050e * '\x02';
    if (*(char *)((byte)(DAT_050e * '\x06') + 0x9ba4) != -1) {
      uStack0000 = 0xca;
      FUN_c93e();
      if ((*(char *)(param_1 + 0x527) != '\0') || (99 < *(byte *)(param_1 + 0x526))) {
        bVar4 = false;
        bVar2 = 0;
        do {
          uStack0000 = 0xca;
          FUN_cc92();
          if ((!bVar4) && (bVar1 = (&DAT_6fa1)[bVar2] & 0xf, bVar1 == 5)) goto LAB_cac2;
          bVar1 = bVar2 + 1;
          bVar4 = (char)(bVar2 - 0x13) < '\0';
          bVar2 = bVar1;
        } while (bVar1 < 0x14);
        uStack0000 = 0xca;
        bVar1 = FUN_cb6a();
        goto LAB_cac2;
      }
    }
    uStack0000 = 0xca;
    FUN_cd06(10);
    uStack0000 = 0xca;
    FUN_c93e();
    bVar1 = (&DAT_0522)[param_1] - DAT_001a;
    bVar2 = ~(&DAT_0522)[param_1];
    bVar1 = ((&DAT_0523)[param_1] - DAT_001b) -
            (((DAT_001a & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
    bVar2 = ~(&DAT_0523)[param_1];
    if (((DAT_001b & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
      uStack0000 = 0xca;
      bVar1 = FUN_cbfe(bVar1);
    }
  }
  else {
    uStack0000 = 0xca;
    FUN_c93e(bVar1);
    param_1 = param_1 ^ 2;
    bVar1 = (&DAT_0522)[param_1] - DAT_001c;
    bVar2 = ~(&DAT_0522)[param_1];
    bVar1 = ((&DAT_0523)[param_1] - DAT_001d) -
            (((DAT_001c & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
    bVar2 = ~(&DAT_0523)[param_1];
    if (((DAT_001d & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
      uStack0000 = 0xca;
      FUN_cd06(5);
      uStack0000 = 0xca;
      FUN_c93e();
      param_1 = param_1 ^ 2;
      bVar1 = (&DAT_0522)[param_1] - DAT_001c;
      bVar2 = ~(&DAT_0522)[param_1];
      bVar1 = ((&DAT_0523)[param_1] - DAT_001d) -
              (((DAT_001c & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
      bVar2 = ~(&DAT_0523)[param_1];
      if (((DAT_001d & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
        uStack0000 = 0xca;
        bVar1 = FUN_cb4d(bVar1);
      }
    }
  }
LAB_cac2:
  uStack0000 = 0xca;
  FUN_f25f(bVar1,0x31);
  DAT_0000 = DAT_050e * '\x02';
  if (*(char *)((byte)(DAT_050e * '\x06' + 4) + 0x9ba4) != -1) {
    uStack0000 = 0xca;
    FUN_c93e();
    if ((*(char *)(param_1 + 0x527) != '\0') || (0x31 < *(byte *)(param_1 + 0x526))) {
      bVar1 = 0;
      bVar4 = false;
      bVar2 = 0;
      do {
        uStack0000 = 0xca;
        FUN_cc92();
        if ((!bVar4) && (((&DAT_6fa1)[bVar2] & 0xf) == 6)) {
          bVar1 = bVar1 + 1;
        }
        bVar3 = bVar2 + 1;
        bVar4 = (char)(bVar2 - 0x13) < '\0';
        bVar2 = bVar3;
      } while (bVar3 < 0x14);
      if (bVar1 < 2) {
        bVar4 = false;
        bVar2 = 0;
        DAT_0010 = bVar1;
        do {
          uStack0000 = 0xcb;
          FUN_cc92();
          if (((!bVar4) && ((&DAT_6fa1)[bVar2] != 0)) && ((byte)(&DAT_6fa1)[bVar2] < 5)) {
            uStack0000 = 0xcb;
            FUN_cc19();
          }
          bVar1 = bVar2 + 1;
          bVar4 = (char)(bVar2 - 0x13) < '\0';
          bVar2 = bVar1;
        } while (bVar1 < 0x14);
      }
    }
  }
  uStack0000 = 0xcb;
  FUN_ccaa();
  bVar2 = (DAT_001d - 3) -
          (((~DAT_001c & 0xe8 | DAT_001c + 0x18 & 0xe8 | DAT_001c + 0x18 & ~DAT_001c) & 0x80) == 0);
  if ((bVar2 & ~DAT_001d & 0x80) == 0) {
    bVar2 = (DAT_001b - 0x13) -
            (((~DAT_001a & 0x88 | DAT_001a + 0x78 & 0x88 | DAT_001a + 0x78 & ~DAT_001a) & 0x80) == 0
            );
    if ((bVar2 & ~DAT_001b & 0x80) != 0) {
      FUN_cbfe(bVar2);
      return;
    }
    FUN_cb9a();
    return;
  }
  FUN_cb9a(bVar2);
  return;
}

