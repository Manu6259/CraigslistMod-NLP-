import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import csv
import time
from datetime import datetime
import os
import argparse

def save_html_for_debugging(html, filename):
    """Save the HTML content to a file for debugging"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved HTML to {filename}")

def get_frame_urls(url):
    """Extract frame URLs from the main frameset page"""
    print(f"Fetching main page: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the page: {e}")
        return {}
    
    # Save the main frameset HTML for debugging
    save_html_for_debugging(response.text, "debug_frameset.html")
    
    # Parse the HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all frame tags
    frames = soup.find_all('frame')
    frame_urls = {}
    
    base_url = url.split('?')[0]
    
    for frame in frames:
        frame_id = frame.get('id', '')
        frame_src = frame.get('src', '')
        
        if frame_id and frame_src:
            # Handle relative URLs
            if not frame_src.startswith('http'):
                frame_src = base_url + frame_src
            
            frame_urls[frame_id] = frame_src
    
    print(f"Found {len(frame_urls)} frames: {', '.join(frame_urls.keys())}")
    return frame_urls

def scrape_forum_page(left_frame_url, page_num=1, max_pages=1):
    """Scrape a single page of the forum"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    forum_data = []
    pagination_links = {}
    
    print(f"Fetching page {page_num}: {left_frame_url}")
    
    try:
        response = requests.get(left_frame_url, headers=headers)
        response.raise_for_status()
        
        # Save the left frame HTML for debugging if it's the first page
        if page_num == 1:
            save_html_for_debugging(response.text, "debug_left_frame.html")
        
        # Parse the thread list
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find pagination links for "newer" and "older" posts
        # Craigslist forums use "threadpaginator" class for pagination
        pagination_div = soup.find('div', class_='threadpaginator')
        if pagination_div:
            # Look for the "older" link (to go to previous/older posts)
            older_link = pagination_div.find('a', class_='previous')
            if older_link and not 'disabled' in older_link.get('class', []):
                href = older_link.get('href', '')
                if href:
                    # Handle relative URLs
                    if not href.startswith('http'):
                        base_url = left_frame_url.split('?')[0]
                        href = base_url + href
                    pagination_links['older'] = href
                    print(f"Found 'older' posts link: {href}")
            
            # Look for the "newer" link (to go to more recent posts)
            newer_link = pagination_div.find('a', class_='next')
            if newer_link and not 'disabled' in newer_link.get('class', []):
                href = newer_link.get('href', '')
                if href:
                    # Handle relative URLs
                    if not href.startswith('http'):
                        base_url = left_frame_url.split('?')[0]
                        href = base_url + href
                    pagination_links['newer'] = href
                    print(f"Found 'newer' posts link: {href}")
        
        # Look for thread articles
        threads = soup.find_all('article', class_='thread')
        print(f"Found {len(threads)} thread articles on page {page_num}")
        
        thread_id = 1
        # Process each thread article
        for thread_article in threads:
            # Each thread article contains multiple threadlines
            threadlines = thread_article.find_all('div', class_='threadline')
            
            if not threadlines:
                continue
            
            # Process each threadline (post or reply) in the thread
            for i, threadline in enumerate(threadlines):
                # Extract the link (title)
                title_link = threadline.find('a', class_='title')
                if not title_link:
                    continue
                
                title = title_link.get_text().strip()
                thread_url = title_link.get('href', '')
                
                # Handle relative URLs
                if thread_url and not thread_url.startswith('http'):
                    base_url = left_frame_url.split('?')[0]
                    thread_url = base_url + thread_url
                
                # Determine if it's the first post or a reply based on the div class
                is_first_post = 'first' in threadline.get('class', [])
                
                # Extract author (handle)
                author_elem = threadline.find('span', class_='handle')
                author = author_elem.get_text().strip() if author_elem else "Unknown"
                
                # Extract date (time tag)
                time_elem = threadline.find('time')
                post_date = time_elem.get_text().strip() if time_elem else ""
                
                # Determine nesting level by counting ": . ." in dotz span
                nesting_level = 0
                dotz_elem = threadline.find('span', class_='dotz')
                if dotz_elem:
                    dotz_text = dotz_elem.get_text()
                    nesting_level = dotz_text.count(': . .')
                
                # Add post to list
                post_data = {
                    'thread_id': thread_id,
                    'post_id': thread_id + i,
                    'title': title,
                    'author': author,
                    'time': post_date,
                    'url': thread_url,
                    'nesting_level': nesting_level,
                    'is_first_post': is_first_post,
                    'page_num': page_num,
                    'content': ""  # Will be filled when we fetch the content
                }
                
                forum_data.append(post_data)
                print(f"Post {post_data['post_id']} (Page {page_num}): {title} by {author} (nesting level: {nesting_level})")
            
            thread_id += len(threadlines)
    
    except Exception as e:
        print(f"Error fetching page {page_num}: {e}")
    
    return forum_data, pagination_links

def fetch_post_content(posts, start_idx=0):
    """Fetch content for each post"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Process in batches to avoid overwhelming the server
    processed_urls = set()
    
    for i, post in enumerate(posts[start_idx:], start=start_idx):
        if post['url'] and post['url'] not in processed_urls:
            print(f"Fetching content for post {i+1}/{len(posts)}: {post['title']}")
            
            try:
                response = requests.get(post['url'], headers=headers)
                response.raise_for_status()
                
                # Save the first post content for debugging
                if i == 0:
                    save_html_for_debugging(response.text, "debug_post_content.html")
                
                # Parse the content
                content_soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for content in various possible elements
                content = ""
                
                # Try to find the content in common elements
                content_elem = None
                for selector in ['div.msg', 'div.content', 'pre', 'blockquote']:
                    content_elem = content_soup.select_one(selector)
                    if content_elem:
                        content = content_elem.get_text().strip()
                        break
                
                # If no content found, try getting text from the body
                if not content and content_soup.body:
                    content = content_soup.body.get_text().strip()
                
                # Clean up content
                content = re.sub(r'\s+', ' ', content).strip()
                
                # Update content for all posts with the same URL
                for p in posts:
                    if p['url'] == post['url']:
                        p['content'] = content
                
                # Mark URL as processed
                processed_urls.add(post['url'])
                
            except Exception as e:
                print(f"Error fetching post content: {e}")
            
            # Add small delay to avoid overloading the server
            time.sleep(1)
    
    return posts

def scrape_forum_content(frame_urls, max_pages=1):
    """Scrape content from the forum frames across multiple pages"""
    # The main forum content is usually in the frame with ID 'L'
    # The detailed post content is usually in the frame with ID 'R'
    all_posts = []
    current_page = 1
    
    # First, fetch the frame with the thread list (usually L)
    if 'L' in frame_urls:
        left_frame_url = frame_urls['L']
        next_url = left_frame_url
        
        while current_page <= max_pages and next_url:
            # Scrape the current page
            page_posts, pagination_links = scrape_forum_page(next_url, current_page, max_pages)
            
            if not page_posts:
                print(f"No posts found on page {current_page}. Stopping.")
                break
            
            # Add the current page's posts to our collection
            all_posts.extend(page_posts)
            
            # Determine the next URL to scrape (if any)
            if current_page < max_pages:
                # Use the "older" link for the next page
                next_url = pagination_links.get('older', None)
                if not next_url:
                    print("No 'older' pagination link found or it's disabled. Reached the last page.")
                    break
                current_page += 1
            else:
                break
        
        # Now fetch content for all the posts
        print(f"\nFetching content for {len(all_posts)} posts across {current_page} pages...")
        all_posts = fetch_post_content(all_posts)
    
    return all_posts

def save_to_csv(data, filename):
    """Save the scraped data to a CSV file."""
    if not data:
        print("No data to save!")
        return
    
    # Define CSV columns
    fieldnames = ['thread_id', 'post_id', 'title', 'author', 'time', 'content', 'nesting_level', 'is_first_post', 'page_num', 'url']
    
    # Write to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for post in data:
            writer.writerow(post)
    
    print(f"Data saved to {filename}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Scrape Craigslist forum posts across multiple pages')
    parser.add_argument('--forum', type=str, default="5178", help='Forum ID to scrape (default: 5178 for Android forum)')
    parser.add_argument('--pages', type=int, default=1, help='Number of pages to scrape (default: 1)')
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    forum_id = args.forum
    max_pages = args.pages
    
    forum_url = f"https://forums.craigslist.org/?forumID={forum_id}"
    output_file = f"craigslist_forum_data_{forum_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    print(f"Scraping data from {forum_url}, up to {max_pages} page(s)...")
    
    # Get frame URLs from the main page
    frame_urls = get_frame_urls(forum_url)
    
    # Scrape content from the frames
    forum_data = scrape_forum_content(frame_urls, max_pages)
    
    # Save data to CSV
    print(f"Found {len(forum_data)} posts across up to {max_pages} page(s)")
    save_to_csv(forum_data, output_file)
    
    print("Scraping completed!")

if __name__ == "__main__":
    main() 