"""Route-order bag packing with weight + volume caps; reject when exceed."""

from __future__ import annotations

from dataclasses import dataclass, field

EPS = 1e-9


class InvalidThresholdError(ValueError):
    """封袋阈值大于重量上限。"""


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
    seal_weight_kg: float | None


def can_fit(bag: Bag, item: StopItem, max_weight: float, max_volume: float) -> bool:
    return (
        bag.weight_kg + item.weight_kg <= max_weight + EPS
        and bag.volume_l + item.volume_l <= max_volume + EPS
    )


def pack_route(
    stops: list[StopItem],
    max_weight: float,
    max_volume: float,
    seal_weight: float | None = None,
) -> PackResult:
    """按 seq 顺序装袋。

    现网约束：单站本身超重/超体积一律拒收；体积或重量上限装不下则开新袋。
    封袋阈值：当前袋已装重量达到阈值后，即使体积和重量上限都有余量，
    下一站也必须进入新袋。单站自身大于阈值但不超过上限时，独占一袋。
    """
    if seal_weight is not None and seal_weight > max_weight + EPS:
        raise InvalidThresholdError(
            f"封袋阈值 {seal_weight} 不得大于重量上限 {max_weight}"
        )

    ordered = sorted(stops, key=lambda s: s.seq)
    bags: list[Bag] = []
    rejects: list[tuple[StopItem, str]] = []
    current: Bag | None = None

    def reached_seal(bag: Bag) -> bool:
        return seal_weight is not None and bag.weight_kg >= seal_weight - EPS

    for item in ordered:
        if item.weight_kg > max_weight or item.volume_l > max_volume:
            reason = []
            if item.weight_kg > max_weight:
                reason.append(f"超重 {item.weight_kg}>{max_weight}")
            if item.volume_l > max_volume:
                reason.append(f"超体积 {item.volume_l}>{max_volume}")
            rejects.append((item, "；".join(reason)))
            continue

        # 当前袋已达封袋阈值 → 下一站必须开新袋（即使双上限都有余量）
        if current is not None and reached_seal(current):
            current = None

        if current is None or not can_fit(current, item, max_weight, max_volume):
            current = Bag(bag_index=len(bags) + 1)
            bags.append(current)

        if not can_fit(current, item, max_weight, max_volume):
            # should not happen after single-item check, but keep safe
            rejects.append((item, "无法装入新袋"))
            continue

        current.items.append(item)
        current.weight_kg += item.weight_kg
        current.volume_l += item.volume_l

    return PackResult(bags=bags, rejects=rejects, seal_weight_kg=seal_weight)
