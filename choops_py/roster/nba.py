"""Evidence-bounded NBA PS3 roster schemas; never reuse College Hoops offsets."""
import math
import struct
from collections import Counter

from ..core.errors import ToolError
from .adapters import load

PROFILES = {
    'nba2k9': dict(title='NBA 2K9', marker=0xd1, player_header=0x10,
                   template_header=0x18, player_stride=452, team_header=0x30,
                   team_stride=572, arena_header=0x28, arena_stride=60,
                   height=0x34, weight=0x30, number=(0x38,16), face=(0x38,0),
                   team_strings={'team_name':0xc0,'abbreviation':0xc4,'city':0x100,
                                 'city_abbreviation':0x104,'display_city':0x108},
                   arena_strings={'arena_name':0,'display_name':4,'stadium_asset':8,
                                  'city':12,'abbreviation':16,'state':24}),
    'nba2k14': dict(title='NBA 2K14', marker=0x235, player_header=0x18,
                    template_header=0x24, player_stride=460, team_header=0x6c,
                    team_stride=760, arena_header=0x60, arena_stride=56,
                    height=0x1c, weight=0x20, number=(0x30,12), face=(0x2c,16),
                    team_strings={'team_name':0x80,'abbreviation':0x84,'city':0x88,
                                  'display_city':0x8c,'menu_logo':0x1b0,'audio_name':0x1b8},
                    arena_strings={'arena_name':8,'display_name':12,'stadium_asset':16,
                                   'led_asset':20,'dorna_asset':24,'floor_asset':28,
                                   'city':32,'abbreviation':36,'state':44}),
}


def family(payload):
    if len(payload) < 0x240 or struct.unpack_from('>I',payload)[0] != 1:
        return None
    marker = struct.unpack_from('>I',payload,4)[0]
    for name, profile in PROFILES.items():
        if marker == profile['marker']:
            if name == 'nba2k14' and struct.unpack_from('>I',payload,0x14)[0] != 0xf34551e7:
                return None
            return name
    return None


class NBARosterModel:
    def __init__(self, source):
        self.source = source
        self.game = family(source.payload)
        if self.game is None:
            raise ToolError('unsupported_nba_roster','NBA roster schema is unrecognized')
        self.profile = PROFILES[self.game]
        self.original = source.payload
        self.data = bytearray(self.original)
        self.edits = []
        self.history = []
        self.redo_history = []
        self.tables = {}
        for table, header_key, bias in (('players','player_header',17),('teams','team_header',49),('arenas','arena_header',1)):
            field = self.profile[header_key]
            count, delta = struct.unpack_from('>Ii',self.data,field)
            start = field+4+delta-bias
            stride = self.profile[table[:-1]+'_stride']
            if not 0 < count <= (20000 if table == 'players' else 2048) or start < 0 or start+count*stride > len(self.data):
                raise ToolError('invalid_nba_table',table)
            self.tables[table] = (start,count,stride)
        field = self.profile['template_header']+4
        next_anchor = field+struct.unpack_from('>i',self.data,field)[0]-1
        start,count,stride = self.tables['players']
        if next_anchor != start+16+count*stride:
            raise ToolError('unsupported_nba_roster','Player table stride does not match the researched schema')
        self.reload()
        self.initial_issues = list(self.issues)

    @classmethod
    def open(cls,path):
        return cls(load(path))

    def row_offset(self,table,index):
        start,count,stride = self.tables[table]
        if not isinstance(index,int) or not 0 <= index < count:
            raise ToolError('roster_index_out_of_range',str(index))
        return start+index*stride

    def strings(self,table):
        return {'first_name':20,'last_name':16} if table == 'players' else self.profile[table[:-1]+'_strings']

    def string_span(self,field):
        delta = struct.unpack_from('>i',self.data,field)[0]
        if delta in (0,-1):return None
        start = field+delta-1
        if start < 0 or start+2 > len(self.data):raise ValueError('String pointer outside roster')
        end = start
        while end+2 <= len(self.data) and end-start <= 4096:
            if self.data[end:end+2] == bytes(2):
                text = bytes(self.data[start:end]).decode('utf-16-be')
                if any(not c.isprintable() for c in text):raise ValueError('Nonprinting roster text')
                return start,end,text
            end += 2
        raise ValueError('Unterminated roster text')

    def reload(self):
        self.rows = {};self.issues = [];self.string_users = Counter()
        for table,(start,count,stride) in self.tables.items():
            rows = []
            for index in range(count):
                off = start+index*stride;row = {'index':index,'row_offset':off}
                for name,rel in self.strings(table).items():
                    try:
                        span = self.string_span(off+rel)
                        row[name] = span[2] if span else ''
                        if span:self.string_users[span[0]] += 1
                    except (ValueError,UnicodeError) as error:
                        self.issues.append((table,index,name,str(error)));row[name] = ''
                if table == 'players':
                    row['display_name'] = (row['first_name']+' '+row['last_name']).strip()
                    for name in ('height','weight'):
                        value = struct.unpack_from('>f',self.data,off+self.profile[name])[0]
                        row['height_inches' if name == 'height' else 'weight_pounds'] = round(value/2.54,2) if name == 'height' else value
                    for name in ('number','face'):
                        rel,shift = self.profile[name]
                        row['jersey_number' if name == 'number' else 'face_id'] = (struct.unpack_from('>I',self.data,off+rel)[0]>>shift)&(127 if name == 'number' else 65535)
                    row['position_code'] = self.data[off+0x71]&7 if self.game == 'nba2k9' else self.data[off+0x45]>>5
                    if self.game == 'nba2k14':row['secondary_position_code'] = (self.data[off+0x45]>>2)&7
                elif table == 'teams':
                    row['roster_slots'] = []
                    ps,pc,pstride = self.tables['players']
                    for slot in range(20):
                        field = off+0x30+slot*4
                        value = struct.unpack_from('>i',self.data,field)[0]
                        target = field+value-1
                        pi,rem = divmod(target-ps-16,pstride)
                        row['roster_slots'].append(pi if value not in (0,-1) and not rem and 0 <= pi < pc else None)
                rows.append(row)
            self.rows[table] = rows

    def editable(self,table):
        # Asset strings and team membership are researched read-only links.
        if table == 'players':return ('first_name','last_name','height_inches','weight_pounds','jersey_number','face_id','position_code')+(('secondary_position_code',) if self.game == 'nba2k14' else ())
        if table == 'teams':return ('team_name','abbreviation','city','display_city')
        return ('arena_name','display_name','city','abbreviation','state')

    def edit(self,table,index,field,value,slot=None):
        if field not in self.editable(table):raise ToolError('roster_field_read_only',field)
        off = self.row_offset(table,index);before = bytes(self.data)
        try:
            if field in self.strings(table):
                at = off+self.strings(table)[field];span = self.string_span(at)
                if not span:raise ToolError('nba_text_storage_unconfirmed','Null text fields cannot be allocated yet')
                start,end,old = span
                if not isinstance(value,str) or any(not c.isprintable() for c in value):raise ValueError('Enter printable text')
                encoded = value.encode('utf-16-be')
                if len(encoded)>end-start:raise ToolError('nba_text_growth_unconfirmed','NBA text heap relocation is not established; available UTF-16 units: '+str((end-start)//2))
                # Count all aligned relative references, including unparsed tables.
                refs = sum(pos+struct.unpack_from('>i',self.data,pos)[0]-1==start for pos in range(0,len(self.data)-3,4))
                if value != old and refs>1:raise ToolError('nba_shared_string','This text is shared by other records; individual copy-on-write allocation is not established')
                self.data[start:end] = encoded+bytes(end-start-len(encoded))
            elif field in ('position_code','secondary_position_code'):
                number=int(value)
                if str(value).strip()!=str(number) or not 0 <= number <= (5 if field == 'secondary_position_code' else 4):raise ValueError('Invalid position code')
                rel,shift = (0x71,0) if self.game == 'nba2k9' else (0x45,5 if field == 'position_code' else 2)
                self.data[off+rel]=(self.data[off+rel]&~(7<<shift))|(number<<shift)
            elif field in ('height_inches','weight_pounds'):
                number = float(value)
                low,high = (36,100) if field == 'height_inches' else (80,450)
                if not math.isfinite(number) or not low <= number <= high:raise ValueError('Value outside editor bounds')
                rel = self.profile['height' if field == 'height_inches' else 'weight']
                struct.pack_into('>f',self.data,off+rel,number*2.54 if field == 'height_inches' else number)
            else:
                number = int(value)
                if str(value).strip() != str(number) or not 0 <= number <= (100 if field == 'jersey_number' else 65535):raise ValueError('Invalid integer')
                rel,shift = self.profile['number' if field == 'jersey_number' else 'face']
                mask = (127 if field == 'jersey_number' else 65535)<<shift
                word = struct.unpack_from('>I',self.data,off+rel)[0]
                struct.pack_into('>I',self.data,off+rel,(word&~mask)|(number<<shift))
            self.reload()
            if self.issues != self.initial_issues:raise ValueError('Edit introduced invalid text')
        except BaseException:
            self.data[:] = before;self.reload();raise
        after = bytes(self.data)
        if after != before:
            self.history.append((before,after,list(self.edits)))
            self.redo_history.clear()
            self.edits.append(dict(table=table,index=index,field=field,value=value))

    def undo(self):
        if not self.history:return
        before,after,edits = self.history.pop()
        self.redo_history.append((before,after,edits,list(self.edits)))
        self.data[:] = before;self.edits = edits;self.reload()

    def redo(self):
        if not self.redo_history:return
        before,after,old,new = self.redo_history.pop()
        self.history.append((before,after,old))
        self.data[:] = after;self.edits = new;self.reload()

    def validate(self):
        self.reload()
        return dict(valid=self.issues == self.initial_issues,issues=[x for x in self.issues if x not in self.initial_issues],
                    game=self.game,source_type=self.source.kind,counts={n:len(r) for n,r in self.rows.items()},
                    unsaved_edits=len(self.edits),read_only_fields=['unconfirmed ratings, tendencies, appearance and membership','unconfirmed NBA text heap growth'])

    def document(self):
        from ..archive.manifests import digest
        return dict(schema=1,game=self.game,source_sha256=digest(self.source.original),tables=self.rows)

    def apply_document(self,document):
        from ..archive.manifests import digest
        if document.get('game') != self.game or document.get('source_sha256') != digest(self.source.original):
            raise ToolError('roster_source_mismatch','Patch game/source does not match')
        before=bytes(self.data);edits=list(self.edits);history=list(self.history);redo=list(self.redo_history)
        try:
            if 'edits' in document:
                for item in document['edits']:self.edit(item['table'],item['index'],item['field'],item['value'])
            elif 'tables' in document:
                if set(document['tables'])!=set(self.rows):raise ToolError('roster_table_shape_changed','Table set differs')
                changes=[]
                for table,rows in document['tables'].items():
                    if len(rows)!=len(self.rows[table]):raise ToolError('roster_table_shape_changed',table)
                    for index,row in enumerate(rows):
                        old=self.rows[table][index]
                        if set(row)!=set(old):raise ToolError('roster_table_shape_changed','Row fields differ')
                        for field,value in row.items():
                            if value!=old[field]:
                                if field not in self.editable(table):raise ToolError('roster_field_read_only',field)
                                changes.append((table,index,field,value))
                for args in changes:self.edit(*args)
            else:raise ToolError('invalid_roster_patch','Expected edits or tables')
        except BaseException:
            self.data[:]=before;self.edits=edits;self.history=history;self.redo_history=redo;self.reload();raise
