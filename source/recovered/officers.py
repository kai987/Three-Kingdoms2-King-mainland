"""Readable model reconstructed from this ROM's 12-byte officer records.

NOT original source. Field meaning is supported by displayed ROM glyphs and
the field read/write routines documented in analysis/officer_fields/fields.json.
Keep raw bytes: unvalidated upper bits and unusual values are not discarded.
"""
from dataclasses import dataclass

ROM_SHA256="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82"
TERRAIN_GLYPHS={0:"平",1:"山",2:"水"}
WEAPON_NAMES=("短剣","飛剣","長剣","破斬剣","大剣","青釭の剣","倚天の剣","七星宝剣",
              "薙刀","眉尖刀","三尖刀","鈎鎌刀","偃月刀","鳳嘴刀","龍牙刀","関王刀",
              "矛","双戟","単鈎槍","戦斧","雙鈎槍","方天画戟","狼牙槍","蛇矛")
ARMOR_NAMES=("絹巾","籠手","兜","硬皮","鶴氅","甲冑","聖者の衣","竜鱗の鎧")
STATUS_INTERPRETATION={
    0:"unaffiliated / roaming (strong inference)",
    1:"pending scripted appearance (strong inference)",
    2:"assigned to city roster (confirmed transition)",
    3:"removed / defeated / unavailable; permanent death not implied",
}

@dataclass(frozen=True)
class OfficerRecord:
    raw: bytes

    def __post_init__(self):
        if len(self.raw)!=12:raise ValueError("Officer records contain exactly 12 bytes")
        object.__setattr__(self,"raw",bytes(self.raw))

    @property
    def health(self):return self.raw[0]  # UI 体
    @property
    def martial_strength(self):return self.raw[1]  # UI 武
    @property
    def intellect(self):return self.raw[2]  # UI 知
    @property
    def loyalty(self):return self.raw[3]  # UI 忠; 100 displayed as --
    @property
    def virtue(self):return self.raw[4]  # UI 徳; not renamed to 魅力
    @property
    def roaming_city_id(self):return self.raw[5]  # Strong inference; meaningful with status0
    @property
    def experience_raw(self):return self.raw[6] | (self.raw[7]<<8)
    @property
    def experience_display(self):return (self.experience_raw//50)%1000  # Three display digits; normal raw cap49999
    @property
    def troops_raw(self):return self.raw[8] | (self.raw[9]<<8)
    @property
    def troops_display(self):return self.troops_raw & 0x3FF
    @property
    def troops_upper_raw_bits(self):
        # Numeric overflow can generate bit10 in the real allocation controller;
        # this is not evidence for a separate training/status field.
        return self.raw[9]>>2
    @property
    def troops_upper_unresolved_bits(self):return self.troops_upper_raw_bits
    @property
    def weapon_id(self):return self.raw[10]&31
    @property
    def armor_id(self):return self.raw[10]>>5
    @property
    def weapon_name(self):return WEAPON_NAMES[self.weapon_id] if self.weapon_id<24 else None
    @property
    def armor_name(self):return ARMOR_NAMES[self.armor_id]
    @property
    def status_code(self):return self.raw[11]&3
    @property
    def terrain_affinity_code(self):return (self.raw[11]>>2)&3
    @property
    def terrain_glyph(self):return TERRAIN_GLYPHS.get(self.terrain_affinity_code)
    @property
    def experience_tier(self):return self.raw[11]>>4
    @property
    def level_display(self):return self.experience_tier+1

    def with_raw_byte(self,offset,value):
        if not 0<=offset<12 or not 0<=value<=255:raise ValueError("Invalid byte update")
        data=bytearray(self.raw);data[offset]=value;return OfficerRecord(data)

    def with_status(self,status):
        if not 0<=status<=3:raise ValueError("Invalid 2-bit status")
        return self.with_raw_byte(11,(self.raw[11]&0xFC)|status)

    def with_weapon(self,weapon_id):
        if not 0<=weapon_id<=23:raise ValueError("Confirmed weapon IDs are 0..23")
        return self.with_raw_byte(10,(self.raw[10]&0xE0)|weapon_id)

    def with_armor(self,armor_id):
        if not 0<=armor_id<=7:raise ValueError("Confirmed armor IDs are 0..7")
        return self.with_raw_byte(10,(self.raw[10]&31)|(armor_id<<5))

    def loyalty_text(self):
        return "--" if self.loyalty==100 else f"{self.loyalty%100:2d}"

def initial_officers(rom: bytes):
    """Extract 237 initial records; caller must supply the analyzed ROM."""
    import hashlib
    if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError("Different ROM")
    return [OfficerRecord(rom[0x22010+i*12:0x22010+(i+1)*12]) for i in range(237)]
