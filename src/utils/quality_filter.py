"""
Quality filter for Person Radar.
Filters out low-quality content like clickbait, fan-made videos, reactions, etc.
"""

import re
from typing import Optional

# Patterns that indicate low-quality content
BLACKLIST_PATTERNS = [
    # Clickbait patterns
    r'you won\'?t believe',
    r'shocking',
    r'mind.?blow',
    r'gone wrong',
    r'exposed',
    r'destroyed',
    r'slams',
    r'blasts',
    r'rips',
    r'BREAKING:?\s*$',  # Fake breaking news at end

    # Reaction/fan content
    r'\breact(s|ing|ion)?\b',
    r'\breaction\b',
    r'fan.?made',
    r'tribute',
    r'compilation',
    r'best moments',
    r'top \d+ moments',
    r'every time',
    r'all .* scenes',

    # Low effort content
    r'shorts',
    r'#shorts',
    r'tiktok',
    r'\bclip\b',
    r'highlights only',
    r'teaser',
    r'trailer only',

    # Misleading titles
    r'what .* thinks about',
    r'responds to',
    r'fires back',
    r'claps back',
    r'vs\.?\s',
    r'versus',
    r'debate:',
    r'roasts',

    # AI-generated spam
    r'ai.?generated',
    r'made with ai',
    r'deepfake',
]

# Patterns that indicate high-quality content
WHITELIST_PATTERNS = [
    # Official interviews
    r'interview',
    r'keynote',
    r'full (talk|speech|presentation)',
    r'official',

    # Conferences and talks
    r'conference',
    r'summit',
    r'ted\s?talk',
    r'google i/o',
    r'neurips',
    r'icml',
    r'iclr',
    r'cvpr',
    r'aaai',

    # Podcasts (usually long-form quality content)
    r'podcast',
    r'lex fridman',
    r'joe rogan',
    r'tim ferriss',
    r'huberman',
    r'dwarkesh',
    r'logan bartlett',
    r'eye on ai',

    # Quality news sources
    r'bloomberg',
    r'reuters',
    r'financial times',
    r'wall street journal',
    r'new york times',
    r'washington post',
    r'wired',
    r'mit technology review',
    r'nature',
    r'science',
    r'the verge',
    r'ars technica',
    r'techcrunch',

    # Academic/research content
    r'paper',
    r'research',
    r'lecture',
    r'course',
    r'tutorial',
    r'explained',
]

# Minimum content length (in characters) to consider
MIN_TITLE_LENGTH = 10
MIN_DESCRIPTION_LENGTH = 20

# Channels/sources known for quality content
TRUSTED_CHANNELS = [
    'lex fridman',
    'two minute papers',
    'yannic kilcher',
    'machine learning street talk',
    'the robot brains',
    'google',
    'deepmind',
    'openai',
    'anthropic',
    'stanford',
    'mit',
    'berkeley',
    'carnegie mellon',
]

# Channels/sources known for low-quality content
UNTRUSTED_CHANNELS = [
    'daily',
    'news24',
    'trending',
    'viral',
    'buzz',
]


def calculate_quality_score(
    title: str,
    description: Optional[str] = None,
    source_channel: Optional[str] = None,
    content_type: str = 'unknown'
) -> float:
    """
    Calculate a quality score for content.
    Returns a float between 0.0 (low quality) and 1.0 (high quality).
    """
    score = 0.5  # Start neutral
    title_lower = title.lower()
    desc_lower = (description or '').lower()
    channel_lower = (source_channel or '').lower()
    combined_text = f"{title_lower} {desc_lower}"

    # Check blacklist patterns (reduce score)
    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            score -= 0.15
            if score <= 0:
                return 0.0

    # Check whitelist patterns (increase score)
    for pattern in WHITELIST_PATTERNS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            score += 0.1
            if score >= 1.0:
                return 1.0

    # Check trusted channels
    for trusted in TRUSTED_CHANNELS:
        if trusted in channel_lower:
            score += 0.2
            break

    # Check untrusted channels
    for untrusted in UNTRUSTED_CHANNELS:
        if untrusted in channel_lower:
            score -= 0.2
            break

    # Title length check
    if len(title) < MIN_TITLE_LENGTH:
        score -= 0.1

    # All caps title (usually clickbait)
    if title.isupper() and len(title) > 20:
        score -= 0.2

    # Excessive punctuation (clickbait indicator)
    exclamation_count = title.count('!')
    question_count = title.count('?')
    if exclamation_count > 2 or question_count > 2:
        score -= 0.15

    # Emoji spam in title (often clickbait)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "]+",
        flags=re.UNICODE
    )
    emoji_count = len(emoji_pattern.findall(title))
    if emoji_count > 3:
        score -= 0.1

    # Boost for longer descriptions (usually more substantive)
    if description and len(description) > 200:
        score += 0.1

    # Content type specific adjustments
    if content_type == 'youtube':
        # YouTube shorts are usually lower quality
        if 'short' in title_lower or len(title) < 30:
            score -= 0.1
    elif content_type == 'twitter':
        # Tweets are inherently shorter, adjust expectations
        score += 0.1
    elif content_type == 'news':
        # News articles from search are usually decent quality
        score += 0.05

    # Clamp score between 0 and 1
    return max(0.0, min(1.0, score))


def is_quality_content(
    title: str,
    description: Optional[str] = None,
    source_channel: Optional[str] = None,
    content_type: str = 'unknown',
    threshold: float = 0.4
) -> bool:
    """
    Determine if content meets quality threshold.
    """
    score = calculate_quality_score(title, description, source_channel, content_type)
    return score >= threshold


def filter_content_list(
    items: list[dict],
    threshold: float = 0.4
) -> list[dict]:
    """
    Filter a list of content items, keeping only quality content.
    Each item should have 'title', optionally 'description', 'source_channel', 'content_type'.
    Returns filtered list with quality_score added to each item.
    """
    filtered = []

    for item in items:
        score = calculate_quality_score(
            title=item.get('title', ''),
            description=item.get('description'),
            source_channel=item.get('source_channel'),
            content_type=item.get('content_type', 'unknown')
        )

        if score >= threshold:
            item['quality_score'] = score
            filtered.append(item)

    # Sort by quality score (highest first)
    filtered.sort(key=lambda x: x.get('quality_score', 0), reverse=True)

    return filtered


if __name__ == '__main__':
    # Test the quality filter
    test_cases = [
        {
            'title': 'Demis Hassabis: The Future of AI - Full Interview at Google I/O 2024',
            'description': 'In this exclusive interview, Demis Hassabis discusses the latest breakthroughs at DeepMind.',
            'content_type': 'youtube'
        },
        {
            'title': 'YOU WON\'T BELIEVE what Demis Hassabis said!!! 😱😱😱',
            'description': 'Reaction video',
            'content_type': 'youtube'
        },
        {
            'title': 'Lex Fridman Podcast #400 - Andrej Karpathy: Neural Networks and Deep Learning',
            'description': 'Andrej Karpathy is a legendary AI researcher...',
            'content_type': 'youtube'
        },
        {
            'title': 'Jeff Dean DESTROYS interviewer with FACTS',
            'description': 'Watch Jeff Dean respond to tough questions',
            'content_type': 'youtube'
        },
    ]

    for case in test_cases:
        score = calculate_quality_score(
            case['title'],
            case.get('description'),
            case.get('source_channel'),
            case.get('content_type', 'unknown')
        )
        status = "PASS" if score >= 0.4 else "FAIL"
        print(f"[{status}] Score: {score:.2f} - {case['title'][:60]}...")
