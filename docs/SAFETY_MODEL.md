# Safety model

Supplied JB, overrides, templates, rosters and EBOOT remain immutable. Generated
game edits/rips/reports live under output/. Reject source overlap, traversal and
linked build trees. Existing outputs are refused except owned transactional build
replacement. Cleanup never targets unknown/user data.

Manual builds validate staged identities/source hashes and patch only a new copy.
Supported growth may relocate records/archives; untouched bytes are compared.
Unknown offsets/aliases remain blocked. D1 conversion is explicitly optional.

DDS conversion uses independent Python code. Audio uses experimental open-source
components. Song metadata must not be implemented through EBOOT writes.

Agents use synthetic tests and read-only fixtures. NEVER launch RPCS3 or create
full testing JB builds. Review PR code/dependencies before execution; CI uses no
private inputs/secrets and never executes untrusted pull_request_target checkouts.
