
void FUN_aa2d(byte param_1)

{
  undefined1 uVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  undefined1 uStack0000;
  
  DAT_0025 = 0xff;
  DAT_0026 = 0xff;
  DAT_0027 = 0;
  DAT_0024 = param_1;
  do {
    if (*(char *)(DAT_0024 + 0x664) != -1) {
      uStack0000 = 0xaa;
      cVar2 = FUN_d2ab(3);
      if ((cVar2 != 'd') &&
         (bVar3 = *(char *)(DAT_0022 + 1) + *(char *)(DAT_0022 + 2), bVar3 < DAT_0025)) {
        DAT_0026 = DAT_0024;
        DAT_0025 = bVar3;
      }
    }
    DAT_0024 = DAT_0024 + 1;
    DAT_0027 = DAT_0027 + 1;
  } while (DAT_0027 < 10);
  uVar1 = *(undefined1 *)(DAT_0026 + 0x664);
  *(undefined1 *)(DAT_0026 + 0x664) = 0xff;
  bVar4 = 0xb;
  uStack0000 = 0xaa;
  bVar3 = FUN_d2ab(uVar1);
  *(byte *)(DAT_0022 + (ushort)bVar4) = bVar3 & 0xfc | 3;
  return;
}

