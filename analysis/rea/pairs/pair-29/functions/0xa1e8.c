
void FUN_a1e8(char param_1,byte param_2)

{
  if ((DAT_030c == '\0') && ((param_1 == '9' || (param_1 == ':')))) {
    *(char *)(param_2 + 0x34b) = param_1;
    return;
  }
  (&DAT_031c)[param_2] = param_1 + DAT_030f;
  return;
}

