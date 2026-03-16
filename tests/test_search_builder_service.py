"""Tests for search builder service."""

import pytest

from app.models.case import SearchIntent, SearchProvider
from app.services.search_builder_service import SearchBuildRequest, SearchBuilderService


class TestSearchBuilderService:
    def test_list_recipes_returns_guided_catalog(self):
        service = SearchBuilderService()
        recipes = service.list_recipes()
        assert len(recipes) >= 5
        assert any(recipe.id == "domain_exposure" for recipe in recipes)

    def test_parse_terms_deduplicates_case_insensitive(self):
        service = SearchBuilderService()
        terms = service.parse_terms("admin, login Admin\nportal")
        assert terms == ["admin", "login", "portal"]

    def test_normalize_domain_and_filetype(self):
        service = SearchBuilderService()
        assert service.normalize_domain("https://Example.com/") == "example.com"
        assert service.normalize_filetype(".PDF") == "pdf"

    def test_build_query_with_structured_operators(self):
        service = SearchBuilderService()
        request = SearchBuildRequest(
            provider=SearchProvider.GOOGLE,
            intent=SearchIntent.DOMAIN_EXPOSURE,
            target_value="example.com",
            exact_phrase="internal portal",
            all_terms=["admin", "dashboard"],
            any_terms=["login", "signin"],
            excluded_terms=["staging"],
            site="example.com",
            filetype="pdf",
            in_title_terms=["credentials"],
            in_url_terms=["backup"],
        )

        result = service.build_query(request)

        assert '"example.com"' in result.query
        assert '"internal portal"' in result.query
        assert "admin" in result.query
        assert "(login OR signin)" in result.query
        assert "-staging" in result.query
        assert "site:example.com" in result.query
        assert "filetype:pdf" in result.query
        assert "intitle:credentials" in result.query
        assert "inurl:backup" in result.query
        assert result.launch_url.startswith("https://www.google.com/search?q=")
        assert "Google search for" in result.explanation

    def test_build_query_requires_input(self):
        service = SearchBuilderService()
        request = SearchBuildRequest(
            provider=SearchProvider.GOOGLE,
            intent=SearchIntent.GENERAL_DISCOVERY,
        )
        with pytest.raises(ValueError):
            service.build_query(request)

    def test_build_query_rejects_non_google_provider(self):
        service = SearchBuilderService()
        request = SearchBuildRequest(
            provider="BING",  # type: ignore[arg-type]
            intent=SearchIntent.GENERAL_DISCOVERY,
            target_value="example.com",
        )
        with pytest.raises(ValueError):
            service.build_query(request)
