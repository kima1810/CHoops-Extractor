from ..formats.cdf_backed_iff import CDFPair
def validate(iff,cdf):return dict(valid=True,scope='metadata and CDF range bounds; payload semantics unverified',**CDFPair(iff,cdf).manifest())
