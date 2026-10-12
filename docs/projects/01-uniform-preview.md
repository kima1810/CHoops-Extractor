# Uniform preview

Implemented. Open a cloth SCNE, choose a searchable home/away/alternate uniform from the loaded JB folder, or choose Open uniform IFF. The preview uses the selected source's `unifregion`/`shortregion` authored RGB; `unif`/`short` are fallback records. Normal maps and number atlases are not substituted for color artwork. Material-data alpha is made opaque only in the preview copy.

Jersey and shorts use their corresponding images. Same-name cloth SCNE sections are alternatives, rather than superimposed geometry. Player names, numbers, cloth simulation and full game material shading are not reproduced. The original assets remain unchanged.

Verified with a native OpenGL jersey render and synthetic sampler-selection tests.
