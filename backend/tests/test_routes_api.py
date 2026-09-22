from app.models.models import DeliveryRoute, SubscriberStop


def _make_route(db, seal=None):
    route = DeliveryRoute(
        name="测试线", max_weight_kg=8.0, max_volume_l=18.0, seal_weight_kg=seal
    )
    db.add(route)
    db.flush()
    db.add_all(
        [
            SubscriberStop(route_id=route.id, seq=1, name="甲站", weight_kg=2.0, volume_l=2.0),
            SubscriberStop(route_id=route.id, seq=2, name="乙站", weight_kg=1.0, volume_l=2.0),
            SubscriberStop(route_id=route.id, seq=3, name="丙站", weight_kg=1.0, volume_l=2.0),
        ]
    )
    db.commit()
    return route.id


def test_save_threshold_greater_than_cap_fails(client, db_session):
    rid = _make_route(db_session)
    res = client.put(f"/api/routes/{rid}", json={"seal_weight_kg": 9.0})
    assert res.status_code == 400

    # 非法阈值不得落库
    db_session.expire_all()
    route = db_session.get(DeliveryRoute, rid)
    assert route.seal_weight_kg is None

    # 路线列表不应出现非法阈值
    rows = client.get("/api/routes").json()
    assert rows[0]["seal_weight_kg"] is None


def test_save_valid_threshold_persists(client, db_session):
    rid = _make_route(db_session)
    res = client.put(f"/api/routes/{rid}", json={"seal_weight_kg": 2.0})
    assert res.status_code == 200
    assert res.json()["seal_weight_kg"] == 2.0

    # 再次进入仍有效（重新查询）
    rows = client.get("/api/routes").json()
    assert rows[0]["seal_weight_kg"] == 2.0


def test_threshold_equal_to_cap_is_allowed(client, db_session):
    rid = _make_route(db_session)
    res = client.put(f"/api/routes/{rid}", json={"seal_weight_kg": 8.0})
    assert res.status_code == 200
    assert res.json()["seal_weight_kg"] == 8.0


def test_pack_uses_threshold_and_returns_it(client, db_session):
    rid = _make_route(db_session, seal=2.0)
    bags = client.post("/api/pack", json={"route_id": rid}).json()
    # 第一站 2.0kg 达阈值即封；第二、三站共 2.0kg 同袋
    assert len(bags) == 2
    assert bags[0]["seal_weight_kg"] == 2.0
    assert bags[0]["max_weight_kg"] == 8.0
    assert [i["stop_name"] for i in bags[0]["items"]] == ["甲站"]
    assert [i["stop_name"] for i in bags[1]["items"]] == ["乙站", "丙站"]

    # /bags 同样可核阈值与上限
    persisted = client.get("/api/bags").json()
    assert {b["seal_weight_kg"] for b in persisted} == {2.0}
    assert {b["max_weight_kg"] for b in persisted} == {8.0}
