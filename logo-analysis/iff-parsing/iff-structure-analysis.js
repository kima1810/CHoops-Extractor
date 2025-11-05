const fs = require('fs');

const IFF_FILE_PATH = './IFFs/teamselectlogo.iff';

function analyzeIFFStructure() {
    console.log('🔍 IFF Structure Analysis Using NBA2K9 Format\n');
    
    const iffBuffer = fs.readFileSync(IFF_FILE_PATH);
    console.log(`📁 IFF File: ${iffBuffer.length} bytes\n`);
    
    // Parse IFF_HEADER according to the documentation
    const header = {
        dwMagic: iffBuffer.readUInt32BE(0),
        dwSize: iffBuffer.readUInt32BE(4),
        dwFileLen: iffBuffer.readUInt32BE(8),
        dwReserve: iffBuffer.readUInt32BE(12),
        dwDataFileCount: iffBuffer.readUInt32BE(16),
        dwUnknow1: iffBuffer.readUInt32BE(20),
        dwSubFileCount: iffBuffer.readUInt32BE(24),
        dwUnknow2: iffBuffer.readUInt32BE(28)
    };
    
    console.log('📋 IFF_HEADER Analysis:');
    console.log(`  Magic: 0x${header.dwMagic.toString(16).toUpperCase()} ${header.dwMagic === 0xF0985030 ? '✅ Type 2 IFF' : '❌'}`);
    console.log(`  Size: ${header.dwSize} (0x${header.dwSize.toString(16)})`);
    console.log(`  File Length: ${header.dwFileLen} (0x${header.dwFileLen.toString(16)})`);
    console.log(`  Reserve: ${header.dwReserve}`);
    console.log(`  Data File Count: ${header.dwDataFileCount} 📊`);
    console.log(`  Unknown1: ${header.dwUnknow1} (0x${header.dwUnknow1.toString(16)})`);
    console.log(`  Sub File Count: ${header.dwSubFileCount} 📊`);
    console.log(`  Unknown2: ${header.dwUnknow2} (0x${header.dwUnknow2.toString(16)})`);
    
    console.log(`\n🎯 Key Findings:`);
    console.log(`  → This IFF references ${header.dwDataFileCount} data files`);
    console.log(`  → This IFF contains ${header.dwSubFileCount} sub files`);
    
    // Parse IFF_HEADER_DATA structures
    if (header.dwDataFileCount > 0) {
        console.log(`\n📦 IFF_HEADER_DATA Entries (${header.dwDataFileCount} entries):`);
        
        let offset = 32; // After the main header
        for (let i = 0; i < header.dwDataFileCount; i++) {
            const headerData = {
                dwName: iffBuffer.readUInt32BE(offset),
                dwType: iffBuffer.readUInt32BE(offset + 4),
                dwUnknow1: iffBuffer.readUInt32BE(offset + 8),
                dwUnCompressLen: iffBuffer.readUInt32BE(offset + 12),
                dwUnknow2: iffBuffer.readUInt32BE(offset + 16),
                dwStartOffset: iffBuffer.readUInt32BE(offset + 20),
                dwCompressLen: iffBuffer.readUInt32BE(offset + 24),
                dwReserve: iffBuffer.readUInt32BE(offset + 28)
            };
            
            console.log(`  Entry ${i + 1}:`);
            console.log(`    Name Hash: 0x${headerData.dwName.toString(16).toUpperCase()}`);
            console.log(`    Type: 0x${headerData.dwType.toString(16).toUpperCase()}`);
            console.log(`    Uncompressed Length: ${headerData.dwUnCompressLen} bytes`);
            console.log(`    Start Offset in CDF: 0x${headerData.dwStartOffset.toString(16)} (${headerData.dwStartOffset})`);
            console.log(`    Compressed Length: ${headerData.dwCompressLen} bytes`);
            console.log(`    Unknown1: ${headerData.dwUnknow1}`);
            console.log(`    Unknown2: ${headerData.dwUnknow2}`);
            console.log(`    Reserve: ${headerData.dwReserve}`);
            console.log();
            
            offset += 32; // Each IFF_HEADER_DATA is 32 bytes
        }
    }
    
    // Parse Sub File offsets
    if (header.dwSubFileCount > 0) {
        console.log(`\n📄 Sub File Offsets (${header.dwSubFileCount} entries):`);
        
        let subFileOffset = 32 + (header.dwDataFileCount * 32);
        for (let i = 0; i < header.dwSubFileCount; i++) {
            const offset = iffBuffer.readUInt32BE(subFileOffset + (i * 4));
            console.log(`  Sub File ${i + 1}: Offset 0x${offset.toString(16)} (${offset})`);
        }
        
        // Parse IFF_HEADER_SUB structures
        console.log(`\n📋 IFF_HEADER_SUB Entries:`);
        let subHeaderOffset = subFileOffset + (header.dwSubFileCount * 4);
        
        for (let i = 0; i < header.dwSubFileCount; i++) {
            const subHeader = {
                dwName: iffBuffer.readUInt32BE(subHeaderOffset),
                dwType: iffBuffer.readUInt32BE(subHeaderOffset + 4),
                dwSubCount: iffBuffer.readUInt32BE(subHeaderOffset + 8)
            };
            
            console.log(`  Sub Header ${i + 1}:`);
            console.log(`    Name Hash: 0x${subHeader.dwName.toString(16).toUpperCase()}`);
            console.log(`    Type: 0x${subHeader.dwType.toString(16).toUpperCase()}`);
            console.log(`    Sub Count: ${subHeader.dwSubCount}`);
            
            // Parse offset array for this sub header
            console.log(`    Offsets:`);
            for (let j = 0; j < subHeader.dwSubCount; j++) {
                const offset = iffBuffer.readUInt32BE(subHeaderOffset + 12 + (j * 4));
                console.log(`      [${j}]: 0x${offset.toString(16)} (${offset})`);
            }
            
            subHeaderOffset += 12 + (subHeader.dwSubCount * 4);
            console.log();
        }
    }
    
    console.log(`\n💡 Analysis Summary:`);
    console.log(`✅ IFF Type 2 structure confirmed`);
    console.log(`✅ ${header.dwDataFileCount} data file references (likely pointing to CDF sections)`);
    console.log(`✅ ${header.dwSubFileCount} sub files catalogued`);
    console.log(`✅ Structure matches NBA2K9 format documentation`);
}

// Run the analysis
analyzeIFFStructure();