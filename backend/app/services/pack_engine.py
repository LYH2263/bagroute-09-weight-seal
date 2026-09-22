"""Route-order bag packing with weight + volume caps; reject when exceed.

封袋阈值：当前袋已装重量达到 seal_threshold 后即封袋，下一站必须开新袋，
即使重量上限与体积上限都还有余量。单站本身大于阈值但不超过上限时独占一袋。
"""

from __future__ import annotations

from dataclasses import dataclass, field

_EPS = 1e-9


@dataclass(frozen=True)
class StopItem:
    stop_id: int
    seq: int
    weight_kg: float
    volume_l: float
    label: str = ""


@dataclass
class Bag:
    bag_index: int
    items: list[StopItem] = field(default_factory=list)
    weight_kg: float = 0.0
    volume_l: float = 0.0


@dataclass(frozen=True)
class PackResult:
    bags: list[Bag]
    rejects: list[tuple[StopItem, str]]


def can_fit(bag: Bag, item: StopItem, max_weight: float, max_volume: float) -> bool:
    return (
        bag.weight_kg + item.weight_kg <= max_weight + _EPS
        and bag.volume_l + item.volume_l <= max_volume + _EPS
    )


def is_sealed(bag: Bag, seal_threshold: float) -> bool:
    """袋重达到封袋阈值即封袋，后续站点必须开新袋。"""
    return bag.weight_kg >= seal_threshold - _EPS


def pack_route(
    stops: list[StopItem],
    max_weight: float,
    max_volume: float,
    seal_threshold: float | None = None,
) -> PackResult:
    if seal_threshold is None:
        seal_threshold = max_weight
    ordered = sorted(stops, key=lambda s: s.seq)
    bags: list[Bag] = []
    rejects: list[tuple[StopItem, str]] = []
    current: Bag | None = None

    for item in ordered:
        if item.weight_kg > max_weight or item.volume_l > max_volume:
            reason = []
            if item.weight_kg > max_weight:
                reason.append(f"超重 {item.weight_kg}>{max_weight}")
            if item.volume_l > max_volume:
                reason.append(f"超体积 {item.volume_l}>{max_volume}")
            rejects.append((item, "；".join(reason)))
            continue

        if (
            current is None
            or is_sealed(current, seal_threshold)
            or not can_fit(current, item, max_weight, max_volume)
        ):
            current = Bag(bag_index=len(bags) + 1)
            bags.append(current)

        if not can_fit(current, item, max_weight, max_volume):
            # should not happen after single-item check, but keep safe
            rejects.append((item, "无法装入新袋"))
            continue

        current.items.append(item)
        current.weight_kg += item.weight_kg
        current.volume_l += item.volume_l

    return PackResult(bags=bags, rejects=rejects)
