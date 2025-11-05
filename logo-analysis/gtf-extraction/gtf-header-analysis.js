const fs = require('fs');
const path = require('path');

// Analyze GTF file structure to understand conversion issues
const logoDir = path.join('D:', 'Reborn', 'CH2KRB', 'LogoExtract', 'Logos');

function analyzeGTFStructure(filename) {
    const filePath = path.join(logoDir, filename);
    if (!fs.existsSync(filePath)) {
        console.log(`File not found: ${filename}`);
        return;
    }
    
    const buffer = fs.readFileSync(filePath);
    console.log(`\n=== Analyzing ${filename} ===`);
    console.log(`Size: ${buffer.length} bytes`);
    
    // GTF header structure analysis
    if (buffer.length >= 32) {
        console.log('\nGTF Header (first 32 bytes):');
        const header = buffer.subarray(0, 32);
        
        for (let i = 0; i < 32; i += 4) {
            const valueBE = header.readUInt32BE(i);
            const valueLE = header.readUInt32LE(i);
            const bytes = Array.from(header.subarray(i, i + 4)).map(b => b.toString(16).padStart(2, '0')).join(' ');
            
            console.log(`  @${i.toString(16).padStart(2, '0')}: ${bytes} | BE=0x${valueBE.toString(16).padStart(8, '0')} | LE=0x${valueLE.toString(16).padStart(8, '0')}`);
        }
        
        // Check if this looks like a proper GTF header
        const magic = header.readUInt32BE(0);
        const magicLE = header.readUInt32LE(0);
        
        if (magic === 0x00000801 || magicLE === 0x01080000) {
            console.log('✓ Valid GTF magic found');
            
            // Try to parse GTF header fields
            console.log('\nGTF Header Fields:');
            
            if (magicLE === 0x01080000) {
                // Little-endian GTF
                console.log('Format: Little-endian GTF');
                const version = header.readUInt8(4);
                const flags = header.readUInt8(5);
                console.log(`  Version: ${version}`);
                console.log(`  Flags: 0x${flags.toString(16)}`);
                
                // Dimensions might be at different offsets
                for (let offset = 8; offset <= 16; offset += 2) {
                    if (offset + 4 <= header.length) {
                        const width = header.readUInt16LE(offset);
                        const height = header.readUInt16LE(offset + 2);
                        if (width > 0 && height > 0 && width <= 4096 && height <= 4096) {
                            console.log(`  Possible dimensions @${offset}: ${width}x${height}`);
                        }
                    }
                }
            } else {
                // Big-endian GTF  
                console.log('Format: Big-endian GTF');
                const version = header.readUInt8(7);
                const flags = header.readUInt8(6);
                console.log(`  Version: ${version}`);
                console.log(`  Flags: 0x${flags.toString(16)}`);
            }
        } else {
            console.log('✗ No valid GTF magic found');
            console.log(`Found: BE=0x${magic.toString(16)}, LE=0x${magicLE.toString(16)}`);
        }
    }
    
    // Look for texture data patterns
    console.log('\nSearching for texture data patterns...');
    
    // Look for repeating patterns that might indicate compressed texture blocks
    const sampleSize = Math.min(1024, buffer.length);
    const sample = buffer.subarray(0, sampleSize);
    
    // Count zero bytes
    let zeroCount = 0;
    for (let i = 0; i < sample.length; i++) {
        if (sample[i] === 0) zeroCount++;
    }
    
    console.log(`Zero bytes in first ${sampleSize}: ${zeroCount} (${(zeroCount/sampleSize*100).toFixed(1)}%)`);
    
    // Look for patterns
    const patterns = new Map();
    for (let i = 0; i < sample.length - 3; i++) {
        const pattern = sample.readUInt32LE(i);
        patterns.set(pattern, (patterns.get(pattern) || 0) + 1);
    }
    
    const sortedPatterns = Array.from(patterns.entries()).sort((a, b) => b[1] - a[1]).slice(0, 5);
    console.log('Most common 4-byte patterns:');
    sortedPatterns.forEach(([pattern, count]) => {
        console.log(`  0x${pattern.toString(16).padStart(8, '0')}: ${count} times`);
    });
    
    return {
        size: buffer.length,
        hasValidMagic: buffer.readUInt32BE(0) === 0x00000801 || buffer.readUInt32LE(0) === 0x01080000,
        zeroPercentage: zeroCount / sampleSize * 100
    };
}

// Analyze different GTF files
console.log('Analyzing extracted GTF files to understand structure...');

const gtfFiles = [
    'extracted_from_decompressed_21381950.bin_gtf0.gtf',
    'extracted_from_decompressed_21381950.bin_gtf4.gtf',
    'extracted_from_decompressed_21381950.bin_gtf12.gtf'
];

const results = [];
for (const filename of gtfFiles) {
    const result = analyzeGTFStructure(filename);
    if (result) {
        results.push({ filename, ...result });
    }
}

console.log('\n=== SUMMARY ===');
results.forEach(result => {
    console.log(`${result.filename}:`);
    console.log(`  Size: ${result.size} bytes`);
    console.log(`  Valid GTF: ${result.hasValidMagic ? '✓' : '✗'}`);
    console.log(`  Zero %: ${result.zeroPercentage.toFixed(1)}%`);
});

console.log('\n=== RECOMMENDATIONS ===');
const validGTFs = results.filter(r => r.hasValidMagic);
if (validGTFs.length > 0) {
    console.log('✓ Found valid GTF files with correct magic numbers');
    console.log('The conversion failure might be due to:');
    console.log('1. Incorrect GTF header structure (missing required fields)');
    console.log('2. Unsupported texture format within the GTF');
    console.log('3. Big-endian vs little-endian issues');
    console.log('4. GTF version compatibility');
} else {
    console.log('✗ No valid GTF magic numbers found');
    console.log('This suggests the extracted data is not in standard GTF format');
    console.log('The textures might be in a custom or modified format');
}