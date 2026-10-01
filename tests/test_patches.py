"""Live tests against NYC Open Data (needs internet, no API key)."""

from patches import count_noise_complaints, get_gardens, sincerity


def test_queens_returns_gardens_with_expected_keys():
    gardens = get_gardens("QUEENS", limit=3)
    assert len(gardens) >= 1
    for g in gardens:
        assert set(g) == {"gardenname", "address", "zipcode", "borough", "nta"}
        assert g["borough"] == "QUEENS"


def test_neighborhood_name_returns_empty_list():
    # The Milestone 2 bug: a neighborhood isn't a borough, so we get [] with no hint.
    assert get_gardens("Astoria") == []


def test_noise_count_is_a_non_negative_int():
    count = count_noise_complaints("11102", days=7)
    assert isinstance(count, int)
    assert count >= 0


def test_two_zips_can_differ():
    # Live data, so we only check they're both real counts. In practice they differ.
    a = count_noise_complaints("11102", days=7)
    b = count_noise_complaints("10009", days=7)
    assert isinstance(a, int) and isinstance(b, int)


def test_sincerity_labels():
    assert sincerity(0) == {"noise_complaints": 0, "sincerity_score": 100, "label": "Sincere"}
    assert sincerity(100)["label"] == "Mostly sincere"   # score 50
    assert sincerity(156)["label"] == "Chaotic patch"    # score 22
    assert sincerity(500)["sincerity_score"] == 0         # never below 0
