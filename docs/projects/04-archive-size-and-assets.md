## Header-gap preservation and user destinations (current update)

The post-TOC/pre-asset gap can contain opaque nonzero bytes in rebuilt inputs.
Existing replacement slots consume none of it; append planning preserves the gap
verbatim and validates only slots occupied by additions. Repack planning can keep
opaque bytes at their original offsets when the body start is unchanged and the
new TOC consumes only verified zeros. Moving the body with opaque header data or
expanding TOC over that data remains blocked. This deliberately does not infer
unknown header pointers or erase nonzero bytes.

Mod Builder's **Choose JB output folder…** accepts an empty destination on another
drive. CLI build-copy accepts the same destinations. The original JB and mod
workspace cannot overlap the output in either direction; roots and linked paths
are refused. Existing nonempty folders require the existing explicit overwrite
option and a valid tool-owned build manifest. Publication/rollback uses siblings
on the destination drive. Other export/staging paths still use output/.

# Archive size and new assets

TOC offsets use alignment units; TOC lengths are byte counts. The reader now distinguishes byte length from the aligned allocation. Existing same-extent texture edits retain compression and bank sizes. A bounded H7A recompressor avoids literal expansion when it produces a smaller verified stream.

New-asset builds create a separate JB folder. The append writer uses verified zero TOC padding; when it runs out, the repacker expands the TOC and relocates the preserved archive body across split banks. Both verify every existing asset, reparse additions and replacements, and check that the source inventory is unchanged. New assets necessarily increase total size; ordinary replacement edits do not silently grow fixed allocations.

Uniform roster growth copies the counted table to the payload end and updates its count and relative pointer. Existing table/heap addresses remain intact. The IFF writer preserves container metadata and name trailers and verifies decoded payload equality.

Synthetic tests cover TOC expansion, split-bank growth, oversized roster relocation, invalid compression and source preservation. Copied-JB tests have validated a new second alternate and a first alternate on a previously home/away-only team, including both uniform and menu-selection containers. In-game execution remains unverified. A bulk copied-JB build validated 1,179 new uniform records for 429 current/classic school owners, using six split banks; all 3,380 existing entries were checked. All eligible owners had five linked banks in the rebuilt roster. The source was unchanged. The extra cloned art increased the archive by approximately 801 MiB.

Two-block CDF texture banks support independent internal record cloning with preserved original CDF bytes. IFF and CDF replacements must be supplied together and all compressed spans are validated. Team-selection logo cloning preserves existing records and adds a new named logo. Runtime validation remains outstanding.
