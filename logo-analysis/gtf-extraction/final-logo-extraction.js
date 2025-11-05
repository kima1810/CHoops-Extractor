const fs = require('fs');
const path = require('path');

// Import the CHoops H7A utility
const h7aCompressionUtil = require('./2k-tools/src/util/h7aCompressionUtil');

// Read files
const cdfFilePath = path.join(__dirname, 'IFFs', 'teamselectlogo.cdf');
const mappingPath = path.join(__dirname, 'logo-mapping.json');

const logoMapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));

// Output directory
const outputDir = path.join('D:', 'Reborn', 'CH2KRB', 'LogoExtract', 'Logos');
if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
}

console.log(`Decompressing CDF and extracting all 520 logos`);
console.log(`Input: ${cdfFilePath}`);
console.log(`Output: ${outputDir}`);

async function extractAllLogos() {
    try {
        console.log('\n=== Step 1: Decompressing H7A CDF file ===');
        
        // Read the compressed CDF file
        const compressedData = fs.readFileSync(cdfFilePath);
        console.log(`Compressed CDF size: ${compressedData.length} bytes`);
        
        // Decompress using CHoops H7A utility
        console.log('Attempting H7A decompression...');
        const decompressedData = await h7aCompressionUtil.decompress(compressedData);
        
        console.log(`Decompressed size: ${decompressedData.length} bytes`);
        console.log(`Compression ratio: ${(compressedData.length / decompressedData.length * 100).toFixed(1)}%`);
        
        // Save decompressed data for analysis
        const decompressedPath = path.join(__dirname, 'teamselectlogo_decompressed.bin');
        fs.writeFileSync(decompressedPath, decompressedData);
        console.log(`Saved decompressed data to: ${decompressedPath}`);
        
        console.log('\n=== Step 2: Analyzing decompressed data ===');
        
        // Search for GTF headers in decompressed data
        const gtfHeaders = [];
        const gtfMagic = 0x01080000; // GTF magic (little-endian)
        
        for (let i = 0; i <= decompressedData.length - 4; i += 4) { // Align to 4-byte boundaries
            const magic = decompressedData.readUInt32LE(i);
            if (magic === gtfMagic) {
                gtfHeaders.push({
                    offset: i,
                    magic: magic
                });
            }
        }
        
        console.log(`Found ${gtfHeaders.length} GTF headers in decompressed data:`);
        gtfHeaders.forEach((header, i) => {
            console.log(`  GTF[${i}]: offset 0x${header.offset.toString(16)} (${header.offset})`);
        });
        
        if (gtfHeaders.length === 0) {
            console.log('No GTF headers found in decompressed data. Checking alignment...');
            
            // Try unaligned search
            for (let i = 0; i <= decompressedData.length - 4; i++) {
                const magic = decompressedData.readUInt32LE(i);
                if (magic === gtfMagic) {
                    console.log(`  Unaligned GTF at offset 0x${i.toString(16)} (${i})`);
                    gtfHeaders.push({ offset: i, magic: magic });
                    if (gtfHeaders.length >= 10) break; // Don't spam too much
                }
            }
        }
        
        console.log('\n=== Step 3: Extracting GTF textures ===');
        
        if (gtfHeaders.length > 0) {
            // Calculate GTF file sizes
            for (let i = 0; i < gtfHeaders.length; i++) {
                const startOffset = gtfHeaders[i].offset;
                const endOffset = i < gtfHeaders.length - 1 ? gtfHeaders[i + 1].offset : decompressedData.length;
                const size = endOffset - startOffset;
                
                gtfHeaders[i].size = size;
                console.log(`GTF[${i}]: offset 0x${startOffset.toString(16)}, size ${size} bytes`);
                
                // Extract the GTF file
                const gtfData = decompressedData.subarray(startOffset, startOffset + size);
                const gtfFilePath = path.join(outputDir, `extracted_gtf_${i}.gtf`);
                fs.writeFileSync(gtfFilePath, gtfData);
                console.log(`  Saved: ${gtfFilePath}`);
                
                // Try to convert to DDS
                try {
                    const { exec } = require('child_process');
                    const ddsPath = path.join(outputDir, `extracted_gtf_${i}.dds`);
                    const gtf2ddsPath = path.join(__dirname, 'gtf2dds.exe');
                    
                    if (fs.existsSync(gtf2ddsPath)) {
                        exec(`"${gtf2ddsPath}" "${gtfFilePath}" "${ddsPath}"`, (error, stdout, stderr) => {
                            if (error) {
                                console.log(`    GTF->DDS conversion failed: ${error.message}`);
                            } else {
                                console.log(`    Converted to DDS: ${ddsPath}`);
                            }
                        });
                    }
                } catch (convError) {
                    console.log(`    GTF->DDS conversion error: ${convError.message}`);
                }
            }
        }
        
        console.log('\n=== Step 4: Mapping logos to textures ===');
        
        // Group logos by their hash2 identifiers
        const offsetGroups = {};
        logoMapping.forEach(logo => {
            const key = logo.hash2.toString(16);
            if (!offsetGroups[key]) offsetGroups[key] = [];
            offsetGroups[key].push(logo);
        });
        
        console.log('Logo groups:');
        Object.entries(offsetGroups).forEach(([offset, logos]) => {
            console.log(`  Group 0x${offset}: ${logos.length} logos`);
            console.log(`    Sample logos: ${logos.slice(0, 5).map(l => l.fileName).join(', ')}`);
        });
        
        // If we have 3 groups and found GTF textures, try to correlate them
        const groupKeys = Object.keys(offsetGroups).sort();
        if (groupKeys.length === 3 && gtfHeaders.length >= 3) {
            console.log('\nAttempting to correlate logo groups with GTF textures:');
            
            groupKeys.forEach((groupKey, i) => {
                if (i < gtfHeaders.length) {
                    const group = offsetGroups[groupKey];
                    console.log(`  Group 0x${groupKey} (${group.length} logos) -> GTF[${i}]`);
                    
                    // Create individual logo files pointing to the correct GTF
                    group.forEach(logo => {
                        const logoInfo = {
                            fileName: logo.fileName,
                            gtfIndex: i,
                            gtfOffset: gtfHeaders[i].offset,
                            gtfSize: gtfHeaders[i].size,
                            sourceGroup: groupKey
                        };
                        
                        const logoInfoPath = path.join(outputDir, `${logo.fileName}_info.json`);
                        fs.writeFileSync(logoInfoPath, JSON.stringify(logoInfo, null, 2));
                    });
                }
            });
            
            console.log(`\nCreated info files for all ${logoMapping.length} logos in: ${outputDir}`);
        }
        
        return {
            decompressedSize: decompressedData.length,
            gtfHeaders: gtfHeaders,
            offsetGroups: offsetGroups
        };
        
    } catch (error) {
        console.error('H7A decompression failed:', error.message);
        console.log('Error details:', error);
        
        // Try alternative approach - manual decompression detection
        console.log('\n=== Attempting manual analysis ===');
        
        const compressedData = fs.readFileSync(cdfFilePath);
        
        console.log('First 32 bytes of CDF:');
        const header = compressedData.subarray(0, 32);
        console.log(Array.from(header).map(b => b.toString(16).padStart(2, '0')).join(' '));
        
        return null;
    }
}

// Run extraction
extractAllLogos().then(result => {
    if (result) {
        console.log('\n=== SUCCESS ===');
        console.log(`Extracted ${result.gtfHeaders.length} GTF textures`);
        console.log(`Mapped ${logoMapping.length} logo files`);
        console.log(`Decompressed ${result.decompressedSize} bytes from H7A format`);
    } else {
        console.log('\n=== NEED ALTERNATIVE APPROACH ===');
        console.log('H7A decompression failed - may need to use different decompression method');
    }
}).catch(error => {
    console.error('Extraction failed:', error);
});