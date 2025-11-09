## Choops Extractor

*This is the continuation of a discontinued tool by BPhit in an effort to expand development on College Hoops 2K Reborn*

### Instructions
1. Download the file from the releases page on here.
2. Use 7-zip to extract it somewhere. You'll see two files: choops-extractor.exe and gtf2dds.exe
3. Open a command prompt and type `choops-extractor.exe rip <path to game files up till USRDIR> <path to output>`
4. It will take awhile, it will build a cache and then go through each IFF one by one to extract the contents.

### Usage
By default, the tool will extract all files within the IFFs. It will automatically convert the textures to DDS format.

#### Help
If you want to get documentation on any of the options from the command prompt, use `choops-extractor.exe help` or `choops-extractor.exe help rip`

#### IFF Only
If you do not want to extract the sub-files, you can add `--iff-only` to the command prompt and it will extract the full .iff file without any textures.

#### Index
If you know which index you want to extract, you can use `-i <index>`. The index must be a number. It will extract the IFF file at <index> in the game files.

#### File by name
If you only want to extract one IFF file by name, you can use `-f <name>`. This will ONLY extract the IFF file with the <name> specified. You have to include .iff on the end of the name.

#### Cache
If you want to force re-build the cache, use `-c`

#### Log output
If you want to customize where to put the log output, use `--log-output <logPath>`. By default, the log is placed in the output directory.

#### Show console
If you want to show the log in the console in addition to the log file, use `--show-console`.

## Project Structure

### Core Components
- **extract-all-ch2k8-logos.js** - Working logo extraction script that successfully extracts 350 team logos from College Hoops 2K8's teamselectlogo.cdf file
- **2k-tools/** - Collection of utilities for working with 2K game files and IFF archives
- **src/** - Core extractor source files (builder, importer, ripper, cache management)
- **test/** - Test files and validation data
- **IFFs/** - Sample IFF files and reference data for development

### Extracted Assets
- **logo-analysis/final-logos/** - 350 successfully extracted College Hoops 2K8 team logos (96x96 RGBA format)
- **logo-analysis/utilities/** - Helper scripts for logo processing and analysis

### Current Capabilities
- ✅ **Logo Extraction**: Successfully extracts all 350 College Hoops 2K8 team logos from CDF files
- ✅ **IFF Archive Processing**: Can extract and manipulate IFF archive files
- ✅ **Texture Format Conversion**: Converts extracted textures to standard formats (DDS, TGA)
- ✅ **File Structure Analysis**: Can analyze and parse complex game file structures

### Known Challenges
- **H7A Compression**: Some files use H7A compression format which requires specialized decompression
- **Format Variations**: Different 2K game versions may use varying file formats and compression methods
- **Texture Format Detection**: Automatic detection of texture formats can be challenging without proper headers
- **File Size Optimization**: Some extraction processes generate large intermediate files

### Technical Notes
- CDF files contain uncompressed sequential texture data, not H7A compressed data
- Logo extraction uses entropy-based scanning (0.4-0.9 range) to identify valid texture regions
- Successful extraction method bypasses compression issues by working directly with raw texture data
