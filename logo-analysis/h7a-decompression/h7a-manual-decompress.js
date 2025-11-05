const fs = require('fs');
const path = require('path');

// Read the CDF file - adjusted path for organized structure
const cdfFilePath = path.join(__dirname, '..', '..', 'IFFs', 'teamselectlogo.cdf');
const cdfBuffer = fs.readFileSync(cdfFilePath);

// Output directory
const outputDir = path.join('D:', 'Reborn', 'CH2KRB', 'LogoExtract', 'Logos');
if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
}

console.log(`H7A Decompression Analysis and Manual Extraction`);
console.log(`CDF file size: ${cdfBuffer.length} bytes`);

function analyzeH7AHeader() {
    console.log('\n=== H7A Header Analysis ===');
    
    // H7A format analysis based on the first 32 bytes
    console.log('First 32 bytes:');
    const header = cdfBuffer.subarray(0, 32);
    
    for (let i = 0; i < 32; i += 4) {
        const valueBE = header.readUInt32BE(i);
        const valueLE = header.readUInt32LE(i);
        const bytes = Array.from(header.subarray(i, i + 4)).map(b => b.toString(16).padStart(2, '0')).join(' ');
        
        console.log(`  @${i.toString(16).padStart(2, '0')}: ${bytes} | BE=${valueBE.toString().padStart(10)} (0x${valueBE.toString(16).padStart(8, '0')}) | LE=${valueLE.toString().padStart(10)} (0x${valueLE.toString(16).padStart(8, '0')})`);
    }
    
    // Common H7A header patterns:
    // Byte 0: Usually 0x0E (compression type/version)
    // Next few bytes: Often contain size information
    
    console.log('\n=== Extracting Size Information ===');
    
    // Try different interpretations of the size fields
    const possibleSizes = [
        { name: 'LE @0x04', value: header.readUInt32LE(4) },
        { name: 'BE @0x04', value: header.readUInt32BE(4) },
        { name: 'LE @0x08', value: header.readUInt32LE(8) },
        { name: 'BE @0x08', value: header.readUInt32BE(8) },
        { name: 'LE @0x0C', value: header.readUInt32LE(12) },
        { name: 'BE @0x0C', value: header.readUInt32BE(12) },
    ];
    
    console.log('Possible decompressed sizes:');
    possibleSizes.forEach(size => {
        if (size.value > 0 && size.value < 100000000) { // Reasonable size range
            console.log(`  ${size.name}: ${size.value} bytes (${(size.value / 1024 / 1024).toFixed(2)} MB)`);
        }
    });
    
    // Based on the header pattern, let's try the most likely candidates
    console.log('\n=== Attempting H7A Decompression ===');
    
    // The header shows: 0e 48 37 c3 00 00 00 b0 00 00 00 5e 00 00 00 08
    // This suggests:
    // - 0x0E: H7A version/type
    // - Size might be at offset 0x04 or combined from multiple fields
    
    const candidateSizes = [
        176, // 0xb0 from offset 0x07
        94,  // 0x5e from offset 0x0B
        11616829, // Combined interpretation
        // Let's also try some computed values
        cdfBuffer.length * 2, // Common compression ratios
        cdfBuffer.length * 3,
        cdfBuffer.length * 4
    ];
    
    for (const decompressedSize of candidateSizes) {
        console.log(`\nTrying decompressed size: ${decompressedSize} bytes`);
        
        try {
            const result = h7aDecompress(cdfBuffer, decompressedSize);
            if (result && result.length > 0) {
                console.log(`  ✓ Success! Decompressed ${result.length} bytes`);
                
                // Save the result
                const outputPath = path.join(outputDir, `decompressed_${decompressedSize}.bin`);
                fs.writeFileSync(outputPath, result);
                console.log(`  Saved to: ${outputPath}`);
                
                // Look for GTF headers in the result
                const gtfCount = countGTFHeaders(result);
                console.log(`  Found ${gtfCount} GTF headers`);
                
                if (gtfCount > 0) {
                    console.log(`  🎉 This looks promising!`);
                    return { decompressedData: result, size: decompressedSize };
                }
            }
        } catch (error) {
            console.log(`  ✗ Failed: ${error.message}`);
        }
    }
    
    return null;
}

function h7aDecompress(buf, decompressedSize, shiftAmount = 0x8) {
    // Skip the header - H7A data typically starts after some header bytes
    // Let's try starting from different offsets
    const startOffsets = [0x18, 0x20, 0x1C, 0x10];
    
    for (const startOffset of startOffsets) {
        try {
            console.log(`    Trying start offset: 0x${startOffset.toString(16)}`);
            
            let currentCompressedOffset = startOffset;
            let currentDecompressedOffset = 0;
            let output = Buffer.alloc(decompressedSize);

            while (currentDecompressedOffset < decompressedSize && currentCompressedOffset < buf.length) {
                let descriptor = buf[currentCompressedOffset++];

                for (let bitOffset = 0; bitOffset <= 7; bitOffset++) {
                    if (currentDecompressedOffset >= decompressedSize) {
                        break;
                    }

                    if ((descriptor & 1) > 0) {
                        if (currentCompressedOffset + 1 >= buf.length) break;
                        
                        let lookbackLength = buf[currentCompressedOffset++];
                        let sequenceLength = buf[currentCompressedOffset++];

                        lookbackLength = (lookbackLength << 8) + sequenceLength;
                        
                        sequenceLength = (lookbackLength >> shiftAmount & (1 << 15 - shiftAmount + 1) - 1) + 2;
                        lookbackLength = lookbackLength >> 0 & (1 << (shiftAmount - 1) + 1) - 1;

                        for (let i = 0; i <= sequenceLength; i++) {
                            if (currentDecompressedOffset >= decompressedSize) break;
                            if (currentDecompressedOffset - lookbackLength < 0) break;
                            
                            output[currentDecompressedOffset] = output[currentDecompressedOffset - lookbackLength];
                            currentDecompressedOffset += 1;
                        }
                    } else {
                        if (currentCompressedOffset >= buf.length) break;
                        output[currentDecompressedOffset++] = buf[currentCompressedOffset++];
                    }

                    descriptor >>= 1;
                }
            }

            // Check if we got reasonable data
            if (currentDecompressedOffset > decompressedSize * 0.1) { // At least 10% filled
                console.log(`      Decompressed ${currentDecompressedOffset} bytes (${(currentDecompressedOffset/decompressedSize*100).toFixed(1)}%)`);
                return output.subarray(0, currentDecompressedOffset);
            }
            
        } catch (error) {
            console.log(`      Error with offset 0x${startOffset.toString(16)}: ${error.message}`);
        }
    }
    
    throw new Error('All start offsets failed');
}

function countGTFHeaders(buffer) {
    let count = 0;
    const gtfMagic = 0x01080000; // GTF magic (little-endian)
    
    for (let i = 0; i <= buffer.length - 4; i += 4) {
        const magic = buffer.readUInt32LE(i);
        if (magic === gtfMagic) {
            count++;
        }
    }
    
    return count;
}

// Run analysis
try {
    const result = analyzeH7AHeader();
    
    if (result) {
        console.log('\n=== SUCCESS ===');
        console.log(`Successfully decompressed ${result.size} bytes`);
        console.log(`Decompressed data saved and ready for GTF extraction`);
    } else {
        console.log('\n=== NEED MORE ANALYSIS ===');
        console.log('Could not determine correct decompression parameters');
        console.log('May need to analyze the H7A format more carefully or try different approaches');
    }
    
} catch (error) {
    console.error('Analysis failed:', error);
}