"""Succinct GUI-only staging/build diagnostics; no separate display report file."""

def summary(result):
    imports=[item for group in result.get('imports',[]) for item in group.get('dds_imports',[])]
    resized=[item for item in imports if item.get('artwork_resampled')]
    cached=sum(bool(item.get('cache_hit')) for item in imports)
    problems=result.get('unapplied_overrides',[])
    lines=[f"Status: {result.get('status','complete')}",f"Replacements: {result.get('staged',result.get('patched_entries',0))} archives",f"Textures: {sum('width' in item for item in imports)} imported · {cached} cached · {len(resized)} resized",f"Compatibility: {len(problems)} unapplied overrides"]
    if result.get('added_assets'):lines.append(f"New team assets: {len(result['added_assets'])} archives")
    lines.extend('Notice: '+warning for warning in result.get('warnings',[])[:30])
    if result.get('parallel_workers'):
        lines.append(f"Override preparation: up to {result['parallel_workers']} workers · {result.get('reused_archives',0)} unchanged archives reused")
    groups=result.get('imports',[])
    for group in groups[:50]:
        changed=group.get('dds_imports',[])
        count=sum('width' in item for item in changed)
        resize=sum(bool(item.get('artwork_resampled')) for item in changed)
        lines.append(f"{group['archive']}: {group.get('binary_records',0)} records, {count} textures"+(f", {resize} resized to base layout" if resize else ''))
    if len(groups)>50:lines.append(f"… {len(groups)-50} more replaced archives")
    cube_faces=[(group['archive'],item) for group in groups for item in group.get('dds_imports',[]) if item.get('cubemap_face_updated')]
    for archive,item in cube_faces[:10]:
        lines.append(f"Cubemap: {archive} / {item.get('selector','')}: legacy DDS updates +X; other five faces preserved")
    from .build_diagnostics import diagnose
    for item in problems[:30]:
        lines.append(f"Issue: {item.get('archive','')} / {item.get('selector','')}: {item.get('reason','unapplied')}")
        lines.append('Fix: '+diagnose(item.get('reason','unapplied'))['suggested_fix'])
    if result.get('build_supported') is False:lines.append('Preview only: authenticated SDAT JB rebuilding is unavailable.')
    if len(problems)>30:lines.append(f"… {len(problems)-30} more unapplied overrides")
    if result.get('mod'):lines.append('Workspace: '+str(result['mod']))
    if result.get('workspace_changed'):lines.append('Existing workspace preserved; a new workspace was selected.')
    if result.get('output'):lines.append('Output: '+str(result['output']))
    return '\n'.join(lines)
