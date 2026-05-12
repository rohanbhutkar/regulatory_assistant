from __future__ import annotations

from agents.fda_labels_agent import FDALabelsAgent, dailymed_label_url


def test_dailymed_label_url_uses_setid_from_zip_file() -> None:
    assert (
        dailymed_label_url("20220630_f198ab39-9394-4280-be44-93a88264a450.zip")
        == "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=f198ab39-9394-4280-be44-93a88264a450"
    )


def test_dailymed_label_url_rejects_empty_ids() -> None:
    assert dailymed_label_url("") is None
    assert dailymed_label_url(None) is None


def test_dailymed_label_url_falls_back_to_ndc_search() -> None:
    assert (
        dailymed_label_url("", "0143-9368")
        == "https://dailymed.nlm.nih.gov/dailymed/search.cfm?query=0143-9368"
    )


def test_convert_to_standard_format_uses_dailymed_url() -> None:
    agent = FDALabelsAgent()
    result = agent._convert_to_standard_format(
        {
            "document_id": "000114da-959d-4159-bd00-22d9b7faad4d",
            "zip_file": "20210128_bb559b34-79b1-45a6-a148-38639115cd49.zip",
            "document_title": "Fenofibric Acid Tablets",
            "effective_time": 20210118,
            "product_code": "68134-601",
        }
    )

    assert result is not None
    assert result["url"] == (
        "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm"
        "?setid=bb559b34-79b1-45a6-a148-38639115cd49"
    )
    assert "accessdata.fda.gov/drugsatfda_docs/label" not in result["url"]
