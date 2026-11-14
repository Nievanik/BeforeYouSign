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



def _box(x_m, y_m, w_m, h_m, lat=29.7):
    import math
    k = 111_320 * math.cos(math.radians(lat))
    x0, y0 = x_m / k, lat + y_m / 111_320
    x1, y1 = x0 + w_m / k, y0 + h_m / 111_320
    return f"POLYGON(({x0} {y0},{x1} {y0},{x1} {y1},{x0} {y1},{x0} {y0}))"


PARCEL = _box(0, 0, 100, 100)


def test_parking_rows_counted_by_length():
    from app.tools import vexcel
    rows = [_box(5, 5, 71.3, 8), _box(5, 30, 60.2, 6.9)]  # 6003 Bellaire's two rows
    assert vexcel.estimate_spaces(PARCEL, rows) == 48


def test_parking_unclear_when_boxes_overlap_or_are_not_rows():
    from app.tools import vexcel
    assert vexcel.estimate_spaces(PARCEL, [_box(5, 5, 70, 8), _box(10, 6, 60, 8)]) is None  # overlapping
    assert vexcel.estimate_spaces(PARCEL, [_box(5, 5, 40, 40)]) is None  # blob, not a row
    assert vexcel.estimate_spaces(PARCEL, [_box(80, 5, 70, 8)]) is None  # mostly off the parcel
    assert vexcel.estimate_spaces(PARCEL, []) == 0
