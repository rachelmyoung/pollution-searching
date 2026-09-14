#!/usr/bin/env python3
"""
Filter geocoded data to keep only high-quality records with coordinates.

High quality includes:
- Records that already had coordinates
- Census geocoded records
- Google Maps high-quality geocodes (ROOFTOP, RANGE_INTERPOLATED)
- Parsed from address

Output: CSV with lat, lon, indicator (3 columns only)
"""

import csv
from pathlib import Path

# Configuration
INPUT_FILE = "sitelist_geocoded_with_metadata.csv"
OUTPUT_FILE = "CERCLIS_test_labels.csv"

# High quality location types for Google geocodes
HIGH_QUALITY_GOOGLE = {'ROOFTOP', 'RANGE_INTERPOLATED'}


def get_coordinates(row):
    """
    Extract coordinates from the appropriate columns.

    Returns: (lat, lon) or (None, None) if invalid
    """
    # If record already had coordinates, use original columns
    if not row.get('GEOCODE_METHOD') or row.get('GEOCODE_METHOD') == '':
        lat = row.get('LATITUDE', '').strip()
        lon = row.get('LONGITUDE', '').strip()
    else:
        # Use new geocoded coordinates
        lat = row.get('LATITUDE_NEW', '').strip()
        lon = row.get('LONGITUDE_NEW', '').strip()

    # Validate coordinates exist and are not empty
    if not lat or not lon:
        return None, None

    try:
        lat_float = float(lat)
        lon_float = float(lon)
        return lat_float, lon_float
    except (ValueError, TypeError):
        return None, None


def is_high_quality(row):
    """
    Determine if a record is high quality.

    Returns: True if high quality, False otherwise
    """
    method = row.get('GEOCODE_METHOD', '').strip()
    location_type = row.get('LOCATION_TYPE', '').strip()

    # Already had coordinates - consider high quality
    if not method or method == '':
        return True

    # Parsed from address - high quality
    if method == 'parsed_from_address':
        return True

    # Census geocoded - high quality
    if method == 'census':
        return True

    # Google geocoded - only if high quality location type
    if method == 'google':
        if location_type in HIGH_QUALITY_GOOGLE:
            return True
        else:
            return False

    # Failed or other - not high quality
    return False


def main():
    """Main filtering workflow"""
    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        return

    print(f"Reading input file: {INPUT_FILE}")

    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total records in input: {len(rows):,}")

    # Filter and transform records
    output_records = []

    stats = {
        'total': len(rows),
        'high_quality': 0,
        'low_quality': 0,
        'missing_coords': 0,
        'invalid_coords': 0
    }

    for row in rows:
        # Check if high quality
        if not is_high_quality(row):
            stats['low_quality'] += 1
            continue

        # Get coordinates
        lat, lon = get_coordinates(row)

        if lat is None or lon is None:
            stats['missing_coords'] += 1
            continue

        # Get indicator variable
        indicator = row.get('npl01', '').strip()

        # Create output record
        output_records.append({
            'lat': lat,
            'lon': lon,
            'indicator': indicator
        })

        stats['high_quality'] += 1

    # Write output
    print(f"\nWriting output file: {OUTPUT_FILE}")

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['lat', 'lon', 'indicator']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_records)

    # Print statistics
    print("\n" + "="*70)
    print("FILTERING SUMMARY")
    print("="*70)
    print(f"Total records in input:        {stats['total']:>10,}")
    print(f"High quality (kept):           {stats['high_quality']:>10,} ({stats['high_quality']/stats['total']*100:>5.1f}%)")
    print(f"Low quality (filtered out):    {stats['low_quality']:>10,} ({stats['low_quality']/stats['total']*100:>5.1f}%)")
    print(f"Missing/invalid coordinates:   {stats['missing_coords']:>10,} ({stats['missing_coords']/stats['total']*100:>5.1f}%)")
    print("="*70)
    print(f"\nOutput written to: {OUTPUT_FILE}")
    print(f"Records in output: {len(output_records):,}")
    print(f"Columns: lat, lon, indicator")


if __name__ == "__main__":
    main()
