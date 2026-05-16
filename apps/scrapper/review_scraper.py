import sys
import time
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

def safe_text(text):
    if not text:
        return ""
    return str(text).encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')

def fetch_reddit_comments(url):
    try:
        old_reddit_url = url.replace('www.reddit.com', 'old.reddit.com').replace('https://reddit.com', 'https://old.reddit.com')
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(old_reddit_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            comments = []
            for comment_div in soup.select('.comment'):
                author = comment_div.select_one('.author')
                if author and author.text.lower() == 'automoderator':
                    continue
                body = comment_div.select_one('.usertext-body .md') or comment_div.select_one('.md')
                if body:
                    text = body.text.strip().replace('\n', ' ')
                    if text and len(text) > 10:
                        comments.append(text)
            return comments[:10]
    except Exception as e:
        pass
    return []

def fetch_quora_answers(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = [p.text.strip().replace('\n', ' ') for p in soup.find_all('p') if len(p.text.strip()) > 30]
            if paragraphs:
                return paragraphs[:10]
    except Exception as e:
        pass
    return []

def scrape_duckduckgo(query):
    try:
        results = []
        ddgs_results = DDGS().text(query, max_results=10)
        for res in ddgs_results:
            results.append({
                'title': res.get('title', ''),
                'snippet': res.get('body', ''),
                'url': res.get('href', '')
            })
        return results
    except Exception as e:
        print(f"Error scraping for query '{query}': {e}")
        return []

def get_product_reviews(product_name):
    end_string = ""
    end_string += f"[*] Searching for reviews and comments about: '{product_name}'...\n\n"
    
    end_string += f"--- [*] GENERAL REVIEWS ---\n"
    general_results = scrape_duckduckgo(f"Reviews, comments, pros and cons of the product {product_name} in the current market")
    
    if not general_results:
        end_string += "No general reviews found or blocked by the search provider.\n"
    else:
        for i, res in enumerate(general_results[:5], 1):
            end_string += f"\n{i}. {safe_text(res['title'])}\n"
            end_string += f"   [-] Snippet: {safe_text(res['snippet'])}\n"
            end_string += f"   [-] Source: {res['url']}\n"

    time.sleep(2)
    
    end_string += f"\n\n--- [*] USER COMMENTS (via Reddit) ---\n"
    reddit_results = scrape_duckduckgo(f"{product_name} site:reddit.com")
    
    if not reddit_results:
        end_string += "No user comments found or blocked by the search provider.\n"
    else:
        for i, res in enumerate(reddit_results[:5], 1):
            end_string += f"\n{i}. {safe_text(res['title'])}\n"
            end_string += f"   [-] Source: {res['url']}\n"
            comments = fetch_reddit_comments(res['url'])
            if comments:
                end_string += f"   [-] Top Comments:\n"
                for idx, c in enumerate(comments, 1):
                    end_string += f"       {idx}. {safe_text(c)}\n"
            else:
                end_string += f"   [-] Snippet: {safe_text(res['snippet'])}\n"

    time.sleep(2)
    
    end_string += f"\n\n--- [*] Q&A DISCUSSIONS (via Quora) ---\n"
    quora_results = scrape_duckduckgo(f"{product_name} site:quora.com")
    
    if not quora_results:
        end_string += "No Q&A discussions found or blocked by the search provider.\n"
    else:
        for i, res in enumerate(quora_results[:5], 1):
            end_string += f"\n{i}. {safe_text(res['title'])}\n"
            end_string += f"   [-] Source: {res['url']}\n"
            answers = fetch_quora_answers(res['url'])
            if answers:
                end_string += f"   [-] Extracted Answers:\n"
                for idx, a in enumerate(answers, 1):
                    end_string += f"       {idx}. {safe_text(a)}\n"
            else:
                end_string += f"   [-] Snippet: {safe_text(res['snippet'])}\n"

    return end_string

if __name__ == "__main__":
    product_name = "ChatGPT" # Define the product name in this variable
        
    if product_name.strip():
        final_output = get_product_reviews(product_name)
        print(final_output)
    else:
        print("Product name cannot be empty.")
