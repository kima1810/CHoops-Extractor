"""Actionable explanations for known override/build failures; no guessed repairs."""


def diagnose(error):
    detail=str(error);text=detail.casefold()
    rules=(
        (('not a standard ps3 iff','invalid_iff_override'),
         'The named input is not a complete supported PS3 IFF container.',
         'Read the archive name, source/replacement role and magic in Details. Keep raw TXTR/SCNE files inside their archive record folder; do not rename them to .iff. Restore a damaged complete IFF from the same rip and reselect the original overrides.'),
        (('base cubemap faces',),
         'Flat artwork was supplied for a six-face cubemap.',
         'Folder imports update the first (+X) face and preserve the other five base faces. Reselect overrides in the current version. Direct texture edits remain strict: supply a complete cube to replace every face.'),
        (('incomplete archive header','incomplete_archive_header','short split-bank','short archive read','archive part size mismatch'),
         'The source archive header could not be read completely.',
         'Headers may span multiple banks. Update to the split-header fix. If it still fails, restore the named missing/truncated source banks from the same rip, then reselect the source JB. Renaming DDS overrides cannot repair source banks.'),
        (('header_extent','invalid_archive_header','bank descriptors/toc','sdat header authentication failed','sdat block authentication failed'),
         'The source TOC declares an unsupported header region.',
         'Use the original complete JB as the source. Check the expected/actual byte counts in Details; keep the original source and overrides unchanged for diagnosis.'),
        (('cdf_pair_required','cdf companion is missing','cdf_pair_mismatch'),
         'An IFF texture bank is missing its matching CDF.',
         'Keep the matching IFF and CDF from the same rip together. Use the exact companion filename reported by the IFF; do not mix pairs from different games.'),
        (('duplicate','ambiguous','no unique','unresolved_archive_identity','unknown archive filename','no archive folder'),
         'An override target is missing, duplicated or ambiguous.',
         'Use the archive and selector named in Details. Keep each archive in its matching folder, keep one replacement per selector, and check the filename against Explorer. DDS wins over the corresponding TXTR; two DDSes of equal priority need manual resolution.'),
        (('invalid_dds','truncated dds','unsupported_dds','unsupported_texture_layout','dx10'),
         'The named DDS cannot be imported into its target layout.',
         'Re-export that texture as a supported legacy DDS matching the target type, with a complete mip chain. Preserve cubemap faces when applicable. Check the reported dimensions/encoding; do not merely rename another image to .dds.'),
        (('geometry overlaps','overlaps a texture','extended_iff_read_only'),
         'The named container has a layout that cannot safely be rewritten.',
         'Keep its SCNE and textures from the same extraction together. Replace the complete compatible IFF when available. Extra/unclassified IFF metadata remains read-only; deleting unknown bytes is not a safe repair.'),
        (('source_version_mismatch','source changed','another or changed jb','cached source changed'),
         'Prepared overrides no longer match the selected source.',
         'Reselect the intended source JB, then select the original overrides folder again. Leave the old prepared workspace intact; the tool will create a new validated snapshot.'),
        (('sdat/extended bank','sdat/extended-descriptor'),
         'This game supports extraction and previews, but not authenticated JB rebuilding yet.',
         'Use previews and export edited roster/IFF copies for research. A safe SDAT authentication/signature writer must be established before enabling Build JB.'),
    )
    for needles,problem,fix in rules:
        if any(needle in text for needle in needles):
            return dict(problem=problem,suggested_fix=fix,detail=detail)
    return dict(problem='The operation stopped without changing the source game.',
                suggested_fix='Review the exact archive, selector and error below. Keep the original inputs; an unrecognized failure needs investigation rather than an automatic destructive repair.',detail=detail)


def failure_summary(operation,error):
    issue=diagnose(error)
    return operation+' failed\n\nProblem: '+issue['problem']+'\n\nSuggested fix: '+issue['suggested_fix']+'\n\nDetails:\n'+issue['detail']
