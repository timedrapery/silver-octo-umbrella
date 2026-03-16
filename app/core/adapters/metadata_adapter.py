import asyncio
import mimetypes
import os
import re
from pathlib import Path

import httpx

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType


class MetadataAdapter(BaseAdapter):
    name = "metadata"
    description = "Document and URL metadata extraction"
    supported_target_types = [TargetType.DOCUMENT, TargetType.URL]

    async def run(self, target: Target) -> list[Finding]:
        if target.type == TargetType.DOCUMENT:
            return self._extract_document_metadata(target)
        return await self._extract_url_metadata(target)

    def _extract_document_metadata(self, target: Target) -> list[Finding]:
        path = Path(target.value).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Document does not exist: {path}")

        stat_result = path.stat()
        mime_type, _ = mimetypes.guess_type(path.name)
        findings = [
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.METADATA,
                title="Document Filesystem Metadata",
                description=f"Collected filesystem metadata for {path.name}",
                data={
                    "path": str(path),
                    "size_bytes": stat_result.st_size,
                    "created": stat_result.st_ctime,
                    "modified": stat_result.st_mtime,
                    "mime_type": mime_type or "application/octet-stream",
                },
                severity=Severity.INFO,
                source_name="Filesystem Metadata",
            )
        ]

        findings.append(
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.METADATA,
                title="Document Naming Signals",
                description=f"Derived naming metadata from document path {path.name}",
                data={
                    "filename": path.name,
                    "suffix": path.suffix.lower(),
                    "parent_directory": str(path.parent),
                    "hidden": path.name.startswith("."),
                },
                severity=Severity.LOW,
                source_name="Filesystem Metadata",
            )
        )
        return findings

    async def _extract_url_metadata(self, target: Target) -> list[Finding]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0), follow_redirects=True) as client:
            response = await client.get(target.value)
            response.raise_for_status()

        headers = {key.lower(): value for key, value in response.headers.items()}
        title = self._extract_html_title(response.text)
        description = self._extract_meta_description(response.text)
        findings = [
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.METADATA,
                title="URL Response Metadata",
                description=f"Collected URL metadata from {response.url}",
                data={
                    "final_url": str(response.url),
                    "content_type": headers.get("content-type", ""),
                    "content_length": headers.get("content-length", ""),
                    "last_modified": headers.get("last-modified", ""),
                    "etag": headers.get("etag", ""),
                },
                severity=Severity.INFO,
                source_name="HTTP Metadata",
                source_url=str(response.url),
            )
        ]

        if title or description:
            findings.append(
                Finding(
                    target_id=target.id,
                    adapter_name=self.name,
                    finding_type=FindingType.METADATA,
                    title="HTML Page Metadata",
                    description=f"Extracted HTML metadata from {response.url}",
                    data={"title": title, "description": description},
                    severity=Severity.LOW,
                    source_name="HTTP Metadata",
                    source_url=str(response.url),
                )
            )

        media_metadata = await self._extract_media_metadata(str(response.url))
        if media_metadata:
            findings.append(
                Finding(
                    target_id=target.id,
                    adapter_name=self.name,
                    finding_type=FindingType.METADATA,
                    title="Media Platform Metadata (yt-dlp)",
                    description=f"Extracted media-platform metadata via yt-dlp for {response.url}",
                    data=media_metadata,
                    severity=Severity.LOW,
                    source_name="yt-dlp",
                    source_url=str(response.url),
                )
            )
        return findings

    async def _extract_media_metadata(self, url: str) -> dict | None:
        try:
            return await asyncio.to_thread(self._run_ytdlp_extract, url)
        except Exception:
            return None

    @staticmethod
    def _run_ytdlp_extract(url: str) -> dict | None:
        try:
            import yt_dlp
        except ImportError:
            return None

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        if not isinstance(info, dict) or not info:
            return None

        metadata = {
            "platform": info.get("extractor") or info.get("extractor_key", ""),
            "extractor_key": info.get("extractor_key", ""),
            "webpage_url": info.get("webpage_url") or url,
            "title": info.get("title", ""),
            "uploader": info.get("uploader", ""),
            "channel": info.get("channel", ""),
            "upload_date": info.get("upload_date", ""),
            "duration_seconds": info.get("duration", 0),
            "view_count": info.get("view_count", 0),
            "like_count": info.get("like_count", 0),
            "comment_count": info.get("comment_count", 0),
            "availability": info.get("availability", ""),
            "live_status": info.get("live_status", ""),
            "tags": info.get("tags") or [],
            "categories": info.get("categories") or [],
            "thumbnail": info.get("thumbnail", ""),
        }

        if isinstance(info.get("formats"), list):
            metadata["format_count"] = len(info["formats"])

        if info.get("_type") == "playlist":
            entries = info.get("entries") or []
            metadata["entry_count"] = len(entries)

        return metadata

    @staticmethod
    def _extract_html_title(body: str) -> str:
        match = re.search(r"<title>(.*?)</title>", body, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return re.sub(r"\s+", " ", match.group(1)).strip()

    @staticmethod
    def _extract_meta_description(body: str) -> str:
        match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
            body,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return ""
        return re.sub(r"\s+", " ", match.group(1)).strip()
