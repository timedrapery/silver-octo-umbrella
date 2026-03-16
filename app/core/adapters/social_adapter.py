import asyncio
import random

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType


class SocialAdapter(BaseAdapter):
    name = "social"
    description = "Social media account discovery"
    supported_target_types = [TargetType.USERNAME, TargetType.EMAIL]

    async def run(self, target: Target) -> list[Finding]:
        await asyncio.sleep(random.uniform(0.5, 2.0))
        identifier = target.value.split("@")[0] if "@" in target.value else target.value

        platforms = [
            {
                "platform": "Twitter/X",
                "url": f"https://twitter.com/{identifier}",
                "bio": f"Thoughts and ideas | Tech enthusiast | {identifier}",
                "followers": random.randint(50, 5000),
            },
            {
                "platform": "GitHub",
                "url": f"https://github.com/{identifier}",
                "bio": f"Software developer. Open source contributor.",
                "repos": random.randint(5, 80),
            },
            {
                "platform": "LinkedIn",
                "url": f"https://linkedin.com/in/{identifier}",
                "bio": f"Professional profile | Software Engineer",
                "connections": random.randint(100, 500),
            },
            {
                "platform": "Reddit",
                "url": f"https://reddit.com/u/{identifier}",
                "bio": f"Redditor since 2018. Tech & gaming subreddits.",
                "karma": random.randint(100, 10000),
            },
            {
                "platform": "Instagram",
                "url": f"https://instagram.com/{identifier}",
                "bio": f"📸 Photography | Travel | Life",
                "followers": random.randint(50, 2000),
            },
            {
                "platform": "HackerNews",
                "url": f"https://news.ycombinator.com/user?id={identifier}",
                "bio": f"HN member with tech commentary.",
                "karma": random.randint(10, 1000),
            },
        ]

        count = random.randint(3, 6)
        selected = random.sample(platforms, count)

        findings = []
        for p in selected:
            findings.append(
                Finding(
                    target_id=target.id,
                    adapter_name=self.name,
                    finding_type=FindingType.SOCIAL,
                    title=f"Profile Found: {p['platform']}",
                    description=f"Account '{identifier}' found on {p['platform']}. Bio: {p['bio']}",
                    data=p,
                    severity=Severity.LOW,
                    source_name=p["platform"],
                    source_url=p["url"],
                )
            )
        return findings
