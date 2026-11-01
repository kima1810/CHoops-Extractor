# Team asset manager (v1.20)

Open a College Hoops 2K8 JB, choose Source JB or Selected overrides at the top,
then open **Team Assets** (also linked from Roster Editor). **Load / refresh teams**
shows every team, including classics, its roster index/Team ID, general Asset ID,
uniform owner, menu-logo ID, stadium filename, shared assignments and the
Home/Away/X/Y/Z links. Active means linked; an existing unlock ID can still require
profile progression. Inactive, saved-inactive, missing and ambiguous states differ.
Full gameplay/SELU filenames are in cell tooltips. Search filters all row values.
Each shared asset is marked `* (school [Team ID], ...)` in its own cell and
tooltip. Sharing follows actual stadium selectors, uniform filenames and menu
logo IDs, even when teams have different arena rows or uniform owners. A classic
team using a modern team's arena is marked on S; unrelated unique assets are not.
Existing available assets start checked, including a uniform bank only when both
its gameplay and SELU files exist. Missing, inactive, ambiguous and uninspected
assets start unchecked. The defaults reflect the selected source and loaded roster;
they do not request any copies or changes by themselves.

1. Select one or more team rows. Check S, UH, UA, UX, UY, UZ and/or Menu logo,
   individually or with **Check all types for selected teams**. Newly checked
   categories request additions; existing checks keep their assignments. To give
   existing assets independent copies, select the team rows and click **Clone
   checked assets for selected teams**, or change the Target ID (which copies
   all checked categories for that row). Clear unwanted categories before cloning.
   Clearing a check does not remove an existing assignment. **Check missing
   alternates for visible teams** checks X/Y/Z only where inactive; teams without
   valid Home/Away templates are skipped. Unrelated team types are never converted.
2. Target ID starts with the team's original Asset ID. Leaving it unchanged keeps
   current assignments; additions reuse a unique uniform owner or allocate an
   unused ID for shared routes during review. Change it to a different unused
   0–1023 ID to copy all checked categories there. Uniform-only expansion can
   retain an already uniquely owned uniform ID. Forking other categories allocates
   a wholly unused ID. If a missing bank filename at that owner ID already exists,
   a separate free artwork selector is allocated so unrelated art is preserved. General Asset ID is displayed but preserved because other
   consumers use it. Team index, asset ID and uniform owner need not be identical.
3. **Review checked changes** prepares a file/team summary without writing inputs.
   Missing earlier banks are filled so an enabled Z has H/A/X/Y before it. Existing
   linked artwork is retained; genuinely absent alternates use the Home template.
   These are editable copies, not newly authored alternate designs.
4. **Apply to new overrides folder** creates a separate folder under output/overrides,
   selects its prepared snapshot and carries existing selected overrides forward.
   Each new asset gets a named folder containing its complete IFF. Add DDS/SCNE
   edits inside those folders as usual, then select that loose folder again in
   Explorer. DDS retains priority. New assets appear in Explorer and preview lists.
5. **Build JB copy** runs normal compatibility checks and adds the new archive names
   to the copied JB's TOC. Missing linked alternate assets are checked again during
   build preflight. A missing gameplay/SELU container is cloned from the corresponding
   Home container; the task log and build summary name every fallback. Supplied
   alternate artwork and existing JB alternates are not replaced by this fallback.
   Unedited Home placeholders created by the manager also produce notices. A
   missing/ambiguous Home template blocks with a specific filename.

The editable folder includes team_assets.json. Keep it with the folders: it makes
new archive identities discoverable and binds the plan to the source roster. The
prepared workspace holds checksums and additions.json separately from replacement
rows. Tampering or selecting another source is rejected. XOR patch packages cannot
represent additions and explicitly refuse them; share the editable folder instead.
**Save roster to overrides** in Roster Editor saves the entire edited community
roster (including realignment, players and ratings) into a new selected override
snapshot while retaining existing selected asset replacements/additions. The
original community file and JB stay unchanged. Team Assets starts from that same
editor payload when Include roster editor changes is checked. Its apply action
also saves the entire edited/expanded roster and synchronizes the open editor as
one undoable change, so a later save retains the new links. Load from overrides brings that
applied roster back into the editor. Refresh assignments after source/editor
changes; stale reviewed plans cannot be applied.

## Copy activation and assignments between roster sources

Select team rows, then use **Copy assignments from…** or **Copy assignments to…**.
Sources include the open roster editor, Source JB, Selected overrides and an
external roster/decrypted save. Copying to a JB-based destination always creates
new overrides; it never edits the source JB. External destinations are saved as
separate copies under output/. Fixed-size Legacy saves cannot accommodate growth;
use a roster IFF/overrides for expanded records.

The review identifies teams, uniform owners and active/inactive banks. Only asset
IDs, arena routing and counted/dormant uniform records are copied. Destination
names, players, ratings, palettes, classification and conference membership stay
intact. Match uses roster Team ID checks with equal team counts, not an assumed
name search. A shared owner is forked when necessary to protect unselected teams.
Copying to Roster Editor is one undoable edit, including moved table directories.
Art files are separate: copy their overrides too, inspect Missing states, or use
normal expansion/Home fallback. The entire roster-save action is distinct from
these selected-team assignment-only copy actions.

For a community roster: open it in Roster Editor, realign/edit, save to overrides,
then load Team Assets with editor changes included. Check desired new categories,
review/apply, customize the generated folders and build from Selected overrides.
Team Assets appears above Research and Diagnostics in navigation.

## Classic teams and unique stadiums

To separate an existing shared stadium, keep S checked, clear other categories
you do not want copied, then use **Clone checked assets for selected teams**.
This clones the team's current stadium to a new s###.iff (and its n sibling
when supplied), appends a physical arena record, and rewires only that team's arena
reference. Shared original teams keep their old arena. The arena's display code
and native numeric stadium selector are both updated. All arena string pointers
and unaffected team references are rebased; classification/conferences/players/
coaches are preserved. Special arena modes2/3 and teams without a verified arena
are blocked rather than assigned guessed behavior. A copied arena initially looks
like its template; replace its artwork/geometry in its new folder to customize it.

Menu logo creates an independent logo### TXTR record inside teamselectlogo.iff and
its paired CDF, not a standalone team-logo IFF. Existing records and original
payloads remain intact. Explicit clone-template mappings preserve the donor's
texture-layout contract during DDS import and live previews.

## Native assignment evidence and limits

Read-only decoded CH2K8 EBOOT analysis, confirmed with focused Ghidra decompilation:

| Consumer | Evidence | Consequence |
| --- | --- | --- |
| Uniform owner | Getter0x769CB8 extracts word0 bits22–31;0x1C244C compares owners against team anchor+0x160 (editor team row+0x190) | Owner IDs0–1023; distinct from general team Asset ID |
| Uniform artwork | Getter0x769CF4 extracts bits12–21;0x769FD8 formats u%c%03d using haxyz table0x10036070 and variant getter0x769D74 | Artwork IDs0–1023; five supported bank codes0–4 |
| Uniform selection |0x1C252C counts matching owner records and returns requested matching ordinal | Preserve owner bank order; no holes before later banks |
| Stadium |0x580A3C /0x580A9C reads physical arena+0x12; format s%03d.iff at0x124B7290; mode is physical+0x18 low2bits | Updating only arena_code text is insufficient; physical selector is unsigned16-bit |
| Arena index |0x1BC050 indexes28-byte rows using the runtime count/table | Append/rebase arena records; editor bound8192 is a structural safety bound, not a proven engine ceiling |
| Menu logo |0x524A90 formats logo%03d at0x124B2650 from supplied selector; team menu selector is row+0x194 | Add the corresponding CDF record; filename copying alone cannot assign it |

The manager conservatively uses the common ten-bit ID domain. %03d is minimum
padding, not a three-digit maximum. The inspected source has443 teams,441 usable
Home/Away owners,553 entirely unused common IDs, and two temporary unassigned
teams. These counts are observations, not format constants. Existing per-team
uniform owners can be reused; shared arena references require independent copies.
The native logo browser also contains a fixed stock enumeration; arbitrary new
runtime menu/cache limits are not fully established. Added logical records and
TOC entries pass offline validation, not console certification. No EBOOT patch,
classification conversion, emulator test or automatic game-sized JB is produced.

Bulk read-only planning on the supplied roster fills missing banks for435 teams,
produces2,434 paired gameplay/SELU additions, and yields2,205 active rows (five
per usable owner), with all original team owners retained. One final roster
reparse validates the batch rather than rebuilding player dictionaries per team.
This15.95-second local observation is not a portable performance guarantee.


## Loose alternate folders (v1.22)

New X/Y/Z gameplay or SELU folders can be imported without `team_assets.json` when
their exact archive identities are enabled by the source JB roster or the unique
full `roster_english.iff` inside the selected overrides tree. Save roster changes
with **Save roster to overrides** before selecting that tree. A missing container
uses the same owner's Home bank as its structural template; nested DDS artwork
still takes priority over TXTR. Preparation reports the template filename, and
build preflight supplies a missing linked gameplay/SELU partner through the normal
Home fallback. New archive IDs are written to the rebuilt TOC.

Folders not linked by that effective roster are rejected; their names alone do
not activate uniforms. Conflicting rosters/templates, missing Home sources, links
and ambiguous identities remain errors. Existing explicit team-assets manifests
retain their source-roster checks. Selecting a folder never alters its files or
the source JB. Gameplay compatibility is not certified by structural validation.
