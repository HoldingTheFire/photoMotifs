"""Check camera profiles used for Analog images."""
import sqlite3
import re
from pathlib import Path

CATALOG_PATH = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4.lrcat")

conn = sqlite3.connect(f'file:{CATALOG_PATH}?mode=ro', uri=True)
cursor = conn.cursor()

print("=" * 80)
print("CAMERA PROFILES USED IN ANALOG FOLDER")
print("=" * 80)

cursor.execute("""
    SELECT
        f.baseName,
        fo.pathFromRoot,
        d.text
    FROM Adobe_images i
    JOIN AgLibraryFile f ON i.rootFile = f.id_local
    JOIN AgLibraryFolder fo ON f.folder = fo.id_local
    LEFT JOIN Adobe_imageDevelopSettings d ON i.id_local = d.image
    WHERE fo.pathFromRoot LIKE '%Analog%'
    AND d.text IS NOT NULL
    LIMIT 100
""")

profiles = {}
samples = {}
for row in cursor.fetchall():
    name, path, text = row
    # Extract CameraProfile from text
    match = re.search(r'CameraProfile\s*=\s*"([^"]+)"', text)
    if match:
        profile = match.group(1)
        profiles[profile] = profiles.get(profile, 0) + 1
        if profile not in samples:
            samples[profile] = f"{name} ({path})"

print("\nCamera profiles found:")
for profile, count in sorted(profiles.items(), key=lambda x: -x[1]):
    print(f"  {profile}: {count} images")
    print(f"    Example: {samples[profile]}")

# Check specific film types with their profiles
print("\n" + "=" * 80)
print("PROFILES BY FILM TYPE")
print("=" * 80)

film_queries = [
    ("Velvia (slide)", "%Velvia%"),
    ("Portra (negative)", "%Portra%"),
    ("CineStill (negative)", "%CineStill%"),
    ("TMAX (B&W)", "%TMAX%"),
    ("Ilford (B&W)", "%Ilford%"),
    ("Underdog (processed)", "%Underdog%"),
]

for label, pattern in film_queries:
    cursor.execute("""
        SELECT d.text
        FROM Adobe_images i
        JOIN AgLibraryFile f ON i.rootFile = f.id_local
        JOIN AgLibraryFolder fo ON f.folder = fo.id_local
        LEFT JOIN Adobe_imageDevelopSettings d ON i.id_local = d.image
        WHERE fo.pathFromRoot LIKE ?
        AND d.text IS NOT NULL
        LIMIT 5
    """, (f'%Analog%{pattern}',))

    print(f"\n{label}:")
    film_profiles = set()
    for row in cursor.fetchall():
        match = re.search(r'CameraProfile\s*=\s*"([^"]+)"', row[0])
        if match:
            film_profiles.add(match.group(1))
    if film_profiles:
        for p in film_profiles:
            print(f"  - {p}")
    else:
        print("  (no profile data found)")

conn.close()
