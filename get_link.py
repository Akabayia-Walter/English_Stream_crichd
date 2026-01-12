import requests
from bs4 import BeautifulSoup


def get_match_links(match_url):
    """
    Get all stream links from a FootyStream match page
    
    Args:
        match_url (str): The full URL of the match page
        
    Returns:
        list: List of stream URLs found in the table, or empty list if none found
    """
    try:
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Make the request
        response = requests.get(match_url, headers=headers)
        
        if response.status_code != 200:
            return []
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the table
        table = soup.find('table', class_='min-w-full table-auto')
        
        if not table:
            return []
        
        # Find the table body
        tbody = table.find('tbody')
        
        if not tbody:
            return []
        
        # Find all <a> tags in the tbody and extract URLs
        links = tbody.find_all('a', href=True)
        urls = [link['href'] for link in links]
        
        return urls
        
    except Exception as e:
        print(f"Error fetching links: {e}")
        return []


# Example usage
# if __name__ == "__main__":
#     match_url = "https://footystream.pk/events/everton-vs-sunderland"
#     links = get_match_links(match_url)
    
#     print(f"Found {len(links)} links:")
#     for link in links:
#         print(f"  - {link}")