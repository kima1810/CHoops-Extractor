# Reusing classic/all-time slots as independent D1 teams

The new archive insertion and uniform-table writer provide a foundation: independent uniform/menu containers can be added and associated with an existing team owner. Uniform asset selectors are separate from owner IDs, so jersey art need not share a numeric ID with the stadium.

A complete D1 conversion also needs the historical/all-time classification and conference eligibility fields, reciprocal conference-member lists, independent arena/stadium references, coach/player links, and menu logo/portrait routing. Existing same-size field edits and a copied-JB build preserve originals. Do not describe an ID-only edit as a complete D1 conversion.

The uniform owner field is ten bits. The stadium filename construction and menu logo paths require separate bounds and reference checks. Shared physical textures or aliases must be copied into new owned containers rather than edited in place.

D1 conversion is optional in the roster editor. The conference dialog has an unchecked classification checkbox. An ordinary conference move preserves classification; uniform builders never convert teams. The editor updates reciprocal conference member lists and their verified counts, and changes only the confirmed team-type bits when conversion is explicitly selected.

**Give school independent assets…** is a separate, explicit copied-JB action. It clones the referenced stadium, active uniform/menu-selection banks, and an internal team-selection logo record. It appends an independent arena record, rebases the copied arena table's string pointers, and updates team arena references. The selected school's stadium code, uniform owner and menu-logo selector receive the new unused ID. Other schools retain their original values. New uniform records use unlock ID zero.

Asset cloning preserves classification and conference membership. Conversion remains an unchecked option in the separate conference dialog. Arena thumbnails, runtime cache sharing and in-game schedule/menu eligibility remain unvalidated; creating a complete renamed D1 program still requires roster/player/coach edits. The source fixture tests are offline evidence, not gameplay proof.
