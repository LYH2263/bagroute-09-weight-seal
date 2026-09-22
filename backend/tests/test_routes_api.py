"""路线封袋阈值的 API 级测试：保存校验、落库持久化、装袋使用阈值。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import DeliveryRoute, SubscriberStop

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
# 不以上下文管理器方式使用，避免触发 lifespan 连接真实数据库
client = TestClient(app)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def make_route(db, **kw) -> DeliveryRoute:
    route = DeliveryRoute(
        name=kw.pop("name", "测试线"),
        max_weight_kg=kw.pop("max_weight_kg", 8.0),
        max_volume_l=kw.pop("max_volume_l", 20.0),
        **kw,
    )
    db.add(route)
    db.commit()
    return route


def test_patch_seal_threshold_persists(db_session):
    route = make_route(db_session)
    res = client.patch(f"/api/routes/{route.id}", json={"seal_threshold_kg": 5.0})
    assert res.status_code == 200
    assert res.json()["seal_threshold_kg"] == 5.0
    # 再次进入仍有效（已落库）
    again = client.get("/api/routes").json()
    assert again[0]["seal_threshold_kg"] == 5.0


def test_patch_seal_threshold_above_limit_fails(db_session):
    route = make_route(db_session, max_weight_kg=8.0)
    res = client.patch(f"/api/routes/{route.id}", json={"seal_threshold_kg": 9.0})
    assert res.status_code == 400
    assert "阈值" in res.json()["detail"]
    # 非法值未落库
    db_session.expire_all()
    assert db_session.get(DeliveryRoute, route.id).seal_threshold_kg != 9.0


def test_patch_max_weight_below_existing_threshold_fails(db_session):
    route = make_route(db_session, max_weight_kg=8.0, seal_threshold_kg=5.0)
    res = client.patch(f"/api/routes/{route.id}", json={"max_weight_kg": 4.0})
    assert res.status_code == 400


def test_pack_uses_route_threshold(db_session):
    route = make_route(db_session, max_weight_kg=8.0, max_volume_l=20.0, seal_threshold_kg=2.2)
    db_session.add_all(
        [
            SubscriberStop(route_id=route.id, seq=1, name="甲", weight_kg=2.2, volume_l=4.0),
            SubscriberStop(route_id=route.id, seq=2, name="乙", weight_kg=3.5, volume_l=5.5),
            SubscriberStop(route_id=route.id, seq=3, name="丙", weight_kg=1.8, volume_l=3.0),
        ]
    )
    db_session.commit()
    res = client.post("/api/pack", json={"route_id": route.id})
    assert res.status_code == 200
    bags = res.json()
    # 体积与重量上限都够装下全部，但阈值 2.2 使每站达阈即封
    assert [b["bag_index"] for b in bags] == [1, 2, 3]
    assert all(b["seal_threshold_kg"] == 2.2 for b in bags)
    assert bags[0]["weight_kg"] == 2.2  # 第一站装完即达阈封袋
    assert [i["stop_name"] for i in bags[1]["items"]] == ["乙"]  # 第二站开新袋
    # 袋明细可核：阈值与上限随袋返回
    listed = client.get("/api/bags").json()
    assert listed[0]["seal_threshold_kg"] == 2.2
    assert listed[0]["max_weight_kg"] == 8.0
