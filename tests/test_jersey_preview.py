from types import SimpleNamespace
import pytest
from choops_py.studio import services


@pytest.mark.parametrize(
    "parts,roles", [(0, {"jersey", "shorts"}), (1, {"jersey"}), (2, {"shorts"})]
)
def test_combined_uniform_preview_preserves_coordinates_and_texture_roles(
    tmp_path, monkeypatch, parts, roles
):
    archive = SimpleNamespace(
        entries=[
            {"name": n} for n in ("uh000.iff", "cloth_u_reg.iff", "cloth_shorts.iff")
        ]
    )

    def materialize(archive, entry):
        path = tmp_path / entry["name"]
        path.write_bytes(b"synthetic")
        return path

    monkeypatch.setattr(services, "materialize", materialize)
    monkeypatch.setattr(
        services,
        "inspect_uniform_preview",
        lambda *args: {role: ((1, 1), b"\xff" * 4) for role in ("jersey", "shorts")},
    )
    from choops_py.formats import standard_iff

    monkeypatch.setattr(
        standard_iff,
        "StandardIFF",
        lambda raw: SimpleNamespace(
            records=[
                {"type": "SCNE", "name": "jersey_u_reg", "index": 1},
                {"type": "SCNE", "name": "shortsreg", "index": 2},
            ]
        ),
    )

    def scene(path, index, *args):
        return dict(
            meshes=[
                dict(name=path.name, vertices=[(1, 2, 3)], batches=[{"texture": None}])
            ],
            warnings=[],
        )

    monkeypatch.setattr(services, "inspect_scene_preview", scene)
    _, result = services.inspect_jersey_preview(
        archive, {"variant_code": 0, "uniform_asset_id": 0}, 0, "reg", "reg", parts
    )
    assert {m["uniform_surface"] for m in result["meshes"]} == roles
    assert all(m["vertices"] == [(1, 2, 3)] for m in result["meshes"])
    assert all(
        b["texture"] == "__uniform_" + m["uniform_surface"]
        for m in result["meshes"]
        for b in m["batches"]
    )
    assert set(result["images"]) == {"__uniform_" + role for role in roles}
