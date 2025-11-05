# Logo Analysis Scripts

This folder contains the organized analysis scripts for extracting College Hoops 2K8 team logos.

## Folder Structure

### `iff-parsing/`
Scripts for analyzing and parsing the IFF (Interchange File Format) index files:
- `fixed-iff-analysis.js` - Main IFF structure parser with boundary checking
- `decode-utf16-filenames.js` - UTF-16 filename decoder (experimental)
- `analyze-iff-structure.js` - Raw IFF data analysis and pattern detection
- `correlate-iff-filenames.js` - Maps IFF entries to FileNames.txt entries
- `iff-structure-analysis.js` - NBA2K9 format parser for Type 2 IFF files

### `h7a-decompression/`
Scripts for H7A compression handling:
- `h7a-manual-decompress.js` - Manual H7A decompression with multiple size attempts
- `analyze-decompressed-data.js` - Analysis of decompressed CDF data for GTF headers

### `gtf-extraction/`
Scripts for GTF texture extraction and conversion:
- `extract-mapped-logos.js` - Extract logos using IFF mapping data
- `final-logo-extraction.js` - Complete logo extraction pipeline with H7A decompression
- `improved-logo-extraction.js` - Enhanced extraction with better GTF handling
- `gtf-header-analysis.js` - GTF header structure analysis and validation

### `utilities/`
Utility scripts and legacy analysis tools:
- `logo-analysis.js` - Original 4-test verification script
- `enhanced-logo-analysis.js` - FileNames.txt integration script

## Key Data Files

- `../logo-mapping.json` - Complete mapping of 520 logos to IFF data entries
- `../IFFs/FileNames.txt` - List of 520 logo filenames
- `../IFFs/teamselectlogo.iff` - Type 2 IFF index file (86KB)
- `../IFFs/teamselectlogo.cdf` - H7A compressed texture data (10.7MB)

## Analysis Pipeline

1. **IFF Parsing**: Use `iff-parsing/correlate-iff-filenames.js` to map logos to CDF offsets
2. **H7A Decompression**: Use `h7a-decompression/h7a-manual-decompress.js` to decompress CDF
3. **GTF Extraction**: Use `gtf-extraction/analyze-decompressed-data.js` to find and extract GTF textures
4. **Header Analysis**: Use `gtf-extraction/gtf-header-analysis.js` to validate GTF structure

## Current Status

- ✅ 520 logos identified and mapped
- ✅ H7A decompression working
- ✅ 44 GTF headers found in decompressed data
- 🔄 GTF to DDS conversion needs refinement (boundary extraction issues)

## Next Steps

1. Refine GTF extraction boundaries to exclude padding/empty data
2. Analyze texture data patterns for proper dimension detection  
3. Implement successful GTF → DDS conversion pipeline