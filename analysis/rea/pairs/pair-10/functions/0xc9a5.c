
void FUN_c9a5(void)

{
  undefined1 uVar1;
  byte bVar2;
  char cVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xc9;
  bVar2 = FUN_d105(DAT_0036);
  if ((bVar2 & 7) != DAT_0037) {
    return;
  }
  DAT_003a = 0x11;
  DAT_003b = 0;
  DAT_003c = 0xff;
  do {
    if (*(char *)(DAT_0020 + (ushort)DAT_003a) != -1) {
      uStack0000 = 0xc9;
      cVar3 = FUN_d2ab(3);
      if (cVar3 == 'd') {
        DAT_003c = DAT_003a;
        break;
      }
      bVar2 = cVar3 + *(char *)(DAT_0022 + 4);
      if (DAT_003b <= bVar2) {
        DAT_003c = DAT_003a;
        DAT_003b = bVar2;
      }
    }
    DAT_003a = DAT_003a + 1;
  } while (DAT_003a < 0x1b);
  if ((DAT_003c != 0xff) && (DAT_003c != 0x11)) {
    uVar1 = *(undefined1 *)(DAT_0020 + 0x11);
    *(undefined1 *)(DAT_0020 + 0x11) = *(undefined1 *)(DAT_0020 + (ushort)DAT_003c);
    *(undefined1 *)(DAT_0020 + (ushort)DAT_003c) = uVar1;
  }
  return;
}

