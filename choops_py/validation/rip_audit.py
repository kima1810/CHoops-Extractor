from pathlib import Path
def audit(inventory,rip):
    expected={line.strip().replace('\\','/').split('/')[-1] for line in Path(inventory).read_text().splitlines() if line.strip() and not line.startswith('#')}
    actual={p.name for p in Path(rip).rglob('*') if p.is_file()}
    return dict(missing=sorted(expected-actual),present=sorted(expected&actual),unexpected=sorted(actual-expected),valid=not bool(expected-actual))
