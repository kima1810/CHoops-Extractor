const fs = require('fs');
const path = require('path');

// Read the mapping file
const mappingPath = path.join(__dirname, 'logo-mapping.json');
const logoMapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));

// Read the CDF file
const cdfFilePath = path.join(__dirname, 'IFFs', 'teamselectlogo.cdf');
const cdfBuffer = fs.readFileSync(cdfFilePath);

// Output directory
const outputDir = path.join('D:', 'Reborn', 'CH2KRB', 'LogoExtract', 'Logos');
if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
}

console.log(`Extracting logos using IFF mapping`);
console.log(`CDF file size: ${cdfBuffer.length} bytes`);
console.log(`Logos to extract: ${logoMapping.length}`);

function extractLogosUsingMapping() {
    // Group logos by their hash2 values (offset groups)
    const offsetGroups = {};
    logoMapping.forEach(logo => {
        const key = logo.hash2.toString(16);
        if (!offsetGroups[key]) offsetGroups[key] = [];
        offsetGroups[key].push(logo);
    });
    
    console.log('\nOffset groups:');
    Object.entries(offsetGroups).forEach(([offset, logos]) => {
        console.log(`  0x${offset}: ${logos.length} logos`);
    });
    
    // The hash2 values might not be direct offsets, but rather identifiers
    // Let's search for GTF headers in the CDF file and see how they align
    console.log('\n=== Searching for GTF headers in CDF ===');
    
    const gtfHeaders = [];
    const gtfMagic = 0x01080000; // GTF magic number (little-endian)
    
    for (let i = 0; i <= cdfBuffer.length - 4; i++) {
        const magic = cdfBuffer.readUInt32LE(i);
        if (magic === gtfMagic) {
            gtfHeaders.push({
                offset: i,
                magic: magic
            });
        }
    }
    
    console.log(`Found ${gtfHeaders.length} GTF headers in CDF file:`);
    gtfHeaders.forEach((header, i) => {
        console.log(`  GTF[${i}]: offset 0x${header.offset.toString(16)} (${header.offset})`);
    });
    
    if (gtfHeaders.length === 0) {
        console.log('No GTF headers found. The CDF might use H7A compression.');
        
        // Try to find H7A compressed blocks
        console.log('\nSearching for H7A compression signatures...');
        
        // H7A typically starts with specific byte patterns
        // Let's look for potential compressed blocks
        const h7aPatterns = [
            0x48374137, // "H7A7"
            0x789C,     // zlib header
            0x78DA,     // zlib header (different compression level)
        ];
        
        h7aPatterns.forEach(pattern => {
            console.log(`\nSearching for pattern 0x${pattern.toString(16)}:`);
            let patternSize = pattern > 0xFFFF ? 4 : 2;
            
            for (let i = 0; i <= cdfBuffer.length - patternSize; i++) {
                let found = false;
                if (patternSize === 4) {
                    found = cdfBuffer.readUInt32BE(i) === pattern || cdfBuffer.readUInt32LE(i) === pattern;
                } else {
                    found = cdfBuffer.readUInt16BE(i) === pattern || cdfBuffer.readUInt16LE(i) === pattern;
                }
                
                if (found) {
                    console.log(`  Found at offset 0x${i.toString(16)} (${i})`);
                    
                    // Show some context around the pattern
                    const contextStart = Math.max(0, i - 16);
                    const contextEnd = Math.min(cdfBuffer.length, i + 32);
                    const context = cdfBuffer.subarray(contextStart, contextEnd);
                    console.log(`    Context: ${Array.from(context).map(b => b.toString(16).padStart(2, '0')).join(' ')}`);
                    
                    if (i > 1000) break; // Don't spam too much output
                }
            }
        });
    }
    
    // Let's also examine the structure at the beginning of the CDF file
    console.log('\n=== CDF File Header Analysis ===');
    
    if (cdfBuffer.length >= 64) {
        console.log('First 64 bytes of CDF file:');
        const header = cdfBuffer.subarray(0, 64);
        
        // Show as hex
        const hexLines = [];
        for (let i = 0; i < header.length; i += 16) {
            const line = header.subarray(i, Math.min(i + 16, header.length));
            const hex = Array.from(line).map(b => b.toString(16).padStart(2, '0')).join(' ');
            const ascii = Array.from(line).map(b => (b >= 32 && b <= 126) ? String.fromCharCode(b) : '.').join('');
            hexLines.push(`${i.toString(16).padStart(4, '0')}: ${hex.padEnd(47)} | ${ascii}`);
        }
        
        hexLines.forEach(line => console.log(`  ${line}`));
    }
    
    // Try to interpret the first few DWORDs as potential header
    console.log('\nPotential header values:');
    for (let i = 0; i < Math.min(32, cdfBuffer.length - 4); i += 4) {
        const valueBE = cdfBuffer.readUInt32BE(i);
        const valueLE = cdfBuffer.readUInt32LE(i);
        
        console.log(`  @0x${i.toString(16).padStart(2, '0')}: BE=0x${valueBE.toString(16).padStart(8, '0')} (${valueBE}) | LE=0x${valueLE.toString(16).padStart(8, '0')} (${valueLE})`);
    }
    
    return gtfHeaders;
}

// Run extraction
try {
    const gtfHeaders = extractLogosUsingMapping();
    
    console.log('\n=== Next Steps ===');
    if (gtfHeaders.length > 0) {
        console.log('Found GTF headers - can proceed with direct extraction');
    } else {
        console.log('No direct GTF headers found - CDF likely uses compression');
        console.log('Need to identify compression format and decompress before extracting GTF data');
    }
    
} catch (error) {
    console.error('Extraction failed:', error);
}