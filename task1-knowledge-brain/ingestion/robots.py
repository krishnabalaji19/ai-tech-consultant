"""Download robots.txt and ask whether a URL is allowed."""

from __future__ import annotations

from urllib.robotparser import RobotFileParser

import httpx


async def load_robots(
    client: httpx.AsyncClient,
    robots_url: str,
    user_agent: str,
) -> RobotFileParser:
    """Fetch robots.txt first. If the file is missing, allow all paths."""
    parser = RobotFileParser()
    parser.set_url(robots_url)
    response = await client.get(robots_url)
    if response.status_code == 404:
        parser.parse([])
        return parser
    response.raise_for_status()
    parser.parse(response.text.splitlines())
    _ = user_agent  # used by callers with can_fetch
    return parser


def is_allowed(parser: RobotFileParser, user_agent: str, url: str) -> bool:
    return parser.can_fetch(user_agent, url)
