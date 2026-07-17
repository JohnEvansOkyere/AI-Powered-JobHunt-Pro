from app.scrapers.base import clean_job_description


def test_clean_job_description_removes_html_and_decodes_entities():
    value = "<p>Build <strong>Python</strong> APIs.</p><p>&amp; ship them<br>reliably.</p>"

    assert clean_job_description(value) == "Build Python APIs.\n\n& ship them\nreliably."


def test_clean_job_description_keeps_plain_text_readable():
    assert clean_job_description("German Softwareentwickler &amp; Support") == "German Softwareentwickler & Support"
