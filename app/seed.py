"""Known starting state. Tests can rely on these exact ids, prices and stock levels."""
import hashlib
from datetime import datetime

from .database import engine
from .models import Base, Coupon, Product, User

SEED_PASSWORD = "Password123"


def hash_password(password: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), b"shop-static-salt", 50_000).hex()


CATEGORIES = [
    # slug, display name, icon
    ("fashion", "Fashion", "shirt"),
    ("mobiles", "Mobiles", "phone"),
    ("electronics", "Electronics", "laptop"),
    ("beauty", "Beauty", "flower"),
    ("home", "Home", "lamp"),
    ("appliances", "Appliances", "washer"),
    ("toys", "Toys", "teddy"),
    ("food", "Food", "food"),
    ("sports", "Sports", "ball"),
    ("books", "Books", "book"),
]

PRODUCTS = [
    # id, name, category, price, mrp, stock, specs, rating, reviews, image
    (1, "Trail Running Shoes", "sports", 2799, 3499, 12, "Grip sole • Waterproof", 4.4, 1320, "shoe"),
    (2, "Road Running Shoes", "sports", 3499, 3999, 8, "Lightweight • Cushioned", 4.5, 2100, "shoe"),
    (3, "Budget Running Shoes", "sports", 1499, 1999, 20, "Mesh upper • Daily wear", 4.0, 640, "shoe"),
    (4, "Leather Formal Shoes", "fashion", 4299, 4999, 5, "Genuine leather • Lace-up", 4.2, 310, "shoe"),
    (5, "Cotton T-Shirt", "fashion", 499, 599, 50, "100% cotton • Regular fit", 4.1, 5400, "shirt"),
    (6, "Denim Jacket", "fashion", 2199, 2999, 7, "Mid wash • Slim fit", 4.3, 780, "shirt"),
    (7, "Wireless Earbuds", "electronics", 1999, 2399, 15, "Active Noise Cancellation", 4.5, 1600, "earbuds"),
    (8, "Bluetooth Speaker", "electronics", 2499, 2999, 0, "Bluetooth 5.3 • 12H Playtime", 4.4, 980, "speaker"),  # out of stock on purpose
    (9, "Phone Case", "mobiles", 299, 399, 100, "Shockproof • Slim", 4.0, 8900, "phone"),
    (10, "Steel Water Bottle", "home", 649, 799, 2, "1 litre • Insulated", 4.6, 450, "bottle"),  # low stock on purpose
    (11, "Smartphone X1", "mobiles", 49999, 55999, 9, "128GB • 5G • AMOLED", 4.6, 2800, "phone"),
    (12, "Laptop Pro 15", "electronics", 42990, 50990, 6, "Intel i5 • 8GB • 512GB SSD", 4.5, 1200, "laptop"),
    (13, "Smart Watch", "electronics", 6999, 8499, 14, "Heart Rate • SpO2 • GPS", 4.3, 1100, "watch"),
    (14, "Noise Cancelling Headphones", "electronics", 7999, 9299, 10, "Hi-Fi Sound • 40H Playtime", 4.6, 850, "headphones"),
    (15, "Budget Phone M2", "mobiles", 9999, 11999, 25, "64GB • 4G • 5000mAh", 4.1, 3900, "phone"),
    (16, "Smart TV 43 inch", "appliances", 19999, 27999, 4, "4K UHD • HDR • 3 HDMI", 4.4, 2250, "tv"),
    (17, "Front Load Washing Machine", "appliances", 24990, 31990, 3, "7 kg • 1200 RPM", 4.3, 610, "washer"),
    (18, "Mixer Grinder", "appliances", 2899, 3999, 18, "750W • 3 jars", 4.2, 1900, "mixer"),
    (19, "Face Moisturiser", "beauty", 349, 449, 60, "100 ml • All skin types", 4.3, 2700, "jar"),
    (20, "Matte Lipstick", "beauty", 499, 599, 40, "Long lasting • Ruby red", 4.1, 1500, "lipstick"),
    (21, "Table Lamp", "home", 899, 1299, 11, "LED • 3 brightness levels", 4.2, 330, "lamp"),
    (22, "Cotton Bedsheet", "home", 1199, 1799, 16, "Double • 2 pillow covers", 4.0, 720, "bed"),
    (23, "Building Blocks Set", "toys", 1299, 1599, 22, "250 pieces • Ages 5+", 4.7, 940, "blocks"),
    (24, "Teddy Bear", "toys", 599, 799, 30, "40 cm • Soft plush", 4.5, 1250, "teddy"),
    (25, "Basmati Rice 5kg", "food", 649, 749, 45, "Aged • Long grain", 4.4, 6100, "bowl"),
    (26, "Dark Chocolate Box", "food", 399, 499, 35, "70% cocoa • 12 pieces", 4.6, 2050, "choc"),
    (27, "Cricket Bat", "sports", 1899, 2499, 9, "Kashmir willow • Full size", 4.2, 560, "bat"),
    (28, "Yoga Mat", "sports", 799, 999, 28, "6 mm • Anti-slip", 4.4, 3100, "mat"),
    (29, "Mystery Novel", "books", 299, 399, 33, "Paperback • 320 pages", 4.3, 870, "book"),
    (30, "Python Programming Guide", "books", 549, 699, 13, "Paperback • 480 pages", 4.5, 410, "book"),
]

COUPONS = [
    Coupon(code="WELCOME10", kind="percent", value=10, min_order=0),
    Coupon(code="FLAT200", kind="flat", value=200, min_order=1500),
    Coupon(code="EXPIRED50", kind="percent", value=50, expires_at=datetime(2020, 1, 1)),
    Coupon(code="DISABLED20", kind="percent", value=20, active=False),
]


def reset_database(db) -> None:
    db.close()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db.add_all(
        [
            User(id=1, email="alice@example.com", name="Alice", password_hash=hash_password(SEED_PASSWORD)),
            User(id=2, email="bob@example.com", name="Bob", password_hash=hash_password(SEED_PASSWORD)),
        ]
    )
    db.add_all(
        Product(
            id=i, name=n, category=c, price=p, mrp=m, stock=s, specs=sp, rating=r, reviews=rv, image=img,
            description=f"{n}. {sp.replace(' • ', ', ')}.",
        )
        for i, n, c, p, m, s, sp, r, rv, img in PRODUCTS
    )
    db.add_all(
        Coupon(code=c.code, kind=c.kind, value=c.value, min_order=c.min_order, active=c.active, expires_at=c.expires_at)
        for c in COUPONS
    )
    db.commit()
