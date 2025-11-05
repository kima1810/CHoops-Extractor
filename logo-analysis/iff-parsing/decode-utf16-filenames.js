const fs = require('fs');
const path = require('path');

// Read the IFF file
const iffFilePath = path.join(__dirname, 'IFFs', 'teamselectlogo.iff');
const iffBuffer = fs.readFileSync(iffFilePath);

console.log(`Decoding UTF-16 filenames from IFF: ${iffFilePath}`);
console.log(`File size: ${iffBuffer.length} bytes`);

function decodeUTF16Filenames() {
    console.log('\n=== IFF Structure Analysis ===');
    
    // Read header
    const magic = iffBuffer.readUInt32BE(0);
    const unk1 = iffBuffer.readUInt32BE(4);
    const dwDataFileCount = iffBuffer.readUInt32BE(8);
    const dwSubFileCount = iffBuffer.readUInt32BE(12);
    
    console.log(`Magic: 0x${magic.toString(16).toUpperCase()}`);
    console.log(`Data File Count: ${dwDataFileCount}`);
    console.log(`Sub File Count: ${dwSubFileCount}`);
    
    console.log('\n=== Decoding UTF-16 Filenames ===');
    
    let offset = 16;
    const filenames = [];
    
    // Each data file entry is 8 bytes - treat as UTF-16 encoded filename parts
    for (let i = 0; i < dwDataFileCount && offset + 8 <= iffBuffer.length; i++) {
        // Read 8 bytes as UTF-16 little-endian
        const bytes = iffBuffer.subarray(offset, offset + 8);
        
        // Convert bytes to UTF-16 string
        let filename = '';
        for (let j = 0; j < bytes.length; j += 2) {
            const charCode = bytes[j] | (bytes[j + 1] << 8); // Little-endian
            if (charCode !== 0) {
                filename += String.fromCharCode(charCode);
            }
        }
        
        if (filename.length > 0) {
            filenames.push({
                index: i,
                filename: filename,
                offset: offset
            });
            
            // Only show first 50 and last 50 to avoid overwhelming output
            if (i < 50 || i >= dwDataFileCount - 50) {
                console.log(`[${i}]: "${filename}"`);
            } else if (i === 50) {
                console.log('... (showing first and last 50 entries) ...');
            }
        }
        
        offset += 8;
    }
    
    console.log(`\nDecoded ${filenames.length} filenames from ${dwDataFileCount} entries`);
    
    // Look for logo-related filenames
    console.log('\n=== Logo Files Analysis ===');
    const logoFiles = filenames.filter(f => f.filename.toLowerCase().includes('logo'));
    console.log(`Found ${logoFiles.length} logo-related filenames:`);
    
    logoFiles.slice(0, 20).forEach(f => {
        console.log(`  [${f.index}]: "${f.filename}"`);
    });
    
    if (logoFiles.length > 20) {
        console.log(`  ... and ${logoFiles.length - 20} more logo files`);
    }
    
    // Look for texture files
    const textureFiles = filenames.filter(f => 
        f.filename.toLowerCase().includes('txtr') || 
        f.filename.toLowerCase().includes('texture') ||
        f.filename.toLowerCase().endsWith('.dds') ||
        f.filename.toLowerCase().endsWith('.gtf')
    );
    console.log(`\nFound ${textureFiles.length} texture-related filenames:`);
    textureFiles.slice(0, 10).forEach(f => {
        console.log(`  [${f.index}]: "${f.filename}"`);
    });
    
    // Analyze file extensions
    console.log('\n=== File Extensions Analysis ===');
    const extensions = {};
    filenames.forEach(f => {
        const ext = path.extname(f.filename.toLowerCase());
        if (ext) {
            extensions[ext] = (extensions[ext] || 0) + 1;
        }
    });
    
    console.log('File extension counts:');
    Object.entries(extensions)
        .sort((a, b) => b[1] - a[1])
        .forEach(([ext, count]) => {
            console.log(`  ${ext}: ${count} files`);
        });
    
    // Look for specific college teams
    console.log('\n=== College Team Analysis ===');
    const teamKeywords = ['duke', 'unc', 'carolina', 'kentucky', 'kansas', 'michigan', 'ucla', 'syracuse'];
    
    teamKeywords.forEach(keyword => {
        const teamFiles = filenames.filter(f => f.filename.toLowerCase().includes(keyword));
        if (teamFiles.length > 0) {
            console.log(`${keyword.toUpperCase()}: ${teamFiles.length} files`);
            teamFiles.slice(0, 3).forEach(f => {
                console.log(`  "${f.filename}"`);
            });
        }
    });
    
    return {
        filenames,
        logoFiles,
        textureFiles,
        extensions
    };
}

// Run the analysis
try {
    const analysis = decodeUTF16Filenames();
    
    console.log('\n=== Summary ===');
    console.log(`Total filenames decoded: ${analysis.filenames.length}`);
    console.log(`Logo files found: ${analysis.logoFiles.length}`);
    console.log(`Texture files found: ${analysis.textureFiles.length}`);
    console.log(`Unique extensions: ${Object.keys(analysis.extensions).length}`);
    
} catch (error) {
    console.error('Analysis failed:', error);
}