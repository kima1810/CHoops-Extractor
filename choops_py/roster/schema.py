"""Confirmed PS3 ROST tables and writable fields; no generic byte editor."""
TABLES={'players':(0x0271AC,5685,308),'arenas':(0x1D5C84,379,28),'teams':(0x1D85E0,443,704),'coaches':(0x23F7B8,1373,44),'conferences':(0x345978,39,0xb94)}
STRING_FIELDS={'players':{'last_name':0x10,'first_name':0x14},'teams':{'short_name':0x30,'abbreviation':0x34,'school_name':0x38,'mascot_plural':0x3c,'mascot_name':0x40},'arenas':{'arena_code':0x20,'arena_name':0x18,'arena_city':0x1c},'coaches':{'coach_name':0x14,'abbreviation':0x18}}
# ROST reference targets point inside a row, not to the row's start.
# Canonical biases are corroborated across the vanilla table and old schema.
REFERENCES={'arena_index':(0x44,'arenas',0x19),'rival1_index':(0x4c,'teams',0x31),'rival2_index':(0x50,'teams',0x31),'rival3_index':(0x54,'teams',0x31),'coach_index':(0x60,'coaches',0x15),'assistant1_index':(0x64,'coaches',0x15),'assistant2_index':(0x68,'coaches',0x15)}
EDITABLE={'players':('first_name','last_name','jersey_number','height_inches','position_code'),'teams':('asset_id',*REFERENCES,'roster_slots'),'arenas':(),'coaches':()}
POSITIONS={0:'PG',1:'SG',2:'SF',3:'PF',4:'C'}

PALETTE_OFFSET = 0x1a0
PALETTE_COUNT = 31
# Roles are contextual candidates; slot identity and RGBA storage are structural.
PALETTE_HINTS = {0:'Uniform home/light candidate',1:'Uniform away/dark candidate',
    2:'Arena/school tint candidate',3:'Arena/school tint candidate',4:'Arena/school tint candidate',
    14:'School primary candidate',15:'School secondary candidate',
    16:'School primary repeat candidate',17:'School secondary repeat candidate',
    21:'Arena/court accent candidate',22:'Arena/court accent candidate',
    24:'School primary repeat candidate',25:'School secondary repeat candidate'}
STRING_FIELDS['teams'].update(student_section=0x198, event_name=0x19c)
EDITABLE = {**EDITABLE,
    'teams': (*EDITABLE['teams'], *STRING_FIELDS['teams'], 'palette_colors'),
    'arenas': tuple(STRING_FIELDS['arenas']),
    'coaches': tuple(STRING_FIELDS['coaches'])}

STRING_FIELDS['conferences'] = {'conference_name':0, 'abbreviation':4}
REFERENCES['conference_index'] = (0x48,'conferences',1)
EDITABLE['conferences'] = tuple(STRING_FIELDS['conferences'])
# Assignment requires reciprocal member-list updates; expose the link read-only.
HEADER_TABLES = {'players':(8,17,308,65535),'arenas':(0x20,25,28,8192),
                 'teams':(0x28,49,704,8192),'coaches':(0x38,21,44,65535),
                 'conferences':(0xa8,1,0xb94,1024)}


def detect_tables(payload):
    import struct
    from ..formats.binary import Binary
    binary = Binary(payload)
    result = {}
    for name,(field,bias,stride,limit) in HEADER_TABLES.items():
        count = binary.u32(field)
        if name == 'uniforms' and count == 0:
            continue
        delta = struct.unpack('>i',binary.slice(field+4,4))[0]
        start = field+4+delta-bias
        if not 0 < count <= limit:
            raise ValueError(f'Invalid {name} table count')
        binary.slice(start,count*stride)
        result[name] = (start,count,stride)
    return result

RATING_OFFSET = 0x3c
RATING_COUNT = 30
# Names corroborated by localized UI metadata bound to executable getters.
RATING_NAMES = ('Shooting (Close)', 'Shooting (Med.)', 'Shooting (3 Pt.)', 'Free Throws', 'Layups', 'Dunking', 'Shoot Off Dribble', 'Shoot In Traffic', 'Standing Dunk', 'Ballhandling', 'Passing', 'Stamina', 'Low Post Off.', 'Low Post Def.', 'Off. Rebounding', 'Def. Rebounding', 'On Ball Def.', 'Blocking', 'Stealing', 'Speed', 'Def. Awareness', 'Off. Awareness', 'Clutch', 'Commits Fouls', 'Quickness', 'Vertical', 'Strength', 'Hustle', 'Durability', 'Consistency')
RATING_HINTS = dict(enumerate(RATING_NAMES))
RATING_EVIDENCE = ({'offset': 60, 'getter': '0x69dad0', 'text_id': '0xb2753bf5'}, {'offset': 62, 'getter': '0x249600', 'text_id': '0x694b364b'}, {'offset': 64, 'getter': '0x24963c', 'text_id': '0x68a941d9'}, {'offset': 66, 'getter': '0x69dbd8', 'text_id': '0xf7228dd3'}, {'offset': 68, 'getter': '0x69dc58', 'text_id': '0x328e19a5'}, {'offset': 70, 'getter': '0x69dcd8', 'text_id': '0x6e258fd1'}, {'offset': 72, 'getter': '0x69dd40', 'text_id': '0x2d5dc47b'}, {'offset': 74, 'getter': '0x69ddc0', 'text_id': '0x4096a887'}, {'offset': 76, 'getter': '0x69de40', 'text_id': '0x9ab1b5c5'}, {'offset': 78, 'getter': '0x249678', 'text_id': '0xe7396a89'}, {'offset': 80, 'getter': '0x2496b4', 'text_id': '0x13812ee7'}, {'offset': 82, 'getter': '0x69df30', 'text_id': '0x5f5863e5'}, {'offset': 84, 'getter': '0x2496f0', 'text_id': '0x645a1521'}, {'offset': 86, 'getter': '0x69dff4', 'text_id': '0x98f7bfcb'}, {'offset': 88, 'getter': '0x69e074', 'text_id': '0xc8153bdd'}, {'offset': 90, 'getter': '0x69e0f4', 'text_id': '0xeda3e59'}, {'offset': 92, 'getter': '0x69e174', 'text_id': '0xf464f295'}, {'offset': 94, 'getter': '0x69e1f4', 'text_id': '0x59b7b947'}, {'offset': 96, 'getter': '0x69e274', 'text_id': '0xed904fd3'}, {'offset': 98, 'getter': '0x69e2f4', 'text_id': '0x5fa120ad'}, {'offset': 100, 'getter': '0x69e374', 'text_id': '0x7da40367'}, {'offset': 102, 'getter': '0x69e3f4', 'text_id': '0xbe78345d'}, {'offset': 104, 'getter': '0x69e474', 'text_id': '0x7b33e2f5'}, {'offset': 106, 'getter': '0x69e4f4', 'text_id': '0xaf15c913'}, {'offset': 108, 'getter': '0x69e55c', 'text_id': '0x5ae78561'}, {'offset': 110, 'getter': '0x69e5dc', 'text_id': '0xc904ee3'}, {'offset': 112, 'getter': '0x69e65c', 'text_id': '0x39b1db37'}, {'offset': 114, 'getter': '0x69e6dc', 'text_id': '0xaa7b27f3'}, {'offset': 116, 'getter': '0x69e75c', 'text_id': '0x41063623'}, {'offset': 118, 'getter': '0x69e7dc', 'text_id': '0xca248c09'})
EDITABLE['players'] = (*EDITABLE['players'], 'attribute_ratings')

# Localized UI property bindings and executable bit-extraction getters.
PLAYER_PROPERTIES = ({'name': 'Hand', 'offset': 148, 'size': 4, 'shift': 25, 'bits': 1, 'getter': '0x69f0cc', 'text_id': '0xb3aac31'}, {'name': 'Weight', 'offset': 156, 'size': 4, 'shift': 11, 'bits': 9, 'getter': '0x69f10c', 'text_id': '0xf3173fa5'}, {'name': 'Build', 'offset': 140, 'size': 4, 'shift': 3, 'bits': 3, 'getter': '0x69ee14', 'text_id': '0x732ca9ed'}, {'name': 'Muscle Tone', 'offset': 140, 'size': 4, 'shift': 6, 'bits': 1, 'getter': '0x69edd4', 'text_id': '0x1f37513'}, {'name': 'Appearance Color', 'offset': 140, 'size': 4, 'shift': 13, 'bits': 3, 'getter': '0x69ed54', 'text_id': '0x298c9b35'}, {'name': 'Eye Color', 'offset': 144, 'size': 1, 'shift': 0, 'bits': 2, 'getter': '0x69ee54', 'text_id': '0x55e441ff'}, {'name': 'Headband', 'offset': 144, 'size': 4, 'shift': 4, 'bits': 3, 'getter': '0x69efd4', 'text_id': '0x7d5650f'}, {'name': 'Left Arm Band', 'offset': 136, 'size': 2, 'shift': 0, 'bits': 4, 'getter': '0x69ebd8', 'text_id': '0x2605a2a3'}, {'name': 'Right Arm Band', 'offset': 136, 'size': 4, 'shift': 12, 'bits': 4, 'getter': '0x69ec18', 'text_id': '0xdaed7763'}, {'name': 'Left Elbow Pad', 'offset': 136, 'size': 1, 'shift': 0, 'bits': 4, 'getter': '0x69eb58', 'text_id': '0xf58a7115'}, {'name': 'Right Elbow Pad', 'offset': 136, 'size': 4, 'shift': 20, 'bits': 4, 'getter': '0x69eb98', 'text_id': '0x6e125b71'}, {'name': 'Left Wrist Band', 'offset': 136, 'size': 4, 'shift': 7, 'bits': 5, 'getter': '0x69ec58', 'text_id': '0x4f7ab89b'}, {'name': 'Right Wrist Band', 'offset': 136, 'size': 4, 'shift': 2, 'bits': 5, 'getter': '0x69ec98', 'text_id': '0x7239b567'}, {'name': 'Left Knee Pad', 'offset': 140, 'size': 4, 'shift': 27, 'bits': 5, 'getter': '0x69ecd8', 'text_id': '0x2dab5cdf'}, {'name': 'Right Knee Pad', 'offset': 140, 'size': 4, 'shift': 22, 'bits': 5, 'getter': '0x69ed14', 'text_id': '0xd143891f'}, {'name': 'Sock Length', 'offset': 144, 'size': 4, 'shift': 2, 'bits': 2, 'getter': '0x69f014', 'text_id': '0x40296347'}, {'name': 'Home Sock Color', 'offset': 144, 'size': 4, 'shift': 1, 'bits': 1, 'getter': '0x69f054', 'text_id': '0xeff79ff7'}, {'name': 'Away Sock Color', 'offset': 144, 'size': 4, 'shift': 0, 'bits': 1, 'getter': '0x69f094', 'text_id': '0x28c908cb'}, {'name': 'T-Shirt', 'offset': 144, 'size': 4, 'shift': 11, 'bits': 2, 'getter': '0x69ef94', 'text_id': '0x2958fbc3'}, {'name': 'Confidence', 'offset': 128, 'size': 1, 'shift': 0, 'bits': 8, 'getter': '0x69e910', 'text_id': '0x1becae25'}, {'name': 'Potential', 'offset': 127, 'size': 1, 'shift': 0, 'bits': 8, 'getter': '0x69e8e8', 'text_id': '0x8040a689'})
PLAYER_SCALARS = {'potential':(0x7f,1,0,8,0,99), 'weight_lbs':(0x9c,4,11,9,70,400), 'hand_code':(0x94,4,25,1,0,1)}
EDITABLE['players'] = (*EDITABLE['players'], *PLAYER_SCALARS)
TENDENCY_OFFSET = 0x78
TENDENCY_NAMES = ('Close Shots','Mid-Range Shots','3PT Shots','Drive The Lane')
EDITABLE['players'] = (*EDITABLE['players'], 'shot_tendencies')

# Edit Schools' read/write callback arrays select this subset of the palette.
# UI caption/group names are not inferred from callback order.
SCHOOL_COLOR_CONTROL_SLOTS = (2,3,4,5,6,7,8,9,10,12,13,14,15,18,19,20,21,22,23,24,25,26)

# Exact English captions recovered from Edit Schools menu selection callbacks.
# Repeated captions remain literal; the control and slot identify each field.
SCHOOL_COLOR_CAPTIONS = ('Key Circle Outer', 'Center Line', 'Outer Line',
    'Skirt Inner', 'Skirt Outer', 'Lane Right', 'Lane Left', 'Key Hash',
    'Center Circle', 'Top Key Right', 'Top Key Left', 'Primary', 'Secondary',
    '3Pt Line', 'Key', 'Key Line', 'Basket Front', 'Basket Rear', 'Basket Metal',
    'Primary', 'Secondary', 'Tertiary')
CONFIRMED_PALETTE_CAPTIONS = dict(zip(SCHOOL_COLOR_CONTROL_SLOTS, SCHOOL_COLOR_CAPTIONS))
PALETTE_HINTS.update(CONFIRMED_PALETTE_CAPTIONS)

# Localized player option arrays, linked to the corresponding packed getters.
ENUM_CHOICES = {'hand_code': {0:'L',1:'R'}, 'headband_code':{0:'No',1:'Yes'},
                'home_sock_color_code':{0:'Black',1:'White'}}
PROPERTY_CHOICES = {'Hand':{0:'L',1:'R'}, 'Build':dict(enumerate(('Skinny','Thin','Normal','Muscles','Thick'))),
    'Muscle Tone':{0:'Buff',1:'Ripped'}, 'Appearance Color':dict(enumerate(('Darkest','Darker','Dark','Light','Lighter','Lightest'))),
    'Eye Color':dict(enumerate(('Blue','Brown','Green','Hazel'))), 'Headband':{0:'No',1:'Yes'},
    'Sock Length':dict(enumerate(('Ankle Socks','Short','Medium','Long'))), 'Home Sock Color':{0:'Black',1:'White'},
    'T-Shirt':{0:'None',1:'Short Sleeve',2:'Long Sleeve'}}
PLAYER_SCALARS.update(headband_code=(0x90,4,4,3,0,1), home_sock_color_code=(0x90,4,1,1,0,1))
EDITABLE['players'] = (*EDITABLE['players'], 'headband_code','home_sock_color_code')

HEADER_TABLES['uniforms'] = (0x70,1,8,8192)
EDITABLE['uniforms'] = ('uniform_asset_id','jersey_shape_code')
JERSEY_SHAPES = {0:'U',1:'V',2:'V triangle',3:'Triangle',4:'Wishbone'}
ENUM_CHOICES['jersey_shape_code'] = JERSEY_SHAPES

ENUM_CHOICES['variant_code'] = {0:'Home (h)',1:'Away (a)',2:'Alternate 1 (x)',3:'Alternate 2 (y)',4:'Alternate 3 (z)'}

# These are verified runtime/material roles, not extra Edit Schools captions.
CONFIRMED_PALETTE_ROLES = {0:'Home team equipment color',1:'Non-home team equipment color',11:'Key Circle Inner'}
PALETTE_HINTS.update(CONFIRMED_PALETTE_ROLES)

TEAM_TYPE_OFFSET=0x2ec  # Name-anchor +0x2BC, the final word of the physical row.
TEAM_TYPES={0:'Current D1',1:'Classic / All-Time',2:'Created',4:'Special'}
ENUM_CHOICES['team_type_code']=TEAM_TYPES
EDITABLE['teams']=(*EDITABLE['teams'],'team_type_code')
CONFERENCE_MEMBERS=0x6e0
CONFERENCE_MEMBER_COUNT=0x870
CONFERENCE_MEMBER_CAPACITY=100

from .shoes import BRANDS,COLORS,FIELDS as SHOE_FIELDS
ENUM_CHOICES['shoe_brand_code']=BRANDS
ENUM_CHOICES['home_shoe_color_code']=COLORS
ENUM_CHOICES['away_shoe_color_code']=COLORS
ENUM_CHOICES['shoe_style_code']={i:f'Style {i}' for i in range(4)}
for table,fields in SHOE_FIELDS.items():EDITABLE[table]=(*EDITABLE[table],*fields)
