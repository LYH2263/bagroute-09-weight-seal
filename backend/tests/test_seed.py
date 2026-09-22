from sqlalchemy import select

from app.models.models import DeliveryRoute, SubscriberStop
from app.services.pack_engine import StopItem, pack_route
from app.services.seed import seed_if_empty


def test_seed_sets_threshold_sealing_after_first_stop(db_session):
    seed_if_empty(db_session)

    route = db_session.scalar(select(DeliveryRoute).where(DeliveryRoute.name == "城东晨线"))
    assert route is not None
    # 阈值等于第一站重量
    assert route.seal_weight_kg == 2.2
    assert route.seal_weight_kg <= route.max_weight_kg

    stops = db_session.scalars(
        select(SubscriberStop).where(SubscriberStop.route_id == route.id)
    ).all()
    assert (stops[0].weight_kg, stops[0].volume_l) == (2.2, 4.0)

    result = pack_route(
        [StopItem(s.id, s.seq, s.weight_kg, s.volume_l, s.name) for s in stops],
        route.max_weight_kg,
        route.max_volume_l,
        route.seal_weight_kg,
    )
    # 第一站装完即封袋，第二站必须开新袋
    assert [i.stop_id for i in result.bags[0].items] == [stops[0].id]
    assert stops[1].id in [i.stop_id for i in result.bags[1].items]
    # 超大件样例仍被拒收
    assert any(s.label == "超大件样例" and s.weight_kg == 9.5 for s, _ in result.rejects)
