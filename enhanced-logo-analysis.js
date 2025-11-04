const fs = require('fs');
const path = require('path');

const IFF_FILE_PATH = './IFFs/teamselectlogo.iff';
const CDF_FILE_PATH = './IFFs/teamselectlogo.cdf';
const FILENAMES_PATH = './IFFs/FileNames.txt';
const OUTPUT_DIR = 'D:\\Reborn\\CH2KRB\\LogoExtract\\Logos';

async function analyzeLogosWithNames() {
    console.log('🔍 Enhanced Logo Analysis with FileNames.txt\n');
    
    // Ensure output directory exists
    if (!fs.existsSync(OUTPUT_DIR)) {
        fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    }
    
    // Read all files
    const iffBuffer = fs.readFileSync(IFF_FILE_PATH);
    const cdfBuffer = fs.readFileSync(CDF_FILE_PATH);
    const fileNamesText = fs.readFileSync(FILENAMES_PATH, 'utf-8');
    
    // Parse file names
    const logoNames = fileNamesText.trim().split('\n').map(name => name.trim());
    
    console.log(`📁 IFF File: ${iffBuffer.length} bytes`);
    console.log(`📁 CDF File: ${cdfBuffer.length} bytes`);
    console.log(`📄 FileNames: ${logoNames.length} logo entries\n`);
    
    // Find all GTF headers in CDF
    const gtfLocations = findAllGTFHeaders(cdfBuffer);
    console.log(`🎯 Found ${gtfLocations.length} GTF headers in CDF file`);
    console.log(`📝 Found ${logoNames.length} logo names in FileNames.txt\n`);
    
    // Analyze IFF structure to find the mapping
    await analyzeIFFStructure(iffBuffer, logoNames.length);
    
    // Extract logos with proper sizing
    await extractLogosWithNames(cdfBuffer, gtfLocations, logoNames);
}

function findAllGTFHeaders(cdfBuffer) {
    const gtfMagics = [0x01080000, 0x00000801];
    const locations = [];
    
    for (let magic of gtfMagics) {
        for (let i = 0; i < cdfBuffer.length - 4; i++) {
            const value = cdfBuffer.readUInt32BE(i);
            if (value === magic) {
                locations.push({
                    offset: i,
                    magic: magic,
                    magicHex: magic.toString(16).toUpperCase()
                });
            }
        }
    }
    
    // Sort by offset
    locations.sort((a, b) => a.offset - b.offset);
    
    console.log('GTF Header Locations:');
    locations.forEach((loc, index) => {
        const indexStr = (index + 1).toString().padStart(2, ' ');
        const offsetStr = loc.offset.toString().padStart(8, ' ');
        console.log(`  ${indexStr}: 0x${loc.offset.toString(16).toUpperCase().padStart(6, '0')} (${offsetStr}) - Magic: 0x${loc.magicHex}`);
    });
    
    return locations;
}

async function analyzeIFFStructure(iffBuffer, expectedCount) {
    console.log('\n🔬 IFF Structure Analysis');
    console.log('========================');
    
    // Based on our previous analysis, let's look at the structure more carefully
    console.log('Header Analysis:');
    console.log(`  Magic: 0x${iffBuffer.readUInt32BE(0).toString(16).toUpperCase()}`);
    console.log(`  Size1: ${iffBuffer.readUInt32BE(4)} (0x${iffBuffer.readUInt32BE(4).toString(16)})`);
    console.log(`  Size2: ${iffBuffer.readUInt32BE(8)} (0x${iffBuffer.readUInt32BE(8).toString(16)})`);
    console.log(`  Zero1: ${iffBuffer.readUInt32BE(12)}`);
    console.log(`  Count1: ${iffBuffer.readUInt32BE(16)} - Potential entry count`);
    console.log(`  Count2: ${iffBuffer.readUInt32BE(20)} - Another count (${iffBuffer.readUInt32BE(20)})`);
    
    const potentialCount1 = iffBuffer.readUInt32BE(16);
    const potentialCount2 = iffBuffer.readUInt32BE(20);
    
    console.log(`\nExpected logos: ${expectedCount}`);
    console.log(`IFF Count1: ${potentialCount1}`);
    console.log(`IFF Count2: ${potentialCount2}`);
    
    if (potentialCount2 === expectedCount) {
        console.log(`✅ Count2 matches expected logo count!`);
        return potentialCount2;
    } else if (potentialCount1 === expectedCount) {
        console.log(`✅ Count1 matches expected logo count!`);
        return potentialCount1;
    } else {
        console.log(`⚠️  No direct match found. Will analyze structure further.`);
    }
    
    // Look for offset table patterns
    console.log('\nLooking for offset table patterns...');
    for (let startOffset = 24; startOffset < 200; startOffset += 4) {
        const value = iffBuffer.readUInt32BE(startOffset);
        if (value > 0 && value < 50000000) { // Reasonable offset range
            console.log(`  Offset 0x${startOffset.toString(16)}: ${value} (0x${value.toString(16)})`);
        }
    }
}

async function extractLogosWithNames(cdfBuffer, gtfLocations, logoNames) {
    console.log('\n🎨 Logo Extraction Process');
    console.log('==========================');
    
    if (gtfLocations.length === 0) {
        console.log('❌ No GTF headers found to extract');
        return;
    }
    
    // Calculate sizes for each GTF by looking at the distance to the next one
    const gtfWithSizes = gtfLocations.map((location, index) => {
        let size;
        if (index < gtfLocations.length - 1) {
            // Size is distance to next GTF header
            size = gtfLocations[index + 1].offset - location.offset;
        } else {
            // Last GTF - size is remaining buffer
            size = cdfBuffer.length - location.offset;
        }
        
        return {
            ...location,
            size: size,
            logoName: logoNames[index] || `unknown_logo_${index}`
        };
    });
    
    console.log('\nExtracting GTF files with calculated sizes:');
    
    let successCount = 0;
    for (let i = 0; i < gtfWithSizes.length; i++) {
        const gtf = gtfWithSizes[i];
        
        const indexStr = (i + 1).toString().padStart(3, ' ');
        console.log(`\n${indexStr}. ${gtf.logoName}`);
        console.log(`    Offset: 0x${gtf.offset.toString(16)} (${gtf.offset})`);
        console.log(`    Size: ${gtf.size} bytes (${(gtf.size / 1024).toFixed(1)} KB)`);
        
        try {
            // Extract GTF data
            const gtfData = cdfBuffer.slice(gtf.offset, gtf.offset + gtf.size);
            
            // Validate GTF header
            const magic = gtfData.readUInt32BE(0);
            if (magic === gtf.magic) {
                // Save GTF file
                const gtfPath = path.join(OUTPUT_DIR, `${gtf.logoName}.gtf`);
                fs.writeFileSync(gtfPath, gtfData);
                
                // Try to convert to DDS
                const success = await convertGTFToDDS(gtfPath, gtf.logoName);
                if (success) {
                    console.log(`    ✅ Successfully extracted and converted to DDS`);
                    successCount++;
                    
                    // Remove GTF file after successful conversion
                    try { fs.unlinkSync(gtfPath); } catch {}
                } else {
                    console.log(`    ⚠️  GTF extracted but DDS conversion failed`);
                }
            } else {
                console.log(`    ❌ Invalid GTF magic: 0x${magic.toString(16)}`);
            }
        } catch (err) {
            console.log(`    ❌ Extraction error: ${err.message}`);
        }
    }
    
    console.log(`\n🎉 Extraction complete!`);
    console.log(`✅ Successfully converted: ${successCount}/${gtfWithSizes.length} logos`);
    console.log(`📂 Output directory: ${OUTPUT_DIR}`);
}

async function convertGTFToDDS(gtfPath, logoName) {
    return new Promise((resolve) => {
        const { exec } = require('child_process');
        const ddsPath = path.join(OUTPUT_DIR, `${logoName}.dds`);
        const gtfExePath = path.join(__dirname, '2k-tools', 'lib', 'gtf2dds.exe');
        
        exec(`"${gtfExePath}" -v -z -o "${ddsPath}" "${gtfPath}"`, (err, stdout, stderr) => {
            if (!err && fs.existsSync(ddsPath)) {
                resolve(true);
            } else {
                resolve(false);
            }
        });
    });
}

// Run the enhanced analysis
analyzeLogosWithNames().catch(err => {
    console.error('❌ Analysis failed:', err);
});