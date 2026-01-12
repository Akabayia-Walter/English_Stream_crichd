import asyncio
import schedule
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
import re
from get_html import scrape_footystream
from create_firestore import sync_to_firestore_auto


def generate_doc_id(home_team, away_team):
    """
    Generate a clean document ID from team names
    Format: homeTeam-vs-awayTeam (lowercase, hyphens)
    """
    if not home_team or not away_team:
        return "unknown"
    
    # Combine team names
    match_title = f"{home_team} vs {away_team}"
    
    # Convert to lowercase
    doc_id = match_title.lower()
    
    # Replace spaces and special characters with hyphens
    doc_id = re.sub(r'[^\w\s-]', '', doc_id)
    doc_id = re.sub(r'[-\s]+', '-', doc_id)
    
    # Remove leading/trailing hyphens
    doc_id = doc_id.strip('-')
    
    return doc_id


def parse_matches_from_html(html_file='body_content.html', filter_date=None):
    """
    Parse match data from the downloaded HTML file
    
    Args:
        html_file: Path to HTML file
        filter_date: datetime.date object to filter matches by. If None, returns all matches
    """
    print(f"Reading HTML from {html_file}...")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    all_matches = []
    filtered_matches = []
    
    # Find all match containers - looking for the parent link that contains the match info
    match_links = soup.find_all('a', href=re.compile(r'^/events/'))
    
    print(f"Found {len(match_links)} match links")
    
    if filter_date:
        print(f"\n🎯 Filtering matches for: {filter_date.strftime('%A, %B %d, %Y')}\n")
    
    for link in match_links:
        try:
            # Get the URL
            url = 'https://footystream.pk' + link.get('href', '')
            
            # Find the countdown span for date/time with data-countdown attribute
            countdown_span = link.find('span', {'data-countdown': True})
            date_time = countdown_span.get('data-countdown', '') if countdown_span else ''
            
            # Find all team divs - they contain flex gap-2 items-center
            team_divs = link.find_all('div', class_=lambda x: x and 'flex' in x and 'gap-2' in x and 'items-center' in x)
            
            # Extract team names from the divs
            teams = []
            for team_div in team_divs:
                # Get the text content, skip the img tag
                team_text = team_div.get_text(strip=True)
                # Remove any logo text
                team_text = team_text.replace('logo', '').strip()
                if team_text:
                    teams.append(team_text)
            
            # Alternative method: find img tags with alt text
            if len(teams) < 2:
                teams = []
                team_imgs = link.find_all('img', alt=True)
                for img in team_imgs:
                    alt_text = img.get('alt', '')
                    # Skip if it's just "logo" or contains "logo" only
                    if alt_text and alt_text.lower() != 'logo' and not alt_text.endswith(' logo'):
                        # Remove " logo" suffix if present
                        team_name = alt_text.replace(' logo', '')
                        teams.append(team_name)
            
            # Only add if we found both teams
            if len(teams) >= 2:
                home_team = teams[0]
                away_team = teams[1]
                match_title = f"{home_team} vs {away_team}"
                
                match_data = {
                    'doc_id': generate_doc_id(home_team, away_team),
                    'title': match_title,
                    'url': url,
                    'dateTime': date_time,
                    'homeTeam': home_team,
                    'awayTeam': away_team,
                    'scrapedAt': datetime.now().isoformat()
                }
                
                # Always add to all_matches
                all_matches.append(match_data)
                
                # Filter by date if specified
                if filter_date and date_time:
                    try:
                        # Parse the data-countdown date (e.g., "2026-01-12T19:45:00.000Z")
                        match_datetime = datetime.fromisoformat(date_time.replace('Z', '+00:00'))
                        match_date = match_datetime.date()
                        
                        # Check if match date matches filter date
                        if match_date == filter_date:
                            filtered_matches.append(match_data)
                            match_time = match_datetime.strftime('%H:%M UTC')
                            print(f"  ✓ {match_title} - {match_time}")
                    except Exception as e:
                        print(f"  ⚠️  Could not parse date for {match_title}: {e}")
                
        except Exception as e:
            print(f"Error parsing match: {e}")
            continue
    
    # Return filtered matches if filter_date specified, otherwise all matches
    if filter_date:
        print(f"\n📊 Total matches on {filter_date.strftime('%Y-%m-%d')}: {len(filtered_matches)}")
        return filtered_matches
    else:
        return all_matches


def save_to_json(matches, filename='footystream_matches.json'):
    """Save matches to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)
    print(f"✓ Data saved to {filename}")




async def scrape_matches():
    """Main scraping function - Gets today's matches only"""
    print("\n" + "="*100)
    print(f"🕐 Running scheduled scrape at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100 + "\n")
    
    try:
        # Get the current date
        today = datetime.now().date()
        print(f"📅 Current date: {today.strftime('%A, %B %d, %Y')}\n")
        
        # Step 1: Download the HTML
        print("STEP 1: Downloading HTML content...")
        html_content = await scrape_footystream()
        
        # Save HTML to file for backup
        with open('body_content.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✓ HTML saved to body_content.html ({len(html_content)} characters)\n")
        
        # Step 2: Parse the HTML file and filter by today's date
        print("STEP 2: Parsing matches and filtering by today's date...")
        matches = parse_matches_from_html('body_content.html', filter_date=today)
        
        # Display all matches found
        if matches:
            print(f"\n{'='*70}")
            print(f"📺 TODAY'S MATCHES ({len(matches)} total)")
            print(f"{'='*70}\n")
            
            for i, match in enumerate(matches, 1):
                # Parse match time
                match_datetime = datetime.fromisoformat(match['dateTime'].replace('Z', '+00:00'))
                match_time = match_datetime.strftime('%H:%M UTC')
                
                print(f"{i}. {match['title']}")
                print(f"   🕐 Time: {match_time}")
                print(f"   🆔 Doc ID: {match['doc_id']}")
                print(f"   🔗 URL: {match['url']}\n")
        else:
            print("\n⚠️  No matches found for today!")
        
        # Save to JSON
        print("STEP 3: Saving to JSON...")
        save_to_json(matches, 'footystream_matches.json')
        
        # Step 4: Automatically sync to Firestore
        sync_to_firestore_auto('footystream_matches.json')
        
        print("\n✅ Complete workflow finished successfully!")
        print("   ✓ HTML downloaded")
        print("   ✓ Matches parsed and filtered")
        print("   ✓ JSON file saved")
        print("   ✓ Firestore synced")
        print("="*100 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during scrape: {e}")
        import traceback
        traceback.print_exc()
        print("="*100 + "\n")


def run_scheduled_scrape():
    """Wrapper to run async scrape in sync context"""
    asyncio.run(scrape_matches())


def get_match_main():
    """Main scheduler"""
    print("🚀 FootyStream Match Scraper with Auto Firestore Sync")
    print("="*100)
    print(f"⏰ Scheduled to run daily at 06:00 AM")
    print(f"🕐 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 Will scrape matches for: {datetime.now().date().strftime('%A, %B %d, %Y')}")
    print(f"🔥 Firestore: Auto-sync enabled")
    print("="*100 + "\n")
    
    # Schedule the job to run daily at 6 AM
    schedule.every().day.at("06:00").do(run_scheduled_scrape)
    
    print("💡 The script will run immediately, then daily at 6 AM")
    print("💡 Only today's matches will be scraped and saved")
    print("💡 Firestore will be automatically updated after each scrape")
    print("Press Ctrl+C to stop the scheduler\n")
    
    # Run immediately on start
    print("Running initial scrape now...")
    run_scheduled_scrape()
    
    # Keep the scheduler running
    print("\n⏳ Waiting for next scheduled run at 06:00 AM...")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\n\n👋 Scheduler stopped by user")
            break
        except Exception as e:
            print(f"\n❌ Scheduler error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)


if __name__ == "__main__":
    get_match_main()