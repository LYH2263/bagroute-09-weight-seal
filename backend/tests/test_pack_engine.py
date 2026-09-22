from app.services.pack_engine import StopItem, pack_route


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


def test_threshold_forces_new_bag_despite_remaining_capacity():
    # 重量上限与体积都还有余量，但袋重达到阈值必须开新袋
    stops = [
        StopItem(1, 1, 2.0, 3.0),
        StopItem(2, 2, 2.0, 3.0),
        StopItem(3, 3, 1.0, 1.0),
    ]
    # 不设阈值时三站同袋（总量 5kg / 7L，远低于 8kg / 20L 上限）
    assert len(pack_route(stops, max_weight=8.0, max_volume=20.0).bags) == 1
    result = pack_route(stops, max_weight=8.0, max_volume=20.0, seal_threshold=4.0)
    assert len(result.bags) == 2
    assert [i.stop_id for i in result.bags[0].items] == [1, 2]
    assert result.bags[0].weight_kg == 4.0  # 达到阈值即封
    assert [i.stop_id for i in result.bags[1].items] == [3]
    assert not result.rejects


def test_stop_above_threshold_but_under_limit_gets_own_bag():
    # 单站本身大于阈值但小于上限：不拒收，独占一袋且即封
    stops = [StopItem(1, 1, 5.0, 2.0), StopItem(2, 2, 1.0, 1.0)]
    result = pack_route(stops, max_weight=8.0, max_volume=20.0, seal_threshold=3.0)
    assert not result.rejects
    assert len(result.bags) == 2
    assert [i.stop_id for i in result.bags[0].items] == [1]
    assert result.bags[0].weight_kg == 5.0
    assert [i.stop_id for i in result.bags[1].items] == [2]


def test_reject_oversized_stop_with_threshold_set():
    # 配置阈值后，单站超上限仍拒收
    stops = [StopItem(1, 1, 9.0, 1.0, "大件"), StopItem(2, 2, 1.0, 1.0)]
    result = pack_route(stops, max_weight=8.0, max_volume=20.0, seal_threshold=4.0)
    assert len(result.rejects) == 1
    assert result.rejects[0][0].stop_id == 1
    assert "超重" in result.rejects[0][1]
    assert len(result.bags) == 1
    assert [i.stop_id for i in result.bags[0].items] == [2]
