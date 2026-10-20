
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

