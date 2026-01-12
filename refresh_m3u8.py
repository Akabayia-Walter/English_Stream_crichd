import asyncio
import json
import time
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from m3u8 import scrape_m3u8

MATCHES_FILE = 'footystream_matches.json'

class MatchesMonitor:
    def __init__(self, matches_file=MATCHES_FILE):
        """
        Initialize the monitor with the matches file path.
        
        Args:
            matches_file (str): Path to the matches JSON file
        """
        self.matches_file = matches_file
        self.data = None
        
    def load_matches(self):
        """Load matches from JSON file"""
        try:
            with open(self.matches_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            return True
        except FileNotFoundError:
            print(f"❌ File {self.matches_file} not found!")
            return False
        except json.JSONDecodeError:
            print(f"❌ Error reading {self.matches_file}!")
            return False
    
    def save_matches(self):
        """Save matches to JSON file"""
        with open(self.matches_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved updates to {self.matches_file}")
    
    def get_m3u8_url_string(self, m3u8_data):
        """
        Extract the actual m3u8 URL string from m3u8_url field.
        Handles both object format and direct string format.
        
        Args:
            m3u8_data: Can be dict with 'm3u8' key or direct string
            
        Returns:
            str: The m3u8 URL or None
        """
        if not m3u8_data:
            return None
            
        # If it's a dict with 'm3u8' key
        if isinstance(m3u8_data, dict):
            return m3u8_data.get('m3u8')
        
        # If it's already a string
        if isinstance(m3u8_data, str):
            return m3u8_data
            
        return None
    
    def get_expiry_timestamp(self, m3u8_url_string):
        """
        Extract the expiry timestamp from the m3u8 URL.
        Only returns timestamp if 'expires' parameter is present.
        Returns None for URLs without 'expires' (like token-based URLs).
        
        Args:
            m3u8_url_string: The actual m3u8 URL string
            
        Returns:
            int: Unix timestamp or None
        """
        if not m3u8_url_string or not isinstance(m3u8_url_string, str):
            return None
            
        parsed = urlparse(m3u8_url_string)
        params = parse_qs(parsed.query)
        
        # Only process URLs with 'expires' parameter
        if 'expires' in params:
            try:
                return int(params['expires'][0])
            except (ValueError, IndexError):
                return None
        
        return None
    
    def is_expiring_soon(self, m3u8_url_string, minutes=5):
        """
        Check if the m3u8 URL will expire within the specified minutes.
        
        Args:
            m3u8_url_string (str): The m3u8 URL string to check
            minutes (int): Minutes before expiry to trigger refresh
            
        Returns:
            bool: True if expiring within specified minutes or already expired
        """
        expiry_timestamp = self.get_expiry_timestamp(m3u8_url_string)
        if not expiry_timestamp:
            return False
        
        current_time = int(time.time())
        time_until_expiry = expiry_timestamp - current_time
        
        # Convert minutes to seconds
        threshold_seconds = minutes * 60
        
        # Check if within threshold or already expired
        return time_until_expiry <= threshold_seconds
    
    async def refresh_match_m3u8(self, match):
        """
        Fetch a new m3u8 URL from the working embed URL and update the match.
        
        Args:
            match (dict): Match document
            
        Returns:
            bool: True if successfully refreshed
        """
        working_embed_url = match.get('working_embed_url')
        
        if not working_embed_url:
            print(f"   ⚠️  No working_embed_url found for this match")
            return False
        
        print(f"   🔄 Refreshing m3u8 URL from: {working_embed_url[:60]}...")
        
        try:
            # Call the scrape_m3u8 function from m3u8.py
            result = await scrape_m3u8(working_embed_url)
            
            # Update the match with new values
            if result:
                match['m3u8_url'] = result
                match['m3u8_updated_at'] = datetime.now().isoformat()
                
                # Show what was updated
                if isinstance(result, dict):
                    if 'm3u8' in result:
                        print(f"   ✅ Updated m3u8 URL")
                    if 'headers' in result:
                        print(f"   ✅ Updated headers")
                else:
                    print(f"   ✅ Updated m3u8 URL")
                
                return True
            else:
                print(f"   ❌ Failed to get new m3u8 URL")
                return False
                
        except Exception as e:
            print(f"   ❌ Error refreshing URL: {e}")
            return False
    
    async def check_and_refresh_matches(self, expiry_threshold_minutes=5):
        """
        Check all matches and refresh expiring m3u8 URLs.
        
        Args:
            expiry_threshold_minutes (int): Minutes before expiry to trigger refresh
        """
        if not self.load_matches():
            return
        
        # Handle both list format and dict with 'matches' key
        if isinstance(self.data, list):
            matches = self.data
        else:
            matches = self.data.get('matches', [])
        
        refreshed_count = 0
        checked_count = 0
        
        print(f"\n{'='*70}")
        print(f"Checking {len(matches)} matches for expiring m3u8 URLs...")
        print(f"Expiry threshold: ≤{expiry_threshold_minutes} minutes")
        print(f"{'='*70}\n")
        
        for match in matches:
            m3u8_data = match.get('m3u8_url')
            title = match.get('title', 'Unknown')
            doc_id = match.get('doc_id', 'unknown')
            
            # Skip matches without m3u8 data
            if not m3u8_data:
                continue
            
            # Extract the actual URL string
            m3u8_url_string = self.get_m3u8_url_string(m3u8_data)
            
            if not m3u8_url_string:
                continue
            
            checked_count += 1
            expiry_timestamp = self.get_expiry_timestamp(m3u8_url_string)
            
            # Skip token-based URLs or URLs without expiry
            if expiry_timestamp is None:
                if 'token=' in m3u8_url_string:
                    print(f"ℹ️  {title}")
                    print(f"   Token-based URL - skipping expiry check\n")
                continue
            
            # Check if expiring soon
            current_time = int(time.time())
            time_until_expiry = expiry_timestamp - current_time
            expiry_datetime = datetime.fromtimestamp(expiry_timestamp)
            
            print(f"📺 {title}")
            print(f"   Doc ID: {doc_id}")
            print(f"   Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   URL expires at: {expiry_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if time_until_expiry > 0:
                minutes_left = time_until_expiry // 60
                seconds_left = time_until_expiry % 60
                print(f"   Time until expiry: {minutes_left} min, {seconds_left} sec")
            else:
                minutes_ago = abs(time_until_expiry) // 60
                seconds_ago = abs(time_until_expiry) % 60
                print(f"   ⚠️  Expired {minutes_ago} min, {seconds_ago} sec ago")
            
            if self.is_expiring_soon(m3u8_url_string, expiry_threshold_minutes):
                if time_until_expiry > 0:
                    print(f"   ⏰ URL expiring soon! Refreshing...")
                else:
                    print(f"   ⏰ URL already expired! Refreshing...")
                    
                if await self.refresh_match_m3u8(match):
                    refreshed_count += 1
                print()
            else:
                print(f"   ✓ URL still valid (not expiring within {expiry_threshold_minutes} minutes)\n")
        
        # Save if any matches were refreshed
        if refreshed_count > 0:
            self.save_matches()
        
        print(f"{'='*70}")
        print(f"📊 Summary:")
        print(f"   Matches checked: {checked_count}")
        print(f"   M3U8 URLs refreshed: {refreshed_count}")
        print(f"{'='*70}\n")
    
    async def monitor(self, check_interval=60, expiry_threshold_minutes=5):
        """
        Continuously monitor matches and refresh expiring m3u8 URLs.
        
        Args:
            check_interval (int): Seconds between checks
            expiry_threshold_minutes (int): Minutes before expiry to trigger refresh
        """
        print("🚀 Starting M3U8 URL Monitor...")
        print(f"📁 Monitoring file: {self.matches_file}")
        print(f"⏱️  Check interval: {check_interval} seconds")
        print(f"⏰ Expiry threshold: ≤{expiry_threshold_minutes} minutes")
        
        iteration = 0
        
        while True:
            iteration += 1
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"\n{'='*70}")
            print(f"🔄 Check #{iteration} - {current_time}")
            print(f"{'='*70}")
            
            try:
                await self.check_and_refresh_matches(expiry_threshold_minutes)
            except Exception as e:
                print(f"❌ Error during monitoring: {e}")
                import traceback
                traceback.print_exc()
            
            # Wait for next check
            next_check = datetime.now().timestamp() + check_interval
            next_check_time = datetime.fromtimestamp(next_check).strftime('%Y-%m-%d %H:%M:%S')
            print(f"⏳ Next check at: {next_check_time}")
            print(f"💤 Sleeping for {check_interval} seconds...")
            
            await asyncio.sleep(check_interval)


async def main():
    """
    Main entry point
    """
    import sys
    
    # Parse command line arguments
    check_interval = 60  # Default: check every 60 seconds
    expiry_threshold = 5  # Default: refresh 5 minutes before expiry
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--once':
            # Run once mode
            if len(sys.argv) > 2:
                try:
                    expiry_threshold = int(sys.argv[2])
                except ValueError:
                    print("Invalid expiry_threshold. Using default: 5 minutes")
            
            print(f"Running in single-run mode (threshold: ≤{expiry_threshold} minutes)...\n")
            monitor = MatchesMonitor(MATCHES_FILE)
            await monitor.check_and_refresh_matches(expiry_threshold)
            return
        else:
            try:
                check_interval = int(sys.argv[1])
            except ValueError:
                print("Invalid check_interval. Using default: 60 seconds")
    
    if len(sys.argv) > 2:
        try:
            expiry_threshold = int(sys.argv[2])
        except ValueError:
            print("Invalid expiry_threshold. Using default: 5 minutes")
    
    # Create monitor instance
    monitor = MatchesMonitor(MATCHES_FILE)
    
    try:
        await monitor.monitor(check_interval, expiry_threshold)
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    """
    Usage:
        # Run continuously (check every 60 seconds, refresh URLs expiring in ≤5 minutes)
        python monitor_m3u8.py
        
        # Custom check interval (120 seconds)
        python monitor_m3u8.py 120
        
        # Custom check interval and expiry threshold
        python monitor_m3u8.py 120 10
        
        # Run once with default 5 minute threshold
        python monitor_m3u8.py --once
        
        # Run once with custom threshold (e.g., 10 minutes)
        python monitor_m3u8.py --once 10
    """
    asyncio.run(main())