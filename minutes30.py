import json
import asyncio
from datetime import datetime, timedelta
from get_link import get_match_links


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


def is_within_30_minutes(match_datetime_str):
    """
    Check if match time is within 30 minutes from now
    
    Args:
        match_datetime_str: ISO format datetime string
        
    Returns:
        bool: True if within 30 minutes, False otherwise
    """
    try:
        match_time = datetime.fromisoformat(match_datetime_str.replace('Z', '+00:00'))
        now = datetime.now(match_time.tzinfo) if match_time.tzinfo else datetime.now()
        
        time_diff = match_time - now
        
        # Check if match is between now and 30 minutes from now
        return timedelta(0) <= time_diff <= timedelta(minutes=30)
        
    except Exception as e:
        print(f"⚠ Error parsing datetime: {e}")
        return False


async def update_match_links():
    """
    Check all matches and update links for those starting within 30 minutes
    """
    print("🔍 Checking matches for link updates...")
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
        match_url = match.get('url', '')
        datetime_str = match.get('dateTime', '')
        
        # Skip if already has links
        if match.get('stream_links'):
            print(f"⏭️  {title}")
            print(f"   Already has links - skipping\n")
            continue
        
        # Check if within 30 minutes
        if not is_within_30_minutes(datetime_str):
            continue
        
        print(f"⏰ {title}")
        print(f"   Match starting soon - fetching links...")
        
        # Get links
        links = get_match_links(match_url)
        
        if links:
            # Update match with links
            match['stream_links'] = links
            match['links_updated_at'] = datetime.now().isoformat()
            updated_count += 1
            
            print(f"   ✅ Found {len(links)} stream link(s)")
            for i, link in enumerate(links, 1):
                print(f"      {i}. {link}")
            print()
        else:
            print(f"   ⚠️  No links found yet\n")
    
    # Save updated matches
    if updated_count > 0:
        save_matches(matches)
        print(f"{'='*70}")
        print(f"✅ Updated {updated_count} match(es) with stream links")
        print(f"{'='*70}")
    else:
        print(f"{'='*70}")
        print(f"ℹ️  No matches needed updating")
        print(f"{'='*70}")


async def monitor_and_update(check_interval=60):
    """
    Continuously monitor matches and update links
    
    Args:
        check_interval: Time in seconds between checks (default: 1 minutes)
    """
    print("🚀 Starting FootyStream Link Updater...")
    print(f"⏱️  Check interval: {check_interval} seconds ({check_interval // 60} minutes)")
    print(f"{'='*70}\n")
    
    while True:
        try:
            await update_match_links()
            
            next_check = datetime.now() + timedelta(seconds=check_interval)
            print(f"\n⏳ Next check at: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"💤 Sleeping for {check_interval // 60} minutes...\n")
            
            await asyncio.sleep(check_interval)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(60)  # Wait 1 minute on error


async def main_30minutes():
    """Main entry point"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Run once mode
        print("Running in single-run mode...\n")
        await update_match_links()
    else:
        # Continuous monitoring mode
        try:
            await monitor_and_update()
        except KeyboardInterrupt:
            print("\n\n👋 Updater stopped by user")
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    """
    Usage:
        # Run continuously (check every 5 minutes)
        python update_links.py
        
        # Run once (for testing)
        python update_links.py --once
    """
    asyncio.run(main_30minutes())