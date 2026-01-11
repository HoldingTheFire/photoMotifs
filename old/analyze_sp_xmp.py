"""Analyze XMP metadata in Smart Preview DNGs."""
from pathlib import Path

sp_dir = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4 Smart Previews.lrdata")
analog_dir = Path(r"Z:\Zefram Photography\Analog")

# Get some Smart Preview files
sp_files = list(sp_dir.rglob("*.dng"))[:5]

print("=" * 80)
print("ANALYZING SMART PREVIEW XMP METADATA")
print("=" * 80)

for sp in sp_files:
    print(f"\nFile: {sp.name}")
    with open(sp, 'rb') as f:
        data = f.read()

    xmp_start = data.find(b'<x:xmpmeta')
    if xmp_start != -1:
        xmp_end = data.find(b'</x:xmpmeta>', xmp_start)
        xmp = data[xmp_start:xmp_end + 12].decode('utf-8', errors='ignore')
        print(f"XMP found ({len(xmp)} bytes):")
        print(xmp[:2000])
    else:
        print("No XMP found in standard location")

# Now check original Analog files
print("\n" + "=" * 80)
print("COMPARING WITH ORIGINAL ANALOG DNGs")
print("=" * 80)

# Check different film types
test_files = [
    analog_dir / "Nikon F" / "Roll 12 Fujifilm Velvia 50" / "NikonF_Roll12_FujifilmVelvia50_01.dng",  # Slide film
    analog_dir / "Nikon F" / "Roll 14 Kodak Portra 400" / "NikonF_Roll14_KodakPortra400_01.dng",  # Negative film
]

for f in test_files:
    if f.exists():
        print(f"\n{f.relative_to(analog_dir)}")
        with open(f, 'rb') as fh:
            data = fh.read()

        xmp_start = data.find(b'<x:xmpmeta')
        if xmp_start != -1:
            xmp_end = data.find(b'</x:xmpmeta>', xmp_start)
            xmp = data[xmp_start:xmp_end + 12].decode('utf-8', errors='ignore')

            # Look for key indicators
            indicators = {
                'CameraProfile': 'crs:CameraProfile="',
                'ToneCurvePV2012': 'crs:ToneCurvePV2012',
                'ProcessVersion': 'crs:ProcessVersion',
                'NegativeLabPro': 'Negative Lab',
                'InvertImage': 'InvertImage',
            }

            print("XMP indicators found:")
            for name, pattern in indicators.items():
                if pattern in xmp:
                    # Extract the value
                    start = xmp.find(pattern)
                    end = xmp.find('"', start + len(pattern) + 2)
                    if end > start:
                        value = xmp[start:end+1]
                        print(f"  {name}: {value[:80]}")
                    else:
                        print(f"  {name}: PRESENT")

            print(f"\nFull XMP ({len(xmp)} bytes):")
            print(xmp[:1500])
    else:
        print(f"\nFILE NOT FOUND: {f}")
