const fs = require('fs');
const path = require('path');

/**
 * Main Logo Analysis Orchestrator
 * Coordinates the complete logo extraction pipeline using organized scripts
 */

console.log('🏀 College Hoops 2K8 Logo Extraction Pipeline');
console.log('============================================');

// Configuration
const config = {
    // Base paths
    projectRoot: __dirname,
    iffFolder: path.join(__dirname, 'IFFs'),
    outputFolder: path.join('D:', 'Reborn', 'CH2KRB', 'LogoExtract', 'Logos'),
    
    // Script paths
    scripts: {
        iffParsing: path.join(__dirname, 'logo-analysis', 'iff-parsing'),
        h7aDecompression: path.join(__dirname, 'logo-analysis', 'h7a-decompression'),  
        gtfExtraction: path.join(__dirname, 'logo-analysis', 'gtf-extraction'),
        utilities: path.join(__dirname, 'logo-analysis', 'utilities')
    },
    
    // Data files
    files: {
        iffFile: path.join(__dirname, 'IFFs', 'teamselectlogo.iff'),
        cdfFile: path.join(__dirname, 'IFFs', 'teamselectlogo.cdf'),
        fileNamesList: path.join(__dirname, 'IFFs', 'FileNames.txt'),
        logoMapping: path.join(__dirname, 'logo-mapping.json')
    }
};

function validateEnvironment() {
    console.log('\n📋 Environment Validation');
    console.log('-------------------------');
    
    const checks = [
        { name: 'IFF file exists', path: config.files.iffFile },
        { name: 'CDF file exists', path: config.files.cdfFile },
        { name: 'FileNames.txt exists', path: config.files.fileNamesList },
        { name: 'Output directory', path: config.outputFolder, create: true }
    ];
    
    let allPassed = true;
    
    checks.forEach(check => {
        if (fs.existsSync(check.path)) {
            console.log(`✅ ${check.name}: ${check.path}`);
        } else if (check.create) {
            try {
                fs.mkdirSync(check.path, { recursive: true });
                console.log(`✅ ${check.name}: Created ${check.path}`);
            } catch (error) {
                console.log(`❌ ${check.name}: Failed to create ${check.path}`);
                allPassed = false;
            }
        } else {
            console.log(`❌ ${check.name}: Missing ${check.path}`);
            allPassed = false;
        }
    });
    
    return allPassed;
}

function getAnalysisStatus() {
    console.log('\n📊 Analysis Status');
    console.log('------------------');
    
    const status = {
        logoMapping: fs.existsSync(config.files.logoMapping),
        decompressedData: fs.existsSync(path.join(config.outputFolder, 'decompressed_21381950.bin')),
        extractedGTFs: fs.readdirSync(config.outputFolder).filter(f => f.includes('extracted_from_decompressed')).length
    };
    
    console.log(`IFF → Logo Mapping: ${status.logoMapping ? '✅ Complete' : '❌ Pending'}`);
    console.log(`H7A Decompression: ${status.decompressedData ? '✅ Complete' : '❌ Pending'}`);
    console.log(`GTF Extraction: ${status.extractedGTFs > 0 ? `✅ ${status.extractedGTFs} files` : '❌ Pending'}`);
    
    return status;
}

async function runPipelineStep(stepName, scriptPath, description) {
    console.log(`\n🔄 ${stepName}: ${description}`);
    console.log('─'.repeat(50));
    
    try {
        // Import and run the script
        const scriptModule = require(scriptPath);
        
        // If the script exports a function, run it
        if (typeof scriptModule === 'function') {
            await scriptModule();
        } else if (typeof scriptModule.run === 'function') {
            await scriptModule.run();
        } else {
            // Otherwise, just require it (it runs on import)
            console.log(`✅ ${stepName} script loaded`);
        }
        
        console.log(`✅ ${stepName} completed successfully`);
        return true;
        
    } catch (error) {
        console.log(`❌ ${stepName} failed:`, error.message);
        return false;
    }
}

async function runFullPipeline() {
    console.log('\n🚀 Starting Full Logo Extraction Pipeline');
    console.log('==========================================');
    
    const steps = [
        {
            name: 'IFF Analysis',
            script: path.join(config.scripts.iffParsing, 'correlate-iff-filenames.js'),
            description: 'Map IFF entries to logo filenames'
        },
        {
            name: 'H7A Decompression', 
            script: path.join(config.scripts.h7aDecompression, 'h7a-manual-decompress.js'),
            description: 'Decompress CDF file using H7A algorithm'
        },
        {
            name: 'GTF Discovery',
            script: path.join(config.scripts.h7aDecompression, 'analyze-decompressed-data.js'),
            description: 'Find and extract GTF headers from decompressed data'
        },
        {
            name: 'GTF Validation',
            script: path.join(config.scripts.gtfExtraction, 'gtf-header-analysis.js'),
            description: 'Validate GTF structure and analyze conversion issues'
        }
    ];
    
    for (const step of steps) {
        const success = await runPipelineStep(step.name, step.script, step.description);
        if (!success) {
            console.log(`\n⚠️  Pipeline stopped at ${step.name}. Check the error above.`);
            return false;
        }
    }
    
    console.log('\n🎉 Pipeline completed successfully!');
    return true;
}

function displayMenu() {
    console.log('\n🎮 Logo Extraction Menu');
    console.log('=======================');
    console.log('1. Validate Environment');
    console.log('2. Check Analysis Status');
    console.log('3. Run IFF Analysis Only');
    console.log('4. Run H7A Decompression Only');
    console.log('5. Run GTF Extraction Only');
    console.log('6. Run Full Pipeline');
    console.log('7. Show Configuration');
    console.log('0. Exit');
    console.log('\nChoose an option (0-7):');
}

function showConfiguration() {
    console.log('\n⚙️  Current Configuration');
    console.log('========================');
    console.log(`Project Root: ${config.projectRoot}`);
    console.log(`IFF Folder: ${config.iffFolder}`);
    console.log(`Output Folder: ${config.outputFolder}`);
    console.log('\nScript Folders:');
    Object.entries(config.scripts).forEach(([name, path]) => {
        console.log(`  ${name}: ${path}`);
    });
    console.log('\nData Files:');
    Object.entries(config.files).forEach(([name, path]) => {
        console.log(`  ${name}: ${path} ${fs.existsSync(path) ? '✅' : '❌'}`);
    });
}

// Main execution
async function main() {
    // If run with command line arguments, execute specific operations
    const args = process.argv.slice(2);
    
    if (args.length > 0) {
        switch (args[0]) {
            case 'validate':
                return validateEnvironment();
            case 'status':
                return getAnalysisStatus();
            case 'pipeline':
                return await runFullPipeline();
            case 'config':
                return showConfiguration();
            default:
                console.log('Usage: node logo-extraction-orchestrator.js [validate|status|pipeline|config]');
                return;
        }
    }
    
    // Interactive mode
    console.log('Interactive mode - use command line arguments for automation:');
    console.log('  node logo-extraction-orchestrator.js validate');
    console.log('  node logo-extraction-orchestrator.js status');
    console.log('  node logo-extraction-orchestrator.js pipeline');
    console.log('  node logo-extraction-orchestrator.js config');
    
    showConfiguration();
    console.log('\n💡 Tip: Run "node logo-extraction-orchestrator.js status" to check current progress');
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = {
    config,
    validateEnvironment,
    getAnalysisStatus,
    runFullPipeline,
    showConfiguration
};