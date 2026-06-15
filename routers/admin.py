from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session
from models.database import get_db, User, Blog, Feedback, Category
from models.auth import get_admin_user, get_current_user_optional
from pydantic import BaseModel
from typing import Optional
import os, shutil, uuid, re

router = APIRouter(prefix="/api/admin", tags=["admin"])
blog_router = APIRouter(prefix="/api/blogs", tags=["blogs"])
feedback_router = APIRouter(prefix="/api/feedbacks", tags=["feedbacks"])
category_router = APIRouter(prefix="/api/categories", tags=["categories"])

UPLOAD_DIR = "static/images"

def save_upload(file: UploadFile, subfolder="") -> str:
    folder = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"/static/images/{subfolder}/{filename}"

# ── Admin: Users ──────────────────────────────────────────────
@router.get("/users")
def list_users(request: Request, db: Session = Depends(get_db)):
    admin = get_admin_user(request, db)
    users = db.query(User).all()
    return [{"id": u.id, "name": u.name, "email": u.email, "is_admin": u.is_admin,
             "created_at": u.created_at.isoformat(), "order_count": len(u.orders)} for u in users]

@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    admin = get_admin_user(request, db)
    from models.database import Product, Order, OrderStatus
    total_products = db.query(Product).count()
    total_users = db.query(User).filter(User.is_admin == False).count()
    total_orders = db.query(Order).count()
    pending_orders = db.query(Order).filter(Order.status == OrderStatus.pending).count()
    from sqlalchemy import func
    revenue = db.query(func.sum(Order.total)).filter(Order.status == OrderStatus.completed).scalar() or 0
    return {
        "total_products": total_products,
        "total_users": total_users,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "revenue": revenue
    }

# ── Categories ────────────────────────────────────────────────
class CategoryCreate(BaseModel):
    name: str

@category_router.get("")
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).all()
    return [{"id": c.id, "name": c.name, "slug": c.slug} for c in cats]

@category_router.post("")
def create_category(body: CategoryCreate, request: Request, db: Session = Depends(get_db)):
    admin = get_admin_user(request, db)
    slug = re.sub(r'[^a-z0-9]+', '-', body.name.lower()).strip('-')
    c = Category(name=body.name, slug=slug)
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "name": c.name, "slug": c.slug}

@category_router.delete("/{cat_id}")
def delete_category(cat_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_admin_user(request, db)
    c = db.query(Category).filter(Category.id == cat_id).first()
    if not c:
        raise HTTPException(404)
    db.delete(c)
    db.commit()
    return {"message": "Đã xóa danh mục"}

# ── Blogs ─────────────────────────────────────────────────────
def blog_dict(b: Blog):
    return {"id": b.id, "title": b.title, "slug": b.slug, "content": b.content,
            "thumbnail": b.thumbnail, "created_at": b.created_at.isoformat()}

@blog_router.get("")
def list_blogs(db: Session = Depends(get_db)):
    blogs = db.query(Blog).order_by(Blog.created_at.desc()).all()
    return [blog_dict(b) for b in blogs]

@blog_router.get("/{blog_id}")
def get_blog(blog_id: int, db: Session = Depends(get_db)):
    b = db.query(Blog).filter(Blog.id == blog_id).first()
    if not b:
        raise HTTPException(404)
    return blog_dict(b)

@blog_router.post("")
async def create_blog(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    thumbnail: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    admin = get_admin_user(request, db)
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    existing = db.query(Blog).filter(Blog.slug == slug).first()
    if existing:
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"
    thumb_url = None
    if thumbnail and thumbnail.filename:
        thumb_url = save_upload(thumbnail, "blogs")
    b = Blog(title=title, slug=slug, content=content, thumbnail=thumb_url, author_id=admin.id)
    db.add(b)
    db.commit()
    db.refresh(b)
    return blog_dict(b)

@blog_router.delete("/{blog_id}")
def delete_blog(blog_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_admin_user(request, db)
    b = db.query(Blog).filter(Blog.id == blog_id).first()
    if not b:
        raise HTTPException(404)
    db.delete(b)
    db.commit()
    return {"message": "Đã xóa bài viết"}

# ── Feedbacks ─────────────────────────────────────────────────
@feedback_router.get("")
def list_feedbacks(visible_only: bool = True, db: Session = Depends(get_db)):
    q = db.query(Feedback)
    if visible_only:
        q = q.filter(Feedback.is_visible == True)
    return [{"id": f.id, "name": f.name, "role": f.role, "comment": f.comment,
             "avatar": f.avatar, "rating": f.rating} for f in q.all()]

@feedback_router.post("")
def create_feedback(
    request: Request,
    name: str = Form(...),
    role: str = Form(...),
    comment: str = Form(...),
    rating: int = Form(5),
    db: Session = Depends(get_db)
):
    f = Feedback(name=name, role=role, comment=comment, rating=rating)
    db.add(f)
    db.commit()
    return {"message": "Cảm ơn phản hồi của bạn!"}
