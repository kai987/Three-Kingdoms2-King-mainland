
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b2d7(void)

{
  ushort uVar1;
  byte bVar2;
  bool bVar3;
  byte bStack0000;
  
  uVar1 = _DAT_0000;
  if ((DAT_007e & 4) == 0) {
    _DAT_0000 = _DAT_0000 & 0xff;
    if (-1 < (char)DAT_040d) {
      bStack0000 = DAT_040d;
      DAT_0382 = DAT_040d << 5;
      DAT_0381 = ((((DAT_040d >> 7) << 1 | (DAT_040d & 0x7f) >> 6) << 1 | (DAT_040d & 0x3f) >> 5) <<
                  1 | (DAT_040d & 0x1f) >> 4) << 1 | (DAT_040d & 0xf) >> 3;
      DAT_0380 = 0x20;
      _DAT_0000 = CONCAT11(DAT_040c,(char)uVar1);
      DAT_0002 = 0;
      DAT_0004 = 0;
      DAT_0003 = 3;
      FUN_ea7c();
      bVar3 = CARRY1((&DAT_b4b9)[(byte)(DAT_0005 << 1)],DAT_0382);
      DAT_0382 = (&DAT_b4b9)[(byte)(DAT_0005 << 1)] + DAT_0382;
      DAT_0381 = (&DAT_b4ba)[(byte)(DAT_0005 << 1)] + DAT_0381 + bVar3;
      if (*(char *)(DAT_040c + 0x410) == -2) {
        bStack0000 = 0x10;
      }
      else {
        bStack0000 = bStack0000 << 1;
      }
      _DAT_0000 = CONCAT11((&DAT_b386)[bStack0000],(&DAT_b385)[bStack0000]);
      bVar2 = 0;
      do {
        *(undefined1 *)(bVar2 + 899) = *(undefined1 *)(_DAT_0000 + bVar2);
        bVar2 = bVar2 + 1;
      } while (bVar2 < 0x20);
      bStack0000 = 0xb3;
      FUN_b4bf();
      DAT_03a3 = 0xff;
      DAT_007e = DAT_007e | 4;
      DAT_040d = DAT_040d + 1;
      if (9 < DAT_040d) {
        DAT_040d = 0xff;
      }
      return;
    }
  }
  return;
}

