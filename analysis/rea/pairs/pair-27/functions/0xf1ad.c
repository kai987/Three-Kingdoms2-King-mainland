
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

