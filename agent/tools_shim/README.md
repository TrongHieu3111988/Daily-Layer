Stand-in for scikit-image's marching_cubes (marching tetrahedra, numpy only), used when the workshop lacks scikit-image:
`PYTHONPATH=agent/tools_shim python3.13 agent/build.py out <slug>` (python3.13 has numpy). Watertight by construction; about 2x the triangles of marching cubes, so use a coarser step for big models.
