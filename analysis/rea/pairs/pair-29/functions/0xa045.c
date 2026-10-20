
void thunk_FUN_deb9(byte param_1)

{
  byte bVar1;
  
  DAT_0000 = param_1;
  bVar1 = param_1 * '\n';
  DAT_0068 = (&DAT_df1a)[bVar1];
  DAT_0069 = (&DAT_df1b)[bVar1];
  DAT_006a = (&DAT_df1c)[bVar1];
  DAT_006b = (&DAT_df1d)[bVar1];
  DAT_006c = (&DAT_df1e)[bVar1];
  DAT_006d = (&DAT_df1f)[bVar1];
  DAT_006e = (&DAT_df20)[bVar1];
  DAT_006f = (&DAT_df21)[bVar1];
  DAT_0070 = (&DAT_df22)[bVar1];
  DAT_0071 = (&DAT_df23)[bVar1];
  DAT_0072 = (&DAT_df56)[param_1];
  DAT_0073 = (&DAT_df5c)[param_1];
  DAT_0074 = (&DAT_df62)[param_1];
  DAT_0061 = (&DAT_df68)[param_1];
  return;
}

