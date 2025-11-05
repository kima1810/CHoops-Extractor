const fs = require('fs');
const path = require('path');

const CDF_FILE_PATH = './IFFs/teamselectlogo.cdf';
const FILENAMES_PATH = './IFFs/FileNames.txt';
const OUTPUT_DIR = 'D:\\Reborn\\CH2KRB\\LogoExtract\\Logos';

// GTF header locations from our analysis
const GTF_LOCATIONS = [
    { offset: 0x0CD0A9, name: 'logo366' },
    { offset: 0x10A925, name: 'logo933' },
    { offset: 0x1A022A, name: 'logo381' },
    { offset: 0x1D39D1, name: 'logo281' },
    { offset: 0x246A73, name: 'logo266' },
    { offset: 0x2CE75B, name: 'logo066' },
    { offset: 0x341D71, name: 'logo081' },
    { offset: 0x3458E3, name: 'logo181' },
    { offset: 0x41345B, name: 'logo166' },
    { offset: 0x458578, name: 'logo185' },
    { offset: 0x5832C5, name: 'logo162' },
    { offset: 0x661DB3, name: 'logo062' },
    { offset: 0x95F805, name: 'logo085' },
    { offset: 0xA2BA31, name: 'logo285' }
];

async function improvedLogoExtraction() {
    console.log('🔧 Improved Logo Extraction - GTF Format Analysis\n');
    
    // Ensure output directory exists
    if (!fs.existsSync(OUTPUT_DIR)) {
        fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    }
    
    const cdfBuffer = fs.readFileSync(CDF_FILE_PATH);
    console.log(`📁 CDF File: ${cdfBuffer.length} bytes loaded\n`);
    
    let successCount = 0;
    
    for (let i = 0; i < GTF_LOCATIONS.length; i++) {
        const location = GTF_LOCATIONS[i];
        const nextLocation = GTF_LOCATIONS[i + 1];
        
        // Calculate size
        const size = nextLocation ? 
            nextLocation.offset - location.offset : 
            cdfBuffer.length - location.offset;
        
        console.log(`${(i + 1).toString().padStart(2, ' ')}. ${location.name}`);
        console.log(`    Offset: 0x${location.offset.toString(16)} (${location.offset})`);
        console.log(`    Size: ${size} bytes (${(size / 1024).toFixed(1)} KB)`);
        
        // Extract raw data
        const rawGTFData = cdfBuffer.slice(location.offset, location.offset + size);
        
        // Analyze the header
        const magic = rawGTFData.readUInt32BE(0);
        console.log(`    Magic: 0x${magic.toString(16).toUpperCase()}`);
        
        if (magic === 0x01080000 || magic === 0x00000801) {
            // Try different approaches to fix the GTF
            const approaches = [
                { name: 'Raw GTF', data: rawGTFData },
                { name: 'Skip 4 bytes', data: rawGTFData.slice(4) },
                { name: 'Skip 8 bytes', data: rawGTFData.slice(8) },
                { name: 'Reconstructed', data: await reconstructGTF(rawGTFData) }
            ];
            
            for (let approach of approaches) {
                if (approach.data) {
                    const success = await tryConvertGTF(approach.data, `${location.name}_${approach.name.replace(' ', '_')}`);
                    if (success) {
                        console.log(`    ✅ Success with: ${approach.name}`);
                        successCount++;
                        break;
                    }
                }
            }
            
            if (successCount <= i) {
                console.log(`    ❌ All conversion attempts failed`);
                
                // Save raw data for manual analysis
                const rawPath = path.join(OUTPUT_DIR, `${location.name}_raw.bin`);
                fs.writeFileSync(rawPath, rawGTFData.slice(0, Math.min(1024, rawGTFData.length)));
                console.log(`    💾 Saved first 1KB as ${location.name}_raw.bin for analysis`);
            }
        } else {
            console.log(`    ❌ Invalid GTF magic: 0x${magic.toString(16)}`);
        }
        
        console.log();
    }
    
    console.log(`🎉 Extraction Summary:`);
    console.log(`✅ Successfully converted: ${successCount}/${GTF_LOCATIONS.length} logos`);
    console.log(`📂 Output directory: ${OUTPUT_DIR}`);
}

async function reconstructGTF(rawData) {
    try {
        // Try to reconstruct a proper GTF file based on the existing code pattern
        if (rawData.length < 0x30) return null;
        
        const magic = rawData.readUInt32BE(0);
        if (magic !== 0x01080000 && magic !== 0x00000801) return null;
        
        // Look for texture header within the data (similar to ChoopsTextureReader approach)
        let textureHeaderOffset = -1;
        for (let i = 0x18; i < Math.min(0x100, rawData.length - 0x18); i += 4) {
            // Look for patterns that might indicate texture parameters
            const val1 = rawData.readUInt32BE(i);
            const val2 = rawData.readUInt32BE(i + 4);
            
            // Common GTF texture header patterns
            if (val1 > 0 && val1 < 4096 && val2 > 0 && val2 < 4096) {
                textureHeaderOffset = i;
                break;
            }
        }
        
        if (textureHeaderOffset === -1) return null;
        
        // Extract texture header (0x18 bytes starting from found offset)
        const textureGtfHeader = rawData.slice(textureHeaderOffset, textureHeaderOffset + 0x18);
        
        // Create proper GTF header (0x30 bytes)
        let gtfHeader = Buffer.alloc(0x30);
        const textureDataSize = rawData.length - 0x30;
        const fileSize = textureDataSize + 0x30;
        
        // File header
        gtfHeader.writeUInt32BE(0x01080000, 0x0);  // GTF magic
        gtfHeader.writeUInt32BE(fileSize, 0x4);    // File size
        gtfHeader.writeUInt32BE(0x1, 0x8);         // Entry count
        
        // Texture header
        gtfHeader.writeUInt32BE(0x0, 0xC);         // Padding
        gtfHeader.writeUInt32BE(0x30, 0x10);       // Header size
        gtfHeader.writeUInt32BE(textureDataSize, 0x14);  // Texture data size
        gtfHeader.fill(textureGtfHeader, 0x18);    // Texture parameters
        
        // Texture data (skip the original header)
        const textureData = rawData.slice(0x30);
        
        return Buffer.concat([gtfHeader, textureData]);
        
    } catch (err) {
        return null;
    }
}

async function tryConvertGTF(gtfData, filename) {
    return new Promise((resolve) => {
        if (!gtfData || gtfData.length < 64) {
            resolve(false);
            return;
        }
        
        const { exec } = require('child_process');
        const gtfPath = path.join(OUTPUT_DIR, `${filename}.gtf`);
        const ddsPath = path.join(OUTPUT_DIR, `${filename}.dds`);
        
        try {
            // Write GTF file
            fs.writeFileSync(gtfPath, gtfData);
            
            // Try to convert
            const gtfExePath = path.join(__dirname, '2k-tools', 'lib', 'gtf2dds.exe');
            exec(`"${gtfExePath}" -v -o "${ddsPath}" "${gtfPath}"`, (err, stdout, stderr) => {
                // Clean up GTF file
                try { fs.unlinkSync(gtfPath); } catch {}
                
                if (!err && fs.existsSync(ddsPath)) {
                    resolve(true);
                } else {
                    resolve(false);
                }
            });
        } catch (err) {
            resolve(false);
        }
    });
}

// Run the improved extraction
improvedLogoExtraction().catch(err => {
    console.error('❌ Extraction failed:', err);
});