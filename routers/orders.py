from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models.database import get_db, Order, OrderItem, OrderStatus, Product
from models.auth import get_current_user, get_admin_user
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/orders", tags=["orders"])

class CartItem(BaseModel):
    product_id: int
    quantity: int

class OrderRequest(BaseModel):
    items: List[CartItem]
    name: str
    phone: str
    address: str
    payment_method: str  # cod, qr, online
    note: Optional[str] = None

def order_dict(o: Order):
    items = []
    for item in o.items:
        items.append({
            "product_id": item.product_id,
            "product_name": item.product.name if item.product else "N/A",
            "product_image": item.product.image if item.product else None,
            "quantity": item.quantity,
            "price": item.price
        })
    return {
        "id": o.id,
        "status": o.status.value,
        "total": o.total,
        "name": o.name,
        "phone": o.phone,
        "address": o.address,
        "payment_method": o.payment_method,
        "payment_status": o.payment_status,
        "note": o.note,
        "items": items,
        "created_at": o.created_at.isoformat(),
        "updated_at": o.updated_at.isoformat() if o.updated_at else None
    }

@router.post("")
def create_order(req: OrderRequest, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    total = 0
    order_items = []
    for item in req.items:
        p = db.query(Product).filter(Product.id == item.product_id).first()
        if not p:
            raise HTTPException(404, f"Sản phẩm #{item.product_id} không tồn tại")
        if p.stock < item.quantity:
            raise HTTPException(400, f"Sản phẩm '{p.name}' không đủ hàng")
        total += p.price * item.quantity
        order_items.append((p, item.quantity))
    
    order = Order(
        user_id=user.id,
        total=total,
        name=req.name,
        phone=req.phone,
        address=req.address,
        payment_method=req.payment_method,
        note=req.note
    )
    db.add(order)
    db.flush()
    
    for p, qty in order_items:
        oi = OrderItem(order_id=order.id, product_id=p.id, quantity=qty, price=p.price)
        db.add(oi)
        p.stock -= qty
    
    db.commit()
    db.refresh(order)
    return order_dict(order)

@router.get("/my")
def my_orders(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    orders = db.query(Order).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).all()
    return [order_dict(o) for o in orders]

@router.get("/admin/all")
def admin_orders(
    request: Request,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    admin = get_admin_user(request, db)
    q = db.query(Order)
    if status:
        q = q.filter(Order.status == status)
    total = q.count()
    orders = q.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    result = []
    for o in orders:
        d = order_dict(o)
        d["user_name"] = o.user.name if o.user else "N/A"
        d["user_email"] = o.user.email if o.user else "N/A"
        result.append(d)
    return {"total": total, "orders": result}

from pydantic import BaseModel as _BaseModel
class StatusUpdate(_BaseModel):
    status: str

@router.put("/{order_id}/status")
def update_order_status_v2(order_id: int, body: StatusUpdate, request: Request, db: Session = Depends(get_db)):
    admin = get_admin_user(request, db)
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Đơn hàng không tồn tại")
    try:
        order.status = OrderStatus(body.status)
    except ValueError:
        raise HTTPException(400, "Trạng thái không hợp lệ")
    order.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Cập nhật thành công", "status": order.status.value}

@router.get("/{order_id}")
def get_order(order_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Đơn hàng không tồn tại")
    if order.user_id != user.id and not user.is_admin:
        raise HTTPException(403, "Không có quyền xem đơn hàng này")
    return order_dict(order)
