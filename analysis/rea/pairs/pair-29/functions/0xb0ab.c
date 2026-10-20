
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

