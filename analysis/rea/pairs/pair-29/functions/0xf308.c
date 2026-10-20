
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 FUN_f308(byte param_1)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xf3;
  DAT_0002 = param_1;
  FUN_f25f(0x30);
  _DAT_0000 = CONCAT11(((((DAT_0002 >> 7) << 1 | (DAT_0002 & 0x7f) >> 6) +
                        CARRY1(DAT_0002 * '\x04',DAT_0002)) * '\x02' |
                       (byte)(DAT_0002 * '\x05') >> 7) + 0x90 + (0xe5 < (byte)(DAT_0002 * '\n')),
                       DAT_0002 * '\n' + 0x1a);
  bVar3 = 0;
  bVar2 = 0;
  while (cVar1 = *(char *)(_DAT_0000 + (ushort)bVar3), cVar1 != '\0') {
    bVar3 = bVar3 + 1;
    if ((cVar1 != '9') && (cVar1 != ':')) {
      bVar2 = bVar2 + 1;
    }
  }
  return *(undefined1 *)(bVar2 - 0xca1);
}

