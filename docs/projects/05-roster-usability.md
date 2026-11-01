# Roster usability

Implemented confirmed choices. Handedness is 0 L and 1 R, traced through the localized Hand option array. Headband is No/Yes; home sock color is Black/White. Their packed edits preserve unrelated bits and use dropdowns.

The property viewer also labels verified build, muscle tone, appearance color, eye color, sock length and T-shirt choices. Enum values outside recovered choices remain explicit raw/unknown values. Binary values are not universally treated as booleans: muscle tone means Buff/Ripped, while sock color means Black/White.

Verified with packed-neighbor preservation tests and existing undo/round-trip checks.


The Teams and Edit Schools tabs expose **Enable alternates…**, with separate Alternate 1/2/3 checkboxes. Existing linked records can be disabled and restored without changing their asset selector, shape, or unlock ID. Records without linked assets cannot be enabled here; use the copied-JB alternate builder first.

The executable has no confirmed enable bit. Disabled records are excluded from the counted uniform table and retained as editor recovery metadata outside it. Recovery survives IFF save/reopen and undo/redo. Expanded tables currently save through raw ROST or a single-record ROST IFF; save wrappers that require fixed payload size are refused. This layout has offline round-trip validation, not in-game validation. Availability still follows the game's profile/unlock checks for enabled records.
