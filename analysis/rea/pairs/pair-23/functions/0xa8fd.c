
undefined1 FUN_a8fd(undefined1 param_1,byte param_2)

{
  undefined1 uVar1;
  undefined1 uStack0000;
  undefined2 unaff_retaddr;
  
  if (*(char *)(DAT_0019 + 0x680) == -1) {
    return param_1;
  }
  uStack0000 = param_1;
  FUN_a986(unaff_retaddr._1_1_,*(char *)(DAT_0019 + 0x680));
  DAT_0008 = &DAT_01b0;
  if ((DAT_000c & 8) == 0) {
    if ((DAT_0006 != '\0') || ((DAT_000e & 8) == 0)) {
      (&DAT_0142)[param_2] = DAT_01b0;
      param_2 = param_2 + 1;
    }
    uVar1 = DAT_0008[2];
    (&DAT_0142)[param_2] = uVar1;
    return uVar1;
  }
  if ((DAT_0006 != '\0') || ((DAT_000e & 8) == 0)) {
    (&DAT_0142)[param_2] = DAT_01b1;
    param_2 = param_2 + 1;
  }
  uVar1 = DAT_0008[3];
  (&DAT_0142)[param_2] = uVar1;
  return uVar1;
}

