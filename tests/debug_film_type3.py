"""Test film type detection for all categories."""
import sys
sys.path.insert(0, r'C:\projects\photoMotifs')
from pathlib import Path
from photo_search import detect_film_type

test_cases = [
    # Color negatives - should return 'color_negative'
    (r'Z:\Zefram Photography\Analog\Nikon F\Roll 20 CineStill 800T\test.dng', 'color_negative'),
    (r'Z:\Zefram Photography\Analog\Nikon F\Roll 14 Kodak Portra 400\test.dng', 'color_negative'),
    (r'Z:\Zefram Photography\Analog\Nikon F\Roll 18 Kodak Gold 200\test.dng', 'color_negative'),
    (r'Z:\Zefram Photography\Analog\Nikon F\Roll 15 Kodak Ektar 100\test.dng', 'color_negative'),

    # Slide films - should return 'slide'
    (r'Z:\Zefram Photography\Analog\Nikon F\Roll 12 Fujifilm Velvia 50\test.dng', 'slide'),
    (r'Z:\Zefram Photography\Analog\Nikon F\Roll 9 Kodak Ektachrome 100\test.dng', 'slide'),

    # B&W negatives - should return 'bw_negative'
    (r'Z:\Zefram Photography\Analog\Nikon F\Roll 6 Kodak TMAX 100\test.dng', 'bw_negative'),
    (r'Z:\Zefram Photography\Analog\Nikon F\Roll 19 Illford HP5 Pushed 2\test.dng', 'bw_negative'),
    (r'Z:\Zefram Photography\Analog\AkArette\Roll 4 Ilford Delta 400\test.dng', 'bw_negative'),

    # Already processed TIF - should return 'already_processed'
    (r'Z:\Zefram Photography\Analog\Nikon F\Roll 2 CineStill 50D\Roll 2 CineStill 50D Underdog\test.tif', 'already_processed'),
    (r'Z:\Zefram Photography\Analog\Nikon F\Roll 5 Kodak Portra 400 Nikon Scan\test.tif', 'already_processed'),

    # DNG in Nikon Scan folder - should still be 'color_negative' (raw data)
    (r'Z:\Zefram Photography\Analog\Nikon F\Roll 5 Kodak Portra 400 Nikon Scan\test.dng', 'color_negative'),

    # Non-analog - should return 'not_analog'
    (r'Z:\Zefram Photography\Photo Walks\test.jpg', 'not_analog'),
]

print('=' * 80)
print('FILM TYPE DETECTION TEST')
print('=' * 80)

passed = 0
failed = 0
for path_str, expected in test_cases:
    result = detect_film_type(Path(path_str))
    status = 'PASS' if result == expected else 'FAIL'
    if result == expected:
        passed += 1
    else:
        failed += 1
        print(f'{status}: {Path(path_str).parent.name}/{Path(path_str).name}')
        print(f'  Expected: {expected}')
        print(f'  Got: {result}')

print(f'\nResults: {passed} passed, {failed} failed')
