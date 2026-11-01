from types import SimpleNamespace
from choops_py.studio import services


def test_uniform_preview_chooses_artwork_and_excludes_numbers_and_bump(monkeypatch):
    import choops_py.texture_tools.pipeline as pipeline
    assets=[SimpleNamespace(name=n,texture=True) for n in ('unifbump','unifregion','jersey_numbers','unif','shortbump','short')]
    monkeypatch.setattr(pipeline,'Container',lambda *args:SimpleNamespace(assets=assets))
    monkeypatch.setattr(services,'decode_preview_asset',lambda asset,**kw:((1,1), bytes((len(asset.name),2,3,0))))
    from pathlib import Path
    images=services.inspect_uniform_preview(Path(__file__))
    assert images['jersey']==((1,1),bytes((len('unifregion'),2,3,255)))
    assert images['shorts']==((1,1),bytes((len('short'),2,3,255)))
