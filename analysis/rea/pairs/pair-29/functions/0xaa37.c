
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

