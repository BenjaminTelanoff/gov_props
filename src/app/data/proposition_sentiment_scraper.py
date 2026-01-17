"""
Proposition Sentiment Scraper: Fetches public sentiment from Twitter/X and Reddit
about politicians' propositions, then uses Gemini AI to create 1-sentence and 
1-paragraph summaries of how people feel about what the politician did.

Setup:
1. Install dependencies: pip install -r requirements-scraper.txt
2. Set environment variables:
   - GEMINI_API_KEY (or GOOGLE_API_KEY) for AI summarization
   - REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT (optional, for Reddit)
   - TWITTER_BEARER_TOKEN (optional, for Twitter API v2)
3. Run: python proposition_sentiment_scraper.py
"""

import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import re
import time
from typing import List, Dict, Optional
from urllib.parse import quote
from urllib.request import urlopen, Request

# Gemini AI imports
try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    print("Warning: google-genai not installed. Install with: pip install google-genai")

# Reddit imports
try:
    import praw
    HAS_REDDIT = True
except ImportError:
    HAS_REDDIT = False
    print("Warning: praw not installed. Install with: pip install praw")

# Twitter imports - using tweepy for Twitter API v2
try:
    import tweepy
    HAS_TWITTER = True
except ImportError:
    HAS_TWITTER = False
    print("Warning: tweepy not installed. Install with: pip install tweepy")

# Firebase initialization
script_dir = os.path.dirname(os.path.abspath(__file__))
service_account_path = os.path.join(script_dir, "serviceAccountKey.json")

if not firebase_admin._apps:
    if os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    else:
        # Try environment variables
        firebase_creds = {
            "type": os.getenv("FIREBASE_TYPE"),
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
            "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
            "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN"),
        }
        if firebase_creds.get("project_id"):
            cred = credentials.Certificate(firebase_creds)
            firebase_admin.initialize_app(cred)
        else:
            raise Exception("Firebase credentials not found. Set up serviceAccountKey.json or environment variables.")

db = firestore.client()

# Initialize Gemini client
gemini_client = None
if HAS_GEMINI:
    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_api_key:
        os.environ["GEMINI_API_KEY"] = gemini_api_key
        gemini_client = genai.Client()
    else:
        print("Warning: GEMINI_API_KEY not set. AI summarization will be skipped.")

# Initialize Reddit client
reddit_client = None
if HAS_REDDIT:
    reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    reddit_user_agent = os.getenv("REDDIT_USER_AGENT", "GovPropsSentimentScraper/1.0")
    
    if reddit_client_id and reddit_client_secret:
        # Authenticated client (better rate limits)
        reddit_client = praw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent=reddit_user_agent
        )
    else:
        # Read-only client (no auth, limited but works)
        try:
            reddit_client = praw.Reddit(
                client_id=None,
                client_secret=None,
                user_agent=reddit_user_agent
            )
            print("Using Reddit read-only mode (no authentication). For better results, set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET.")
        except Exception as e:
            print(f"Warning: Could not initialize Reddit client: {e}")


def search_reddit(query: str, limit: int = 10) -> List[Dict[str, str]]:
    """Search Reddit for posts and comments related to the query."""
    if not reddit_client:
        return []
    
    results = []
    try:
        # Search in multiple subreddits
        subreddits = ["politics", "news", "worldnews", "TrueReddit", "PoliticalDiscussion"]
        
        for subreddit_name in subreddits:
            try:
                subreddit = reddit_client.subreddit(subreddit_name)
                # Search for posts
                for post in subreddit.search(query, limit=limit//len(subreddits), sort="relevance", time_filter="year"):
                    results.append({
                        "text": post.title + " " + (post.selftext[:500] if post.selftext else ""),
                        "source": f"Reddit r/{subreddit_name}",
                        "url": f"https://reddit.com{post.permalink}",
                        "score": post.score
                    })
                    
                    # Get top comments
                    post.comments.replace_more(limit=0)
                    for comment in post.comments.list()[:3]:
                        if hasattr(comment, 'body') and comment.body:
                            results.append({
                                "text": comment.body[:500],
                                "source": f"Reddit r/{subreddit_name} (comment)",
                                "url": f"https://reddit.com{post.permalink}",
                                "score": comment.score
                            })
            except Exception as e:
                print(f"  [Reddit error for r/{subreddit_name}: {e}]")
                continue
                
            time.sleep(1)  # Rate limiting
            
    except Exception as e:
        print(f"  [Reddit search error: {e}]")
    
    return results[:limit]  # Limit total results


def search_twitter(query: str, limit: int = 20) -> List[Dict[str, str]]:
    """Search Twitter/X for tweets related to the query using Twitter API v2."""
    if not HAS_TWITTER:
        return []
    
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        return []
    
    results = []
    try:
        # Initialize Twitter API v2 client
        client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)
        
        # Search for tweets
        search_query = f"{query} lang:en -is:retweet"
        tweets = client.search_recent_tweets(
            query=search_query,
            max_results=min(limit, 100),  # API limit is 100
            tweet_fields=['public_metrics', 'created_at', 'author_id'],
            user_fields=['username']
        )
        
        if tweets.data:
            for tweet in tweets.data:
                results.append({
                    "text": tweet.text,
                    "source": "Twitter/X",
                    "url": f"https://twitter.com/i/web/status/{tweet.id}",
                    "likes": tweet.public_metrics.get('like_count', 0) if tweet.public_metrics else 0,
                    "retweets": tweet.public_metrics.get('retweet_count', 0) if tweet.public_metrics else 0
                })
    except tweepy.TooManyRequests:
        print(f"  [Twitter rate limit reached, skipping...]")
    except Exception as e:
        print(f"  [Twitter search error: {e}]")
    
    return results


def summarize_with_gemini(texts: List[Dict[str, str]], proposition_name: str, politician_name: str) -> Dict[str, str]:
    """
    Use Gemini AI to create 1-sentence and 1-paragraph summaries of public sentiment.
    Returns dict with 'sentence_summary' and 'paragraph_summary'.
    """
    if not gemini_client or not texts:
        return {
            "sentence_summary": "",
            "paragraph_summary": ""
        }
    
    # Combine all text sources
    combined_text = "\n\n".join([
        f"[{item['source']}] {item['text']}" 
        for item in texts[:50]  # Limit to avoid token limits
    ])
    
    if len(combined_text) < 100:
        return {
            "sentence_summary": "Insufficient data to determine public sentiment.",
            "paragraph_summary": "Insufficient data was found from social media sources to determine public sentiment about this proposition."
        }
    
    # Create prompt for Gemini
    prompt = f"""Analyze the following social media posts and comments about how people feel regarding what {politician_name} did with the proposition: "{proposition_name}".

Social media content:
{combined_text[:8000]}  # Limit to avoid token limits

Based on this content, provide:
1. A one-sentence summary of public sentiment (how people feel about what the politician did)
2. A one-paragraph (3-5 sentences) summary of public sentiment

Format your response as JSON:
{{
  "sentence_summary": "one sentence here",
  "paragraph_summary": "one paragraph here"
}}

Focus on sentiment, opinions, and reactions from the public. Be objective and summarize the overall feeling."""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        
        response_text = response.text.strip()
        
        # Try to parse JSON from response
        # Sometimes Gemini wraps JSON in markdown code blocks
        json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
        
        result = json.loads(response_text)
        return {
            "sentence_summary": result.get("sentence_summary", ""),
            "paragraph_summary": result.get("paragraph_summary", "")
        }
    except json.JSONDecodeError:
        # If JSON parsing fails, try to extract summaries manually
        lines = response_text.split('\n')
        sentence_summary = ""
        paragraph_summary = ""
        
        for i, line in enumerate(lines):
            if 'sentence' in line.lower() or 'one sentence' in line.lower():
                sentence_summary = lines[i+1] if i+1 < len(lines) else ""
            if 'paragraph' in line.lower() or 'one paragraph' in line.lower():
                paragraph_summary = "\n".join(lines[i+1:i+6]) if i+1 < len(lines) else ""
        
        return {
            "sentence_summary": sentence_summary.strip() or "Unable to generate summary.",
            "paragraph_summary": paragraph_summary.strip() or "Unable to generate summary."
        }
    except Exception as e:
        print(f"  [Gemini error: {e}]")
        return {
            "sentence_summary": "Error generating summary.",
            "paragraph_summary": "An error occurred while generating the sentiment summary."
        }


def process_proposition(politician_name: str, proposition: Dict, proposition_id: str, politician_doc_id: str):
    """Process a single proposition: scrape sentiment and generate summaries."""
    prop_name = proposition.get("Name", "")
    prop_desc = proposition.get("Desc", "")
    
    if not prop_name:
        print(f"  Skipping proposition {proposition_id} (no name)")
        return
    
    # Check if sentiment already exists
    if proposition.get("sentiment_sentence_summary") and proposition.get("sentiment_paragraph_summary"):
        print(f"  Proposition '{prop_name}' already has sentiment data, skipping...")
        return
    
    print(f"  Processing: {prop_name}")
    
    # Create search queries
    search_queries = [
        f"{politician_name} {prop_name}",
        f'"{politician_name}" "{prop_name}"',
        f"{prop_name} {politician_name} reaction",
        f"{prop_name} {politician_name} opinion"
    ]
    
    # Collect results from all sources
    all_results = []
    
    # Search Reddit
    if reddit_client:
        print(f"    Searching Reddit...")
        for query in search_queries[:2]:  # Limit queries to avoid rate limits
            results = search_reddit(query, limit=5)
            all_results.extend(results)
            time.sleep(2)
    
    # Search Twitter
    if HAS_TWITTER:
        print(f"    Searching Twitter/X...")
        for query in search_queries[:2]:
            results = search_twitter(query, limit=10)
            all_results.extend(results)
            time.sleep(2)
    
    print(f"    Found {len(all_results)} social media posts/comments")
    
    # Generate summaries with Gemini
    if gemini_client and all_results:
        print(f"    Generating AI summaries...")
        summaries = summarize_with_gemini(all_results, prop_name, politician_name)
        
        # Update proposition in Firestore
        politician_ref = db.collection("Politicians").document(politician_doc_id)
        politician_doc = politician_ref.get()
        
        if politician_doc.exists:
            data = politician_doc.to_dict()
            propositions = data.get("Propositions", {})
            
            if proposition_id in propositions:
                propositions[proposition_id]["sentiment_sentence_summary"] = summaries["sentence_summary"]
                propositions[proposition_id]["sentiment_paragraph_summary"] = summaries["paragraph_summary"]
                
                politician_ref.update({"Propositions": propositions})
                print(f"    ✓ Saved sentiment summaries to Firestore")
            else:
                print(f"    ✗ Proposition {proposition_id} not found in Firestore document")
        else:
            print(f"    ✗ Politician document {politician_doc_id} not found")
    else:
        print(f"    ⚠ Skipping AI summarization (no Gemini client or no results)")


def run():
    """Main function to process all politicians and their propositions."""
    print("Starting proposition sentiment scraper...")
    print(f"Reddit: {'✓' if reddit_client else '✗'}")
    print(f"Twitter: {'✓' if HAS_TWITTER else '✗'}")
    print(f"Gemini AI: {'✓' if gemini_client else '✗'}")
    print()
    
    # Get all politicians from Firestore
    politicians_ref = db.collection("Politicians")
    politicians = list(politicians_ref.stream())
    
    print(f"Found {len(politicians)} politicians in Firestore.")
    print()
    
    total_propositions = 0
    processed = 0
    
    for i, politician_doc in enumerate(politicians):
        data = politician_doc.to_dict() or {}
        name = data.get("Name", "")
        doc_id = politician_doc.id
        
        if not name:
            print(f"[{i+1}/{len(politicians)}] Skipping (no Name): {doc_id}")
            continue
        
        propositions = data.get("Propositions", {})
        if not propositions:
            print(f"[{i+1}/{len(politicians)}] {name} - No propositions")
            continue
        
        print(f"[{i+1}/{len(politicians)}] {name} ({len(propositions)} propositions)")
        
        for prop_id, proposition in propositions.items():
            total_propositions += 1
            process_proposition(name, proposition, prop_id, doc_id)
            time.sleep(3)  # Be nice to APIs
        
        processed += 1
        print()
        
        # Add a longer delay between politicians
        if i < len(politicians) - 1:
            time.sleep(5)
    
    print(f"\nComplete! Processed {processed} politicians with {total_propositions} total propositions.")


if __name__ == "__main__":
    run()
