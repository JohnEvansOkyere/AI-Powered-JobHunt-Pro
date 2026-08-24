"""Tests for the weekly ALX Ghana digest importer."""

from datetime import datetime, timezone

import pytest

from app.services.alx_job_importer import (
    ALX_ORIGIN_SYSTEM,
    ALX_SOURCE,
    DEFAULT_LOCATION,
    AlxJobImportService,
    ParsedAlxJob,
    normalize_url,
    parse_digest_text,
)


DIGEST_TEXT = """ALX GHANA COMMUNITY - JOB OPPORTUNITIES CORNER
1. MDF West Africa is hiring a business development officer.
Apply here:
https://www.jobsinghana.com/job-ads/business-development-officer-57414
Deadline: August 16, 2026
2. Amasha Partners Ltd is hiring a virtual assistant.
Apply here: https://www.jobsinghana.com/job-ads/virtual-assistant-57411
Deadline: September 02, 2026
3. Teabag Charity is hiring an accounts manager.
Apply here:
https://www.jobsinghana.com/job-ads/accounts-manager-57452
Deadline: August 31, 2026
"""


class TestParseDigestText:
    def test_parses_every_entry(self):
        jobs = parse_digest_text(DIGEST_TEXT)
        assert len(jobs) == 3

    def test_splits_company_from_role(self):
        first, second, third = parse_digest_text(DIGEST_TEXT)
        assert first.company == "MDF West Africa"
        assert first.title == "business development officer"
        assert second.company == "Amasha Partners Ltd"
        assert second.title == "virtual assistant"
        # "an accounts manager" - the article is stripped, not folded into the title
        assert third.title == "accounts manager"

    def test_parses_deadlines_as_utc(self):
        first = parse_digest_text(DIGEST_TEXT)[0]
        assert first.deadline == datetime(2026, 8, 16, tzinfo=timezone.utc)

    def test_reads_urls_from_text_when_no_annotations_given(self):
        first = parse_digest_text(DIGEST_TEXT)[0]
        assert first.apply_url.endswith("business-development-officer-57414")

    def test_supplied_links_win_over_text_urls(self):
        """Text-layer URLs wrap and truncate; annotation URIs are authoritative."""
        links = [
            "https://example.com/a-full-url",
            "https://example.com/b-full-url",
            "https://example.com/c-full-url",
        ]
        jobs = parse_digest_text(DIGEST_TEXT, links=links)
        assert [job.apply_url for job in jobs] == links

    def test_entry_without_hiring_phrase_keeps_headline_as_title(self):
        text = (
            "1. Graduate trainee programme now open.\n"
            "Apply here: https://example.com/grad\n"
            "Deadline: August 16, 2026\n"
        )
        job = parse_digest_text(text)[0]
        assert job.title == "Graduate trainee programme now open"
        assert job.apply_url == "https://example.com/grad"

    def test_entry_without_url_is_dropped(self):
        text = "1. Some Co is hiring a cook.\nApply here:\nDeadline: August 16, 2026\n"
        assert parse_digest_text(text) == []

    def test_empty_input_yields_nothing(self):
        assert parse_digest_text("") == []


class TestNormalizeUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.jobsinghana.com/job-ads/x-1",
            "http://jobsinghana.com/job-ads/x-1/",
            "https://JobsInGhana.com/job-ads/x-1",
        ],
    )
    def test_variants_collapse_to_one_key(self, url):
        assert normalize_url(url) == "https://jobsinghana.com/job-ads/x-1"

    def test_query_string_is_significant(self):
        assert normalize_url("https://a.com/j?id=1") != normalize_url("https://a.com/j?id=2")

    def test_fragment_is_dropped(self):
        assert normalize_url("https://a.com/j#apply") == normalize_url("https://a.com/j")


class TestOriginJobId:
    def test_is_stable_across_url_variants(self):
        base = dict(index=1, company="X", title="Y", deadline=None, raw_headline="")
        a = ParsedAlxJob(apply_url="https://www.a.com/job-1", **base)
        b = ParsedAlxJob(apply_url="http://a.com/job-1/", **base)
        assert a.origin_job_id == b.origin_job_id

    def test_differs_between_jobs(self):
        base = dict(index=1, company="X", title="Y", deadline=None, raw_headline="")
        a = ParsedAlxJob(apply_url="https://a.com/job-1", **base)
        b = ParsedAlxJob(apply_url="https://a.com/job-2", **base)
        assert a.origin_job_id != b.origin_job_id


class TestBuildJobValues:
    @pytest.fixture
    def parsed(self):
        return ParsedAlxJob(
            index=1,
            company="MDF West Africa",
            title="business development officer",
            apply_url="https://www.jobsinghana.com/job-ads/bdo-57414",
            deadline=datetime(2026, 8, 16, tzinfo=timezone.utc),
            raw_headline="MDF West Africa is hiring a business development officer.",
        )

    def test_tags_source_and_origin_for_dedupe(self, parsed):
        values = AlxJobImportService(None).build_job_values(parsed)
        assert values["source"] == ALX_SOURCE
        assert values["origin_system"] == ALX_ORIGIN_SYSTEM
        assert values["origin_job_id"] == parsed.origin_job_id

    def test_defaults_location_to_ghana_without_enrichment(self, parsed):
        values = AlxJobImportService(None).build_job_values(parsed)
        assert values["location"] == DEFAULT_LOCATION

    def test_falls_back_to_headline_description(self, parsed):
        values = AlxJobImportService(None).build_job_values(parsed)
        assert values["description"] == (
            "MDF West Africa is hiring a business development officer."
        )

    def test_carries_the_deadline_through(self, parsed):
        values = AlxJobImportService(None).build_job_values(parsed)
        assert values["application_deadline"] == parsed.deadline

    def test_enrichment_overrides_placeholder_fields(self, parsed):
        enrichment = {
            "description": "A real description scraped from the posting.",
            "location": "Accra, Ghana",
            "job_type": "Full-Time",
            "experience_level": "Mid",
            "remote_option": False,
            "skills": ["Sales", "CRM"],
        }
        values = AlxJobImportService(None).build_job_values(parsed, enrichment)
        assert values["description"] == enrichment["description"]
        assert values["location"] == "Accra, Ghana"
        assert values["job_type"] == "full-time"
        assert values["experience_level"] == "mid"
        assert values["remote_type"] == "onsite"
        assert values["skills"] == '["Sales", "CRM"]'

    def test_blank_enrichment_does_not_erase_defaults(self, parsed):
        values = AlxJobImportService(None).build_job_values(
            parsed, {"description": "   ", "location": ""}
        )
        assert values["location"] == DEFAULT_LOCATION
        assert values["description"].startswith("MDF West Africa is hiring")

    def test_apply_url_is_kept_for_the_candidate_link(self, parsed):
        values = AlxJobImportService(None).build_job_values(parsed)
        assert values["job_link"] == parsed.apply_url
        assert values["source_url"] == parsed.apply_url
