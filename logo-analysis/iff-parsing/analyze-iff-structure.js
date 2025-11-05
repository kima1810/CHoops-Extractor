const fs = require('fs');
const path = require('path');

// Read the IFF file
const iffFilePath = path.join(__dirname, 'IFFs', 'teamselectlogo.iff');
const iffBuffer = fs.readFileSync(iffFilePath);

console.log(`Analyzing IFF structure and extracting strings: ${iffFilePath}`);
console.log(`File size: ${iffBuffer.length} bytes`);

function analyzeAndExtractStrings() {
    console.log('\n=== IFF Header Analysis ===');
    
    // Read header
    const magic = iffBuffer.readUInt32BE(0);
    const unk1 = iffBuffer.readUInt32BE(4);
    const dwDataFileCount = iffBuffer.readUInt32BE(8);
    const dwSubFileCount = iffBuffer.readUInt32BE(12);
    
    console.log(`Magic: 0x${magic.toString(16).toUpperCase()}`);
    console.log(`Data File Count: ${dwDataFileCount}`);
    console.log(`Sub File Count: ${dwSubFileCount}`);
    
    console.log('\n=== Raw Data Analysis ===');
    
    let offset = 16;
    const dataEntries = [];
    
    // Read all data file entries as raw data
    for (let i = 0; i < dwDataFileCount && offset + 8 <= iffBuffer.length; i++) {
        const entry = {
            index: i,
            offset: offset,
            hash1: iffBuffer.readUInt32BE(offset),
            hash2: iffBuffer.readUInt32BE(offset + 4),
            bytes: Array.from(iffBuffer.subarray(offset, offset + 8))
        };
        
        dataEntries.push(entry);
        offset += 8;
    }
    
    console.log(`Read ${dataEntries.length} data entries, next offset: ${offset}`);
    console.log(`Remaining bytes: ${iffBuffer.length - offset}`);
    
    // Look for patterns in the data
    console.log('\n=== Pattern Analysis ===');
    
    // Check if this might be concatenated strings
    const remainingData = iffBuffer.subarray(offset);
    
    // Try to find ASCII strings in the remaining data
    let asciiStrings = [];
    let currentString = '';
    
    for (let i = 0; i < remainingData.length; i++) {
        const byte = remainingData[i];
        if (byte >= 32 && byte <= 126) { // Printable ASCII
            currentString += String.fromCharCode(byte);
        } else if (byte === 0 || byte === 10 || byte === 13) { // Null, LF, CR
            if (currentString.length > 2) {
                asciiStrings.push({
                    offset: offset + i - currentString.length,
                    string: currentString
                });
            }
            currentString = '';
        } else {
            if (currentString.length > 2) {
                asciiStrings.push({
                    offset: offset + i - currentString.length,
                    string: currentString
                });
            }
            currentString = '';
        }
    }
    
    console.log(`Found ${asciiStrings.length} ASCII strings in remaining data:`);
    asciiStrings.slice(0, 20).forEach(s => {
        console.log(`  @${s.offset}: "${s.string}"`);
    });
    
    // Look for repeating patterns in the data entries
    console.log('\n=== Data Entry Patterns ===');
    
    // Group entries by hash1 value to see patterns
    const hash1Groups = {};
    dataEntries.forEach(entry => {
        const key = entry.hash1.toString(16);
        if (!hash1Groups[key]) hash1Groups[key] = [];
        hash1Groups[key].push(entry);
    });
    
    console.log('Most common hash1 values:');
    Object.entries(hash1Groups)
        .sort((a, b) => b[1].length - a[1].length)
        .slice(0, 10)
        .forEach(([hash, entries]) => {
            console.log(`  0x${hash}: ${entries.length} entries`);
        });
    
    // Try different string interpretations
    console.log('\n=== Alternative String Decoding ===');
    
    // Maybe the data entries themselves contain string fragments
    console.log('Sample data entries as potential strings:');
    
    for (let i = 0; i < Math.min(20, dataEntries.length); i++) {
        const entry = dataEntries[i];
        
        // Try interpreting as ASCII
        let asciiStr = '';
        entry.bytes.forEach(b => {
            if (b >= 32 && b <= 126) asciiStr += String.fromCharCode(b);
            else asciiStr += '.';
        });
        
        // Try interpreting as UTF-16 BE
        let utf16Str = '';
        for (let j = 0; j < entry.bytes.length; j += 2) {
            if (j + 1 < entry.bytes.length) {
                const charCode = (entry.bytes[j] << 8) | entry.bytes[j + 1];
                if (charCode >= 32 && charCode <= 126) {
                    utf16Str += String.fromCharCode(charCode);
                } else {
                    utf16Str += '.';
                }
            }
        }
        
        console.log(`[${i}]: ${entry.bytes.map(b => b.toString(16).padStart(2, '0')).join(' ')} | ASCII: "${asciiStr}" | UTF16-BE: "${utf16Str}"`);
    }
    
    // Try to correlate with FileNames.txt
    console.log('\n=== FileNames.txt Correlation ===');
    try {
        const fileNamesPath = path.join(__dirname, 'IFFs', 'FileNames.txt');
        const fileNamesContent = fs.readFileSync(fileNamesPath, 'utf8');
        const fileNames = fileNamesContent.split('\n').map(line => line.trim()).filter(line => line.length > 0);
        
        console.log(`FileNames.txt contains ${fileNames.length} entries`);
        console.log('First 10 entries:');
        fileNames.slice(0, 10).forEach((name, i) => {
            console.log(`  [${i}]: "${name}"`);
        });
        
        // The IFF might contain indices or hashes that map to FileNames.txt
        console.log('\nCorrelation analysis:');
        console.log(`Data entries: ${dataEntries.length}`);
        console.log(`FileNames entries: ${fileNames.length}`);
        console.log(`Ratio: ${(dataEntries.length / fileNames.length).toFixed(2)}`);
        
    } catch (error) {
        console.log('Could not read FileNames.txt:', error.message);
    }
    
    return {
        dataEntries,
        asciiStrings,
        hash1Groups
    };
}

// Run the analysis
try {
    const analysis = analyzeAndExtractStrings();
    
} catch (error) {
    console.error('Analysis failed:', error);
}