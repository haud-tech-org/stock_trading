# src/tools/convert_to_utc_timestamp.py
import sys
import os
from datetime import datetime
import pytz

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# This script assumes it is being run by an entry point in the project root
# that has already configured the Python path.
#
# Correct import, assuming 'src' is in the Python path.
from common.settings import timezone_settings as tz_settings


# --- Main Execution ---
# The main logic is wrapped in a function to be callable by the runner.
def main():
    try:
        # 1. Read settings from the imported module
        source_tz_str = tz_settings.TIMEZONE_BY_COUNTRY_CODE[tz_settings.FROM_COUNTRY_CODE]["timezone"]
        datetime_str = tz_settings.DATE_CONVERT
        
        print(f"Input Timezone: {source_tz_str}")
        print(f"Input Datetime: {datetime_str}")

        # 2. Get the timezone object
        source_tz = pytz.timezone(source_tz_str)

        # 3. Create a naive datetime object from the string
        naive_dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')

        # 4. Localize the naive datetime to the source timezone
        localized_dt = source_tz.localize(naive_dt)
        
        print(f"Localized Datetime: {localized_dt}")

        # 5. Convert the localized datetime to a UTC timestamp (integer)
        utc_timestamp = int(localized_dt.timestamp())

        # 6. Display the final result
        print("\n--- Conversion Result ---")
        print(f"UTC Timestamp: {utc_timestamp}")
        print("-------------------------\n")

    except AttributeError:
        print("Error: A setting is missing from 'timezone_settings.py'.", file=sys.stderr)
        print("Make sure TIMEZONE_TO_CONVERT and DATETIME_STRING are defined.", file=sys.stderr)
        sys.exit(1)
    except pytz.UnknownTimeZoneError:
        print(f"Error: The timezone '{source_tz_str}' is not a valid timezone.", file=sys.stderr)
        sys.exit(1)
    except ValueError:
        print(f"Error: The datetime string '{datetime_str}' does not match the format 'YYYY-MM-DD HH:MM:SS'.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

# This allows the script to be imported as a module without running the main logic,
# which is now handled by the runner script.
if __name__ == "__main__":
    main()
