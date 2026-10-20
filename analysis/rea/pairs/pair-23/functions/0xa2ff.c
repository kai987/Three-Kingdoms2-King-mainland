
void FUN_a2ff(void)

{
  undefined1 uVar1;
  byte bVar2;
  char cVar3;
  byte bVar4;
  char cVar5;
  byte bStack0000;
  
  cVar3 = DAT_0091;
  bVar2 = DAT_0090;
  uVar1 = DAT_008f;
  bStack0000 = DAT_008e;
  DAT_001e = DAT_0090;
  DAT_001f = DAT_0091;
  DAT_0091 = DAT_0091 + '\x01';
  cVar5 = '\x1e';
  do {
    FUN_a485();
    FUN_ad9f();
    do {
      FUN_eee6();
    } while (DAT_007e != '\0');
    bVar4 = DAT_0090 - 8;
    if ((DAT_0090 - 8 & ~DAT_0090 & 0x80) == 0) {
      DAT_0091 = DAT_0091 + -1;
      bVar4 = DAT_0090 - 0x18;
    }
    DAT_0090 = bVar4;
    cVar5 = cVar5 + -1;
  } while (-1 < cVar5);
  DAT_0091 = cVar3;
  DAT_0090 = bVar2;
  DAT_008f = uVar1;
  DAT_008e = bStack0000;
  DAT_0092 = bVar2 >> 3;
  DAT_0094 = (byte)(bVar2 + 8) >> 4;
  DAT_0095 = (byte)(bStack0000 - 6) >> 3;
  DAT_0093 = bStack0000 >> 3;
  DAT_009c = 0x90;
  DAT_009d = 0x90;
  return;
}

