"""Check Lightroom develop settings for Analog images."""
import sqlite3
from pathlib import Path

CATALOG_PATH = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4.lrcat")

conn = sqlite3.connect(f'file:{CATALOG_PATH}?mode=ro', uri=True)
cursor = conn.cursor()

# First, find Analog images
print("=" * 80)
print("FINDING ANALOG IMAGES IN LIGHTROOM CATALOG")
print("=" * 80)

cursor.execute("""
    SELECT
        i.id_local,
        f.baseName,
        f.extension,
        fo.pathFromRoot,
        r.absolutePath
    FROM Adobe_images i
    JOIN AgLibraryFile f ON i.rootFile = f.id_local
    JOIN AgLibraryFolder fo ON f.folder = fo.id_local
    JOIN AgLibraryRootFolder r ON fo.rootFolder = r.id_local
    WHERE fo.pathFromRoot LIKE '%Analog%'
    LIMIT 20
""")

analog_images = cursor.fetchall()
print(f"Found {len(analog_images)} Analog images (showing first 20)")

# Look for develop settings table
print("\n" + "=" * 80)
print("CHECKING DEVELOP SETTINGS TABLE")
print("=" * 80)

# List tables that might contain develop settings
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%Develop%' OR name LIKE '%Setting%' OR name LIKE '%Camera%'")
tables = cursor.fetchall()
print(f"Relevant tables: {[t[0] for t in tables]}")

# Check Adobe_imageDevelopSettings
try:
    cursor.execute("PRAGMA table_info(Adobe_imageDevelopSettings)")
    cols = cursor.fetchall()
    print(f"\nAdobe_imageDevelopSettings columns: {[c[1] for c in cols[:20]]}...")
except:
    print("Table Adobe_imageDevelopSettings not found")

# Try to get develop settings for first Analog image
if analog_images:
    img_id = analog_images[0][0]
    img_name = analog_images[0][1]
    img_path = analog_images[0][3]
    print(f"\nChecking develop settings for: {img_name} ({img_path})")

    try:
        cursor.execute("""
            SELECT * FROM Adobe_imageDevelopSettings WHERE image = ? LIMIT 1
        """, (img_id,))
        settings = cursor.fetchone()
        if settings:
            cursor.execute("PRAGMA table_info(Adobe_imageDevelopSettings)")
            cols = [c[1] for c in cursor.fetchall()]
            print(f"Develop settings found!")
            for col, val in zip(cols, settings):
                if val is not None and val != '':
                    print(f"  {col}: {str(val)[:100]}")
        else:
            print("No develop settings found")
    except Exception as e:
        print(f"Error: {e}")

# Check for camera profiles in develop settings
print("\n" + "=" * 80)
print("CHECKING FOR NEGATIVE LAB / CAMERA PROFILES")
print("=" * 80)

try:
    cursor.execute("""
        SELECT
            i.id_local,
            f.baseName,
            fo.pathFromRoot,
            d.profileName
        FROM Adobe_images i
        JOIN AgLibraryFile f ON i.rootFile = f.id_local
        JOIN AgLibraryFolder fo ON f.folder = fo.id_local
        LEFT JOIN Adobe_imageDevelopSettings d ON i.id_local = d.image
        WHERE fo.pathFromRoot LIKE '%Analog%'
        AND d.profileName IS NOT NULL
        LIMIT 20
    """)
    results = cursor.fetchall()
    print(f"Found {len(results)} images with profile names")
    for r in results[:10]:
        print(f"  {r[1]} ({r[2]}): {r[3]}")
except Exception as e:
    print(f"Error: {e}")

# Check specific film types
print("\n" + "=" * 80)
print("CHECKING BY FILM TYPE IN PATH")
print("=" * 80)

film_types = [
    ("Velvia", "Slide film - NO inversion"),
    ("Ektachrome", "Slide film - NO inversion"),
    ("Portra", "Color negative - needs inversion"),
    ("CineStill", "Color negative - needs inversion"),
    ("TMAX", "B&W negative - needs simple inversion"),
    ("Ilford", "B&W negative - needs simple inversion"),
    ("Underdog", "Already processed - NO inversion"),
]

for film, desc in film_types:
    cursor.execute("""
        SELECT COUNT(*) FROM Adobe_images i
        JOIN AgLibraryFile f ON i.rootFile = f.id_local
        JOIN AgLibraryFolder fo ON f.folder = fo.id_local
        WHERE fo.pathFromRoot LIKE ?
    """, (f'%Analog%{film}%',))
    count = cursor.fetchone()[0]
    print(f"  {film}: {count} images ({desc})")

conn.close()
