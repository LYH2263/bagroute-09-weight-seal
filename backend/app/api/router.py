from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import BagItem, DeliveryRoute, PackBag, RejectRecord, SubscriberStop
from app.schemas.schemas import (
    BagItemOut,
    BagOut,
    PackRequest,
    RejectOut,
    RouteOut,
    RouteUpdate,
    StopOut,
    WeightOut,
)
from app.services.pack_engine import StopItem, pack_route

api_router = APIRouter()

_EPS = 1e-9


def route_out(route: DeliveryRoute) -> RouteOut:
    return RouteOut(
        id=route.id,
        name=route.name,
        max_weight_kg=route.max_weight_kg,
        max_volume_l=route.max_volume_l,
        seal_threshold_kg=route.effective_seal_threshold_kg,
    )


def bag_out(db: Session, bag: PackBag, route: DeliveryRoute) -> BagOut:
    items = db.scalars(select(BagItem).where(BagItem.bag_id == bag.id)).all()
    threshold = (
        bag.seal_threshold_kg
        if bag.seal_threshold_kg is not None
        else route.effective_seal_threshold_kg
    )
    return BagOut(
        id=bag.id,
        route_id=bag.route_id,
        bag_index=bag.bag_index,
        weight_kg=bag.weight_kg,
        volume_l=bag.volume_l,
        seal_threshold_kg=threshold,
        max_weight_kg=route.max_weight_kg,
        items=[
            BagItemOut(
                stop_id=i.stop_id,
                stop_name=i.stop_name,
                weight_kg=i.weight_kg,
                volume_l=i.volume_l,
            )
            for i in items
        ],
    )


@api_router.get("/health")
def health():
    return {"status": "ok"}


@api_router.get("/routes", response_model=list[RouteOut])
def routes(db: Session = Depends(get_db)):
    rows = db.scalars(select(DeliveryRoute).order_by(DeliveryRoute.id)).all()
    return [route_out(r) for r in rows]


@api_router.patch("/routes/{route_id}", response_model=RouteOut)
def update_route(route_id: int, body: RouteUpdate, db: Session = Depends(get_db)):
    route = db.get(DeliveryRoute, route_id)
    if not route:
        raise HTTPException(404, "路线不存在")
    max_weight = body.max_weight_kg if body.max_weight_kg is not None else route.max_weight_kg
    max_volume = body.max_volume_l if body.max_volume_l is not None else route.max_volume_l
    if body.seal_threshold_kg is not None:
        threshold = body.seal_threshold_kg
    else:
        # 未显式设置时保持原值；NULL 表示不启用（跟随重量上限）
        threshold = route.seal_threshold_kg
    if max_weight <= 0:
        raise HTTPException(400, "重量上限必须大于 0")
    if max_volume <= 0:
        raise HTTPException(400, "体积上限必须大于 0")
    if threshold is not None:
        if threshold <= 0:
            raise HTTPException(400, "封袋阈值必须大于 0")
        if threshold > max_weight + _EPS:
            raise HTTPException(400, f"封袋阈值不能大于重量上限（{threshold}>{max_weight}）")
    route.max_weight_kg = max_weight
    route.max_volume_l = max_volume
    route.seal_threshold_kg = threshold
    db.commit()
    db.refresh(route)
    return route_out(route)


@api_router.get("/stops", response_model=list[StopOut])
def stops(route_id: int | None = None, db: Session = Depends(get_db)):
    q = select(SubscriberStop).order_by(SubscriberStop.route_id, SubscriberStop.seq)
    if route_id is not None:
        q = q.where(SubscriberStop.route_id == route_id)
    return db.scalars(q).all()


@api_router.post("/pack", response_model=list[BagOut])
def pack(body: PackRequest, db: Session = Depends(get_db)):
    route = db.get(DeliveryRoute, body.route_id)
    if not route:
        raise HTTPException(404, "路线不存在")
    # clear previous pack for route
    old_bags = db.scalars(select(PackBag).where(PackBag.route_id == route.id)).all()
    for b in old_bags:
        for it in list(b.items):
            db.delete(it)
        db.delete(b)
    old_rej = db.scalars(select(RejectRecord).where(RejectRecord.route_id == route.id)).all()
    for r in old_rej:
        db.delete(r)
    db.flush()

    stops = db.scalars(
        select(SubscriberStop).where(SubscriberStop.route_id == route.id).order_by(SubscriberStop.seq)
    ).all()
    items = [
        StopItem(s.id, s.seq, s.weight_kg, s.volume_l, s.name) for s in stops
    ]
    threshold = route.effective_seal_threshold_kg
    result = pack_route(items, route.max_weight_kg, route.max_volume_l, seal_threshold=threshold)
    out_bags: list[PackBag] = []
    for bag in result.bags:
        row = PackBag(
            route_id=route.id,
            bag_index=bag.bag_index,
            weight_kg=round(bag.weight_kg, 3),
            volume_l=round(bag.volume_l, 3),
            seal_threshold_kg=threshold,
        )
        db.add(row)
        db.flush()
        for it in bag.items:
            db.add(
                BagItem(
                    bag_id=row.id,
                    stop_id=it.stop_id,
                    stop_name=it.label,
                    weight_kg=it.weight_kg,
                    volume_l=it.volume_l,
                )
            )
        out_bags.append(row)
    for stop, reason in result.rejects:
        db.add(
            RejectRecord(
                route_id=route.id,
                stop_id=stop.stop_id,
                stop_name=stop.label,
                reason=reason,
            )
        )
    db.commit()
    return [bag_out(db, b, route) for b in out_bags]


@api_router.get("/bags", response_model=list[BagOut])
def bags(db: Session = Depends(get_db)):
    rows = db.scalars(select(PackBag).order_by(PackBag.route_id, PackBag.bag_index)).all()
    out = []
    for b in rows:
        route = db.get(DeliveryRoute, b.route_id)
        assert route
        out.append(bag_out(db, b, route))
    return out


@api_router.get("/rejects", response_model=list[RejectOut])
def rejects(db: Session = Depends(get_db)):
    return db.scalars(select(RejectRecord).order_by(RejectRecord.id.desc())).all()


@api_router.get("/weights", response_model=list[WeightOut])
def weights(db: Session = Depends(get_db)):
    bags = db.scalars(select(PackBag).order_by(PackBag.id)).all()
    out = []
    for b in bags:
        route = db.get(DeliveryRoute, b.route_id)
        assert route
        out.append(
            WeightOut(
                bag_id=b.id,
                bag_index=b.bag_index,
                route_id=b.route_id,
                weight_kg=b.weight_kg,
                volume_l=b.volume_l,
                fill_weight_pct=round(100 * b.weight_kg / route.max_weight_kg, 1),
                fill_volume_pct=round(100 * b.volume_l / route.max_volume_l, 1),
            )
        )
    return out
