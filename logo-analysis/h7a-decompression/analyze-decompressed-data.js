const fs = require('fs');
const path = require('path');

// Analyze the decompressed files to find GTF data
const logoDir = path.join('D:', 'Reborn', 'CH2KRB', 'LogoExtract', 'Logos');

const decompressedFiles = [
    'decompressed_11616829.bin',
    'decompressed_21381950.bin', 
    'decompressed_32072925.bin',
    'decompressed_42763900.bin'
];

console.log('Analyzing decompressed files for GTF headers and texture data...');

function analyzeDecompressedFile(filename) {
    const filePath = path.join(logoDir, filename);
    if (!fs.existsSync(filePath)) {
        console.log(`File not found: ${filename}`);
        return;
    }
    
    const buffer = fs.readFileSync(filePath);
    console.log(`\n=== Analyzing ${filename} ===`);
    console.log(`Size: ${buffer.length} bytes (${(buffer.length / 1024 / 1024).toFixed(2)} MB)`);
    
    // Look for GTF headers with different byte orders
    const gtfMagicLE = 0x01080000;  // Little-endian
    const gtfMagicBE = 0x00000801;  // Big-endian
    
    const gtfHeaders = [];
    
    // Search for GTF headers
    for (let i = 0; i <= buffer.length - 4; i++) {
        const magicLE = buffer.readUInt32LE(i);
        const magicBE = buffer.readUInt32BE(i);
        
        if (magicLE === gtfMagicLE || magicBE === gtfMagicBE) {
            gtfHeaders.push({
                offset: i,
                magic: magicLE === gtfMagicLE ? magicLE : magicBE,
                endian: magicLE === gtfMagicLE ? 'LE' : 'BE'
            });
        }
    }
    
    console.log(`Found ${gtfHeaders.length} GTF headers:`);
    gtfHeaders.forEach((header, i) => {
        console.log(`  GTF[${i}]: offset 0x${header.offset.toString(16)} (${header.offset}) - ${header.endian}`);
    });
    
    // Look for any recognizable patterns or signatures
    console.log('\nFirst 64 bytes:');
    const headerBytes = buffer.subarray(0, Math.min(64, buffer.length));
    for (let i = 0; i < headerBytes.length; i += 16) {
        const line = headerBytes.subarray(i, Math.min(i + 16, headerBytes.length));
        const hex = Array.from(line).map(b => b.toString(16).padStart(2, '0')).join(' ');
        const ascii = Array.from(line).map(b => (b >= 32 && b <= 126) ? String.fromCharCode(b) : '.').join('');
        console.log(`  ${i.toString(16).padStart(4, '0')}: ${hex.padEnd(47)} | ${ascii}`);
    }
    
    // Check for other texture format signatures
    console.log('\nSearching for other texture signatures...');
    
    const signatures = [
        { name: 'DDS', pattern: [0x44, 0x44, 0x53, 0x20] },      // "DDS "
        { name: 'PS3 GTF', pattern: [0x00, 0x00, 0x08, 0x01] },  // GTF big-endian
        { name: 'TXTR', pattern: [0x54, 0x58, 0x54, 0x52] },     // "TXTR"
    ];
    
    signatures.forEach(sig => {
        console.log(`\nSearching for ${sig.name} signatures:`);
        let count = 0;
        
        for (let i = 0; i <= buffer.length - sig.pattern.length && count < 10; i++) {
            let match = true;
            for (let j = 0; j < sig.pattern.length; j++) {
                if (buffer[i + j] !== sig.pattern[j]) {
                    match = false;
                    break;
                }
            }
            
            if (match) {
                console.log(`  Found at offset 0x${i.toString(16)} (${i})`);
                
                // Show context around the signature
                const contextStart = Math.max(0, i - 8);
                const contextEnd = Math.min(buffer.length, i + 24);
                const context = buffer.subarray(contextStart, contextEnd);
                const contextHex = Array.from(context).map(b => b.toString(16).padStart(2, '0')).join(' ');
                console.log(`    Context: ${contextHex}`);
                
                count++;
            }
        }
        
        if (count === 0) {
            console.log(`  No ${sig.name} signatures found`);
        }
    });
    
    // If we found GTF headers, try to extract them
    if (gtfHeaders.length > 0) {
        console.log(`\n=== Extracting GTF files from ${filename} ===`);
        
        for (let i = 0; i < gtfHeaders.length; i++) {
            const header = gtfHeaders[i];
            const nextOffset = i < gtfHeaders.length - 1 ? gtfHeaders[i + 1].offset : buffer.length;
            const gtfSize = nextOffset - header.offset;
            
            console.log(`Extracting GTF[${i}]: offset 0x${header.offset.toString(16)}, size ${gtfSize} bytes`);
            
            const gtfData = buffer.subarray(header.offset, header.offset + gtfSize);
            const outputPath = path.join(logoDir, `extracted_from_${filename}_gtf${i}.gtf`);
            fs.writeFileSync(outputPath, gtfData);
            
            console.log(`  Saved: ${outputPath}`);
            
            // Try to convert to DDS
            try {
                const { exec } = require('child_process');
                const ddsPath = path.join(logoDir, `extracted_from_${filename}_gtf${i}.dds`);
                const gtf2ddsPath = path.join(__dirname, 'gtf2dds.exe');
                
                if (fs.existsSync(gtf2ddsPath)) {
                    exec(`"${gtf2ddsPath}" "${outputPath}" "${ddsPath}"`, (error, stdout, stderr) => {
                        if (error) {
                            console.log(`    GTF->DDS conversion failed: ${error.message}`);
                        } else {
                            console.log(`    ✓ Converted to DDS: ${ddsPath}`);
                        }
                    });
                }
            } catch (convError) {
                console.log(`    Conversion error: ${convError.message}`);
            }
        }
    }
    
    return gtfHeaders.length;
}

// Analyze all decompressed files
let totalGTFsFound = 0;

for (const filename of decompressedFiles) {
    const gtfCount = analyzeDecompressedFile(filename);
    totalGTFsFound += gtfCount;
}

console.log(`\n=== SUMMARY ===`);
console.log(`Total GTF headers found across all decompressed files: ${totalGTFsFound}`);

if (totalGTFsFound === 0) {
    console.log('\n=== ALTERNATIVE APPROACH NEEDED ===');
    console.log('No GTF headers found in decompressed data.');
    console.log('This suggests either:');
    console.log('1. The H7A decompression parameters are incorrect');
    console.log('2. The data uses a different compression format');
    console.log('3. The GTF data is embedded differently than expected');
    console.log('\nLet\'s try examining the original compressed data for clues...');
    
    // Look for any GTF signatures in the original compressed file
    const cdfPath = path.join(__dirname, 'IFFs', 'teamselectlogo.cdf');
    const cdfBuffer = fs.readFileSync(cdfPath);
    
    console.log(`\nSearching original CDF file (${cdfBuffer.length} bytes) for GTF signatures:`);
    
    let found = false;
    for (let i = 0; i <= cdfBuffer.length - 4; i++) {
        const magicLE = cdfBuffer.readUInt32LE(i);
        const magicBE = cdfBuffer.readUInt32BE(i);
        
        if (magicLE === 0x01080000 || magicBE === 0x01080000) {
            console.log(`  GTF signature at offset 0x${i.toString(16)} (${i})`);
            found = true;
            
            if (i > 5) break; // Don't spam too much
        }
    }
    
    if (!found) {
        console.log('  No GTF signatures in original CDF either');
    }
}