import os
import sys

# Dynamic NVIDIA CUDA & cuDNN DLL injection for Python packages under Windows
import site
paths_to_add = []
for base_path in site.getsitepackages():
    nvidia_root = os.path.join(base_path, 'nvidia')
    if os.path.isdir(nvidia_root):
        for folder in os.listdir(nvidia_root):
            bin_dir = os.path.join(nvidia_root, folder, 'bin')
            if os.path.isdir(bin_dir):
                paths_to_add.append(bin_dir)

# Add CUDA toolkit bin folder fallback
cuda_x64_bin = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin\x64"
if os.path.isdir(cuda_x64_bin):
    paths_to_add.append(cuda_x64_bin)

# Append to PATH
if paths_to_add:
    os.environ["PATH"] = ";".join(paths_to_add) + ";" + os.environ.get("PATH", "")

import json
import numpy as np
import pandas as pd
import onnxruntime as rt
import huggingface_hub
from PIL import Image

# Setup directories
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THUMBNAILS_DIR = os.path.join(REPO_DIR, 'thumbnails')
CHARACTER_LIST_PATH = os.path.join(REPO_DIR, 'character_list.json')
TAGS_CACHE_PATH = os.path.join(REPO_DIR, 'tags_cache.json')

MODEL_REPO = "SmilingWolf/wd-vit-large-tagger-v3"
MODEL_FILENAME = "model.onnx"
LABEL_FILENAME = "selected_tags.csv"

SCORE_GENERAL_THRESH = 0.35
SCORE_CHARACTER_THRESH = 0.85

kaomojis = [
    "0_0", "(o)_(o)", "+_+", "+_-", "._.", "<o>_<o>", "<|>_<|>", "=_=",
    ">_<", "3_3", "6_9", ">_o", "@_@", "^_^", "o_o", "u_u", "x_x", "|_|", "||_||",
]

def load_labels(dataframe) -> tuple:
    name_series = dataframe["name"]
    name_series = name_series.map(
        lambda x: x.replace("_", " ") if x not in kaomojis else x
    )
    tag_names = name_series.tolist()
    rating_indexes = list(np.where(dataframe["category"] == 9)[0])
    general_indexes = list(np.where(dataframe["category"] == 0)[0])
    character_indexes = list(np.where(dataframe["category"] == 4)[0])
    return tag_names, rating_indexes, general_indexes, character_indexes

class WDImageTagger:
    def __init__(self):
        print(f"Downloading/Loading WD-Tagger model from {MODEL_REPO}...")
        csv_path = huggingface_hub.hf_hub_download(MODEL_REPO, LABEL_FILENAME)
        model_path = huggingface_hub.hf_hub_download(MODEL_REPO, MODEL_FILENAME)
        
        tags_df = pd.read_csv(csv_path)
        self.tag_names, self.rating_indexes, self.general_indexes, self.character_indexes = load_labels(tags_df)
        
        # Load ONNX session (ONNXRuntime optimizes this automatically for CPU/GPU)
        self.session = rt.InferenceSession(model_path, providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        _, height, width, _ = self.session.get_inputs()[0].shape
        self.target_size = height
        print(f"Model loaded successfully. Target resolution: {self.target_size}x{self.target_size}")

    def prepare_image(self, image):
        # Convert RGBA to RGB using a clean white background canvas
        if image.mode == 'RGBA':
            canvas = Image.new("RGBA", image.size, (255, 255, 255))
            canvas.alpha_composite(image)
            image = canvas.convert("RGB")
        else:
            image = image.convert("RGB")

        # Pad image to square
        w, h = image.size
        max_dim = max(w, h)
        pad_left = (max_dim - w) // 2
        pad_top = (max_dim - h) // 2

        padded_image = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))
        padded_image.paste(image, (pad_left, pad_top))

        # Resize to model input target size
        if max_dim != self.target_size:
            padded_image = padded_image.resize((self.target_size, self.target_size), Image.Resampling.BICUBIC)

        image_array = np.asarray(padded_image, dtype=np.float32)
        # Convert PIL-native RGB to BGR as expected by the model
        image_array = image_array[:, :, ::-1]
        return np.expand_dims(image_array, axis=0)

    def tag_image(self, image_path):
        try:
            with Image.open(image_path) as img:
                prepared = self.prepare_image(img)
        except Exception as e:
            return None, f"Failed to load image: {e}"

        input_name = self.session.get_inputs()[0].name
        label_name = self.session.get_outputs()[0].name
        
        # Run model inference
        preds = self.session.run([label_name], {input_name: prepared})[0]
        labels = list(zip(self.tag_names, preds[0].astype(float)))

        # 1. Characters: threshold >= 0.85
        char_tags = [labels[i] for i in self.character_indexes if labels[i][1] >= SCORE_CHARACTER_THRESH]
        char_tags.sort(key=lambda x: x[1], reverse=True)

        # 2. General Tags: threshold >= 0.35
        general_tags = [labels[i] for i in self.general_indexes if labels[i][1] >= SCORE_GENERAL_THRESH]
        general_tags.sort(key=lambda x: x[1], reverse=True)

        # Combine: Characters first, then general tags
        sorted_tags = [item[0] for item in char_tags] + [item[0] for item in general_tags]
        return sorted_tags, None

def main():
    print("=" * 60)
    print("LIVE2D PORTAL — WD14 TAG SCANNER")
    print("=" * 60)

    if not os.path.exists(CHARACTER_LIST_PATH):
        print(f"Error: {CHARACTER_LIST_PATH} not found.")
        sys.exit(1)

    with open(CHARACTER_LIST_PATH, 'r', encoding='utf-8') as f:
        character_list = json.load(f)

    # Load tags cache to support resuming
    tags_cache = {}
    if os.path.exists(TAGS_CACHE_PATH):
        try:
            with open(TAGS_CACHE_PATH, 'r', encoding='utf-8') as f:
                tags_cache = json.load(f)
            print(f"Loaded {len(tags_cache)} cached tags.")
        except Exception as e:
            print(f"Error loading cache: {e}. Starting fresh.")

    # Find models requiring tagging
    targets = []
    for char in character_list:
        slug = char['slug']
        # If it has a thumbnail and is not already tagged in cache
        if char.get('hasThumbnail', False):
            if slug not in tags_cache:
                targets.append(char)

    print(f"Total models in list: {len(character_list)}")
    print(f"Models needing tagging: {len(targets)}")

    if not targets:
        print("All models are already tagged.")
        # Ensure tags are merged into the main character list just in case
        for char in character_list:
            slug = char['slug']
            char['tags'] = tags_cache.get(slug, [])
        with open(CHARACTER_LIST_PATH, 'w', encoding='utf-8') as f:
            json.dump(character_list, f, ensure_ascii=False, indent=4)
        print("Synced character_list.json with tags cache.")
        return

    # Load tagger
    tagger = WDImageTagger()

    # Process models
    processed_count = 0
    save_interval = 50

    try:
        for idx, char in enumerate(targets, 1):
            slug = char['slug']
            image_path = os.path.join(THUMBNAILS_DIR, f"{slug}.png")

            if not os.path.exists(image_path):
                # Mark as empty tags if image is missing
                tags_cache[slug] = []
                continue

            tags, err = tagger.tag_image(image_path)
            if err:
                print(f"  [{idx}/{len(targets)}] [{slug}] Error: {err}")
                continue

            tags_cache[slug] = tags
            processed_count += 1

            if idx % 10 == 0 or idx == len(targets):
                print(f"  [{idx}/{len(targets)}] Tagged {slug} -> Tags: {tags[:5]}")

            # Save periodically
            if idx % save_interval == 0:
                with open(TAGS_CACHE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(tags_cache, f, ensure_ascii=False, indent=4)
                print(f"  --> Saved cache checkpoint ({len(tags_cache)} items total).")

    except KeyboardInterrupt:
        print("\nProcess interrupted. Saving tags cache...")
        with open(TAGS_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(tags_cache, f, ensure_ascii=False, indent=4)
        sys.exit(0)

    # Save final cache
    with open(TAGS_CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(tags_cache, f, ensure_ascii=False, indent=4)

    # Merge tags into master character list
    for char in character_list:
        slug = char['slug']
        char['tags'] = tags_cache.get(slug, [])

    with open(CHARACTER_LIST_PATH, 'w', encoding='utf-8') as f:
        json.dump(character_list, f, ensure_ascii=False, indent=4)

    print("\n" + "=" * 60)
    print("TAG SCANNING COMPLETE")
    print(f"Successfully processed: {processed_count} new tags.")
    print("=" * 60)

if __name__ == '__main__':
    main()
