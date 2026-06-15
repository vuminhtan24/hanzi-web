from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()  # Đọc .env

# Initialize DB
from models.database import Base, engine, SessionLocal, User, Product, Category, Feedback, Blog
from models.auth import get_password_hash

Base.metadata.create_all(bind=engine)

from routers.auth import router as auth_router
from routers.products import router as products_router
from routers.orders import router as orders_router
from routers.admin import router as admin_router, blog_router, feedback_router, category_router

app = FastAPI(title="ChineseNois API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static/images/products", exist_ok=True)
os.makedirs("static/images/previews", exist_ok=True)
os.makedirs("static/images/reviews", exist_ok=True)
os.makedirs("static/images/blogs", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(admin_router)
app.include_router(blog_router)
app.include_router(feedback_router)
app.include_router(category_router)

# ── Page Routes ───────────────────────────────────────────────
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        "user/index.html",
        {"request": request}
    )
async def home(request: Request):
    return templates.TemplateResponse("user/index.html", {"request": request})

@app.get("/products", response_class=HTMLResponse)
async def products_page(request: Request):
    return templates.TemplateResponse("user/products.html", {"request": request})

@app.get("/products/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: int):
    return templates.TemplateResponse("user/product_detail.html", {"request": request, "product_id": product_id})

@app.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request):
    return templates.TemplateResponse("user/cart.html", {"request": request})

@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    return templates.TemplateResponse("user/checkout.html", {"request": request})

@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request):
    return templates.TemplateResponse("user/account.html", {"request": request})

@app.get("/blog", response_class=HTMLResponse)
async def blog_list(request: Request):
    return templates.TemplateResponse("user/blog.html", {"request": request})

@app.get("/blog/{blog_id}", response_class=HTMLResponse)
async def blog_detail(request: Request, blog_id: int):
    return templates.TemplateResponse("user/blog_detail.html", {"request": request, "blog_id": blog_id})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})

@app.get("/admin/products", response_class=HTMLResponse)
async def admin_products(request: Request):
    return templates.TemplateResponse("admin/products.html", {"request": request})

@app.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders_page(request: Request):
    return templates.TemplateResponse("admin/orders.html", {"request": request})

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request):
    return templates.TemplateResponse("admin/users.html", {"request": request})

@app.get("/admin/blogs", response_class=HTMLResponse)
async def admin_blogs(request: Request):
    return templates.TemplateResponse("admin/blogs.html", {"request": request})

# ── Seed Data ─────────────────────────────────────────────────
@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    try:
        # Admin user
        admin_email = os.getenv("ADMIN_EMAIL", "admin@chinesenois.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin_name = os.getenv("ADMIN_NAME", "Admin")
        if not db.query(User).filter(User.email == admin_email).first():
            admin = User(name=admin_name, email=admin_email,
                         password_hash=get_password_hash(admin_password), is_admin=True)
            db.add(admin)
            db.commit()

        # Categories
        cats = [("Động vật", "dong-vat"), ("Nghề nghiệp", "nghe-nghiep"),
                ("HSK 1", "hsk-1"), ("HSK 2", "hsk-2"), ("Gia đình", "gia-dinh"),
                ("Màu sắc", "mau-sac"), ("Thực phẩm", "thuc-pham")]
        for name, slug in cats:
            if not db.query(Category).filter(Category.slug == slug).first():
                db.add(Category(name=name, slug=slug))
        db.commit()

        # Products
        if db.query(Product).count() == 0:
            placeholder_image = "/static/images/products/placeholder.svg"
            cat = db.query(Category).first()
            products = [
                Product(name="Bộ bài Động vật", slug="bo-bai-dong-vat",
                        description="Bộ 60 lá bài với hình ảnh động vật귀여운, kèm phiên âm và nghĩa tiếng Việt. Phù hợp cho trẻ 3-10 tuổi.",
                        price=125000, original_price=150000, stock=50, card_count=60,
                        category_id=1, is_featured=True, is_new=True, level="Cơ bản", image=placeholder_image),
                Product(name="Bộ bài Nghề nghiệp", slug="bo-bai-nghe-nghiep",
                        description="50 thẻ từ vựng về các nghề nghiệp phổ biến. Có QR code dẫn đến video phát âm.",
                        price=110000, original_price=130000, stock=35, card_count=50,
                        category_id=2, is_featured=True, is_new=False, level="Cơ bản", image=placeholder_image),
                Product(name="Bộ bài HSK 1", slug="bo-bai-hsk-1",
                        description="150 từ vựng chuẩn HSK 1 của Hán ngữ Quốc tế. Bao gồm phiên âm pinyin, nghĩa và ví dụ câu.",
                        price=145000, original_price=175000, stock=40, card_count=150,
                        category_id=3, is_featured=True, is_new=False, level="HSK 1", image=placeholder_image),
                Product(name="Bộ bài Gia đình", slug="bo-bai-gia-dinh",
                        description="40 thẻ về các thành viên và quan hệ gia đình trong tiếng Trung.",
                        price=95000, stock=60, card_count=40,
                        category_id=5, is_featured=False, is_new=True, level="Cơ bản", image=placeholder_image),
                Product(name="Bộ bài HSK 2", slug="bo-bai-hsk-2",
                        description="150 từ vựng chuẩn HSK 2. Phù hợp sau khi đã hoàn thành HSK 1.",
                        price=145000, original_price=175000, stock=25, card_count=150,
                        category_id=4, is_featured=False, is_new=True, level="HSK 2", image=placeholder_image),
                Product(name="Bộ bài Thực phẩm", slug="bo-bai-thuc-pham",
                        description="80 thẻ từ vựng về đồ ăn và thức uống phổ biến. Kèm hình ảnh màu sắc sinh động.",
                        price=115000, stock=45, card_count=80,
                        category_id=7, is_featured=False, is_new=True, level="Cơ bản", image=placeholder_image),
            ]
            for p in products:
                db.add(p)
            db.commit()

        # Feedbacks
        if db.query(Feedback).count() == 0:
            fbs = [
                Feedback(name="Nguyễn Thu Hương", role="Phụ huynh bé 6 tuổi",
                         comment="Bé nhà mình rất thích bộ bài động vật! Học từ vựng qua hình ảnh dễ nhớ hơn nhiều so với sách thông thường.", rating=5),
                Feedback(name="Trần Minh Khoa", role="Học sinh lớp 8",
                         comment="Mình dùng bộ HSK 1 để ôn thi, thiết kế đẹp và rất tiện mang theo. Đã vượt qua kỳ thi với điểm cao!", rating=5),
                Feedback(name="Lê Thị Mai", role="Giáo viên tiếng Trung",
                         comment="Tôi đã dùng bộ bài ChineseNois trong lớp học của mình. Học sinh tiếp thu nhanh hơn và hứng thú hơn rất nhiều.", rating=5),
            ]
            for fb in fbs:
                db.add(fb)
            db.commit()

        # Sample blog
        if db.query(Blog).count() == 0:
            admin_user = db.query(User).filter(User.is_admin == True).first()
            blogs = [
                Blog(title="Cách học tiếng Trung hiệu quả với flashcard", 
                     slug="cach-hoc-tieng-trung-voi-flashcard",
                     content="<p>Học tiếng Trung bằng flashcard là phương pháp được nhiều chuyên gia ngôn ngữ khuyến nghị...</p><p>Phương pháp <strong>spaced repetition</strong> (lặp lại cách quãng) kết hợp với flashcard giúp não bộ ghi nhớ từ vựng lâu dài hơn.</p><h3>5 bước học với flashcard</h3><ol><li>Xem hình ảnh và đọc to chữ Hán</li><li>Đọc phiên âm pinyin nhiều lần</li><li>Ghi nhớ nghĩa tiếng Việt</li><li>Luyện viết chữ Hán</li><li>Ôn tập theo chu kỳ</li></ol>",
                     author_id=admin_user.id if admin_user else 1),
                Blog(title="Top 5 mẹo ghi nhớ chữ Hán siêu nhanh",
                     slug="meo-ghi-nho-chu-han-sieu-nhanh",
                     content="<p>Chữ Hán nhìn phức tạp nhưng có nhiều mẹo thú vị để ghi nhớ nhanh hơn...</p><p>Mỗi chữ Hán đều có <strong>bộ thủ</strong> (radical) mang nghĩa. Hiểu bộ thủ giúp bạn đoán nghĩa của nhiều từ mới.</p>",
                     author_id=admin_user.id if admin_user else 1),
            ]
            for b in blogs:
                db.add(b)
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8000)),
        reload=os.getenv("DEBUG", "true").lower() == "true"
    )
