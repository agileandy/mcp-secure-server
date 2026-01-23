"""Figma REST API client for figma-stories-plugin.

This module provides async HTTP client for interacting with Figma's REST API
to extract design information for story generation.
"""

from __future__ import annotations

import asyncio
import re

import httpx

from .exceptions import (
    FigmaAPIError,
    FigmaAuthenticationError,
    FigmaFileNotFoundError,
    FigmaRateLimitError,
)
from .models import (
    Annotation,
    Component,
    FileInfo,
    Frame,
    Page,
    TextNode,
)


class FigmaClient:
    """Async client for Figma REST API."""

    BASE_URL = "https://api.figma.com/v1"
    RATE_LIMIT_DELAY = 0.5  # Seconds between requests (Figma allows 200/min)

    def __init__(
        self,
        api_token: str,
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_delay: float = 0.5,
    ):
        """Initialize Figma client.

        Args:
            api_token: Figma personal access token
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for rate limit errors
            rate_limit_delay: Delay between requests (default: 0.5s for 200/min)
        """
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_delay = rate_limit_delay

        self._client: httpx.AsyncClient | None = None
        self._last_request_time: float = 0

    async def __aenter__(self) -> FigmaClient:
        """Async context manager entry."""
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self._get_headers(),
            )
        return self._client

    def _get_headers(self) -> dict:
        """Get request headers with authentication."""
        return {
            "X-Figma-Token": self.api_token,
            "Content-Type": "application/json",
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = asyncio.get_event_loop().time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        retry_count: int = 0,
    ) -> dict:
        """Make HTTP request with error handling and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to BASE_URL)
            params: Query parameters
            retry_count: Current retry attempt number

        Returns:
            Parsed JSON response

        Raises:
            FigmaAuthenticationError: When API token is invalid
            FigmaRateLimitError: When rate limit exceeded
            FigmaFileNotFoundError: When file doesn't exist
            FigmaAPIError: For other API errors
        """
        await self._rate_limit()
        client = await self._get_client()

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
            )

            if response.status_code == 200:
                return response.json()

            should_retry = await self._handle_error_response(response, retry_count)
            if should_retry and retry_count < self.max_retries:
                return await self._request(method, endpoint, params, retry_count + 1)

            raise FigmaAPIError(
                "Unexpected error after error handling",
                status_code=response.status_code,
            )

        except httpx.TimeoutException as e:
            raise FigmaAPIError(
                f"Request timeout: {e}",
                status_code=408,
                details={"endpoint": endpoint},
            ) from e
        except httpx.RequestError as e:
            raise FigmaAPIError(
                f"Request failed: {e}",
                details={"endpoint": endpoint, "error": str(e)},
            ) from e

    async def _handle_error_response(self, response: httpx.Response, retry_count: int) -> bool:
        """Handle error response and potentially retry.

        Args:
            response: Error response
            retry_count: Current retry attempt number

        Returns:
            True if should retry, False if should raise exception

        Raises:
            FigmaAuthenticationError: 401 status
            FigmaFileNotFoundError: 404 status
            FigmaRateLimitError: 429 status (with retry)
            FigmaAPIError: Other error statuses
        """
        status_code = response.status_code
        error_data = response.json() if response.content else {}

        if status_code == 401:
            raise FigmaAuthenticationError()

        if status_code == 404:
            raise FigmaFileNotFoundError(response.url.path.split("/")[-1])

        if status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 1))
            if retry_count < self.max_retries:
                await asyncio.sleep(retry_after)
                return True

            raise FigmaRateLimitError(retry_after=retry_after)

        message = error_data.get("err", "Unknown error")
        raise FigmaAPIError(
            f"Figma API error: {message}",
            status_code=status_code,
            error_code=error_data.get("code"),
            details=error_data,
        )

    async def get_file(self, file_key: str) -> dict:
        """Fetch complete file data from Figma.

        Args:
            file_key: Figma file key (from file URL)

        Returns:
            Complete file data as dictionary
        """
        result = await self._request("GET", f"/files/{file_key}")
        return result

    async def get_file_nodes(self, file_key: str, node_ids: list[str]) -> dict:
        """Fetch specific nodes and their children.

        Args:
            file_key: Figma file key
            node_ids: List of node IDs to fetch

        Returns:
            Node data as dictionary
        """
        result = await self._request(
            "GET", f"/files/{file_key}/nodes", params={"ids": ",".join(node_ids)}
        )
        return result

    async def get_comments(self, file_key: str) -> list[dict]:
        """Fetch comments on a file.

        Args:
            file_key: Figma file key

        Returns:
            List of comment dictionaries
        """
        result = await self._request("GET", f"/files/{file_key}/comments")
        return result.get("comments", [])

    async def get_file_info(self, file_key: str) -> FileInfo:
        """Get file metadata and info.

        Args:
            file_key: Figma file key

        Returns:
            FileInfo object with metadata
        """
        file_data = await self.get_file(file_key)
        return FileInfo.from_api_response(file_data)

    def extract_file_key(self, file_url: str) -> str:
        """Extract file key from Figma URL.

        Args:
            file_url: Full Figma file URL

        Returns:
            File key string

        Raises:
            ValueError: If URL is invalid
        """
        patterns = [
            r"figma\.com/file/([a-zA-Z0-9]+)",
            r"figma\.com/design/([a-zA-Z0-9]+)",
            r"figma\.com/([a-zA-Z0-9]{22,})",
        ]

        for pattern in patterns:
            match = re.search(pattern, file_url)
            if match:
                return match.group(1)

        raise ValueError(f"Invalid Figma URL: {file_url}")

    def extract_pages(self, file_data: dict) -> list[Page]:
        """Extract pages from file data.

        Args:
            file_data: Raw file data from API

        Returns:
            List of Page objects
        """
        pages = []
        for page_data in file_data.get("document", {}).get("children", []):
            pages.append(Page.from_dict(page_data))
        return pages

    def extract_components(self, page_data: dict) -> list[Component]:
        """Extract components from page data.

        Args:
            page_data: Page node data

        Returns:
            List of Component objects
        """
        components = []
        parent_frame = page_data.get("name", "")

        def find_components(node: dict) -> None:
            if node.get("type") == "COMPONENT":
                components.append(Component.from_dict(node, parent_frame))
            elif node.get("type") == "COMPONENT_SET":
                components.append(Component.from_dict(node, parent_frame))

            for child in node.get("children", []):
                find_components(child)

        for child in page_data.get("children", []):
            find_components(child)

        return components

    def extract_text_nodes(
        self, page_data: dict, hierarchy_prefix: list[str] | None = None
    ) -> list[TextNode]:
        """Extract text nodes with hierarchy context.

        Args:
            page_data: Page or frame node data
            hierarchy_prefix: Prefix for hierarchy path

        Returns:
            List of TextNode objects
        """
        text_nodes = []
        hierarchy = hierarchy_prefix or [page_data.get("name", "")]
        current_hierarchy = hierarchy.copy()

        def find_text(node: dict, path: list[str]) -> None:
            node_name = node.get("name", "")
            current_path = path + [node_name]

            if node.get("type") == "TEXT":
                text_nodes.append(TextNode.from_dict(node, current_path))

            elif node.get("type") in ("FRAME", "GROUP", "COMPONENT"):
                for child in node.get("children", []):
                    find_text(child, current_path)

        for child in page_data.get("children", []):
            find_text(child, current_hierarchy)

        return text_nodes

    def extract_frames(self, page_data: dict) -> list[Frame]:
        """Extract top-level frames from page.

        Args:
            page_data: Page node data

        Returns:
            List of Frame objects
        """
        frames = []
        for child in page_data.get("children", []):
            if child.get("type") == "FRAME":
                frames.append(Frame.from_dict(child))
        return frames

    def extract_annotations(self, file_data: dict) -> list[Annotation]:
        """Extract design annotations from file.

        Args:
            file_data: Raw file data

        Returns:
            List of Annotation objects
        """
        annotations = []
        comments = file_data.get("comments", [])

        for comment_data in comments:
            annotations.append(Annotation.from_comment(comment_data))

        return annotations

    async def get_full_design_data(
        self, file_key: str, page_names: list[str] | None = None
    ) -> dict:
        """Get complete design data for story generation.

        Args:
            file_key: Figma file key
            page_names: Optional list of page names to include (all if None)

        Returns:
            Dictionary with file info, pages, components, text, etc.
        """
        file_data = await self.get_file(file_key)
        comments = await self.get_comments(file_key)

        file_info = FileInfo.from_api_response(file_data)

        pages_data = []
        all_components = []
        all_text_nodes = []
        all_frames = []

        for page in file_info.pages:
            if page_names and page.name not in page_names:
                continue

            page_dict = {
                "id": page.id,
                "name": page.name,
                "nodeId": page.node_id,
                "children": page.children,
            }

            components = self.extract_components(page_dict)
            text_nodes = self.extract_text_nodes(page_dict)
            frames = self.extract_frames(page_dict)

            pages_data.append(page_dict)
            all_components.extend(components)
            all_text_nodes.extend(text_nodes)
            all_frames.extend(frames)

        return {
            "file_info": file_info,
            "pages": pages_data,
            "components": all_components,
            "text_nodes": all_text_nodes,
            "frames": all_frames,
            "comments": comments,
        }
