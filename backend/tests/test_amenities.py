from app.db.enums import AMENITY_KEYS, AMENITY_LABELS_RU


def test_eighteen_amenities():
    assert len(AMENITY_KEYS) == 18
    assert set(AMENITY_LABELS_RU) == set(AMENITY_KEYS)
