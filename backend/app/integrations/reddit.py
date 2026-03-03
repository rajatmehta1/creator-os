"""Reddit API integration using PRAW, wrapped for async execution."""

import asyncio
from typing import Any, Optional

import praw
import structlog

from app.config import get_settings
from app.utils.cache import cached

logger = structlog.get_logger()


def _get_reddit_client() -> praw.Reddit:
    """Create a read-only PRAW Reddit client from app settings.

    PRAW is synchronous; every public function in this module wraps its
    calls via ``asyncio.to_thread`` so the event loop is never blocked.
    """
    settings = get_settings()
    return praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
    )


def _submission_to_dict(submission: Any) -> dict[str, Any]:
    """Convert a PRAW Submission object to a JSON-serialisable dict."""
    return {
        "id": submission.id,
        "title": submission.title,
        "url": submission.url,
        "permalink": f"https://www.reddit.com{submission.permalink}",
        "score": submission.score,
        "upvote_ratio": submission.upvote_ratio,
        "num_comments": submission.num_comments,
        "created_utc": submission.created_utc,
        "author": str(submission.author) if submission.author else "[deleted]",
        "subreddit": str(submission.subreddit),
        "selftext": submission.selftext[:500] if submission.selftext else "",
        "is_self": submission.is_self,
        "link_flair_text": submission.link_flair_text,
    }


def _comment_to_dict(comment: Any) -> dict[str, Any]:
    """Convert a PRAW Comment object to a JSON-serialisable dict."""
    return {
        "id": comment.id,
        "body": comment.body[:1000] if comment.body else "",
        "score": comment.score,
        "created_utc": comment.created_utc,
        "author": str(comment.author) if comment.author else "[deleted]",
        "is_submitter": comment.is_submitter,
        "permalink": f"https://www.reddit.com{comment.permalink}",
    }


# ------------------------------------------------------------------
# Hot posts
# ------------------------------------------------------------------

@cached("trends:reddit")
async def get_hot_posts(
    subreddit: str,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Fetch hot posts from a subreddit.

    Args:
        subreddit: Subreddit name without the ``r/`` prefix.
        limit: Maximum number of posts to return (max 100).

    Returns:
        List of post dicts containing title, score, comments, URL, etc.
    """
    logger.info("reddit.hot_posts", subreddit=subreddit, limit=limit)

    def _fetch() -> list[dict[str, Any]]:
        reddit = _get_reddit_client()
        sub = reddit.subreddit(subreddit)
        return [_submission_to_dict(post) for post in sub.hot(limit=min(limit, 100))]

    return await asyncio.to_thread(_fetch)


# ------------------------------------------------------------------
# Rising posts
# ------------------------------------------------------------------

@cached("trends:reddit")
async def get_rising_posts(
    subreddit: str,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Fetch rising posts from a subreddit.

    Args:
        subreddit: Subreddit name without the ``r/`` prefix.
        limit: Maximum number of posts to return (max 100).

    Returns:
        List of post dicts containing title, score, comments, URL, etc.
    """
    logger.info("reddit.rising_posts", subreddit=subreddit, limit=limit)

    def _fetch() -> list[dict[str, Any]]:
        reddit = _get_reddit_client()
        sub = reddit.subreddit(subreddit)
        return [_submission_to_dict(post) for post in sub.rising(limit=min(limit, 100))]

    return await asyncio.to_thread(_fetch)


# ------------------------------------------------------------------
# Search subreddits
# ------------------------------------------------------------------

@cached("trends:reddit")
async def search_subreddits(
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search for subreddits matching a query.

    Args:
        query: Search term.
        limit: Maximum number of results.

    Returns:
        List of dicts with subreddit metadata (name, subscribers, description).
    """
    logger.info("reddit.search_subreddits", query=query, limit=limit)

    def _fetch() -> list[dict[str, Any]]:
        reddit = _get_reddit_client()
        results = reddit.subreddits.search(query, limit=limit)
        return [
            {
                "name": str(sub.display_name),
                "title": sub.title,
                "subscribers": sub.subscribers,
                "description": (sub.public_description or "")[:300],
                "url": f"https://www.reddit.com{sub.url}",
                "over18": sub.over18,
            }
            for sub in results
        ]

    return await asyncio.to_thread(_fetch)


# ------------------------------------------------------------------
# Post comments
# ------------------------------------------------------------------

@cached("trends:reddit")
async def get_post_comments(
    post_id: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Fetch top-level comments on a Reddit post.

    Args:
        post_id: The Reddit post ID (e.g. ``"abc123"``).
        limit: Maximum number of comments to return.

    Returns:
        List of comment dicts with body, score, author, etc.
    """
    logger.info("reddit.post_comments", post_id=post_id, limit=limit)

    def _fetch() -> list[dict[str, Any]]:
        reddit = _get_reddit_client()
        submission = reddit.submission(id=post_id)
        submission.comment_sort = "top"
        submission.comments.replace_more(limit=0)
        comments = []
        for comment in submission.comments[:limit]:
            comments.append(_comment_to_dict(comment))
        return comments

    return await asyncio.to_thread(_fetch)
