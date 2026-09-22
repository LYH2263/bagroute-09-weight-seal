import pytest

from app.services.pack_engine import (
    InvalidThresholdError,
    StopItem,
    pack_route,
)


def test_packs_in_route_order_splitting_bags():
    stops = [
        StopItem(1, 1, 2.0, 3.0),
        StopItem(2, 2, 2.5, 3.0),
        StopItem(3, 3, 1.0, 1.0),
    ]
    result = pack_route(stops, max_weight=4.0, max_volume=10.0)
    assert len(result.bags) == 2
    assert [i.stop_id for i in result.bags[0].items] == [1]
    assert [i.stop_id for i in result.bags[1].items] == [2, 3]
    assert not result.rejects
    assert result.seal_weight_kg is None


def test_reject_oversized_stop():
    stops = [StopItem(1, 1, 9.0, 1.0, "大件"), StopItem(2, 2, 1.0, 1.0)]
    result = pack_route(stops, max_weight=5.0, max_volume=5.0)
    assert len(result.rejects) == 1
    assert result.rejects[0][0].stop_id == 1
    assert len(result.bags) == 1
    assert result.bags[0].items[0].stop_id == 2


def test_volume_cap_triggers_new_bag():
    stops = [StopItem(1, 1, 1.0, 4.0), StopItem(2, 2, 1.0, 4.0)]
    result = pack_route(stops, max_weight=10.0, max_volume=5.0)
    assert len(result.bags) == 2


def test_threshold_opens_new_bag_even_with_capacity_left():
    # 体积与重量上限都仍有余量，但第一袋装完 2.0kg 达到阈值 2.0 → 第二站必须开新袋
    stops = [
        StopItem(1, 1, 2.0, 1.0),
        StopItem(2, 2, 1.0, 1.0),
        StopItem(3, 3, 1.0, 1.0),
    ]
    result = pack_route(stops, max_weight=8.0, max_volume=20.0, seal_weight=2.0)
    assert len(result.bags) == 2
    assert [i.stop_id for i in result.bags[0].items] == [1]
    assert [i.stop_id for i in result.bags[1].items] == [2, 3]
    assert result.bags[0].weight_kg == pytest.approx(2.0)
    # 第二袋装到 2.0kg 也达阈值，但后面没有站点
    assert result.bags[1].weight_kg == pytest.approx(2.0)
    assert not result.rejects
    assert result.seal_weight_kg == 2.0


def test_single_stop_above_threshold_but_under_cap_gets_own_bag():
    # 单站本身 3.0kg > 阈值 2.0 但 < 上限 5.0：正常装入并独占一袋，不拒收
    stops = [StopItem(1, 1, 3.0, 1.0), StopItem(2, 2, 1.0, 1.0)]
    result = pack_route(stops, max_weight=5.0, max_volume=10.0, seal_weight=2.0)
    assert not result.rejects
    assert len(result.bags) == 2
    assert [i.stop_id for i in result.bags[0].items] == [1]
    assert result.bags[0].weight_kg == pytest.approx(3.0)
    assert [i.stop_id for i in result.bags[1].items] == [2]


def test_oversized_stop_still_rejected_with_threshold():
    # 有阈值时单站超上限仍拒收，阈值不改变拒收规则
    stops = [StopItem(1, 1, 9.0, 1.0, "大件"), StopItem(2, 2, 1.0, 1.0)]
    result = pack_route(stops, max_weight=5.0, max_volume=5.0, seal_weight=2.0)
    assert len(result.rejects) == 1
    assert result.rejects[0][0].stop_id == 1
    assert len(result.bags) == 1
    assert result.bags[0].items[0].stop_id == 2


def test_threshold_greater_than_cap_raises():
    stops = [StopItem(1, 1, 1.0, 1.0)]
    with pytest.raises(InvalidThresholdError):
        pack_route(stops, max_weight=5.0, max_volume=5.0, seal_weight=6.0)
