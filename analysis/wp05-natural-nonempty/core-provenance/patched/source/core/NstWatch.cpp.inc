// WP05 passive nonempty postbattle observer. All storage is outside serialized objects.
static unsigned watch_mask=0,watch_frame=0,watch_count=0,watch_overflow=0;
static unsigned watch_sequence=0,watch_instruction_pc=0xFFFF,watch_active=0;
static unsigned watch_events[65536][72];
static unsigned watch_snapshot_count=0,watch_snapshot_sequence=0,watch_snapshot_overflow=0;
static unsigned char watch_snapshots[64][10240];
static void (*watch_provider)(const void*,unsigned,unsigned*)=0;
static void (*watch_snapshot_provider)(const void*,unsigned char*)=0;
static const void* watch_board=0;
extern "C" {
__attribute__((visibility("default"))) void nestopia_wp05_enable(unsigned mask){watch_mask=mask;}
__attribute__((visibility("default"))) void nestopia_wp05_begin_frame(unsigned frame){watch_frame=frame;watch_count=0;watch_overflow=0;watch_snapshot_count=0;watch_snapshot_overflow=0;}
__attribute__((visibility("default"))) unsigned nestopia_wp05_count(){return watch_count;}
__attribute__((visibility("default"))) unsigned nestopia_wp05_overflow(){return watch_overflow;}
__attribute__((visibility("default"))) unsigned nestopia_wp05_words(){return 72;}
__attribute__((visibility("default"))) const unsigned* nestopia_wp05_data(){return &watch_events[0][0];}
__attribute__((visibility("default"))) unsigned nestopia_wp05_snapshot_count(){return watch_snapshot_count;}
__attribute__((visibility("default"))) unsigned nestopia_wp05_snapshot_overflow(){return watch_snapshot_overflow;}
__attribute__((visibility("default"))) const unsigned char* nestopia_wp05_snapshot_data(){return &watch_snapshots[0][0];}
void nestopia_wp05_set_provider(void (*provider)(const void*,unsigned,unsigned*),const void* board){watch_provider=provider;watch_board=board;}
void nestopia_wp05_set_snapshot_provider(void (*provider)(const void*,unsigned char*)){watch_snapshot_provider=provider;}
}
static unsigned watch_write_before=0xFFFFFFFF;
static bool watch_city(unsigned address){return (watch_mask&1)&&address>=0x6000&&address<0x63C0&&((address&31)==1||(address&31)>=28);}
// Observation predicates only: never execute an emulated bus read or alter CPU state.
static unsigned watch_seen_hold=0,watch_stage2_far=0,watch_human_seen[2][7]={},watch_root_seen[3][8]={};
// Observer-only first-signature ledger; no emulated storage or bus access.
static unsigned watch_main_seen[1024]={},watch_main_seen_count=0;
static bool watch_result(unsigned address){return (watch_mask&4)&&address>=0x514&&address<=0x517;}
static bool watch_ruler_controller(unsigned address){return (watch_mask&2)&&address>=0x6F0A&&address<=0x6F3A&&((address-0x6F0A)&7)==0;}
static bool watch_human_entry(unsigned pc){switch(pc){
 case 0xCD16:case 0xCD2A:case 0xCD52:case 0xCDF2:case 0xCE56:case 0xCE76:case 0xCE9E:case 0xCF09:
 case 0xD2CD:case 0xD2E1:case 0xD310:case 0xD34B:case 0xD3AF:case 0xD3D7:case 0xD3F7:case 0xD462:return true;default:return false;}}
static bool watch_sparse(unsigned pc){switch(pc){
 case 0xBC49:case 0xBC55:case 0xBC65:case 0xBC68:case 0xBC6C:case 0xBC6D:case 0xBC70:case 0xBC8E:case 0xBC91:case 0xBC95:case 0xBCC9:case 0xBCCC:case 0xBCDF:case 0xBCF6:case 0xBCF9:case 0xBD0D:case 0xBD19:case 0xBD1C:case 0xBD25:case 0xBD28:case 0xBD2B:case 0xBD35:case 0xBD38:case 0xBD41:case 0xBD44:case 0xBD56:case 0xBD5C:case 0xBD5F:case 0xBD64:case 0xBD6A:case 0xBD6D:case 0xBD73:case 0xBD76:case 0xBD83:case 0xBD8E:case 0xBD91:case 0xBD95:case 0xBD99:case 0xBD9C:case 0xBDAA:case 0xBE54:case 0xBE65:case 0xBE89:case 0xBE8F:case 0xBEB0:case 0xBEB3:case 0xBEC7:case 0xBECE:case 0xBED1:case 0xBF07:return true;
 case 0xEAE3:case 0xEAE6:case 0xEAF4:case 0xE066:case 0xCD78:case 0xCD7D:case 0xCD80:case 0xCD84:case 0xCD89:case 0xCEAB:case 0xCF00:case 0xCF02:case 0xCF05:case 0xCF92:case 0xA000:case 0xA028:case 0xDD72:case 0xDD79:case 0xDD7E:case 0xDD95:case 0xDD9A:case 0xDDAB:case 0xCAF8:case 0xC9A6:case 0xC9A9:case 0xA006:case 0xBAB3:case 0xBAC1:case 0xBAEF:case 0xBB0E:case 0xBB1E:case 0xBB36:case 0xBB39:case 0xBB3C:case 0xBB3D:case 0xBB47:case 0xBB64:case 0xBB74:case 0xBB8C:case 0xBB8F:case 0xBB92:case 0xBB93:case 0xBB96:case 0xBB99:case 0xBB9C:case 0xBB9F:case 0xBBA0:case 0xBBA3:case 0xBBB7:case 0xBBB8:case 0xBC00:case 0xBC46:case 0xBC52:case 0xBD59:case 0xBD67:case 0xBD96:case 0xBDB8:case 0xBDC8:case 0xBDCC:case 0xBDCD:case 0xBE55:case 0xBE90:
 case 0xD0E1:case 0xD1F9:case 0xD202:case 0xD205:case 0xD20C:case 0xD20D:case 0xD243:case 0xD255:case 0xD258:case 0xD299:case 0xD2B1:case 0xD2C6:case 0xD2CC:case 0xCF2D:case 0xCF30:case 0xD486:case 0xD489:case 0xD48D:case 0xD498:case 0xD49B:case 0xD4A2:case 0xD4A3:case 0xD4B1:case 0xD4F0:case 0xD4F3:case 0xD4F5:case 0xD4FA:
 case 0xD7B5:case 0xD7BC:case 0xD7C3:case 0xD7D2:case 0xD8E4:case 0xD8F8:case 0xD8FD:case 0xD97A:
 case 0xECEE:case 0xED18:case 0xEC95:case 0xEE07:case 0xEE4A:case 0xEE4D:case 0xEE52:case 0xEADE:case 0xEAFC:case 0xF237:case 0xF25F:case 0xF266:case 0xF2AF:case 0xF2D7:case 0xF368:return true;
 default:return watch_human_entry(pc);}}
static bool watch_target(unsigned pc){return watch_sparse(pc)||(pc>=0xD20D&&pc<=0xD2CC)||(pc>=0xD48D&&pc<0xD4F0)||(pc>=0xBC46&&pc<0xBF0A)||(pc>=0xF237&&pc<=0xF279)||(pc>=0xEE07&&pc<=0xEE52);}
static bool watch_selected(unsigned physical,unsigned pc){
 if(physical==8)return pc==0xA006||pc==0xBAB3||(pc>=0xBAC1&&pc<0xBF0A);
 if(physical==9)return pc==0xCD78||pc==0xCD7D||pc==0xCD80||pc==0xCD84||pc==0xCD89||pc==0xCEAB||pc==0xCF00||pc==0xCF02||pc==0xCF05||pc==0xCF92||pc==0xD7B5||pc==0xD7BC||pc==0xD7C3||pc==0xD7D2||pc==0xD8E4||pc==0xD8F8||pc==0xD8FD||pc==0xD97A;
 if(physical==12)return pc==0xA000||pc==0xA028;
 if(physical==13)return (pc>=0xDD72&&pc<=0xDDAB)||pc==0xCAF8||pc==0xC9A6||pc==0xC9A9||watch_human_entry(pc)||pc==0xD0E1||pc==0xCF2D||pc==0xCF30||(pc>=0xD1F9&&pc<=0xD2CC)||(pc>=0xD486&&pc<=0xD4FA);
 if(physical==31)return pc==0xEAE3||pc==0xEAE6||pc==0xEAF4||pc==0xE066||pc==0xECEE||pc==0xED18||pc==0xEC95||(pc>=0xEE07&&pc<=0xEE52)||(pc>=0xF237&&pc<=0xF279)||pc==0xF2AF||pc==0xF2D7||pc==0xF368||pc==0xEADE||pc==0xEAFC;
 return false;
}
static bool watch_read(unsigned address){return watch_city(address)||((watch_mask&2)&&watch_active&&watch_target(watch_instruction_pc)&&!(watch_instruction_pc>=0xF237&&watch_instruction_pc<=0xF279&&address>=0x8000)&&(address>=0x8000||(address>=0x6000&&address<0x8000)));}
static bool watch_write(unsigned address){unsigned p=address&0x7FF;return watch_city(address)||watch_result(address)||watch_ruler_controller(address)||((watch_mask&4)&&address<0x2000&&(p<=3||p==6||p==7||(p>=0x0A&&p<=0x0C)||(p>=0x1A&&p<=0x1B)||(p>=0x500&&p<=0x50F)||(p>=0x540&&p<=0x547)||(p>=0x580&&p<=0x593)||(p>=0x600&&p<0x678)||(p>=0x42C&&p<0x440)||(p>=0x87&&p<=0x8A)||(p>=0xDE&&p<=0xE5)))||((watch_mask&2)&&address>=0x6000&&address<0x8000)||((watch_mask&2)&&(address==0xE000||address==0xE800||address==0xF000));}
static bool watch_stack_push(){return (watch_mask&2)&&watch_active&&(watch_instruction_pc==0xBB36||watch_instruction_pc==0xBB8C||(watch_instruction_pc>=0xBC46&&watch_instruction_pc<0xBF0A));}
static unsigned watch_stack_word(const unsigned char* memory,unsigned sp,unsigned offset){return memory[0x100+((sp+offset)&255)]|(unsigned(memory[0x100+((sp+offset+1)&255)])<<8);}
static bool watch_snapshot_entry(unsigned physical,unsigned pc,const unsigned char* memory,unsigned sp){
 const unsigned state=memory[0x500],phase=memory[0x501];
 if(physical==31&&pc==0xE066)return true;
 if(physical==12&&(pc==0xA000||pc==0xA028)&&state>=13&&state<=15&&phase<8){
  unsigned bit=pc==0xA000?1:2;
  if(!(watch_root_seen[state-13][phase]&bit)){watch_root_seen[state-13][phase]|=bit;return true;}return false;
 }
 if(physical==9)return pc==0xCD78||pc==0xCEAB||pc==0xCF02||pc==0xD7C3||pc==0xD7D2||pc==0xD8E4||pc==0xD8FD;
 if(physical==13){
  if(pc==0xDD72||pc==0xCAF8)return true;
  if((state==13||state==14)&&phase<7&&watch_human_entry(pc)){
   unsigned bit=pc==0xCD16||pc==0xD2CD?1:2;
   if(!(watch_human_seen[state-13][phase]&bit)){watch_human_seen[state-13][phase]|=bit;return true;}
  }
  return pc==0xD1F9||pc==0xD20D||pc==0xD299||pc==0xD2B1||pc==0xD2C6||pc==0xD2CC||pc==0xD48D||pc==0xD4A3||pc==0xD4A2||pc==0xD4F0||pc==0xD4F5;
 }
 if(physical!=8||state!=15||phase>3)return false;
 switch(pc){case 0xBB36:case 0xBB39:case 0xBC49:case 0xBD6A:case 0xBD6D:case 0xBD73:case 0xBD76:case 0xBD8E:case 0xBD91:case 0xBD95:case 0xBD99:case 0xBD9C:case 0xBDAA:case 0xBE54:case 0xBE65:case 0xBE89:case 0xBE8F:return true;default:break;}
 if(pc==0xA006||pc==0xBAB3||pc==0xBBA0){
  if(phase<3||(memory[0x87]&128))return true;
  unsigned bit=pc==0xA006?1:pc==0xBAB3?2:4;
  if(!(watch_seen_hold&bit)){watch_seen_hold|=bit;return true;}return false;
 }
 return pc==0xBAC1||pc==0xBB3D||pc==0xBC46||pc==0xBC52||pc==0xBD59||pc==0xBD67||pc==0xBD96||pc==0xBDB8||pc==0xBDCD||pc==0xBE55||pc==0xBE90||pc==0xBB93||pc==0xBBB8||pc==0xBC00;
}
static void watch_before_store(unsigned address,const unsigned char* memory){
 watch_write_before=0xFFFFFFFF;
 if(address<0x2000)watch_write_before=memory[address&0x7FF];
 else if(watch_provider){unsigned source[10]={0};watch_provider(watch_board,address,source);watch_write_before=source[5];}
}
static void watch_emit(unsigned kind,unsigned pc,unsigned address,unsigned value,unsigned a,unsigned x,unsigned y,unsigned p,unsigned sp,const unsigned char* memory,unsigned cycle,unsigned last_opcode,unsigned bus_internal,unsigned bus_external){
 unsigned source[10]={0xFF,0xFF,0xFF,0xFF,0,0xFFFFFFFF,0,0,0,0};
 if(watch_provider)watch_provider(watch_board,address,source);
 unsigned physical=(watch_instruction_pc>=0x8000&&watch_instruction_pc<0x10000)?source[(watch_instruction_pc-0x8000)/8192]:0xFF;
 if(kind!=2&&physical==31&&watch_instruction_pc==0xE066)return; // only first-signature opcode/software snapshots, never hot-loop bus noise
 if(kind==2&&(!watch_selected(physical,watch_instruction_pc)||!watch_sparse(watch_instruction_pc)))return;
 if(kind==2&&physical==31&&watch_instruction_pc==0xE066){
  const unsigned signature=unsigned(memory[0x7A])|(unsigned(memory[0x78])<<8)|(unsigned(memory[0x500])<<16)|(unsigned(memory[0x501])<<24);
  for(unsigned i=0;i<watch_main_seen_count;++i)if(watch_main_seen[i]==signature)return;
  if(watch_main_seen_count>=1024){++watch_overflow;return;}
  watch_main_seen[watch_main_seen_count++]=signature;
 }

 if(kind!=2&&!watch_city(address)&&!watch_result(address)&&!watch_ruler_controller(address)&&!watch_selected(physical,watch_instruction_pc))return;
 if((kind==0||kind==3||kind==4)&&address>=0x8000&&!watch_selected(physical,watch_instruction_pc))return;
 if(watch_count>=65536){++watch_overflow;return;}
 unsigned* e=watch_events[watch_count++];e[0]=++watch_sequence;e[1]=watch_frame;e[2]=cycle;e[3]=kind;
 e[4]=watch_active?watch_instruction_pc:0xFFFF;e[5]=pc;e[6]=address;e[7]=value&255;e[8]=a;e[9]=x;e[10]=y;e[11]=p;e[12]=sp;
 e[13]=source[0]|(source[1]<<8)|(source[2]<<16)|(source[3]<<24);
 e[14]=unsigned(memory[0x53])|(unsigned(memory[0x54])<<8)|(unsigned(memory[0x22])<<16)|(unsigned(memory[0x23])<<24);
 e[15]=unsigned(memory[0x36])|(unsigned(memory[0x37])<<8)|(unsigned(memory[0x38])<<16)|(unsigned(memory[0x39])<<24);e[16]=source[4];e[17]=source[5];
 for(unsigned i=0;i<9;++i)e[18+i]=unsigned(memory[4*i])|(unsigned(memory[4*i+1])<<8)|(unsigned(memory[4*i+2])<<16)|(unsigned(memory[4*i+3])<<24);
 e[27]=unsigned(memory[0x400])|(unsigned(memory[0x401])<<8)|(unsigned(memory[0x402])<<16)|(unsigned(memory[0x403])<<24);
 e[28]=unsigned(memory[0x12])|(unsigned(memory[0x47A])<<8)|(unsigned(memory[0x47B])<<16)|(unsigned(memory[0x47C])<<24);
 e[29]=unsigned(memory[0x42C])|(unsigned(memory[0x42D])<<8)|(unsigned(memory[0x42E])<<16)|(unsigned(memory[0x42F])<<24);
 e[30]=unsigned(memory[0x100+((sp+1)&255)])|(unsigned(memory[0x100+((sp+2)&255)])<<8)|(unsigned(memory[0x100+((sp+3)&255)])<<16)|(unsigned(memory[0x100+((sp+4)&255)])<<24);
 e[31]=0;
 if(kind==2&&watch_snapshot_entry(physical,watch_instruction_pc,memory,sp)){
  if(watch_snapshot_count>=64){++watch_snapshot_overflow;}else{
   unsigned char* s=watch_snapshots[watch_snapshot_count++];for(unsigned i=0;i<2048;++i)s[i]=memory[i];
   if(watch_snapshot_provider){watch_snapshot_provider(watch_board,s+2048);e[31]=++watch_snapshot_sequence;}else{++watch_snapshot_overflow;}
  }
 }
 e[32]=last_opcode;e[33]=(bus_internal&255)|((bus_external&255)<<8);
 e[34]=memory[0x12]<10?memory[0x151+memory[0x12]]:0xFFFFFFFF;
 e[35]=unsigned(memory[0x78])|(unsigned(memory[0x7A])<<8)|(unsigned(memory[0x81])<<16)|(unsigned(memory[0xC2])<<24);
 for(unsigned i=0;i<3;++i)e[36+i]=unsigned(memory[0x24+4*i])|(unsigned(memory[0x25+4*i])<<8)|(unsigned(memory[0x26+4*i])<<16)|(unsigned(memory[0x27+4*i])<<24);
 e[39]=source[6];
 e[40]=unsigned(memory[0x506])|(unsigned(memory[0x507])<<8)|(unsigned(memory[0x50E])<<16)|(unsigned(memory[0x514])<<24);
 e[41]=source[7]|(unsigned(memory[0xDE])<<16)|(unsigned(memory[0xDF])<<24);e[42]=source[8];e[43]=source[9];
 e[44]=kind==1?watch_write_before:0xFFFFFFFF;
 e[45]=unsigned(memory[0x500])|(unsigned(memory[0x501])<<8)|(unsigned(memory[0x502])<<16)|(unsigned(memory[0x503])<<24);
 e[46]=unsigned(memory[0x514])|(unsigned(memory[0x515])<<8)|(unsigned(memory[0x516])<<16)|(unsigned(memory[0x517])<<24);
 e[47]=unsigned(memory[0x518])|(unsigned(memory[0x519])<<8)|(unsigned(memory[0x51A])<<16)|(unsigned(memory[0x51B])<<24);
 e[48]=unsigned(memory[0x87])|(unsigned(memory[0x88])<<8)|(unsigned(memory[0x89])<<16)|(unsigned(memory[0x8A])<<24);
 e[49]=unsigned(memory[0x7D])|(unsigned(memory[0x7E])<<8)|(unsigned(memory[0x7F])<<16)|(unsigned(memory[0x80])<<24);
 for(unsigned i=0;i<16;++i)e[50+i]=unsigned(memory[0x100+4*i])|(unsigned(memory[0x101+4*i])<<8)|(unsigned(memory[0x102+4*i])<<16)|(unsigned(memory[0x103+4*i])<<24);
 e[66]=unsigned(memory[0xDE])|(unsigned(memory[0xDF])<<8)|(unsigned(memory[0xE0])<<16)|(unsigned(memory[0xE1])<<24);
 e[67]=unsigned(memory[0xE2])|(unsigned(memory[0xE3])<<8)|(unsigned(memory[0xE4])<<16)|(unsigned(memory[0xE5])<<24);
 e[68]=unsigned(memory[0x81])|(unsigned(memory[0x82])<<8)|(unsigned(memory[0x83])<<16)|(unsigned(memory[0x84])<<24);
 e[69]=unsigned(memory[0x85])|(unsigned(memory[0x86])<<8)|(unsigned(memory[0x504])<<16)|(unsigned(memory[0x50B])<<24);
 e[70]=unsigned(memory[0x540])|(unsigned(memory[0x541])<<8)|(unsigned(memory[0x542])<<16)|(unsigned(memory[0x543])<<24);
 e[71]=unsigned(memory[0x544])|(unsigned(memory[0x545])<<8)|(unsigned(memory[0x546])<<16)|(unsigned(memory[0x547])<<24);
}
#define NST_PASSIVE_WATCH(kind_,address_,value_) watch_emit(kind_,pc,address_,value_,a,x,y,flags.Pack(),sp,ram.mem,cycles.count,opcode,busDataInternal,busData)
