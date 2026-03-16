from dataclasses import dataclass, field
from urllib.parse import quote_plus

from app.models.case import SearchIntent, SearchProvider


@dataclass
class SearchRecipe:
    id: str
    name: str
    intent: SearchIntent
    description: str
    suggested_site: str = ""
    suggested_filetype: str = ""
    suggested_all_terms: list[str] = field(default_factory=list)
    suggested_excluded_terms: list[str] = field(default_factory=list)


@dataclass
class SearchBuildRequest:
    provider: SearchProvider
    intent: SearchIntent
    target_value: str = ""
    exact_phrase: str = ""
    all_terms: list[str] = field(default_factory=list)
    any_terms: list[str] = field(default_factory=list)
    excluded_terms: list[str] = field(default_factory=list)
    site: str = ""
    filetype: str = ""
    in_title_terms: list[str] = field(default_factory=list)
    in_url_terms: list[str] = field(default_factory=list)


@dataclass
class SearchBuildResult:
    query: str
    explanation: str
    launch_url: str


_RECIPES: list[SearchRecipe] = [
    SearchRecipe(
        id="person_profile",
        name="Person Profile Discovery",
        intent=SearchIntent.PERSON_PROFILE,
        description="Find public profiles and mentions for a person.",
        suggested_all_terms=["profile", "bio"],
    ),
    SearchRecipe(
        id="username_footprint",
        name="Username Footprint",
        intent=SearchIntent.USERNAME_FOOTPRINT,
        description="Find where a username appears on public websites.",
        suggested_all_terms=["account", "profile"],
    ),
    SearchRecipe(
        id="domain_exposure",
        name="Domain Exposure Search",
        intent=SearchIntent.DOMAIN_EXPOSURE,
        description="Find public references, leaks, or exposed artifacts mentioning a domain.",
        suggested_all_terms=["leak", "config", "password"],
    ),
    SearchRecipe(
        id="document_discovery",
        name="Public Documents Discovery",
        intent=SearchIntent.DOCUMENT_DISCOVERY,
        description="Find public documents and indexed files tied to a target.",
        suggested_filetype="pdf",
        suggested_all_terms=["report", "document"],
    ),
    SearchRecipe(
        id="email_mentions",
        name="Email Mention Search",
        intent=SearchIntent.EMAIL_MENTION,
        description="Find public mentions of an email address.",
        suggested_all_terms=["contact", "email"],
    ),
    SearchRecipe(
        id="credential_mentions",
        name="Credential Exposure Mentions",
        intent=SearchIntent.CREDENTIAL_MENTION,
        description="Find public discussions or dumps mentioning credentials.",
        suggested_all_terms=["password", "dump", "leak"],
    ),
    SearchRecipe(
        id="infrastructure_refs",
        name="Infrastructure Reference Search",
        intent=SearchIntent.INFRASTRUCTURE_REFERENCE,
        description="Find references to infrastructure assets in public pages.",
        suggested_all_terms=["server", "endpoint", "api"],
    ),
    SearchRecipe(
        id="contact_footprint",
        name="Public Contact Footprint",
        intent=SearchIntent.CONTACT_FOOTPRINT,
        description="Find phone, address, and contact details on public pages.",
        suggested_all_terms=["phone", "contact", "address"],
    ),
]


class SearchBuilderService:
    def list_recipes(self) -> list[SearchRecipe]:
        return list(_RECIPES)

    def get_recipe(self, recipe_id: str) -> SearchRecipe | None:
        for recipe in _RECIPES:
            if recipe.id == recipe_id:
                return recipe
        return None

    def parse_terms(self, text: str) -> list[str]:
        if not text.strip():
            return []
        parts = [
            part.strip()
            for chunk in text.replace("\n", ",").split(",")
            for part in chunk.split()
        ]
        seen: set[str] = set()
        terms: list[str] = []
        for part in parts:
            if part and part.lower() not in seen:
                terms.append(part)
                seen.add(part.lower())
        return terms

    def normalize_domain(self, domain: str) -> str:
        value = domain.strip().lower()
        if value.startswith("https://"):
            value = value[len("https://") :]
        if value.startswith("http://"):
            value = value[len("http://") :]
        return value.strip("/")

    def normalize_filetype(self, filetype: str) -> str:
        return filetype.strip().lower().lstrip(".")

    def build_query(self, request: SearchBuildRequest) -> SearchBuildResult:
        if request.provider != SearchProvider.GOOGLE:
            raise ValueError("Only GOOGLE provider is supported in Sprint 3")

        query_parts: list[str] = []
        explanation_parts: list[str] = []

        target_value = request.target_value.strip()
        if target_value:
            query_parts.append(self._quote(target_value))
            explanation_parts.append(f"focuses on '{target_value}'")

        exact_phrase = request.exact_phrase.strip()
        if exact_phrase:
            query_parts.append(f'"{exact_phrase}"')
            explanation_parts.append(f"requires exact phrase '{exact_phrase}'")

        if request.all_terms:
            all_terms = [self._quote_if_needed(term) for term in request.all_terms]
            query_parts.extend(all_terms)
            explanation_parts.append(
                "requires all keywords: " + ", ".join(request.all_terms)
            )

        if request.any_terms:
            any_terms = [self._quote_if_needed(term) for term in request.any_terms]
            query_parts.append("(" + " OR ".join(any_terms) + ")")
            explanation_parts.append(
                "matches any of: " + ", ".join(request.any_terms)
            )

        if request.excluded_terms:
            for term in request.excluded_terms:
                query_parts.append("-" + self._quote_if_needed(term))
            explanation_parts.append(
                "excludes: " + ", ".join(request.excluded_terms)
            )

        if request.site:
            site = self.normalize_domain(request.site)
            if site:
                query_parts.append(f"site:{site}")
                explanation_parts.append(f"limits results to site '{site}'")

        if request.filetype:
            filetype = self.normalize_filetype(request.filetype)
            if filetype:
                query_parts.append(f"filetype:{filetype}")
                explanation_parts.append(f"limits to filetype '{filetype}'")

        if request.in_title_terms:
            for term in request.in_title_terms:
                query_parts.append("intitle:" + self._quote_if_needed(term))
            explanation_parts.append(
                "requires title terms: " + ", ".join(request.in_title_terms)
            )

        if request.in_url_terms:
            for term in request.in_url_terms:
                query_parts.append("inurl:" + self._quote_if_needed(term))
            explanation_parts.append(
                "requires URL terms: " + ", ".join(request.in_url_terms)
            )

        query = " ".join(query_parts).strip()
        if not query:
            raise ValueError("Please provide at least one search input")

        intent_label = request.intent.value.replace("_", " ").title()
        explanation = (
            f"Google search for {intent_label.lower()} that "
            + "; ".join(explanation_parts)
            + "."
        )

        launch_url = "https://www.google.com/search?q=" + quote_plus(query)
        return SearchBuildResult(query=query, explanation=explanation, launch_url=launch_url)

    @staticmethod
    def _quote(value: str) -> str:
        return '"' + value.replace('"', "") + '"'

    def _quote_if_needed(self, term: str) -> str:
        cleaned = term.strip().replace('"', "")
        if " " in cleaned:
            return self._quote(cleaned)
        return cleaned
