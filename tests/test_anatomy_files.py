# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Anatomy read from mesh files: reading, entrance detection, placement, case options.

Only synthetic meshes are used (the spiral duct written to STL/OBJ), never
restricted data.
"""

import numpy as np
import pytest

from auris_sim.anatomy import AnatomyError, build_anatomy
from auris_sim.geometry import (
    SpiralDuct,
    TriangleMesh,
    boundary_loops,
    file_sha256,
    insertion_frame,
    mesh_report,
    place_by_entrance,
    read_mesh,
    spiral_duct,
    write_stl,
)
from auris_sim.geometry.mesh import (
    MeshError,
    close_except,
    find_entrance,
    rotation_about_z,
    signed_volume,
)
from auris_sim.io import Case, CaseError, validate_case

PARAMS = SpiralDuct(n_rings=80, n_sides=12)


def open_duct(params: SpiralDuct = PARAMS) -> TriangleMesh:
    """Spiral duct open at both ends; the apex cut is made non-planar (as a real cut)."""
    mesh = spiral_duct(params)
    k = params.n_sides
    triangles = mesh.triangles[:-k]  # drop the apex fan
    vertices = mesh.vertices[:-1].copy()  # and its centre vertex
    last = (params.n_rings - 1) * k
    vertices[last : last + k, 2] += 0.3e-3 * (-1.0) ** np.arange(k)  # jagged apex cut
    return TriangleMesh(vertices, triangles)


def rigid(angle_deg=37.0, axis=(1.0, 2.0, 0.5), translation=(0.01, -0.02, 0.005)):
    """A 4x4 rigid transform (rotation about ``axis``, then translation)."""
    a = np.asarray(axis, dtype=float)
    a /= np.linalg.norm(a)
    t = np.radians(angle_deg)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    r = np.eye(3) + np.sin(t) * k + (1 - np.cos(t)) * k @ k
    m = np.eye(4)
    m[:3, :3], m[:3, 3] = r, translation
    return m


def files_case(tmp_path, meshes, strategy=None, **source):
    data = {
        "schema_version": "0.1",
        "units": {"length": "m", "mass": "kg", "time": "s", "force": "N", "pressure": "Pa"},
        "anatomy": {"id": "test", "source": {"type": "files", "meshes": meshes, **source}},
        "instrument": {
            "type": "electrode_array", "model": "cosserat", "length": 0.02,
            "radius": 2e-4, "young_modulus": 1e8,
        },
        "strategy": {"insertion_speed": 1e-3, "insertion_depth": 0.01, **(strategy or {})},
        "simulation": {"dt": 0.01, "duration": 1.0},
    }  # fmt: skip
    path = tmp_path / "case.yaml"
    path.write_text("# placeholder: the data is passed directly\n")
    return Case(validate_case(data), path)


# --------------------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------------------
def test_binary_stl_round_trip_welds_vertices(tmp_path):
    mesh = spiral_duct(PARAMS)
    back = read_mesh(write_stl(tmp_path / "duct.stl", mesh.scaled(1e3)), unit="mm")
    assert len(back.vertices) == len(mesh.vertices)
    assert len(back.triangles) == len(mesh.triangles)
    assert np.sort(back.vertices, axis=0) == pytest.approx(np.sort(mesh.vertices, axis=0), abs=1e-9)


def test_ascii_stl_and_obj(tmp_path):
    v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    tris = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [0, 3, 2]])
    lines = ["solid t"]
    for t in tris:
        lines += ["facet normal 0 0 0", "outer loop"]
        lines += [f"vertex {x:.6e} {y:.6e} {z:.6e}" for x, y, z in v[t]]
        lines += ["endloop", "endfacet"]
    (tmp_path / "t.stl").write_text("\n".join(lines + ["endsolid t"]))
    obj = ["v " + " ".join(map(str, p)) for p in v]
    obj += ["f " + " ".join(str(i + 1) for i in t) for t in tris]
    (tmp_path / "t.obj").write_text("\n".join(obj))
    for name in ("t.stl", "t.obj"):
        mesh = read_mesh(tmp_path / name, unit="mm")
        assert mesh.triangles.shape == (4, 3)
        assert mesh.vertices.max() == pytest.approx(1e-3)
        assert boundary_loops(mesh) == []  # closed tetrahedron


def test_unsupported_inputs(tmp_path):
    (tmp_path / "a.ply").write_text("ply")
    with pytest.raises(MeshError, match="unsupported"):
        read_mesh(tmp_path / "a.ply")
    (tmp_path / "b.stl").write_text("not a mesh")
    with pytest.raises(MeshError):
        read_mesh(tmp_path / "b.stl")
    with pytest.raises(MeshError, match="unit"):
        read_mesh(write_stl(tmp_path / "c.stl", spiral_duct(PARAMS)), unit="inch")


# --------------------------------------------------------------------------------------
# Loops, entrance, placement
# --------------------------------------------------------------------------------------
def test_boundary_loops_and_entrance():
    mesh = open_duct()
    loops = boundary_loops(mesh)
    assert sorted(len(lp) for lp in loops) == [PARAMS.n_sides, PARAMS.n_sides]
    entrance = loops[find_entrance(mesh, loops)]
    assert set(entrance.tolist()) == set(range(PARAMS.n_sides))  # the base ring
    report = mesh_report(mesh)
    assert report["boundary_edges"] == 2 * PARAMS.n_sides
    assert report["non_manifold_edges"] == 0


def test_placement_matches_the_synthetic_frame():
    placement = place_by_entrance(open_duct())
    rotation, centre = insertion_frame(PARAMS)
    assert placement.centre == pytest.approx(centre, abs=1e-12)
    assert placement.rotation[0] == pytest.approx(rotation[0], abs=1e-9)  # insertion axis
    cos_z = float(placement.rotation[2] @ rotation[2])
    # spiral axis: principal-axis estimate, about 4 deg off on this 2.5-turn duct
    assert np.degrees(np.arccos(min(cos_z, 1.0))) < 5.0
    assert np.linalg.det(placement.rotation) == pytest.approx(1.0)


def test_placement_is_independent_of_the_file_frame():
    mesh = open_duct()
    m = rigid()
    moved = TriangleMesh(mesh.vertices @ m[:3, :3].T + m[:3, 3], mesh.triangles)
    a = place_by_entrance(mesh).to_insertion(mesh.vertices)
    b = place_by_entrance(moved).to_insertion(moved.vertices)
    assert b == pytest.approx(a, abs=1e-9)


def test_capping_and_orientation():
    mesh = open_duct()
    loops = boundary_loops(mesh)
    closed, n = close_except(mesh, loops, None)
    assert n == 2 and boundary_loops(closed) == []
    # spiral_duct faces the lumen: inward normals give a negative volume
    assert signed_volume(closed) < 0.0
    assert rotation_about_z(90.0) @ [1.0, 0.0, 0.0] == pytest.approx([0.0, 1.0, 0.0])


# --------------------------------------------------------------------------------------
# Case files with a "files" anatomy
# --------------------------------------------------------------------------------------
@pytest.fixture
def duct_files(tmp_path):
    """Open duct written in mm, with its triangles flipped (normals out of the lumen)."""
    mesh = open_duct()
    flipped = TriangleMesh(mesh.vertices * 1e3, mesh.triangles[:, ::-1].copy())
    coarse = write_stl(tmp_path / "coarse.stl", flipped)
    fine = write_stl(tmp_path / "fine.stl", flipped)
    return {"coarse": coarse, "fine": fine, "mesh": mesh}


def max_distance_to(points, cloud):
    """Largest distance from ``points`` to their nearest point of ``cloud``."""
    d = np.linalg.norm(points[:, None, :] - cloud[None, :, :], axis=2)
    return float(d.min(axis=1).max())


def test_build_anatomy_from_files(tmp_path, duct_files):
    meshes = {
        "collision": {
            "file": "coarse.stl", "unit": "mm", "sha256": file_sha256(duct_files["coarse"]),
        },
        "display": {"file": str(duct_files["fine"]), "unit": "mm"},
    }  # fmt: skip
    anatomy = build_anatomy(files_case(tmp_path, meshes))
    # the apex is capped, the entrance stays open, triangles face the lumen
    assert [len(lp) for lp in boundary_loops(anatomy.collision)] == [PARAMS.n_sides]
    closed, _ = close_except(anatomy.collision, boundary_loops(anatomy.collision), None)
    assert signed_volume(closed) < 0.0
    # same placement as the synthetic duct read directly
    expected = place_by_entrance(duct_files["mesh"]).to_insertion(duct_files["mesh"].vertices)
    assert len(anatomy.collision.vertices) == len(expected) + 1  # + the apex cap centre
    assert max_distance_to(expected, anatomy.collision.vertices) < 1e-9
    assert max_distance_to(expected, anatomy.display.vertices) < 1e-9
    assert anatomy.axis_estimated
    assert set(anatomy.inputs) == {"collision", "display"}


def test_transform_and_angle(tmp_path, duct_files):
    m = rigid()
    # write the mesh in another frame and give the transform back to the anatomy frame
    mesh = duct_files["mesh"]
    inv = np.linalg.inv(m)
    other = TriangleMesh((mesh.vertices @ inv[:3, :3].T + inv[:3, 3]) * 1e3, mesh.triangles)
    write_stl(tmp_path / "other.stl", other)
    ref = {"file": "other.stl", "unit": "mm", "transform": m.ravel().tolist()}
    base = build_anatomy(files_case(tmp_path, {"collision": ref}))
    turned = build_anatomy(
        files_case(tmp_path, {"collision": ref}, strategy={"insertion_angle_deg": 10.0})
    )
    assert base.placement.centre == pytest.approx(
        mesh.vertices[: PARAMS.n_sides].mean(axis=0), abs=1e-9
    )
    rz = rotation_about_z(10.0)
    assert turned.collision.vertices == pytest.approx(base.collision.vertices @ rz.T, abs=1e-12)
    # tip positions map back to the same anatomy point whatever the angle
    p = np.array([[1e-3, 2e-3, 0.5e-3]])
    assert turned.to_anatomy(p @ rz.T) == pytest.approx(base.to_anatomy(p))


def test_sha256_mismatch_and_missing_file(tmp_path, duct_files):
    bad = {"collision": {"file": "coarse.stl", "unit": "mm", "sha256": "0" * 64}}
    with pytest.raises(AnatomyError, match="SHA-256 mismatch"):
        build_anatomy(files_case(tmp_path, bad))
    with pytest.raises(AnatomyError, match="not found"):
        build_anatomy(files_case(tmp_path, {"collision": {"file": "nope.stl"}}))


def test_environment_variables_in_paths(tmp_path, duct_files, monkeypatch):
    monkeypatch.setenv("AURIS_TEST_DATA", str(tmp_path))
    ref = {"collision": {"file": "${AURIS_TEST_DATA}/coarse.stl", "unit": "mm"}}
    assert build_anatomy(files_case(tmp_path, ref)).inputs["collision"]["sha256"]
    monkeypatch.delenv("AURIS_TEST_DATA")
    with pytest.raises(AnatomyError, match="environment variable"):
        build_anatomy(files_case(tmp_path, ref))


def test_explicit_entrance_and_axis(tmp_path, duct_files):
    mesh = duct_files["mesh"]
    apex = mesh.vertices[-PARAMS.n_sides :].mean(axis=0)
    ref = {"file": "coarse.stl", "unit": "mm"}
    case = files_case(tmp_path, {"collision": ref}, entrance={"centre": apex.tolist()})
    case.data["anatomy"]["modiolar_axis"] = {"origin": [0, 0, 0], "direction": [0, 0, 2]}
    anatomy = build_anatomy(case)
    assert anatomy.placement.centre == pytest.approx(apex)
    assert not anatomy.axis_estimated
    assert anatomy.axis_direction == pytest.approx([0, 0, 1])


def test_schema_for_files_source(tmp_path):
    with pytest.raises(CaseError, match="collision"):
        files_case(tmp_path, {"display": {"file": "a.stl"}})
    with pytest.raises(CaseError, match="unit"):
        files_case(tmp_path, {"collision": {"file": "a.stl", "unit": "inch"}})
    with pytest.raises(CaseError, match="insertion_angle_deg"):
        files_case(tmp_path, {"collision": {"file": "a.stl"}}, {"insertion_angle_deg": 120})
    case = files_case(tmp_path, {"collision": {"file": "a.stl"}})
    assert case["strategy"]["insertion_angle_deg"] == 0


def test_synthetic_anatomy_with_angle(example_case_path):
    from auris_sim.io import load_case

    case = load_case(example_case_path)
    base = build_anatomy(case)
    case.data["strategy"]["insertion_angle_deg"] = -10.0
    turned = build_anatomy(case)
    assert turned.collision.vertices == pytest.approx(
        base.collision.vertices @ rotation_about_z(-10.0).T, abs=1e-12
    )
    assert base.display is None and not base.axis_estimated
