const fs = require('fs');
const path = require('path');

// Read the IFF file
const iffFilePath = path.join(__dirname, 'IFFs', 'teamselectlogo.iff');
const iffBuffer = fs.readFileSync(iffFilePath);

console.log(`Analyzing IFF file: ${iffFilePath}`);
console.log(`File size: ${iffBuffer.length} bytes`);

function analyzeIFFStructure() {
    console.log('\n=== IFF Structure Analysis ===');
    
    // Read the header (first 16 bytes based on NBA2K9 documentation)
    if (iffBuffer.length < 16) {
        console.log('File too small for IFF header');
        return;
    }
    
    const magic = iffBuffer.readUInt32BE(0);
    const unk1 = iffBuffer.readUInt32BE(4);
    const dwDataFileCount = iffBuffer.readUInt32BE(8);
    const dwSubFileCount = iffBuffer.readUInt32BE(12);
    
    console.log(`Magic: 0x${magic.toString(16).toUpperCase()}`);
    console.log(`Unknown1: 0x${unk1.toString(16).toUpperCase()}`);
    console.log(`Data File Count: ${dwDataFileCount}`);
    console.log(`Sub File Count: ${dwSubFileCount}`);
    
    // Verify this is Type 2 IFF
    if (magic === 0xF0985030) {
        console.log('✓ Confirmed Type 2 IFF format (NBA2K9 style)');
    } else if (magic === 0xFF3BEF94) {
        console.log('! Type 1 IFF format detected (different from expected)');
    } else {
        console.log(`! Unknown IFF magic: 0x${magic.toString(16).toUpperCase()}`);
    }
    
    console.log('\n=== Data File Entries ===');
    
    // Calculate where data file entries start (after 16-byte header)
    let offset = 16;
    
    // Each data file entry is 8 bytes according to NBA2K9 docs
    console.log(`Reading ${dwDataFileCount} data file entries starting at offset ${offset}...`);
    
    for (let i = 0; i < dwDataFileCount && offset + 8 <= iffBuffer.length; i++) {
        const hash = iffBuffer.readUInt32BE(offset);
        const unk = iffBuffer.readUInt32BE(offset + 4);
        
        console.log(`Data File [${i}]: Hash=0x${hash.toString(16).toUpperCase()}, Unk=0x${unk.toString(16).toUpperCase()}`);
        offset += 8;
    }
    
    console.log('\n=== Sub File Entries ===');
    
    // Sub file entries come after data file entries
    console.log(`Reading ${dwSubFileCount} sub file entries starting at offset ${offset}...`);
    
    const subFiles = [];
    
    // Each sub file entry is 16 bytes according to NBA2K9 docs  
    for (let i = 0; i < dwSubFileCount && offset + 16 <= iffBuffer.length; i++) {
        const hash = iffBuffer.readUInt32BE(offset);
        const unk1 = iffBuffer.readUInt32BE(offset + 4);
        const dataFileIndex = iffBuffer.readUInt32BE(offset + 8);
        const dataOffset = iffBuffer.readUInt32BE(offset + 12);
        
        subFiles.push({
            index: i,
            hash: hash,
            unk1: unk1,
            dataFileIndex: dataFileIndex,
            dataOffset: dataOffset
        });
        
        console.log(`Sub File [${i}]: Hash=0x${hash.toString(16).toUpperCase()}, Unk1=0x${unk1.toString(16).toUpperCase()}, DataFile=${dataFileIndex}, Offset=0x${dataOffset.toString(16).toUpperCase()}`);
        offset += 16;
    }
    
    console.log(`\nFinished reading structure. Next offset would be: ${offset}`);
    console.log(`Remaining bytes in file: ${iffBuffer.length - offset}`);
    
    // Look for any remaining data that might contain filenames or other info
    if (offset < iffBuffer.length) {
        console.log('\n=== Remaining Data Analysis ===');
        console.log('Checking for filename strings or other structured data...');
        
        // Look for null-terminated strings in remaining data
        const remainingData = iffBuffer.subarray(offset);
        const strings = [];
        let currentString = '';
        
        for (let i = 0; i < remainingData.length; i++) {
            const byte = remainingData[i];
            if (byte === 0) {
                if (currentString.length > 3) { // Only interested in strings longer than 3 chars
                    strings.push(currentString);
                }
                currentString = '';
            } else if (byte >= 32 && byte <= 126) { // Printable ASCII
                currentString += String.fromCharCode(byte);
            } else {
                if (currentString.length > 3) {
                    strings.push(currentString);
                }
                currentString = '';
            }
        }
        
        if (strings.length > 0) {
            console.log('Found potential filename strings:');
            strings.forEach((str, idx) => {
                if (str.includes('logo') || str.includes('.') || str.length > 10) {
                    console.log(`  [${idx}]: "${str}"`);
                }
            });
        }
        
        // Look for patterns that might indicate more structure
        console.log('\nSearching for additional structural patterns...');
        
        // Look for 4-byte aligned values that could be offsets or sizes
        for (let i = 0; i < remainingData.length - 4; i += 4) {
            const value = remainingData.readUInt32BE(i);
            // Look for values that could be reasonable file sizes or offsets
            if (value > 1000 && value < 50000000) {
                console.log(`Potential offset/size at ${offset + i}: 0x${value.toString(16).toUpperCase()} (${value})`);
            }
        }
    }
    
    return {
        magic,
        dwDataFileCount,
        dwSubFileCount,
        subFiles,
        structureEnd: offset
    };
}

// Run the analysis
try {
    const analysis = analyzeIFFStructure();
    
    console.log('\n=== Summary ===');
    console.log(`IFF Magic: 0x${analysis.magic.toString(16).toUpperCase()}`);
    console.log(`Data Files: ${analysis.dwDataFileCount}`);
    console.log(`Sub Files: ${analysis.dwSubFileCount}`);
    console.log(`Structure ends at offset: ${analysis.structureEnd}`);
    console.log(`Total file size: ${iffBuffer.length}`);
    
    if (analysis.subFiles.length > 0) {
        console.log('\nSub files appear to reference:');
        analysis.subFiles.forEach(sf => {
            console.log(`  Hash 0x${sf.hash.toString(16).toUpperCase()} -> Data file ${sf.dataFileIndex} at offset 0x${sf.dataOffset.toString(16).toUpperCase()}`);
        });
    }
    
} catch (error) {
    console.error('Analysis failed:', error);
    console.log(`Error occurred at file position, stopping safely.`);
}