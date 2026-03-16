import hashlib

import httpx

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType


class SocialAdapter(BaseAdapter):
    name = "social"
    description = "Social media account discovery"
    supported_target_types = [TargetType.USERNAME, TargetType.EMAIL]

    async def run(self, target: Target) -> list[Finding]:
        identifier = target.value.split("@")[0] if "@" in target.value else target.value
        findings = []
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0), follow_redirects=True) as client:
            if target.type == TargetType.EMAIL:
                gravatar = await self._lookup_gravatar(client, target.value)
                if gravatar:
                    findings.append(
                        Finding(
                            target_id=target.id,
                            adapter_name=self.name,
                            finding_type=FindingType.SOCIAL,
                            title="Public Avatar Profile Found: Gravatar",
                            description=f"Observed a public Gravatar profile for {target.value}",
                            data=gravatar,
                            severity=Severity.LOW,
                            source_name="Gravatar",
                            source_url=gravatar["url"],
                        )
                    )

            for profile in await self._lookup_username_profiles(client, identifier):
                findings.append(
                    Finding(
                        target_id=target.id,
                        adapter_name=self.name,
                        finding_type=FindingType.SOCIAL,
                        title=f"Profile Found: {profile['platform']}",
                        description=profile["description"],
                        data=profile,
                        severity=Severity.LOW,
                        source_name=profile["platform"],
                        source_url=profile["url"],
                    )
                )
        return findings

    async def _lookup_username_profiles(self, client: httpx.AsyncClient, username: str) -> list[dict]:
        findings: list[dict] = []

        github_response = await client.get(f"https://api.github.com/users/{username}")
        if github_response.status_code == 200:
            payload = github_response.json()
            findings.append(
                {
                    "platform": "GitHub",
                    "url": payload.get("html_url", f"https://github.com/{username}"),
                    "description": f"GitHub account {username} found with {payload.get('public_repos', 0)} public repositories.",
                    "followers": payload.get("followers", 0),
                    "public_repos": payload.get("public_repos", 0),
                    "bio": payload.get("bio", ""),
                }
            )

        gitlab_response = await client.get("https://gitlab.com/api/v4/users", params={"username": username})
        if gitlab_response.status_code == 200:
            payload = gitlab_response.json()
            if payload:
                user = payload[0]
                findings.append(
                    {
                        "platform": "GitLab",
                        "url": user.get("web_url", f"https://gitlab.com/{username}"),
                        "description": f"GitLab account {username} found with state {user.get('state', 'unknown')}.",
                        "state": user.get("state", ""),
                        "bio": user.get("bio", ""),
                    }
                )

        hn_response = await client.get(f"https://hacker-news.firebaseio.com/v0/user/{username}.json")
        if hn_response.status_code == 200 and hn_response.text != "null":
            payload = hn_response.json()
            findings.append(
                {
                    "platform": "Hacker News",
                    "url": f"https://news.ycombinator.com/user?id={username}",
                    "description": f"Hacker News account {username} found with karma {payload.get('karma', 0)}.",
                    "karma": payload.get("karma", 0),
                    "created": payload.get("created"),
                }
            )

        keybase_response = await client.get(
            "https://keybase.io/_/api/1.0/user/lookup.json",
            params={"usernames": username},
        )
        if keybase_response.status_code == 200:
            payload = keybase_response.json()
            them = payload.get("them") or []
            if them:
                profile = them[0]
                findings.append(
                    {
                        "platform": "Keybase",
                        "url": f"https://keybase.io/{username}",
                        "description": f"Keybase account {username} found.",
                        "bio": profile.get("profile", {}).get("bio", ""),
                        "full_name": profile.get("profile", {}).get("full_name", ""),
                    }
                )

        return findings

    async def _lookup_gravatar(self, client: httpx.AsyncClient, email: str) -> dict | None:
        digest = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
        url = f"https://www.gravatar.com/avatar/{digest}?d=404"
        response = await client.get(url)
        if response.status_code != 200:
            return None
        return {"platform": "Gravatar", "url": url, "email_hash": digest}
