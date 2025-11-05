const fs = require('fs');
const path = require('path');

// Read files - adjusted paths for organized structure
const iffFilePath = path.join(__dirname, '..', '..', 'IFFs', 'teamselectlogo.iff');
const iffBuffer = fs.readFileSync(iffFilePath);

const fileNamesPath = path.join(__dirname, '..', '..', 'IFFs', 'FileNames.txt');
const fileNamesContent = fs.readFileSync(fileNamesPath, 'utf8');
const fileNames = fileNamesContent.split('\n').map(line => line.trim()).filter(line => line.length > 0);

console.log(`Correlating IFF structure with FileNames.txt`);
console.log(`IFF file size: ${iffBuffer.length} bytes`);
console.log(`FileNames.txt entries: ${fileNames.length}`);

function correlateIFFWithFileNames() {
    // Read IFF header
    const magic = iffBuffer.readUInt32BE(0);
    const unk1 = iffBuffer.readUInt32BE(4);
    const dwDataFileCount = iffBuffer.readUInt32BE(8);
    const dwSubFileCount = iffBuffer.readUInt32BE(12);
    
    console.log(`\nIFF Header:`);
    console.log(`Magic: 0x${magic.toString(16).toUpperCase()}`);
    console.log(`Data File Count: ${dwDataFileCount}`);
    console.log(`Sub File Count: ${dwSubFileCount}`);
    
    // Read data entries
    let offset = 16;
    const dataEntries = [];
    
    for (let i = 0; i < dwDataFileCount && offset + 8 <= iffBuffer.length; i++) {
        const entry = {
            index: i,
            hash1: iffBuffer.readUInt32BE(offset),
            hash2: iffBuffer.readUInt32BE(offset + 4)
        };
        dataEntries.push(entry);
        offset += 8;
    }
    
    console.log(`\nRead ${dataEntries.length} data entries`);
    
    // Group entries by hash1 to find patterns
    const hash1Groups = {};
    dataEntries.forEach(entry => {
        const key = entry.hash1;
        if (!hash1Groups[key]) hash1Groups[key] = [];
        hash1Groups[key].push(entry);
    });
    
    console.log(`\nHash1 groups with exactly 520 entries (matching FileNames count):`);
    const groups520 = Object.entries(hash1Groups).filter(([hash, entries]) => entries.length === 520);
    
    groups520.forEach(([hash, entries]) => {
        console.log(`  0x${parseInt(hash).toString(16).toUpperCase()}: ${entries.length} entries`);
    });
    
    console.log(`\nFound ${groups520.length} groups with exactly 520 entries`);
    
    if (groups520.length > 0) {
        console.log(`\nAnalyzing the first group (0x${parseInt(groups520[0][0]).toString(16).toUpperCase()}):`);
        const firstGroup = groups520[0][1];
        
        console.log('First 10 entries in this group:');
        firstGroup.slice(0, 10).forEach((entry, i) => {
            console.log(`  [${i}] FileNames[${i}]="${fileNames[i]}" -> Hash1=0x${entry.hash1.toString(16)}, Hash2=0x${entry.hash2.toString(16)}`);
        });
        
        console.log('\nLast 10 entries in this group:');
        firstGroup.slice(-10).forEach((entry, i) => {
            const fileIndex = firstGroup.length - 10 + i;
            console.log(`  [${fileIndex}] FileNames[${fileIndex}]="${fileNames[fileIndex]}" -> Hash1=0x${entry.hash1.toString(16)}, Hash2=0x${entry.hash2.toString(16)}`);
        });
        
        // Analyze hash2 values - these might be offsets into the CDF file
        console.log('\nHash2 values (potential CDF offsets):');
        console.log('First 10 hash2 values:');
        firstGroup.slice(0, 10).forEach((entry, i) => {
            console.log(`  ${fileNames[i]}: 0x${entry.hash2.toString(16)} (${entry.hash2})`);
        });
        
        // Check if hash2 values are increasing (suggesting file offsets)
        const hash2Values = firstGroup.map(e => e.hash2).sort((a, b) => a - b);
        const isIncreasing = hash2Values.every((val, i) => i === 0 || val >= hash2Values[i - 1]);
        console.log(`\nHash2 values appear to be ${isIncreasing ? 'sorted/increasing' : 'unsorted'}`);
        console.log(`Hash2 range: 0x${hash2Values[0].toString(16)} to 0x${hash2Values[hash2Values.length - 1].toString(16)}`);
        console.log(`Hash2 range: ${hash2Values[0]} to ${hash2Values[hash2Values.length - 1]} bytes`);
        
        // Map FileNames to their corresponding data
        console.log('\n=== FileNames to IFF Mapping ===');
        const logoMapping = [];
        
        firstGroup.forEach((entry, i) => {
            if (i < fileNames.length) {
                logoMapping.push({
                    fileName: fileNames[i],
                    hash1: entry.hash1,
                    hash2: entry.hash2,
                    cdfOffset: entry.hash2  // Assuming hash2 is CDF offset
                });
            }
        });
        
        // Sort by CDF offset to see the file order
        const sortedByOffset = [...logoMapping].sort((a, b) => a.cdfOffset - b.cdfOffset);
        
        console.log('First 20 files sorted by CDF offset:');
        sortedByOffset.slice(0, 20).forEach((mapping, i) => {
            console.log(`  Offset 0x${mapping.cdfOffset.toString(16).padStart(8, '0')}: ${mapping.fileName}`);
        });
        
        console.log('\nLast 20 files sorted by CDF offset:');
        sortedByOffset.slice(-20).forEach((mapping, i) => {
            console.log(`  Offset 0x${mapping.cdfOffset.toString(16).padStart(8, '0')}: ${mapping.fileName}`);
        });
        
        return logoMapping;
    }
    
    return null;
}

// Run the correlation
try {
    const mapping = correlateIFFWithFileNames();
    
    if (mapping) {
        console.log(`\n=== SUCCESS ===`);
        console.log(`Successfully mapped ${mapping.length} logo files from FileNames.txt to IFF data entries`);
        console.log(`Each hash2 value likely represents the offset of that logo in teamselectlogo.cdf`);
        
        // Save the mapping for later use
        const mappingPath = path.join(__dirname, '..', '..', 'logo-mapping.json');
        fs.writeFileSync(mappingPath, JSON.stringify(mapping, null, 2));
        console.log(`Saved mapping to: ${mappingPath}`);
    }
    
} catch (error) {
    console.error('Correlation failed:', error);
}