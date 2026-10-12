# Legacy removal checklist

The intended master tree includes Python package/tests, project metadata, documentation, and the two authorized original texture converter executables in tools/. No package.json/package-lock.json, JavaScript entry points, src/ or 2k-tools/ JavaScript trees, node_modules, native desktop editors, dist products, old packaged applications or generated output.

Preserved information: useful filename hashes rewritten as names.json; parsing formulas/constants rewritten as Python; format/research notes consolidated into PROJECT_SOURCE_OF_TRUTH.md and MASTER_HANDOFF.md. Those historical documents mention obsolete files as provenance only. Output, caches, temporary dependencies and Python bytecode are gitignored.
