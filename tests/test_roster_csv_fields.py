import csv
import io
import json
import shutil
import uuid

import pytest
from choops_py.archive.manifests import OUTPUT, safe_output
from choops_py.roster import bulk
from choops_py.roster.workflow import export_model
from support import roster_fixture


def test_csv_exports_exclude_ui_and_research_fields_but_keep_import_safety():
    model=roster_fixture()
    model.rows['players'][0].update(references='UI asset references',preview_source='Selected overrides',research='Private research')
    text=bulk.export_csv(model)
    assert 'source_sha256' in text.splitlines()[0]
    assert not any(marker in text for marker in ('UI asset references','Selected overrides','Private research'))
    assert bulk.csv_changes(model,text)==[]
    work=OUTPUT/'temp'/('csv_fields_'+uuid.uuid4().hex)
    try:
        export_model(model,work)
        with (work/'players.csv').open(encoding='utf8',newline='') as stream:
            reader=csv.DictReader(stream)
            assert 'first_name' in reader.fieldnames and 'index' in reader.fieldnames
            assert not set(reader.fieldnames)&{'references','preview_source','research','row_offset','display_name','properties','position','home_shoe_texture'}
    finally:
        if work.exists():shutil.rmtree(safe_output(work))


@pytest.mark.parametrize('field',['references','preview_source','research','row_offset','display_name'])
def test_csv_import_rejects_non_game_fields_without_mutation(field):
    model=roster_fixture();before=bytes(model.data)
    row=next(csv.DictReader(io.StringIO(bulk.export_csv(model))))
    row.update(field=field,slot='',original=json.dumps('old'),value=json.dumps('new'))
    stream=io.StringIO();writer=csv.DictWriter(stream,bulk.CSV_COLUMNS);writer.writeheader();writer.writerow(row)
    with pytest.raises(ValueError,match='unsupported field'):
        bulk.csv_changes(model,stream.getvalue())
    assert bytes(model.data)==before
