
byte FUN_a52a(byte param_1)

{
  byte bVar1;
  byte bVar2;
  
  bVar1 = *(byte *)(DAT_0010 + (ushort)(byte)(param_1 + 1));
  bVar2 = (bVar1 - 0x27) -
          ((*(byte *)(DAT_0010 + (ushort)param_1) - 0x10 & ~*(byte *)(DAT_0010 + (ushort)param_1) &
           0x80) == 0);
  if ((bVar2 & ~bVar1 & 0x80) != 0) {
    *(undefined1 *)(DAT_0010 + (ushort)(byte)(param_1 + 1)) = 0x27;
    bVar2 = 0xf;
    *(undefined1 *)(DAT_0010 + (ushort)param_1) = 0xf;
  }
  return bVar2;
}

