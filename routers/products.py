from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models.database import get_db, Product, Category, Review
from models.auth import get_admin_user, get_current_user_optional
from typing import Optional, List
import json, os, shutil, uuid
from datetime import datetime

router = APIRouter(prefix="/api/products", tags=["products"])
UPLOAD_DIR = "static/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_upload(file: UploadFile, subfolder="") -> str:
    folder = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = file.filename.replace(" ", "_")
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"/static/images/{subfolder}/{filename}" if subfolder else f"/static/images/{filename}"

def product_dict(p: Product):
    previews = []
    try:
        if p.preview_images:
            previews = json.loads(p.preview_images)
    except:
        pass
    avg_rating = 0
    if p.reviews:
        avg_rating = round(sum(r.rating for r in p.reviews) / len(p.reviews), 1)
    return {
        "id": p.id, "name": p.name, "slug": p.slug, "description": p.description,
        "price": p.price, "original_price": p.original_price, "stock": p.stock,
        "image": p.image, "preview_images": previews,
        "category": p.category.name if p.category else None,
        "category_id": p.category_id,
        "is_featured": p.is_featured, "is_new": p.is_new,
        "card_count": p.card_count, "level": p.level,
        "avg_rating": avg_rating, "review_count": len(p.reviews),
        "created_at": p.created_at.isoformat()
    }

@router.get("")
def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    featured: Optional[bool] = None,
    is_new: Optional[bool] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    q = db.query(Product)
    if category:
        q = q.join(Category).filter(Category.slug == category)
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))
    if featured is not None:
        q = q.filter(Product.is_featured == featured)
    if is_new is not None:
        q = q.filter(Product.is_new == is_new)
    total = q.count()
    products = q.order_by(Product.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "products": [product_dict(p) for p in products]}

@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Sản phẩm không tồn tại")
    reviews = []
    for r in p.reviews:
        reviews.append({
            "id": r.id, "rating": r.rating, "comment": r.comment,
            "image": r.image, "created_at": r.created_at.isoformat(),
            "user_name": r.user.name if r.user else "Ẩn danh",
            "user_avatar": r.user.avatar if r.user else None
        })
    d = product_dict(p)
    d["reviews"] = reviews
    return d

@router.post("")
async def create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    original_price: Optional[float] = Form(None),
    stock: int = Form(0),
    category_id: int = Form(...),
    card_count: int = Form(0),
    level: Optional[str] = Form(None),
    is_featured: bool = Form(False),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    admin = get_admin_user(request, db)
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    # ensure unique slug
    existing = db.query(Product).filter(Product.slug == slug).first()
    if existing:
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"
    
    image_url = None
    if image and image.filename:
        image_url = save_upload(image, "products")
    
    p = Product(
        name=name, slug=slug, description=description, price=price,
        original_price=original_price, stock=stock, category_id=category_id,
        card_count=card_count, level=level, is_featured=is_featured, image=image_url
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return product_dict(p)

@router.put("/{product_id}")
async def update_product(
    product_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    original_price: Optional[float] = Form(None),
    stock: int = Form(0),
    category_id: int = Form(...),
    card_count: int = Form(0),
    level: Optional[str] = Form(None),
    is_featured: bool = Form(False),
    is_new: bool = Form(False),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    admin = get_admin_user(request, db)
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Sản phẩm không tồn tại")
    p.name = name
    p.description = description
    p.price = price
    p.original_price = original_price
    p.stock = stock
    p.category_id = category_id
    p.card_count = card_count
    p.level = level
    p.is_featured = is_featured
    p.is_new = is_new
    if image and image.filename:
        p.image = save_upload(image, "products")
    db.commit()
    db.refresh(p)
    return product_dict(p)

@router.delete("/{product_id}")
def delete_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_admin_user(request, db)
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Sản phẩm không tồn tại")
    db.delete(p)
    db.commit()
    return {"message": "Đã xóa sản phẩm"}

@router.post("/{product_id}/preview")
async def upload_preview(product_id: int, request: Request, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    admin = get_admin_user(request, db)
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Sản phẩm không tồn tại")
    existing = []
    try:
        if p.preview_images:
            existing = json.loads(p.preview_images)
    except:
        pass
    for file in files:
        if file.filename:
            url = save_upload(file, "previews")
            existing.append(url)
    p.preview_images = json.dumps(existing)
    db.commit()
    return {"preview_images": existing}

@router.post("/{product_id}/reviews")
def add_review(
    product_id: int,
    request: Request,
    rating: int = Form(...),
    comment: str = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    if not user:
        raise HTTPException(401, "Cần đăng nhập")
    image_url = None
    if image and image.filename:
        image_url = save_upload(image, "reviews")
    r = Review(product_id=product_id, user_id=user.id, rating=rating, comment=comment, image=image_url)
    db.add(r)
    db.commit()
    return {"message": "Đã gửi đánh giá"}

# Categories
@router.get("/categories/all")
def get_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).all()
    return [{"id": c.id, "name": c.name, "slug": c.slug} for c in cats]
