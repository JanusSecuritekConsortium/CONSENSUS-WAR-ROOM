from core.data_sources.models import NormalizedDataItem


def test_normalized_item_schema_contains_required_fields() -> None:
    required = {"item_id", "source", "source_type", "title", "summary", "url", "published_at", "fetched_at", "geography", "actors", "topics", "confidence", "credibility", "bias_label", "raw_ref"}
    assert required == set(NormalizedDataItem.__dataclass_fields__)


if __name__ == "__main__":
    test_normalized_item_schema_contains_required_fields()
    print("test_normalized_item_schema PASS")
