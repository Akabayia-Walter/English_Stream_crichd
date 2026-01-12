import json
import asyncio
from datetime import datetime, timedelta
from m3u8 import scrape_m3u8


def load_matches(filename='footystream_matches.json'):
    """Load matches from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"❌ Could not load {filename}")
        return []


def save_matches(matches, filename='footystream_matches.json'):
    """Save matches to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)


def is_within_10_minutes(match_datetime_str):
    """
    Check if match time is within 10 minutes range (before or after current time)
    This allows scraping matches that are already live
    
    Args:
        match_datetime_str: ISO format datetime string
        
    Returns:
        bool: True if within ±10 minutes, False otherwise
    """
    try:
        match_time = datetime.fromisoformat(match_datetime_str.replace('Z', '+00:00'))
        now = datetime.now(match_time.tzinfo) if match_time.tzinfo else datetime.now()
        
        time_diff = match_time - now
        
        # Check if match is within 10 minutes before OR after (±10 minutes range)
        return timedelta(minutes=-10) <= time_diff <= timedelta(minutes=10)
        
    except Exception as e:
        print(f"⚠ Error parsing datetime: {e}")
        return False


async def get_working_m3u8(stream_links):
    """
    Try each stream link until we find one that returns a valid m3u8 URL
    
    Args:
        stream_links: List of stream URLs to try
        
    Returns:
        tuple: (m3u8_url, working_embed_url) if found, (None, None) otherwise
    """
    for i, link in enumerate(stream_links, 1):
        print(f"   Trying link {i}/{len(stream_links)}: {link}")
        
        try:
            m3u8_url = await scrape_m3u8(link)
            
            if m3u8_url:
                print(f"   ✅ Found working m3u8 URL!")
                return m3u8_url, link  # Return both m3u8 URL and the working embed URL
            else:
                print(f"   ❌ No m3u8 found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    return None, None


async def update_match_m3u8():
    """
    Check all matches and update m3u8 URLs for those starting within 10 minutes
    """
    print("🔍 Checking matches for m3u8 updates...")
    print("="*70 + "\n")
    
    # Load matches
    matches = load_matches()
    
    if not matches:
        print("No matches found in file")
        return
    
    print(f"Loaded {len(matches)} matches\n")
    
    updated_count = 0
    
    for match in matches:
        doc_id = match.get('doc_id', 'unknown')
        title = match.get('title', 'Unknown match')
        datetime_str = match.get('dateTime', '')
        stream_links = match.get('stream_links', [])
        
        # Skip if already has m3u8 URL
        if match.get('m3u8_url'):
            print(f"⏭️  {title}")
            print(f"   Already has m3u8 URL - skipping\n")
            continue
        
        # Skip if no stream links
        if not stream_links:
            continue
        
        # Check if within 10 minutes
        if not is_within_10_minutes(datetime_str):
            continue
        
        print(f"⏰ {title}")
        print(f"   Match starting soon - fetching m3u8 URL...")
        
        # Try to get working m3u8 URL and the embed URL that worked
        m3u8_url, working_embed_url = await get_working_m3u8(stream_links)
        
        if m3u8_url:
            # Update match with m3u8 URL and working embed URL
            match['m3u8_url'] = m3u8_url
            match['working_embed_url'] = working_embed_url
            match['m3u8_updated_at'] = datetime.now().isoformat()
            updated_count += 1
            
            print(f"   ✅ M3U8 URL: {m3u8_url}")
            print(f"   ✅ Working Embed: {working_embed_url}\n")
        else:
            print(f"   ⚠️  No working m3u8 URL found\n")
    
    # Save updated matches
    if updated_count > 0:
        save_matches(matches)
        print(f"{'='*70}")
        print(f"✅ Updated {updated_count} match(es) with m3u8 URLs")
        print(f"{'='*70}")
    else:
        print(f"{'='*70}")
        print(f"ℹ️  No matches needed updating")
        print(f"{'='*70}")


async def monitor_and_update(check_interval=60):
    """
    Continuously monitor matches and update m3u8 URLs
    
    Args:
        check_interval: Time in seconds between checks (default: 1 minutes)
    """
    print("🚀 Starting FootyStream M3U8 Fetcher...")
    print(f"⏱️  Check interval: {check_interval} seconds ({check_interval // 60} minutes)")
    print(f"🎯 Fetches m3u8 for matches within ±10 minutes of start time")
    print(f"{'='*70}\n")
    
    while True:
        try:
            await update_match_m3u8()
            
            next_check = datetime.now() + timedelta(seconds=check_interval)
            print(f"\n⏳ Next check at: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"💤 Sleeping for {check_interval // 60} minutes...\n")
            
            await asyncio.sleep(check_interval)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(60)  # Wait 1 minute on error


async def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Run once mode
        print("Running in single-run mode...\n")
        await update_match_m3u8()
    else:
        # Continuous monitoring mode
        try:
            await monitor_and_update()
        except KeyboardInterrupt:
            print("\n\n👋 M3U8 fetcher stopped by user")
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    """
    Usage:
        # Run continuously (check every 3 minutes)
        python fetch_m3u8.py
        
        # Run once (for testing)
        python fetch_m3u8.py --once
    """
    asyncio.run(main())