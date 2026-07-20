const fs = require('fs');
const path = require('path');

const ROOT_MODEL_DIR = 'E:\\Live2d-model';
const THUMBNAILS_DIR = 'E:\\Live2d-model-thumbnails';
const OUTPUT_DIR = path.join(__dirname, '..');

function generateSlug(relativePath) {
    return relativePath
        .replace(/^[\\/]+/, '')
        .replace(/[\\/]/g, '_')
        .replace(/\.(model3|model)\.json$/i, '')
        .replace(/[^a-zA-Z0-9_\-]/g, '');
}

function findModelConfigs(dir, fileList = []) {
    let files;
    try {
        files = fs.readdirSync(dir);
    } catch (e) {
        return fileList;
    }
    for (const file of files) {
        const filePath = path.join(dir, file);
        let stat;
        try {
            stat = fs.statSync(filePath);
        } catch (e) {
            continue;
        }
        if (stat.isDirectory()) {
            findModelConfigs(filePath, fileList);
        } else if (file.toLowerCase().endsWith('.model3.json') || file.toLowerCase().endsWith('.model.json')) {
            fileList.push(filePath);
        }
    }
    return fileList;
}

function listModelFiles(dir, modelRootDir, fileList = []) {
    let files;
    try {
        files = fs.readdirSync(dir, { withFileTypes: true });
    } catch (e) {
        return fileList;
    }

    for (const file of files) {
        const fullPath = path.join(dir, file.name);
        if (file.isDirectory()) {
            // Check if this subdirectory has its own model config. If so, do NOT recurse (it belongs to another model)
            let subFiles = [];
            try { subFiles = fs.readdirSync(fullPath); } catch (_) {}
            const hasOwnConfig = subFiles.some(f => f.toLowerCase().endsWith('.model3.json') || f.toLowerCase().endsWith('.model.json'));
            if (!hasOwnConfig) {
                listModelFiles(fullPath, modelRootDir, fileList);
            }
        } else if (file.isFile()) {
            // Skip model configs other than the current one if they somehow exist
            const relPath = path.relative(modelRootDir, fullPath).replace(/\\/g, '/');
            fileList.push(relPath);
        }
    }
    return fileList;
}

function main() {
    console.log('Scanning for model configuration files...');
    const configs = findModelConfigs(ROOT_MODEL_DIR);
    console.log(`Found ${configs.length} model configurations.`);

    const characterList = [];
    const fileMap = {};

    for (const configPath of configs) {
        const relativeConfigPath = path.relative(ROOT_MODEL_DIR, configPath).replace(/\\/g, '/');
        const slug = generateSlug(relativeConfigPath);
        const parts = relativeConfigPath.split('/');
        
        const franchise = parts[0];
        const configFilename = parts[parts.length - 1];
        const modelDir = path.dirname(configPath);
        
        // Clean name (folder name containing the config)
        const name = parts[parts.length - 2] || slug;

        const type = configFilename.toLowerCase().endsWith('.model3.json') ? 'moc3' : 'moc';

        // Gather all files belonging to this model
        const rawFiles = listModelFiles(modelDir, ROOT_MODEL_DIR);
        // Filter down raw files to only include files starting with the model directory
        const modelDirRel = path.relative(ROOT_MODEL_DIR, modelDir).replace(/\\/g, '/');
        const files = rawFiles.filter(f => f.startsWith(modelDirRel));

        // Check if thumbnail exists
        const thumbnailName = `${slug}.png`;
        const thumbnailPath = path.join(THUMBNAILS_DIR, thumbnailName);
        const hasThumbnail = fs.existsSync(thumbnailPath);

        characterList.push({
            slug,
            name,
            franchise,
            type,
            modelDir: modelDirRel,
            configPath: relativeConfigPath,
            hasThumbnail
        });

        fileMap[slug] = files;
    }

    // Write metadata files
    fs.writeFileSync(path.join(OUTPUT_DIR, 'character_list.json'), JSON.stringify(characterList, null, 2), 'utf8');
    fs.writeFileSync(path.join(OUTPUT_DIR, 'file_map.json'), JSON.stringify(fileMap, null, 2), 'utf8');
    
    console.log(`Metadata generated!`);
    console.log(`Saved character_list.json (${characterList.length} items)`);
    console.log(`Saved file_map.json (${Object.keys(fileMap).length} mappings)`);
}

main();
