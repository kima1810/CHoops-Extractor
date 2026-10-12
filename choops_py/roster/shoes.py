"""Executable-confirmed team defaults and per-player shoe texture routing."""
BASES=(0,100,200,300,500)
BRANDS={0:'Generic',1:'Nike',2:'Reebok',3:'Adidas',4:'Special / Jordan artwork'}
STYLE_COUNTS={0:1,1:3,2:1,3:1,4:4}
COLOR_COUNTS={0:2,1:16,2:16,3:16,4:2}
FIELDS={
    'players':{'shoe_brand_code':(0xa8,29,3),'shoe_style_code':(0xa0,27,5),
               'home_shoe_color_code':(0xa0,22,5),'away_shoe_color_code':(0xa0,17,5)},
    'teams':{'shoe_brand_code':(0x2e8,20,3),'shoe_style_code':(0x2e0,22,5),
             'home_shoe_color_code':(0x2e0,17,5),'away_shoe_color_code':(0x2e0,12,5)}}


def choices(field,brand):
    if field=='shoe_brand_code':return BRANDS
    if brand not in STYLE_COUNTS:return {}
    if field=='shoe_style_code':return {i:f'Style {BASES[brand]+i}' for i in range(STYLE_COUNTS[brand])}
    return {i:COLORS[i] for i in range(COLOR_COUNTS[brand])}


def texture_name(brand,style,color):
    if brand not in STYLE_COUNTS or not 0<=style<STYLE_COUNTS[brand] or not 0<=color<COLOR_COUNTS[brand]:
        return None
    return f'shoe_{color}.iff' if brand==0 else f'shoe_{BASES[brand]+style}_{color:02d}.iff'


def player_fields(binary,offset):
    word=binary.u32(offset+0xa0);brand=binary.u32(offset+0xa8)>>29
    style=word>>27;home=word>>22&31;away=word>>17&31
    return dict(shoe_brand_code=brand,shoe_style_code=style,home_shoe_color_code=home,away_shoe_color_code=away,
                home_shoe_texture=texture_name(brand,style,home),away_shoe_texture=texture_name(brand,style,away))


def team_fields(binary,offset):
    if offset+0x2ec>len(binary.data):return {}
    word=binary.u32(offset+0x2e0);brand=binary.u32(offset+0x2e8)>>20&7
    style=word>>22&31;home=word>>17&31;away=word>>12&31
    return dict(shoe_brand_code=brand,shoe_style_code=style,home_shoe_color_code=home,away_shoe_color_code=away,
                home_shoe_texture=texture_name(brand,style,home),away_shoe_texture=texture_name(brand,style,away))


COLORS=dict(enumerate(('White','Black','Red','Yellow','Blue','Green','Orange','Purple',
                       'Black / White','Black / Black','Black / Red','Black / Yellow',
                       'Black / Blue','Black / Green','Black / Orange','Black / Purple')))
