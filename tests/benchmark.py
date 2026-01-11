"""Quick benchmark for CLIP performance."""
import time
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from pathlib import Path

print('=== CLIP Benchmark ===')
print()

# Check device
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Device: {device}')
if device == 'cuda':
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')
print()

# Load model
print('Loading CLIP model...')
t0 = time.time()
model = CLIPModel.from_pretrained('openai/clip-vit-base-patch32').to(device)
processor = CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32', use_fast=True)
model.eval()
print(f'Model load time: {time.time() - t0:.2f}s')
print()

# Find test images
source = Path(r'Z:\Zefram Photography')
test_images = list(source.rglob('*.jpg'))[:20]
print(f'Found {len(test_images)} test images')

# Benchmark embedding computation
print()
print('Benchmarking image embedding...')
times = []
for img_path in test_images:
    try:
        t0 = time.time()
        img = Image.open(img_path).convert('RGB')
        img.thumbnail((512, 512))
        inputs = processor(images=img, return_tensors='pt').to(device)
        with torch.no_grad():
            embedding = model.get_image_features(**inputs)
        if device == 'cuda':
            torch.cuda.synchronize()
        times.append(time.time() - t0)
        print(f'  {img_path.name}: {times[-1]*1000:.1f} ms')
    except Exception as e:
        print(f'  Error: {img_path.name}: {e}')

if times:
    avg_time = sum(times) / len(times)
    print()
    print(f'Average time per image: {avg_time*1000:.1f} ms')
    print(f'Images per second: {1/avg_time:.1f}')
    print(f'Estimated time for 10,000 images: {10000 * avg_time / 60:.1f} minutes')
