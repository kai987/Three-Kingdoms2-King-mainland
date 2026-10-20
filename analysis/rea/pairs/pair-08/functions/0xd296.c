
void FUN_d296(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  char cVar5;
  undefined1 uStack0000;
  
  bVar4 = DAT_000a >> 7;
  bVar1 = DAT_000a & 0x7f;
  bVar2 = DAT_000a & 0x3f;
  bVar3 = DAT_000a & 0x1f;
  DAT_000a = DAT_000a << 4;
  DAT_000b = ((bVar4 << 1 | bVar1 >> 6) << 1 | bVar2 >> 5) << 1 | bVar3 >> 4;
  bVar4 = DAT_000c >> 7;
  bVar1 = DAT_000c & 0x7f;
  bVar2 = DAT_000c & 0x3f;
  bVar3 = DAT_000c & 0x1f;
  DAT_000c = DAT_000c << 4;
  cVar5 = '\0';
  DAT_000d = ((bVar4 << 1 | bVar1 >> 6) << 1 | bVar2 >> 5) << 1 | bVar3 >> 4;
  uStack0000 = 0xd2;
  FUN_d337();
  if (cVar5 != '\0') {
    DAT_0000 = 0x26;
    DAT_0001 = 0xd3;
    DAT_0002 = 0;
    DAT_0003 = 0;
    DAT_0004 = 0x9c;
    FUN_f09c();
    return;
  }
  return;
}

