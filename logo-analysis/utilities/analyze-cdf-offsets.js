const fs = require('fs');
const path = require('path');

// Load the logo mapping to analyze CDF offset distribution
const mappingPath = path.join(__dirname, '..', '..', 'logo-mapping.json');
const logoMapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));

console.log('Analyzing 520 logo CDF offset distribution...\n');

// Group logos by CDF offset
const offsetGroups = {};
logoMapping.forEach(logo => {
    const offset = logo.cdfOffset;
    if (!offsetGroups[offset]) {
        offsetGroups[offset] = [];
    }
    offsetGroups[offset].push(logo.fileName);
});

const sortedOffsets = Object.keys(offsetGroups).map(Number).sort((a, b) => a - b);

console.log('=== CDF Offset Distribution ===');
console.log(`Total unique offsets: ${sortedOffsets.length}`);
console.log(`Total logos mapped: ${logoMapping.length}`);

console.log('\nOffset groups:');
sortedOffsets.forEach(offset => {
    const logos = offsetGroups[offset];
    console.log(`  0x${offset.toString(16).padStart(8, '0').toUpperCase()} (${offset}): ${logos.length} logos`);
    if (logos.length <= 5) {
        console.log(`    Files: ${logos.join(', ')}`);
    } else {
        console.log(`    Files: ${logos.slice(0, 3).join(', ')}, ... ${logos.slice(-2).join(', ')}`);
    }
});

// Check the CDF file size and validate offsets
const cdfPath = path.join(__dirname, '..', '..', 'IFFs', 'teamselectlogo.cdf');
const cdfSize = fs.statSync(cdfPath).size;

console.log(`\n=== CDF File Analysis ===`);
console.log(`CDF file size: ${cdfSize} bytes (${(cdfSize / 1024 / 1024).toFixed(2)} MB)`);
console.log(`Smallest offset: 0x${Math.min(...sortedOffsets).toString(16)} (${Math.min(...sortedOffsets)})`);
console.log(`Largest offset: 0x${Math.max(...sortedOffsets).toString(16)} (${Math.max(...sortedOffsets)})`);

// Validate if offsets are within file bounds
const invalidOffsets = sortedOffsets.filter(offset => offset >= cdfSize);
if (invalidOffsets.length > 0) {
    console.log(`\n❌ PROBLEM: ${invalidOffsets.length} offsets exceed CDF file size!`);
    invalidOffsets.forEach(offset => {
        console.log(`  Invalid offset: 0x${offset.toString(16)} (${offset}) - exceeds file size by ${offset - cdfSize} bytes`);
    });
} else {
    console.log(`\n✅ All offsets are within CDF file bounds`);
}

// Check if we're looking at the right decompression approach
console.log('\n=== Decompression Analysis ===');
console.log('Current approach: Decompress entire CDF file, then search for GTF headers');
console.log('Alternative approach needed: Use CDF offsets to extract individual logo chunks');

console.log('\n=== HYPOTHESIS ===');
console.log('The issue might be:');
console.log('1. We are decompressing the ENTIRE CDF file as one unit');
console.log('2. But each logo might be separately compressed at its CDF offset');  
console.log('3. We should try extracting/decompressing chunks at each CDF offset instead');
console.log('4. Each of the 520 logos is likely a separate H7A compressed chunk');