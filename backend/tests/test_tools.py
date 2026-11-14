from app.tools import costar, matterport, osm


def test_rent_yearly_and_monthly_basis():
    assert costar.normalize_rent({"rateLow": 24, "rateBasis": 2, "squareFeetMax": 1000}) == (2000, 24)
    assert costar.normalize_rent({"rateLow": 2, "rateBasis": 1, "squareFeetMax": 1000}) == (2000, 24)


def test_rent_zero_means_not_given():
    assert costar.normalize_rent({"rateLow": 0, "rateHigh": 0, "rateBasis": 2, "squareFeetMax": 1000}) == (None, None)


def test_osm_filter_needs_every_part():
    f = '["amenity"~"cafe|restaurant"]["name"~"boba",i]'
    assert osm.matches(f, {"amenity": "cafe", "name": "Boba Bar"})
    assert not osm.matches(f, {"amenity": "school", "name": "Boba Academy"})
    assert not osm.matches('["amenity"="cafe"]', {"amenity": "cafe;bar"})


def _fake_model(monkeypatch, floor, rooms):
    model = {"floors": [{"dimensions": {"areaFloor": floor, "units": "imperial"}}], "rooms": rooms}
    monkeypatch.setattr(matterport, "cached", lambda *a: model)


def test_seats_subtract_back_of_house(monkeypatch):
    _fake_model(monkeypatch, 1500, [{"label": "Kitchen", "dimensions": {"areaFloor": 300, "units": "imperial"}},
                                    {"label": "", "dimensions": None}])
    i = matterport.interior("x", listed_sqft=1500)
    assert i.estSeats == 80 and len(i.rooms) == 1  # (1500-300)/15; unlabeled room skipped


def test_building_scan_uses_listed_size(monkeypatch):
    _fake_model(monkeypatch, 8000, [])
    assert matterport.interior("x", listed_sqft=1000).estSeats == 40  # 0.6*1000/15, not 0.6*8000/15
