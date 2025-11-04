const fs = require('fs');
const path = require('path');
const h7aCompressionUtil = require('./2k-tools/src/util/h7aCompressionUtil');
const hashUtil = require('./2k-tools/src/util/2kHashUtil');

const IFF_FILE_PATH = './IFFs/teamselectlogo.iff';
const CDF_FILE_PATH = './IFFs/teamselectlogo.cdf';
const OUTPUT_DIR = 'D:\\Reborn\\CH2KRB\\LogoExtract\\Logos';

async function analyzeLogoFiles() {
    console.log('🔍 Starting Logo File Analysis...\n');
    
    // Ensure output directory exists
    if (!fs.existsSync(OUTPUT_DIR)) {
        fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    }
    
    // Read the files
    const iffBuffer = fs.readFileSync(IFF_FILE_PATH);
    const cdfBuffer = fs.readFileSync(CDF_FILE_PATH);
    
    console.log(`📁 IFF File: ${IFF_FILE_PATH} (${iffBuffer.length} bytes)`);
    console.log(`📁 CDF File: ${CDF_FILE_PATH} (${cdfBuffer.length} bytes)\n`);
    
    // Test 1: Try H7A decompression with different shift values
    await test1_H7ADecompression(iffBuffer);
    
    // Test 2: Look for pattern matches between IFF and CDF
    await test2_PatternMatching(iffBuffer, cdfBuffer);
    
    // Test 3: Search for GTF headers in CDF
    await test3_GTFHeaderSearch(cdfBuffer, iffBuffer);
    
    // Test 4: Check for hash values corresponding to team names
    await test4_HashLookup(iffBuffer);
}

async function test1_H7ADecompression(iffBuffer) {
    console.log('🧪 Test 1: H7A Decompression Attempts');
    console.log('=====================================');
    
    const originalMagic = iffBuffer.readUInt32BE(0);
    console.log(`Original magic: 0x${originalMagic.toString(16).toUpperCase()}`);
    console.log('Expected IFF magic: 0xFF3BEF94\n');
    
    // Try different shift values and decompressed sizes
    const shiftValues = [8, 13, 10, 12, 15];
    const possibleSizes = [
        iffBuffer.length * 2,
        iffBuffer.length * 3,
        iffBuffer.length * 4,
        100000,  // Common IFF size
        200000,
        500000
    ];
    
    for (let shift of shiftValues) {
        for (let size of possibleSizes) {
            try {
                console.log(`Trying H7A decompression: shift=${shift}, size=${size}`);
                const decompressed = h7aCompressionUtil.decompress(iffBuffer, size, shift);
                
                if (decompressed && decompressed.length >= 4) {
                    const decompressedMagic = decompressed.readUInt32BE(0);
                    console.log(`  → Decompressed magic: 0x${decompressedMagic.toString(16).toUpperCase()}`);
                    
                    if (decompressedMagic === 0xFF3BEF94) {
                        console.log(`  ✅ SUCCESS! Found valid IFF magic with shift=${shift}, size=${size}`);
                        
                        // Save the decompressed IFF
                        const outputPath = path.join(OUTPUT_DIR, 'decompressed_teamselectlogo.iff');
                        fs.writeFileSync(outputPath, decompressed);
                        console.log(`  💾 Saved decompressed IFF to: ${outputPath}`);
                        return decompressed;
                    }
                }
            } catch (err) {
                // Silently continue - most attempts will fail
            }
        }
    }
    
    console.log('❌ No valid IFF magic found through H7A decompression\n');
    return null;
}

async function test2_PatternMatching(iffBuffer, cdfBuffer) {
    console.log('🧪 Test 2: Pattern Matching Analysis');
    console.log('===================================');
    
    // Look for offset patterns in IFF that might point to CDF locations
    console.log('Analyzing IFF structure for offset patterns...');
    
    // Check the IFF header structure we saw in the hex dump
    const headerValues = [];
    for (let i = 0; i < Math.min(256, iffBuffer.length); i += 4) {
        if (i + 4 <= iffBuffer.length) {
            const value = iffBuffer.readUInt32BE(i);
            headerValues.push({ offset: i, value, hex: value.toString(16).padStart(8, '0') });
        }
    }
    
    console.log('IFF Header Analysis:');
    headerValues.slice(0, 20).forEach(item => {
        console.log(`  Offset 0x${item.offset.toString(16).padStart(3, '0')}: 0x${item.hex} (${item.value})`);
    });
    
    // Look for values that might be offsets into the CDF file
    const potentialOffsets = headerValues.filter(item => 
        item.value > 0 && 
        item.value < cdfBuffer.length && 
        item.value % 16 === 0  // Aligned offsets are common
    );
    
    console.log(`\nFound ${potentialOffsets.length} potential CDF offsets:`);
    potentialOffsets.slice(0, 10).forEach(item => {
        console.log(`  IFF[0x${item.offset.toString(16)}] → CDF[0x${item.hex}] (${item.value})`);
    });
    
    console.log();
}

async function test3_GTFHeaderSearch(cdfBuffer, iffBuffer) {
    console.log('🧪 Test 3: GTF Header Search in CDF');
    console.log('==================================');
    
    // GTF files typically start with specific magic numbers
    const gtfMagics = [
        0x01080000,  // Common GTF magic from the code
        0x00000801,  // Little endian version
    ];
    
    const gtfLocations = [];
    
    for (let magic of gtfMagics) {
        console.log(`Searching for GTF magic: 0x${magic.toString(16).toUpperCase()}`);
        
        for (let i = 0; i < cdfBuffer.length - 4; i++) {
            const value = cdfBuffer.readUInt32BE(i);
            if (value === magic) {
                gtfLocations.push({ offset: i, magic });
                console.log(`  ✅ Found GTF magic at CDF offset: 0x${i.toString(16)} (${i})`);
            }
        }
    }
    
    if (gtfLocations.length > 0) {
        console.log(`\nFound ${gtfLocations.length} potential GTF headers!`);
        
        // Try to extract some GTF data around these locations
        for (let i = 0; i < Math.min(5, gtfLocations.length); i++) {
            const location = gtfLocations[i];
            await extractPotentialGTF(cdfBuffer, location.offset, i);
        }
    } else {
        console.log('❌ No GTF magic numbers found in CDF file');
    }
    
    console.log();
}

async function extractPotentialGTF(cdfBuffer, offset, index) {
    try {
        // Try different GTF sizes (textures can vary widely)
        const sizes = [1024, 4096, 16384, 65536, 262144, 1048576];
        
        for (let size of sizes) {
            if (offset + size <= cdfBuffer.length) {
                const gtfData = cdfBuffer.slice(offset, offset + size);
                const outputPath = path.join(OUTPUT_DIR, `potential_logo_${index}_size_${size}.gtf`);
                fs.writeFileSync(outputPath, gtfData);
                
                // Try to convert to DDS using the existing tools
                await tryGTFToDDS(outputPath, `logo_${index}_${size}`);
            }
        }
    } catch (err) {
        console.log(`Error extracting GTF at offset 0x${offset.toString(16)}: ${err.message}`);
    }
}

async function tryGTFToDDS(gtfPath, baseName) {
    try {
        const { exec } = require('child_process');
        const ddsPath = path.join(OUTPUT_DIR, `${baseName}.dds`);
        
        // Use the GTF to DDS converter from the project
        const gtfExePath = path.join(__dirname, '2k-tools', 'lib', 'gtf2dds.exe');
        
        return new Promise((resolve) => {
            exec(`"${gtfExePath}" -v -z -o "${ddsPath}" "${gtfPath}"`, (err, stdout, stderr) => {
                if (!err && fs.existsSync(ddsPath)) {
                    console.log(`  ✅ Successfully converted to DDS: ${baseName}.dds`);
                } else {
                    // Clean up the GTF file if conversion failed
                    try { fs.unlinkSync(gtfPath); } catch {}
                }
                resolve();
            });
        });
    } catch (err) {
        console.log(`Conversion error: ${err.message}`);
    }
}

async function test4_HashLookup(iffBuffer) {
    console.log('🧪 Test 4: Hash Value Analysis');
    console.log('=============================');
    
    try {
        // Wait for hash lookup to be ready
        await hashUtil.hashLookupPromise;
        console.log('Hash lookup system initialized');
        
        // Extract potential hash values from IFF
        const hashValues = [];
        for (let i = 0; i < iffBuffer.length - 4; i += 4) {
            const value = iffBuffer.readUInt32BE(i);
            hashValues.push({ offset: i, hash: value });
        }
        
        console.log(`Checking ${hashValues.length} potential hash values...`);
        
        let foundMatches = 0;
        for (let item of hashValues.slice(0, 100)) { // Check first 100 to avoid overwhelming
            try {
                const result = await hashUtil.hashLookup(item.hash);
                if (result && result.str) {
                    console.log(`  ✅ Hash match at 0x${item.offset.toString(16)}: ${item.hash.toString(16)} → "${result.str}"`);
                    foundMatches++;
                }
            } catch (err) {
                // Continue silently
            }
        }
        
        if (foundMatches === 0) {
            console.log('❌ No hash matches found in hash lookup table');
        } else {
            console.log(`✅ Found ${foundMatches} hash matches!`);
        }
        
    } catch (err) {
        console.log(`Hash lookup error: ${err.message}`);
    }
    
    console.log();
}

// Run the analysis
analyzeLogoFiles().then(() => {
    console.log('🎉 Logo file analysis complete!');
    console.log(`📂 Check results in: ${OUTPUT_DIR}`);
}).catch(err => {
    console.error('❌ Analysis failed:', err);
});