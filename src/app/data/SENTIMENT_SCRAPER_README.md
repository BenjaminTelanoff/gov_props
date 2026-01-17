# Proposition Sentiment Scraper

This script scrapes Twitter/X and Reddit to gather public sentiment about politicians' propositions, then uses Gemini AI (via Firebase AI API) to generate 1-sentence and 1-paragraph summaries of how people feel about what the politician did.

## Features

- **Reddit Scraping**: Searches multiple political subreddits for posts and comments
- **Twitter/X Scraping**: Uses Twitter API v2 to find relevant tweets
- **AI Summarization**: Uses Gemini AI to create concise sentiment summaries
- **Firestore Integration**: Automatically stores summaries in your Firestore database

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements-scraper.txt
```

### 2. Get API Keys

#### Gemini API Key (Required for AI summarization)
1. Go to [Google AI Studio](https://ai.google.dev/)
2. Create a new API key
3. Set it as an environment variable:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```
   Or on Windows:
   ```powershell
   $env:GEMINI_API_KEY="your-api-key-here"
   ```

#### Reddit API Credentials (Optional but recommended)
1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app" or "create app"
3. Choose "script" as the app type
4. Note your client ID and secret
5. Set environment variables:
   ```bash
   export REDDIT_CLIENT_ID="your-client-id"
   export REDDIT_CLIENT_SECRET="your-client-secret"
   export REDDIT_USER_AGENT="GovPropsSentimentScraper/1.0"
   ```

#### Twitter API Bearer Token (Optional)
1. Go to https://developer.twitter.com/
2. Create a new app and get a Bearer Token
3. Set environment variable:
   ```bash
   export TWITTER_BEARER_TOKEN="your-bearer-token"
   ```

### 3. Firebase Credentials

Make sure you have either:
- `serviceAccountKey.json` in the same directory as the script, OR
- Firebase credentials set as environment variables (see main README)

## Usage

Run the scraper:

```bash
python proposition_sentiment_scraper.py
```

The script will:
1. Fetch all politicians and their propositions from Firestore
2. For each proposition, search Reddit and Twitter for relevant posts
3. Use Gemini AI to generate sentiment summaries
4. Store the summaries in Firestore under each proposition:
   - `sentiment_sentence_summary`: One-sentence summary
   - `sentiment_paragraph_summary`: One-paragraph summary

## Output Structure

The script adds the following fields to each proposition in Firestore:

```json
{
  "Name": "Proposition Name",
  "Desc": "Description",
  "Verdict": "Success",
  "Verdict_desc": "...",
  "sentiment_sentence_summary": "Public sentiment in one sentence...",
  "sentiment_paragraph_summary": "Detailed paragraph about public sentiment..."
}
```

## Rate Limiting

The script includes rate limiting to be respectful to APIs:
- Reddit: 1 second delay between subreddit searches
- Twitter: Uses tweepy's built-in rate limit handling
- Between propositions: 3 second delay
- Between politicians: 5 second delay

## Notes

- The script skips propositions that already have sentiment data
- If no social media data is found, it will store a message indicating insufficient data
- You can run the script multiple times - it will only process propositions without sentiment data
- Reddit scraping works without authentication but is limited; API credentials provide better results

## Troubleshooting

**"Warning: GEMINI_API_KEY not set"**
- Make sure you've set the GEMINI_API_KEY environment variable

**"Warning: Reddit credentials not set"**
- Reddit will still work but with limited functionality. Get API credentials for better results.

**"Warning: tweepy not installed"**
- Install with: `pip install tweepy`
- Or skip Twitter scraping if you only want Reddit

**Firebase authentication errors**
- Make sure serviceAccountKey.json exists or environment variables are set correctly
