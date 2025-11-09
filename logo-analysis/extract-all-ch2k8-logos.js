const fs = require('fs');
const path = require('path');

console.log('=== COLLEGE HOOPS 2K8 COMPLETE LOGO EXTRACTION ===\n');

async function extractAllLogos() {
    try {
        const cdfPath = path.join(__dirname, '../IFFs/teamselectlogo.cdf');
        const cdfData = fs.readFileSync(cdfPath);
        const outputDir = path.join(__dirname, 'complete-logo-extraction');
        
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }
        
        console.log(`📄 Processing ${cdfData.length} bytes from teamselectlogo.cdf`);
        
        const logoSize = 96 * 96 * 4; // 36864 bytes
        const maxLogos = Math.floor(cdfData.length / logoSize);
        
        console.log(`🎯 Extracting up to ${maxLogos} logos...`);
        
        let extracted = 0;
        const step = 1024; // Check every 1KB for texture data
        
        for (let offset = 0; offset < cdfData.length - logoSize; offset += step) {
            const logoData = cdfData.slice(offset, offset + logoSize);
            const entropy = calculateEntropy(logoData.slice(0, 1024));
            
            // Extract data with good texture entropy
            if (entropy > 0.4 && entropy < 0.9) {
                console.log(`  Logo ${extracted} at offset ${offset}: entropy ${entropy.toFixed(3)}`);
                
                // Save in the most promising format (based on analysis)
                await saveLogoAsRGBA(logoData, `logo_${extracted.toString().padStart(3, '0')}`, outputDir);
                extracted++;
                
                if (extracted >= 350) break; // Safety limit
            }
        }
        
        console.log(`\n✅ Extraction complete: ${extracted} logos extracted`);
        console.log(`📂 Results saved to: ${outputDir}`);
        
    } catch (error) {
        console.error('❌ Error:', error);
    }
}

function calculateEntropy(data) {
    const frequency = new Array(256).fill(0);
    for (const byte of data) {
        frequency[byte]++;
    }
    
    let entropy = 0;
    const length = data.length;
    
    for (let i = 0; i < 256; i++) {
        if (frequency[i] > 0) {
            const p = frequency[i] / length;
            entropy -= p * Math.log2(p);
        }
    }
    
    return entropy / 8;
}

async function saveLogoAsRGBA(logoData, baseName, outputDir) {
    // Convert RGBA to BGRA for TGA format
    const convertedData = Buffer.alloc(logoData.length);
    for (let i = 0; i < logoData.length; i += 4) {
        convertedData[i] = logoData[i + 2];     // B
        convertedData[i + 1] = logoData[i + 1]; // G
        convertedData[i + 2] = logoData[i];     // R
        convertedData[i + 3] = logoData[i + 3]; // A
    }
    
    // Create TGA header
    const header = Buffer.alloc(18);
    header[2] = 2;  // Uncompressed RGB
    header[12] = 96;  // Width
    header[13] = 0;
    header[14] = 96;  // Height  
    header[15] = 0;
    header[16] = 32; // 32-bit
    
    const tgaData = Buffer.concat([header, convertedData]);
    const outputPath = path.join(outputDir, `${baseName}.tga`);
    fs.writeFileSync(outputPath, tgaData);
}

// Run the extraction
extractAllLogos().catch(console.error);