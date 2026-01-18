#!/usr/bin/env python3
"""
Reddit Scraper using JSON API (No authentication required!)

Since Reddit blocked their free API tier, this script uses Reddit's public JSON endpoints
by appending .json to any Reddit URL. No API keys or authentication needed!

Setup Instructions:
1. Install requests: pip install requests
2. Run the script!

Note: Reddit may rate limit if you make too many requests too quickly.
Add delays between requests if needed.
"""

import requests
from datetime import datetime
from typing import List, Dict, Optional


class RedditScraper:
    """Wrapper class for Reddit JSON API operations (no auth required)"""
    
    def __init__(self, user_agent: str = "python:reddit-scraper:v1.0"):
        """
        Initialize Reddit JSON scraper
        
        Args:
            user_agent: User agent string to identify your requests
        """
        self.base_url = "https://www.reddit.com"
        self.headers = {
            "User-Agent": user_agent
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        print(f"✓ Reddit JSON Scraper initialized (no auth required!)")
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to Reddit's JSON API
        
        Args:
            url: Full URL to request
            params: Optional query parameters
        
        Returns:
            JSON response as dictionary
        """
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {url}: {e}")
            return {}
    
    def get_subreddit_posts(
        self,
        subreddit_name: str,
        sort: str = "hot",
        limit: Optional[int] = 25,
        after: Optional[str] = None
    ) -> Dict:
        """
        Get posts from a subreddit
        
        Args:
            subreddit_name: Name of subreddit (without r/)
            sort: Sort type: hot, new, top, rising, controversial
            limit: Number of posts (max 100)
            after: Pagination token for next page
        
        Returns:
            Dictionary with posts data and pagination info
        """
        url = f"{self.base_url}/r/{subreddit_name}/{sort}.json"
        params = {"limit": limit}
        if after:
            params["after"] = after
        
        data = self._make_request(url, params)
        
        if not data or "data" not in data:
            return {"posts": [], "after": None, "before": None}
        
        posts = []
        for child in data["data"].get("children", []):
            post_data = child.get("data", {})
            posts.append(self._parse_post(post_data))
        
        return {
            "posts": posts,
            "after": data["data"].get("after"),
            "before": data["data"].get("before"),
        }
    
    def _parse_post(self, post_data: Dict) -> Dict:
        """
        Parse post data from Reddit JSON response
        
        Args:
            post_data: Raw post data from Reddit API
        
        Returns:
            Cleaned post dictionary
        """
        return {
            "id": post_data.get("id"),
            "title": post_data.get("title"),
            "author": post_data.get("author", "[deleted]"),
            "score": post_data.get("score", 0),
            "upvote_ratio": post_data.get("upvote_ratio", 0),
            "num_comments": post_data.get("num_comments", 0),
            "created_utc": datetime.fromtimestamp(post_data.get("created_utc", 0)).isoformat(),
            "url": post_data.get("url"),
            "permalink": f"{self.base_url}{post_data.get('permalink', '')}",
            "selftext": post_data.get("selftext", "")[:500],  # Truncate long text
            "is_self": post_data.get("is_self", False),
            "link_flair_text": post_data.get("link_flair_text"),
            "subreddit": post_data.get("subreddit"),
            "thumbnail": post_data.get("thumbnail"),
            "domain": post_data.get("domain"),
        }
    
    def _parse_comment(self, comment_data: Dict) -> Dict:
        """
        Parse comment data from Reddit JSON response
        
        Args:
            comment_data: Raw comment data from Reddit API
        
        Returns:
            Cleaned comment dictionary
        """
        return {
            "id": comment_data.get("id"),
            "author": comment_data.get("author", "[deleted]"),
            "body": comment_data.get("body", ""),
            "score": comment_data.get("score", 0),
            "created_utc": datetime.fromtimestamp(comment_data.get("created_utc", 0)).isoformat(),
            "permalink": f"{self.base_url}{comment_data.get('permalink', '')}",
            "is_submitter": comment_data.get("is_submitter", False),
            "depth": comment_data.get("depth", 0),
        }
    
    def get_post_details(
        self,
        subreddit_name: str,
        post_id: str
    ) -> Dict:
        """
        Get detailed information about a specific post including comments
        
        Args:
            subreddit_name: Name of subreddit (without r/)
            post_id: Reddit post ID
        
        Returns:
            Dictionary with post details and comments
        """
        url = f"{self.base_url}/r/{subreddit_name}/comments/{post_id}.json"
        data = self._make_request(url)
        
        if not data or len(data) < 2:
            return {"post": {}, "comments": []}
        
        # First element is the post
        post_data = data[0]["data"]["children"][0]["data"]
        post = self._parse_post(post_data)
        
        # Second element is comments
        comments = []
        for child in data[1]["data"]["children"]:
            if child["kind"] == "t1":  # t1 is a comment
                comment_data = child.get("data", {})
                comments.append(self._parse_comment(comment_data))
        
        return {
            "post": post,
            "comments": comments
        }
    
    def search_posts(
        self,
        query: str,
        subreddit_name: Optional[str] = None,
        sort: str = "relevance",
        time_filter: str = "all",
        limit: int = 25
    ) -> List[Dict]:
        """
        Search for posts
        
        Args:
            query: Search query string
            subreddit_name: Specific subreddit to search (None for all)
            sort: One of: relevance, hot, top, new, comments
            time_filter: One of: all, day, hour, month, week, year
            limit: Number of results
        
        Returns:
            List of post dictionaries
        """
        if subreddit_name:
            url = f"{self.base_url}/r/{subreddit_name}/search.json"
        else:
            url = f"{self.base_url}/search.json"
        
        params = {
            "q": query,
            "sort": sort,
            "t": time_filter,
            "limit": limit,
        }
        if subreddit_name:
            params["restrict_sr"] = "on"
        
        data = self._make_request(url, params)
        
        if not data or "data" not in data:
            return []
        
        posts = []
        for child in data["data"].get("children", []):
            post_data = child.get("data", {})
            posts.append(self._parse_post(post_data))
        
        return posts
    
    def get_subreddit_info(self, subreddit_name: str) -> Dict:
        """
        Get information about a subreddit
        
        Args:
            subreddit_name: Name of subreddit (without r/)
        
        Returns:
            Dictionary with subreddit information
        """
        url = f"{self.base_url}/r/{subreddit_name}/about.json"
        data = self._make_request(url)
        
        if not data or "data" not in data:
            return {}
        
        sub_data = data["data"]
        return {
            "name": sub_data.get("display_name"),
            "title": sub_data.get("title"),
            "description": sub_data.get("public_description"),
            "subscribers": sub_data.get("subscribers", 0),
            "created_utc": datetime.fromtimestamp(sub_data.get("created_utc", 0)).isoformat(),
            "over18": sub_data.get("over18", False),
            "url": f"{self.base_url}{sub_data.get('url', '')}",
        }
    
    def list_posts(self, posts: List[Dict], verbose: bool = False):
        """
        Print a formatted list of posts
        
        Args:
            posts: List of post dictionaries
            verbose: If True, show more details
        """
        for i, post in enumerate(posts, 1):
            print(f"\n{i}. {post['title']}")
            print(f"   Author: u/{post['author']} | Score: {post['score']} | Comments: {post['num_comments']}")
            print(f"   Posted: {post['created_utc']}")
            print(f"   URL: {post['permalink']}")
            
            if verbose:
                if post.get('selftext'):
                    print(f"   Text: {post['selftext'][:200]}...")
                if post.get('link_flair_text'):
                    print(f"   Flair: {post['link_flair_text']}")
            print("   " + "-" * 70)


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)


def print_post_content(post: Dict, comments: List[Dict], max_comments: int = 5):
    """Print formatted post with comments"""
    print_header(f"📝 {post['title']}")
    
    print(f"\n👤 Author: u/{post['author']}")
    print(f"⬆️  Score: {post['score']:,} | 💬 Comments: {post['num_comments']:,}")
    print(f"🕒 Posted: {post['created_utc']}")
    
    if post.get('link_flair_text'):
        print(f"🏷️  Flair: {post['link_flair_text']}")
    
    print(f"🔗 URL: {post['permalink']}")
    
    # Print post content
    if post.get('selftext'):
        print("\n" + "-"*80)
        print("📄 POST CONTENT:")
        print("-"*80)
        print(post['selftext'])
    elif post.get('url') and not post.get('is_self'):
        print("\n" + "-"*80)
        print(f"🔗 Link Post: {post['url']}")
        print("-"*80)
    
    # Print comments
    if comments:
        print("\n" + "-"*80)
        print(f"💬 TOP {min(max_comments, len(comments))} COMMENTS:")
        print("-"*80)
        
        for i, comment in enumerate(comments[:max_comments], 1):
            print(f"\n[{i}] u/{comment['author']} • ⬆️ {comment['score']:,}")
            print("-" * 40)
            # Word wrap the comment
            body = comment['body']
            # Simple word wrapping
            words = body.split()
            line = ""
            for word in words:
                if len(line) + len(word) + 1 <= 76:
                    line += word + " "
                else:
                    print(line)
                    line = word + " "
            if line:
                print(line)
            print()
    else:
        print("\n💬 No comments yet.")


def interactive_mode():
    """Run the scraper in interactive mode"""
    scraper = RedditScraper()
    
    print_header("🔍 Reddit Interactive Browser")
    print("\nWelcome! This tool lets you browse Reddit posts interactively.")
    print("Type 'quit' or 'exit' at any time to leave.\n")
    
    while True:
        # Step 1: Choose mode - browse or search
        print("\n" + "─"*80)
        print("Choose an option:")
        print("  [1] Browse a subreddit")
        print("  [2] Search posts")
        print("  [q] Quit")
        print("─"*80)
        
        mode = input("Enter choice (1/2/q): ").strip()
        
        if mode.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Thanks for browsing! Goodbye!")
            break
        
        # SEARCH MODE
        if mode == '2':
            print("\n" + "─"*80)
            query = input("🔍 Enter search query: ").strip()
            
            if not query:
                print("❌ Please enter a search query.")
                continue
            
            # Ask if they want to search in a specific subreddit
            subreddit_search = input("📍 Search in specific subreddit? (press Enter to search all, or enter subreddit name): ").strip()
            
            if subreddit_search.startswith('r/'):
                subreddit_search = subreddit_search[2:]
            
            # Ask for sort option
            print("\nSort by: [1] Relevance  [2] Hot  [3] Top  [4] New  [5] Comments")
            sort_choice = input("Enter choice (default: 1): ").strip() or '1'
            sort_map = {'1': 'relevance', '2': 'hot', '3': 'top', '4': 'new', '5': 'comments'}
            sort = sort_map.get(sort_choice, 'relevance')
            
            # Ask for time filter if sorted by top
            time_filter = 'all'
            if sort == 'top':
                print("\nTime filter: [1] All  [2] Day  [3] Week  [4] Month  [5] Year")
                time_choice = input("Enter choice (default: 1): ").strip() or '1'
                time_map = {'1': 'all', '2': 'day', '3': 'week', '4': 'month', '5': 'year'}
                time_filter = time_map.get(time_choice, 'all')
            
            # Perform search
            print(f"\n🔍 Searching for '{query}'...")
            if subreddit_search:
                print(f"   📍 In r/{subreddit_search}")
            else:
                print(f"   📍 Across all of Reddit")
            print(f"   📊 Sort: {sort}" + (f" | Time: {time_filter}" if sort == 'top' else ""))
            
            result_posts = scraper.search_posts(
                query=query,
                subreddit_name=subreddit_search if subreddit_search else None,
                sort=sort,
                time_filter=time_filter,
                limit=25
            )
            
            if not result_posts:
                print(f"❌ No results found for '{query}'")
                continue
            
            # Display search results
            print_header(f"🔍 Search Results for '{query}'")
            print(f"Found {len(result_posts)} results\n")
            
            for i, post in enumerate(result_posts, 1):
                # Truncate long titles
                title = post['title']
                if len(title) > 70:
                    title = title[:67] + "..."
                
                print(f"\n[{i:2d}] {title}")
                print(f"     ⬆️ {post['score']:,} | 💬 {post['num_comments']:,} | "
                      f"👤 u/{post['author']} | 📍 r/{post['subreddit']}")
            
            # Let user view a post
            while True:
                print("\n" + "─"*80)
                selection = input("📌 Enter post number to view (or 'back' for main menu): ").strip()
                
                if selection.lower() in ['back', 'b']:
                    break
                
                if selection.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Thanks for browsing! Goodbye!")
                    return
                
                try:
                    post_index = int(selection) - 1
                    
                    if post_index < 0 or post_index >= len(result_posts):
                        print(f"❌ Please enter a number between 1 and {len(result_posts)}")
                        continue
                    
                    # Get the selected post
                    selected_post = result_posts[post_index]
                    post_id = selected_post['id']
                    post_subreddit = selected_post['subreddit']
                    
                    # Fetch full post details with comments
                    print(f"\n📥 Loading post and comments...")
                    details = scraper.get_post_details(post_subreddit, post_id)
                    
                    # Display the post and comments
                    print_post_content(
                        details['post'],
                        details['comments'],
                        max_comments=5
                    )
                    
                    # Ask if they want to see another post
                    print("\n" + "─"*80)
                    another = input("📌 View another post? (y/n): ").strip().lower()
                    if another in ['n', 'no']:
                        break
                    
                    # Re-display the search results for easy reference
                    print_header(f"🔍 Search Results for '{query}'")
                    print(f"Found {len(result_posts)} results\n")
                    
                    for i, post in enumerate(result_posts, 1):
                        title = post['title']
                        if len(title) > 70:
                            title = title[:67] + "..."
                        
                        print(f"\n[{i:2d}] {title}")
                        print(f"     ⬆️ {post['score']:,} | 💬 {post['num_comments']:,} | "
                              f"👤 u/{post['author']} | 📍 r/{post['subreddit']}")
                    
                except ValueError:
                    print("❌ Please enter a valid number.")
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            continue
        
        # BROWSE SUBREDDIT MODE
        if mode != '1':
            print("❌ Please enter 1, 2, or q")
            continue
        
        # Step 2: Get subreddit name
        print("\n" + "─"*80)
        subreddit_name = input("📍 Enter subreddit name (without r/): ").strip()
        
        if subreddit_name.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Thanks for browsing! Goodbye!")
            break
        
        if not subreddit_name:
            print("❌ Please enter a subreddit name.")
            continue
        
        # Remove r/ if user included it
        if subreddit_name.startswith('r/'):
            subreddit_name = subreddit_name[2:]
        
        # Try to get subreddit info to validate
        print(f"\n🔍 Checking r/{subreddit_name}...")
        info = scraper.get_subreddit_info(subreddit_name)
        
        if not info or not info.get('name'):
            print(f"❌ Subreddit r/{subreddit_name} not found or is private.")
            continue
        
        # Show subreddit info
        print(f"\n✅ Found: r/{info['name']}")
        print(f"   {info['title']}")
        print(f"   👥 {info['subscribers']:,} subscribers")
        if info.get('description'):
            desc = info['description'][:150]
            print(f"   📝 {desc}{'...' if len(info['description']) > 150 else ''}")
        
        # Get posts
        print(f"\n📥 Fetching hot posts from r/{subreddit_name}...")
        result = scraper.get_subreddit_posts(subreddit_name, sort="hot", limit=25)
        
        if not result['posts']:
            print(f"❌ No posts found in r/{subreddit_name}")
            continue
        
        # Step 2: Display posts with indices
        print_header(f"🔥 Hot Posts from r/{subreddit_name}")
        
        for i, post in enumerate(result['posts'], 1):
            # Truncate long titles
            title = post['title']
            if len(title) > 70:
                title = title[:67] + "..."
            
            print(f"\n[{i:2d}] {title}")
            print(f"     ⬆️ {post['score']:,} | 💬 {post['num_comments']:,} | "
                  f"👤 u/{post['author']}")
        
        # Step 3: Get user selection
        while True:
            print("\n" + "─"*80)
            selection = input("📌 Enter post number to view (or 'back' to choose another subreddit): ").strip()
            
            if selection.lower() in ['back', 'b']:
                break
            
            if selection.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Thanks for browsing! Goodbye!")
                return
            
            try:
                post_index = int(selection) - 1
                
                if post_index < 0 or post_index >= len(result['posts']):
                    print(f"❌ Please enter a number between 1 and {len(result['posts'])}")
                    continue
                
                # Get the selected post
                selected_post = result['posts'][post_index]
                post_id = selected_post['id']
                
                # Fetch full post details with comments
                print(f"\n📥 Loading post and comments...")
                details = scraper.get_post_details(subreddit_name, post_id)
                
                # Display the post and comments
                print_post_content(
                    details['post'],
                    details['comments'],
                    max_comments=5
                )
                
                # Ask if they want to see another post
                print("\n" + "─"*80)
                another = input("📌 View another post? (y/n): ").strip().lower()
                if another in ['n', 'no']:
                    break
                
                # Re-display the post list for easy reference
                print_header(f"🔥 Hot Posts from r/{subreddit_name}")
                
                for i, post in enumerate(result['posts'], 1):
                    # Truncate long titles
                    title = post['title']
                    if len(title) > 70:
                        title = title[:67] + "..."
                    
                    print(f"\n[{i:2d}] {title}")
                    print(f"     ⬆️ {post['score']:,} | 💬 {post['num_comments']:,} | "
                          f"👤 u/{post['author']}")
                
            except ValueError:
                print("❌ Please enter a valid number.")
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    """Main entry point - run interactive mode"""
    interactive_mode()


if __name__ == "__main__":
    main()

