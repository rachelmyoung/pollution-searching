#!/usr/bin/env python3
"""
Geocode CERCLIS site addresses using a three-phase approach:
1. Parse embedded UTM coordinates from address text
2. Geocode using Census Bureau API
3. Geocode remaining failures using Google Maps API
"""

import csv
import re
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

# Third-party imports
try:
    import requests
    from pyproj import Transformer
except ImportError:
    print("Required packages not installed. Please run:")
    print("pip install requests pyproj")
    exit(1)

# Configuration
INPUT_FILE = "sitelist_nogeocodes.csv"
OUTPUT_FILE = "sitelist_geocoded.csv"
FAILED_FILE = "sitelist_failed_geocode.csv"
LOG_FILE = "geocoding_log.txt"
PROGRESS_FILE = "geocoding_progress.json"

# API Configuration
CENSUS_BASE_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
GOOGLE_API_KEY = ""  # USER MUST SET THIS

# Rate limiting
CENSUS_RATE_LIMIT = 0.35  # seconds between requests (2.8 req/sec)
GOOGLE_RATE_LIMIT = 0.05  # seconds between requests (20 req/sec)

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds, will multiply by attempt number

# UTM zones for US states (simplified - using most common zone per state)
STATE_UTM_ZONES = {
    'AL': 16, 'AK': 5, 'AZ': 12, 'AR': 15, 'CA': 11, 'CO': 13, 'CT': 18,
    'DE': 18, 'FL': 17, 'GA': 17, 'HI': 4, 'ID': 11, 'IL': 16, 'IN': 16,
    'IA': 15, 'KS': 14, 'KY': 16, 'LA': 15, 'ME': 19, 'MD': 18, 'MA': 19,
    'MI': 16, 'MN': 15, 'MS': 16, 'MO': 15, 'MT': 12, 'NE': 14, 'NV': 11,
    'NH': 19, 'NJ': 18, 'NM': 13, 'NY': 18, 'NC': 17, 'ND': 14, 'OH': 17,
    'OK': 14, 'OR': 10, 'PA': 18, 'RI': 19, 'SC': 17, 'SD': 14, 'TN': 16,
    'TX': 14, 'UT': 12, 'VT': 18, 'VA': 18, 'WA': 10, 'WV': 17, 'WI': 16,
    'WY': 13
}


class GeocodingStats:
    """Track geocoding statistics"""
    def __init__(self):
        self.already_had = 0
        self.parsed_from_address = 0
        self.census_success = 0
        self.census_failed = 0
        self.google_success = 0
        self.google_failed = 0
        self.total_processed = 0
        self.start_time = datetime.now()

    def report(self) -> str:
        """Generate statistics report"""
        elapsed = datetime.now() - self.start_time
        total_geocoded = self.parsed_from_address + self.census_success + self.google_success
        total_attempted = self.census_failed + self.google_failed

        return f"""
=== Geocoding Statistics ===
Processing Time: {elapsed}
Total Records: {self.total_processed}

Already Had Coordinates: {self.already_had}
Parsed from Address: {self.parsed_from_address}
Census Geocoder Success: {self.census_success}
Census Geocoder Failed: {self.census_failed}
Google Maps Success: {self.google_success}
Google Maps Failed: {self.google_failed}

Total Successfully Geocoded: {total_geocoded}
Final Failure Count: {self.google_failed}
Success Rate: {(self.already_had + total_geocoded) / self.total_processed * 100:.1f}%
"""


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )


def parse_utm_from_address(streetaddress: str, streetaddress2: str, state: str) -> Optional[Tuple[float, float]]:
    """
    Parse UTM coordinates from address text and convert to lat/long.

    Returns: (latitude, longitude) or None if not found/invalid
    """
    addr_text = f"{streetaddress} {streetaddress2}".upper()

    # Pattern for UTM coordinates like "E667500 : N4041480" or "12568459E 4097500 N"
    patterns = [
        # Pattern 1: E######: N#######
        r'E\s*([0-9,\s]+)\s*:?\s*N\s*([0-9,\s]+)',
        # Pattern 2: Zone followed by E and N
        r'UTM\s*(\d{1,2})\s*([0-9]+)\s*E\s*([0-9]+)\s*N',
        # Pattern 3: E N with UTM indicator
        r'E\s*([0-9,\s]+).*?N\s*([0-9,\s]+).*?U\.?T\.?M',
    ]

    zone = None
    easting = None
    northing = None

    for i, pattern in enumerate(patterns):
        match = re.search(pattern, addr_text, re.IGNORECASE)
        if match:
            try:
                if i == 1:  # Zone is in match
                    zone_str = match.group(1).strip()
                    easting_str = match.group(2).replace(',', '').replace(' ', '').strip()
                    northing_str = match.group(3).replace(',', '').replace(' ', '').strip()

                    if not zone_str or not easting_str or not northing_str:
                        continue  # Skip this pattern, try next

                    zone = int(zone_str)
                    easting = int(easting_str)
                    northing = int(northing_str)
                else:
                    easting_str = match.group(1).replace(',', '').replace(' ', '').strip()
                    northing_str = match.group(2).replace(',', '').replace(' ', '').strip()

                    if not easting_str or not northing_str:
                        continue  # Skip this pattern, try next

                    easting = int(easting_str)
                    northing = int(northing_str)
                break
            except (ValueError, AttributeError):
                # If conversion fails, try next pattern
                continue

    if easting is None or northing is None:
        return None

    # Infer zone from state if not specified
    if zone is None:
        zone = STATE_UTM_ZONES.get(state)
        if zone is None:
            logging.warning(f"Could not determine UTM zone for state {state}")
            return None

    # Validate UTM coordinates (basic sanity check)
    if not (100000 <= easting <= 900000 and 1000000 <= northing <= 10000000):
        logging.warning(f"Invalid UTM coordinates: E{easting} N{northing}")
        return None

    try:
        # Convert UTM to lat/long
        # Assuming WGS84 datum (EPSG:4326)
        transformer = Transformer.from_crs(
            f"EPSG:326{zone:02d}",  # UTM zone (northern hemisphere)
            "EPSG:4326",  # WGS84 lat/long
            always_xy=True
        )
        lon, lat = transformer.transform(easting, northing)

        # Validate result is in reasonable US bounds
        if 24 <= lat <= 72 and -180 <= lon <= -65:
            return (lat, lon)
        else:
            logging.warning(f"Converted coordinates out of US bounds: {lat}, {lon}")
            return None

    except Exception as e:
        logging.error(f"Error converting UTM to lat/long: {e}")
        return None


def geocode_census(address: str, retry_count: int = 0) -> Optional[Tuple[float, float]]:
    """
    Geocode address using Census Bureau API.

    Returns: (latitude, longitude) or None if failed
    """
    params = {
        'address': address,
        'benchmark': 'Public_AR_Current',
        'format': 'json'
    }

    try:
        response = requests.get(CENSUS_BASE_URL, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Check if we got results
        if data.get('result', {}).get('addressMatches'):
            match = data['result']['addressMatches'][0]
            coords = match['coordinates']
            lat = float(coords['y'])
            lon = float(coords['x'])

            # Validate coordinates
            if 24 <= lat <= 72 and -180 <= lon <= -65:
                return (lat, lon)

        return None

    except requests.exceptions.RequestException as e:
        if retry_count < MAX_RETRIES:
            wait_time = RETRY_BACKOFF * (retry_count + 1)
            logging.warning(f"Census API error, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)
            return geocode_census(address, retry_count + 1)
        else:
            logging.error(f"Census API failed after {MAX_RETRIES} retries: {e}")
            return None
    except (KeyError, ValueError, IndexError) as e:
        logging.debug(f"Census API returned no results for: {address}")
        return None


def geocode_google(address: str, retry_count: int = 0) -> Optional[Tuple[float, float, str, str, bool]]:
    """
    Geocode address using Google Maps API and return metadata.

    Returns: (latitude, longitude, location_type, formatted_address, partial_match) or None if failed
    """
    if not GOOGLE_API_KEY:
        logging.error("Google API key not set!")
        return None

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'address': address,
        'key': GOOGLE_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data['status'] == 'OK' and data['results']:
            result = data['results'][0]

            # Extract coordinates
            location = result['geometry']['location']
            lat = float(location['lat'])
            lon = float(location['lng'])

            # Extract metadata
            location_type = result['geometry'].get('location_type', 'UNKNOWN')
            formatted_address = result.get('formatted_address', '')
            partial_match = result.get('partial_match', False)

            # Validate coordinates
            if 24 <= lat <= 72 and -180 <= lon <= -65:
                return (lat, lon, location_type, formatted_address, partial_match)
        elif data['status'] == 'ZERO_RESULTS':
            return None
        elif data['status'] in ['OVER_QUERY_LIMIT', 'REQUEST_DENIED']:
            logging.error(f"Google API error: {data['status']}")
            return None

        return None

    except requests.exceptions.RequestException as e:
        if retry_count < MAX_RETRIES:
            wait_time = RETRY_BACKOFF * (retry_count + 1)
            logging.warning(f"Google API error, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)
            return geocode_google(address, retry_count + 1)
        else:
            logging.error(f"Google API failed after {MAX_RETRIES} retries: {e}")
            return None
    except (KeyError, ValueError, IndexError) as e:
        logging.error(f"Error parsing Google API response: {e}")
        return None


def build_address_string(row: Dict) -> str:
    """Build clean address string for geocoding"""
    parts = []

    if row['STREETADDRESS'].strip():
        parts.append(row['STREETADDRESS'].strip())

    if row['CITY'].strip():
        parts.append(row['CITY'].strip())

    if row['STATE'].strip():
        parts.append(row['STATE'].strip())

    if row['ZIP'].strip():
        parts.append(row['ZIP'].strip())

    return ', '.join(parts)


def is_ungecodable(row: Dict) -> bool:
    """Check if address is likely ungecodable"""
    addr = f"{row['STREETADDRESS']} {row['STREETADDRESS2']}".upper()

    ungecodable_patterns = [
        'POSTAL ADDRESS IS UNAVAILABLE',
        'ADDRESS UNAVAILABLE',
        'NO ADDRESS',
        'UNKNOWN ADDRESS'
    ]

    return any(pattern in addr for pattern in ungecodable_patterns)


def load_progress() -> Dict:
    """Load progress from checkpoint file"""
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'last_row': 0, 'geocoded_ids': []}


def save_progress(row_num: int, geocoded_ids: List[str]):
    """Save progress checkpoint"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({
            'last_row': row_num,
            'geocoded_ids': geocoded_ids,
            'timestamp': datetime.now().isoformat()
        }, f)


def main():
    """Main geocoding workflow"""
    setup_logging()
    logging.info("Starting geocoding process")

    # Check if Google API key is set for Phase 3
    if not GOOGLE_API_KEY:
        logging.warning("Google API key not set. Phase 3 (Google geocoding) will be skipped.")
        logging.warning("Set GOOGLE_API_KEY in the script to enable Google Maps geocoding.")

    stats = GeocodingStats()

    # Load progress if resuming
    progress = load_progress()
    start_row = progress['last_row']

    # Open files
    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)
    failed_path = Path(FAILED_FILE)

    # Read all input data
    logging.info(f"Reading input file: {INPUT_FILE}")
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames + ['LATITUDE_NEW', 'LONGITUDE_NEW', 'GEOCODE_METHOD', 'GEOCODE_DATE', 'LOCATION_TYPE', 'FORMATTED_ADDRESS', 'PARTIAL_MATCH']
        rows = list(reader)

    total_rows = len(rows)
    logging.info(f"Total rows to process: {total_rows}")

    # Open output files for incremental writing
    # If resuming, we need to append; if starting fresh, write header
    output_mode = 'a' if start_row > 0 else 'w'
    failed_mode = 'a' if start_row > 0 else 'w'

    output_file = open(output_path, output_mode, newline='', encoding='utf-8')
    failed_file = open(failed_path, failed_mode, newline='', encoding='utf-8')

    output_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
    failed_writer = csv.DictWriter(failed_file, fieldnames=fieldnames)

    # Write headers if starting fresh
    if start_row == 0:
        output_writer.writeheader()
        failed_writer.writeheader()

    logging.info(f"Output files opened in {'append' if start_row > 0 else 'write'} mode")

    # Process each row
    try:
        for idx, row in enumerate(rows):
            stats.total_processed += 1

            # Skip if already processed
            if idx < start_row:
                continue

            # Initialize new columns
            row['LATITUDE_NEW'] = ''
            row['LONGITUDE_NEW'] = ''
            row['GEOCODE_METHOD'] = ''
            row['GEOCODE_DATE'] = datetime.now().strftime('%Y-%m-%d')
            row['LOCATION_TYPE'] = ''
            row['FORMATTED_ADDRESS'] = ''
            row['PARTIAL_MATCH'] = ''

            epaid = row['EPAID']

            # Check if already has coordinates
            if row['LATITUDE'] and row['LONGITUDE']:
                stats.already_had += 1
                output_writer.writerow(row)
                output_file.flush()  # Ensure it's written to disk
                if idx % 100 == 0:
                    logging.info(f"Progress: {idx}/{total_rows} - {stats.already_had} already had coordinates")
                continue

            # Check if ungecodable
            if is_ungecodable(row):
                logging.info(f"Skipping ungecodable address: {epaid}")
                row['GEOCODE_METHOD'] = 'ungecodable'
                failed_writer.writerow(row)
                failed_file.flush()
                continue

            # PHASE 1: Try parsing embedded coordinates
            parsed_coords = parse_utm_from_address(
                row['STREETADDRESS'],
                row['STREETADDRESS2'],
                row['STATE']
            )

            if parsed_coords:
                lat, lon = parsed_coords
                row['LATITUDE_NEW'] = f"{lat:.6f}"
                row['LONGITUDE_NEW'] = f"{lon:.6f}"
                row['GEOCODE_METHOD'] = 'parsed_from_address'
                stats.parsed_from_address += 1
                output_writer.writerow(row)
                output_file.flush()
                logging.info(f"Parsed coordinates for {epaid}: {lat:.6f}, {lon:.6f}")
                continue

            # Build address string for API geocoding
            address = build_address_string(row)

            if not address or len(address) < 10:
                logging.warning(f"Insufficient address info for {epaid}: {address}")
                row['GEOCODE_METHOD'] = 'insufficient_address'
                failed_writer.writerow(row)
                failed_file.flush()
                continue

            # PHASE 2: Try Census Geocoder
            time.sleep(CENSUS_RATE_LIMIT)
            census_coords = geocode_census(address)

            if census_coords:
                lat, lon = census_coords
                row['LATITUDE_NEW'] = f"{lat:.6f}"
                row['LONGITUDE_NEW'] = f"{lon:.6f}"
                row['GEOCODE_METHOD'] = 'census'
                stats.census_success += 1
                output_writer.writerow(row)
                output_file.flush()

                if idx % 100 == 0:
                    logging.info(f"Progress: {idx}/{total_rows} - Census success rate: {stats.census_success}/{stats.census_success + stats.census_failed}")
                continue

            stats.census_failed += 1

            # PHASE 3: Try Google Maps (if API key is set)
            if GOOGLE_API_KEY:
                time.sleep(GOOGLE_RATE_LIMIT)
                google_result = geocode_google(address)

                if google_result:
                    lat, lon, location_type, formatted_address, partial_match = google_result
                    row['LATITUDE_NEW'] = f"{lat:.6f}"
                    row['LONGITUDE_NEW'] = f"{lon:.6f}"
                    row['GEOCODE_METHOD'] = 'google'
                    row['LOCATION_TYPE'] = location_type
                    row['FORMATTED_ADDRESS'] = formatted_address
                    row['PARTIAL_MATCH'] = 'True' if partial_match else 'False'
                    stats.google_success += 1
                    output_writer.writerow(row)
                    output_file.flush()

                    if idx % 100 == 0:
                        logging.info(f"Progress: {idx}/{total_rows} - Google success rate: {stats.google_success}/{stats.google_failed + stats.google_success}")
                    continue

                stats.google_failed += 1
            else:
                stats.google_failed += 1

            # Failed all methods
            row['GEOCODE_METHOD'] = 'failed_all_methods'
            failed_writer.writerow(row)
            failed_file.flush()

            # Save progress every 500 rows
            if idx % 500 == 0:
                save_progress(idx, [])
                logging.info(f"Progress saved at row {idx}")

    finally:
        # Close output files
        output_file.close()
        failed_file.close()
        logging.info("Output files closed")

    # Print statistics
    logging.info(stats.report())
    print(stats.report())

    logging.info(f"Main output written to: {OUTPUT_FILE}")
    logging.info(f"Failed geocodes written to: {FAILED_FILE}")

    # Clean up progress file
    if Path(PROGRESS_FILE).exists():
        Path(PROGRESS_FILE).unlink()

    logging.info("Geocoding process completed!")


if __name__ == "__main__":
    main()
