import json
import os
import secrets
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Path as PathParam, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, inspect, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, get_db
from .models import Base, CartItem, Coupon, Order, OrderItem, Product, Token, User, now_utc
from .seed import CATEGORIES, hash_password, reset_database

ALLOW_RESET = os.getenv("ALLOW_RESET", "true").lower() == "true"
RESET_KEY = os.getenv("RESET_KEY", "practice-reset")  # sent as the X-Reset-Key header
MAX_INT = 2_147_483_647  # largest value the database integer columns hold
DECLINED_CARD = "4000000000000002"  # mock payment: this card number is always declined


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("products")}
    order_columns = {c["name"] for c in inspect(engine).get_columns("orders")}
    with SessionLocal() as db:
        # Reseed when the database is empty or was created by an older version of the schema.
        if "mrp" not in columns or "shipping" not in order_columns or db.scalar(select(Product).limit(1)) is None:
            reset_database(db)
    yield


app = FastAPI(title="Practice Shop API", version="0.1.0", lifespan=lifespan)


# ---------- schemas ----------
class RegisterIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$", max_length=255)
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=100)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v

    @field_validator("password")
    @classmethod
    def _password_not_blank(cls, v):
        if not v.strip():
            raise ValueError("Password cannot be only spaces")
        return v


class LoginIn(BaseModel):
    email: str
    password: str


class CartAddIn(BaseModel):
    product_id: int = Field(le=MAX_INT)
    quantity: int = Field(default=1, ge=1, le=MAX_INT)


class CartSetIn(BaseModel):
    quantity: int = Field(ge=1, le=MAX_INT)


class CouponIn(BaseModel):
    code: str


EMAIL_PATTERN = r"^[^@\s]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$"
COUNTRIES = ["India"]
STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha",
    "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry",
]


class ShippingIn(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    full_name: str = Field(max_length=100)
    line1: str = Field(max_length=200)
    line2: str = Field(default="", max_length=200)
    city: str = Field(max_length=100)
    state: str
    postal_code: str = Field(pattern=r"^[1-9][0-9]{5}$")  # Indian PIN code
    country: str = "India"

    @field_validator("full_name", "line1", "city")
    @classmethod
    def _required_text(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be blank")
        return v

    @field_validator("line2")
    @classmethod
    def _trim(cls, v):
        return v.strip()

    @field_validator("state")
    @classmethod
    def _known_state(cls, v):
        if v not in STATES:
            raise ValueError("Unknown state")
        return v

    @field_validator("country")
    @classmethod
    def _known_country(cls, v):
        if v not in COUNTRIES:
            raise ValueError("We only deliver in India")
        return v


class CheckoutIn(BaseModel):
    card_number: str = Field(pattern=r"^[0-9]{16}$")
    coupon_code: Optional[str] = None
    shipping: ShippingIn


# ---------- helpers ----------
def current_user(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = db.get(Token, authorization[7:])
    if token is None:
        raise HTTPException(401, "Invalid token")
    return db.get(User, token.user_id)


def product_out(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "description": p.description,
        "specs": p.specs,
        "price": p.price,
        "mrp": p.mrp,
        "discount_percent": round((p.mrp - p.price) * 100 / p.mrp) if p.mrp > p.price else 0,
        "rating": round(p.rating, 1),
        "reviews": p.reviews,
        "image": p.image,
        "stock": p.stock,
        "in_stock": p.stock > 0,
    }


def cart_out(db: Session, user: User) -> dict:
    items = db.scalars(select(CartItem).where(CartItem.user_id == user.id).order_by(CartItem.id)).all()
    lines = [
        {
            "product_id": i.product_id,
            "name": i.product.name,
            "unit_price": i.product.price,
            "quantity": i.quantity,
            "line_total": i.product.price * i.quantity,
        }
        for i in items
    ]
    return {"items": lines, "subtotal": sum(line["line_total"] for line in lines)}


def compute_discount(db: Session, code: str, subtotal: int) -> int:
    coupon = db.get(Coupon, code.strip().upper())
    if coupon is None:
        raise HTTPException(400, "Coupon not found")
    if not coupon.active:
        raise HTTPException(400, "Coupon is not active")
    if coupon.expires_at and coupon.expires_at < now_utc():
        raise HTTPException(400, "Coupon has expired")
    if subtotal < coupon.min_order:
        raise HTTPException(400, f"Coupon needs a minimum order of {coupon.min_order}")
    if coupon.kind == "percent":
        return subtotal * coupon.value // 100
    return min(coupon.value, subtotal)


def order_out(o: Order) -> dict:
    return {
        "id": o.id,
        "status": o.status,
        "subtotal": o.subtotal,
        "discount": o.discount,
        "total": o.total,
        "coupon_code": o.coupon_code,
        "created_at": o.created_at.isoformat(),
        "shipping": json.loads(o.shipping) if o.shipping else None,
        "items": [
            {
                "product_id": i.product_id,
                "name": i.name,
                "unit_price": i.unit_price,
                "quantity": i.quantity,
                "line_total": i.unit_price * i.quantity,
            }
            for i in o.items
        ],
    }


def issue_token(db: Session, user: User) -> dict:
    token = secrets.token_hex(24)
    db.add(Token(token=token, user_id=user.id))
    db.commit()
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name}}


# ---------- system ----------
FAVICON = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='#1a56f0'/>"
    "<path d='M9 13h14l-1 12H10z' fill='none' stroke='white' stroke-width='2.2' stroke-linejoin='round'/>"
    "<path d='M12.5 13v-2a3.5 3.5 0 0 1 7 0v2' fill='none' stroke='white' stroke-width='2.2' stroke-linecap='round'/></svg>"
)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Browsers ask for this on their own. Answering it keeps the console free of a 404 error."""
    return Response(FAVICON, media_type="image/svg+xml", headers={"Cache-Control": "max-age=86400"})


@app.get("/", include_in_schema=False)
def ui():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.post("/test/reset", tags=["system"])
def reset(x_reset_key: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    """Drop everything and reload the seed data, so every test run starts from the same state.
    Needs the X-Reset-Key header (RESET_KEY setting)."""
    if not ALLOW_RESET:
        raise HTTPException(403, "Reset is disabled")
    if not x_reset_key or not secrets.compare_digest(x_reset_key, RESET_KEY):
        raise HTTPException(403, "A valid X-Reset-Key header is required")
    reset_database(db)
    return {"status": "reset"}


# ---------- auth ----------
@app.post("/auth/register", status_code=201, tags=["auth"])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = User(email=email, name=body.name, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return issue_token(db, user)


@app.post("/auth/login", tags=["auth"])
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not secrets.compare_digest(user.password_hash, hash_password(body.password)):
        raise HTTPException(401, "Wrong email or password")
    return issue_token(db, user)


@app.post("/auth/logout", tags=["auth"])
def logout(
    authorization: Optional[str] = Header(default=None), user: User = Depends(current_user), db: Session = Depends(get_db)
):
    """End this session: the token stops working straight away."""
    db.delete(db.get(Token, authorization[7:]))
    db.commit()
    return {"status": "logged out"}


@app.get("/me", tags=["auth"])
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "name": user.name}


# ---------- products ----------
def _search(stmt, q: Optional[str]):
    """Keep products that match every word of the search text. A word matches when it appears anywhere in
    the product name, its category or its specs, so "mob" finds the Mobiles category and "amoled" finds a phone."""
    for word in (q or "").lower().split()[:8]:
        # % and _ are wildcards in LIKE, so escape them to search for the characters themselves.
        literal = "%" + word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        stmt = stmt.where(
            or_(
                Product.name.ilike(literal, escape="\\"),
                Product.category.ilike(literal, escape="\\"),
                Product.specs.ilike(literal, escape="\\"),
            )
        )
    return stmt


@app.get("/products/suggest", tags=["products"])
def suggest_products(
    q: str = Query(default="", max_length=100), limit: int = Query(default=6, ge=1, le=20), db: Session = Depends(get_db)
):
    """Suggestions for the search box. Needs at least 2 characters. Best matches first: names that start with
    the text, then names with a word that starts with it, then other name matches, then category and specs matches."""
    text = " ".join(q.lower().split())
    if len(text) < 2:
        return {"query": text, "categories": [], "products": [], "total": 0}
    first = text.split()[0]
    counts = dict(db.execute(select(Product.category, func.count()).group_by(Product.category)).all())
    categories = [
        {"slug": slug, "name": name, "icon": icon, "count": counts.get(slug, 0)}
        for slug, name, icon in CATEGORIES
        if all(word in name.lower() for word in text.split())
    ]

    def rank(p: Product) -> int:
        name = p.name.lower()
        if name.startswith(text):
            return 0
        if any(part.startswith(first) for part in name.split()):
            return 1
        if first in name:
            return 2
        return 3 if first in p.category.lower() else 4

    found = sorted(db.scalars(_search(select(Product), text)).all(), key=lambda p: (rank(p), p.id))
    products = [
        {"id": p.id, "name": p.name, "category": p.category, "price": p.price, "image": p.image, "in_stock": p.stock > 0}
        for p in found[:limit]
    ]
    return {"query": text, "categories": categories, "products": products, "total": len(found)}


@app.get("/products", tags=["products"])
def list_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[int] = Query(default=None, ge=0, le=MAX_INT),
    max_price: Optional[int] = Query(default=None, ge=0, le=MAX_INT),
    in_stock: Optional[bool] = None,
    sort: str = Query(default="id", pattern="^(id|price_asc|price_desc|name|discount|rating)$"),
    limit: Optional[int] = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Product)
    stmt = _search(stmt, q)
    if category:
        stmt = stmt.where(Product.category == category.lower())
    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)
    if in_stock is not None:
        stmt = stmt.where(Product.stock > 0 if in_stock else Product.stock == 0)
    order = {
        "id": Product.id,
        "price_asc": Product.price.asc(),
        "price_desc": Product.price.desc(),
        "name": Product.name,
        "discount": ((Product.mrp - Product.price) * 100.0 / Product.mrp).desc(),
        "rating": Product.rating.desc(),
    }[sort]
    stmt = stmt.order_by(order, Product.id)
    if limit:
        stmt = stmt.limit(limit)
    return [product_out(p) for p in db.scalars(stmt).all()]


@app.get("/categories", tags=["products"])
def list_categories(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Product.category, func.count()).group_by(Product.category)).all())
    return [{"slug": s, "name": n, "icon": i, "count": counts.get(s, 0)} for s, n, i in CATEGORIES]


@app.get("/products/{product_id}", tags=["products"])
def get_product(product_id: int = PathParam(le=MAX_INT), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    return product_out(product)


# ---------- cart ----------
@app.get("/cart", tags=["cart"])
def get_cart(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return cart_out(db, user)


def _set_quantity(db: Session, user: User, product_id: int, quantity: int, add: bool) -> dict:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    item = db.scalar(select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id))
    if item is None and not add:
        raise HTTPException(404, "Product is not in the cart")
    wanted = quantity + (item.quantity if item and add else 0)
    if wanted > product.stock:
        raise HTTPException(409, f"Only {product.stock} in stock")
    if item is None:
        db.add(CartItem(user_id=user.id, product_id=product_id, quantity=wanted))
    else:
        item.quantity = wanted
    try:
        db.commit()
    except IntegrityError:  # two requests added the same product at the same moment
        db.rollback()
        raise HTTPException(409, "The cart was changed by another request. Please try again")
    return cart_out(db, user)


@app.post("/cart/items", tags=["cart"])
def add_to_cart(body: CartAddIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _set_quantity(db, user, body.product_id, body.quantity, add=True)


@app.put("/cart/items/{product_id}", tags=["cart"])
def set_cart_quantity(
    body: CartSetIn, product_id: int = PathParam(le=MAX_INT), user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return _set_quantity(db, user, product_id, body.quantity, add=False)


@app.delete("/cart/items/{product_id}", tags=["cart"])
def remove_from_cart(product_id: int = PathParam(le=MAX_INT), user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id))
    if item is None:
        raise HTTPException(404, "Product is not in the cart")
    db.delete(item)
    db.commit()
    return cart_out(db, user)


@app.delete("/cart", tags=["cart"])
def clear_cart(user: User = Depends(current_user), db: Session = Depends(get_db)):
    for item in db.scalars(select(CartItem).where(CartItem.user_id == user.id)).all():
        db.delete(item)
    db.commit()
    return cart_out(db, user)


# ---------- coupons and checkout ----------
@app.post("/coupons/validate", tags=["checkout"])
def validate_coupon(body: CouponIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    subtotal = cart_out(db, user)["subtotal"]
    if subtotal == 0:
        raise HTTPException(400, "Cart is empty")
    discount = compute_discount(db, body.code, subtotal)
    return {"code": body.code.strip().upper(), "subtotal": subtotal, "discount": discount, "total": subtotal - discount}


@app.get("/shipping/options", tags=["checkout"])
def shipping_options():
    """Countries and states the checkout form offers. Shipping is free."""
    return {"countries": COUNTRIES, "states": STATES, "shipping_fee": 0}


@app.post("/checkout", status_code=201, tags=["checkout"])
def checkout(body: CheckoutIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(CartItem).where(CartItem.user_id == user.id).order_by(CartItem.id)).all()
    if not items:
        raise HTTPException(400, "Cart is empty")
    subtotal = sum(i.product.price * i.quantity for i in items)
    discount = compute_discount(db, body.coupon_code, subtotal) if body.coupon_code else 0
    if body.card_number == DECLINED_CARD:
        raise HTTPException(402, "Payment declined")

    # Claim the cart first. If another checkout for this user got there first, the rows are already gone
    # and this request stops, so one cart can only ever become one order.
    claimed = db.execute(delete(CartItem).where(CartItem.user_id == user.id, CartItem.id.in_([i.id for i in items])))
    if claimed.rowcount != len(items):
        db.rollback()
        raise HTTPException(409, "This cart is already being checked out")

    # Take stock with a guarded UPDATE so two buyers cannot both get the last unit.
    for i in items:
        taken = db.execute(
            update(Product)
            .where(Product.id == i.product_id, Product.stock >= i.quantity)
            .values(stock=Product.stock - i.quantity)
        )
        if taken.rowcount != 1:
            db.rollback()
            raise HTTPException(409, f"Not enough stock for {i.product.name}")

    order = Order(
        user_id=user.id,
        subtotal=subtotal,
        discount=discount,
        total=subtotal - discount,
        coupon_code=body.coupon_code.strip().upper() if body.coupon_code else None,
        shipping=json.dumps(body.shipping.model_dump()),
        items=[
            OrderItem(product_id=i.product_id, name=i.product.name, unit_price=i.product.price, quantity=i.quantity)
            for i in items
        ],
    )
    db.add(order)
    db.commit()
    return order_out(order)


# ---------- orders ----------
def _own_order(db: Session, user: User, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(404, "Order not found")
    return order


@app.get("/orders", tags=["orders"])
def list_orders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    orders = db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())).all()
    return [order_out(o) for o in orders]


@app.get("/orders/{order_id}", tags=["orders"])
def get_order(order_id: int = PathParam(le=MAX_INT), user: User = Depends(current_user), db: Session = Depends(get_db)):
    return order_out(_own_order(db, user, order_id))


@app.post("/orders/{order_id}/cancel", tags=["orders"])
def cancel_order(order_id: int = PathParam(le=MAX_INT), user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = _own_order(db, user, order_id)
    # Guarded update: of two cancel requests sent together only one changes the row, so stock is returned once.
    changed = db.execute(update(Order).where(Order.id == order.id, Order.status == "paid").values(status="cancelled"))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Order is already cancelled")
    for i in order.items:
        db.execute(update(Product).where(Product.id == i.product_id).values(stock=Product.stock + i.quantity))
    db.commit()
    db.refresh(order)
    return order_out(order)


# The chat agent reuses the functions above, so it is registered last.
from . import agent  # noqa: E402

app.include_router(agent.router)
