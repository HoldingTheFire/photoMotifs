"""Test film type detection logic."""
import sys
sys.path.insert(0, r'C:\projects\photoMotifs')

from pathlib import Path
from photo_search import detect_film_type, get_lightroom_profile

# Test paths
test_cases = [
    # Slide films - should return 'slide'
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 12 Fujifilm Velvia 50\test.dng"), "slide"),
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 9 Kodak Ektachrome 100\test.dng"), "slide"),
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 4 Fujifilm Velvia 50\test.dng"), "slide"),

    # B&W negative - should return 'bw_negative'
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 6 Kodak TMAX 100\test.dng"), "bw_negative"),
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 19 Illford HP5 Pushed 2\test.dng"), "bw_negative"),
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 10 Fujifilm Acros100II\test.dng"), "bw_negative"),
    (Path(r"Z:\Zefram Photography\Analog\AkArette\Roll 4 Ilford Delta 400\test.dng"), "bw_negative"),
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 13 Ferraina Orto 50\test.dng"), "bw_negative"),

    # Color negative - should return 'color_negative'
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 14 Kodak Portra 400\test.dng"), "color_negative"),
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 11 CineStill 400D\test.dng"), "color_negative"),
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 18 Kodak Gold 200\test.dng"), "color_negative"),
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 15 Kodak Ektar 100\test.dng"), "color_negative"),

    # Already processed - should return 'already_processed'
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 2 CineStill 50D\Roll 2 CineStill 50D Underdog\test.tif"), "already_processed"),
    (Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 5 Kodak Portra 400 Nikon Scan\test.tif"), "already_processed"),

    # Non-analog - should return 'not_analog'
    (Path(r"Z:\Zefram Photography\Photo Walks\Downtown\test.jpg"), "not_analog"),
]

print("=" * 80)
print("TESTING FILM TYPE DETECTION")
print("=" * 80)

passed = 0
failed = 0

for path, expected in test_cases:
    result = detect_film_type(path)
    status = "PASS" if result == expected else "FAIL"

    if result == expected:
        passed += 1
    else:
        failed += 1
        print(f"\n{status}: {path.parent.name}/{path.name}")
        print(f"  Expected: {expected}")
        print(f"  Got: {result}")

print(f"\n{'=' * 80}")
print(f"RESULTS: {passed} passed, {failed} failed")
print(f"{'=' * 80}")

# Also test Lightroom profile detection
print("\n" + "=" * 80)
print("TESTING LIGHTROOM PROFILE LOOKUP")
print("=" * 80)

# Real paths that exist
real_test_paths = [
    Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 14 Kodak Portra 400\NikonF_Roll14_KodakPortra400_01.dng"),
    Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 12 Fujifilm Velvia 50\NikonF_Roll12_FujifilmVelvia50_01.dng"),
]

for path in real_test_paths:
    if path.exists():
        profile = get_lightroom_profile(path)
        film_type = detect_film_type(path)
        print(f"\n{path.parent.name}/{path.name}:")
        print(f"  LR Profile: {profile or '(none)'}")
        print(f"  Film Type: {film_type}")
    else:
        print(f"\n{path.parent.name}/{path.name}: FILE NOT FOUND")
