
void FUN_dcd8(byte param_1)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xdc;
  FUN_dc31();
  if ((((DAT_07f4 & 0x40) != 0x40) && (*(char *)(param_1 + 0x715) == '\0')) &&
     ((char)*(byte *)(param_1 + 0x701) < '\0')) {
    DAT_07f7 = *(byte *)(param_1 + 0x701) & 0x70;
    *(char *)(DAT_07f5 + 0x4002) =
         (&DAT_dd5e)[DAT_07f9 & 0xf | DAT_07f7] + *(char *)(param_1 + 0x712);
  }
  return;
}

