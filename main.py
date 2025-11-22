import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Cart, CartItem

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Gym Mats API"}


# Utility converters

def product_doc_to_model(doc) -> Product:
    # Convert Mongo doc to Product model compatible dict
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    # Remove _id or convert to string if needed
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])  # not used on frontend but safe
    return Product(**doc)


# Seed a default rubber gym mat product if not exists
@app.post("/seed")
def seed_product():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    existing = db["product"].find_one({"slug": "rubber-gym-mat-pro"})
    if existing:
        return {"status": "exists"}

    product = Product(
        title="Premium Rubber Gym Mat",
        slug="rubber-gym-mat-pro",
        subtitle="Anti-slip, shock-absorbing flooring for serious lifters",
        description=(
            "Durable, dense rubber mats engineered to protect your floors and equipment. "
            "Low odor, easy to clean, and built for heavy use in home or commercial gyms."
        ),
        base_price=49.99,
        images=[
            {"url": "/images/mat-1.jpg", "alt": "Gym mat close-up texture"},
            {"url": "/images/mat-2.jpg", "alt": "Mat with barbell on top"},
            {"url": "/images/mat-3.jpg", "alt": "Home gym setup with mats"},
        ],
        variants=[
            {
                "sku": "MAT10-BLK-100",
                "thickness_mm": 10,
                "size": "1m x 1m",
                "color": "Black",
                "price": 49.99,
                "stock": 120,
            },
            {
                "sku": "MAT15-BLK-100",
                "thickness_mm": 15,
                "size": "1m x 1m",
                "color": "Black",
                "price": 64.99,
                "stock": 80,
            },
            {
                "sku": "MAT20-GRY-100",
                "thickness_mm": 20,
                "size": "1m x 1m",
                "color": "Speckled Grey",
                "price": 79.99,
                "stock": 50,
            },
        ],
        specs={
            "Material": "Recycled vulcanized rubber",
            "Surface": "Anti-slip fine grain",
            "Hardness": "60 Shore A",
            "Smell": "Low-odor",
            "Maintenance": "Mop with mild detergent",
        },
        uvps=[
            "Shock-absorbing protection for floors and equipment",
            "Anti-slip surface with low odor",
            "Precision-cut edges for seamless fit",
            "Easy clean, water-resistant finish",
            "Backed by 2-year commercial warranty",
        ],
        faqs=[
            {
                "question": "Can I cut the mats to fit my space?",
                "answer": "Yes, use a sharp utility knife and straight edge to score and cut."
            },
            {
                "question": "Do these reduce noise?",
                "answer": "The dense rubber helps dampen sound from drops and footsteps."
            },
            {
                "question": "Are they safe for basement floors?",
                "answer": "Yes, they are water-resistant and safe on concrete."
            }
        ],
        rating=4.9,
        reviews_count=312,
        in_stock=True,
    )

    _id = create_document("product", product)
    return {"status": "seeded", "id": _id}


@app.get("/api/products/{slug}", response_model=Product)
def get_product(slug: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    doc = db["product"].find_one({"slug": slug})
    return product_doc_to_model(doc)


class AddToCartRequest(BaseModel):
    cart_id: str
    product_slug: str
    sku: str
    quantity: int = 1


@app.post("/api/cart/add")
def add_to_cart(payload: AddToCartRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    product = db["product"].find_one({"slug": payload.product_slug})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # find variant
    variant = next((v for v in product.get("variants", []) if v.get("sku") == payload.sku), None)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    # Create/update cart document
    cart = db["cart"].find_one({"cart_id": payload.cart_id})
    item = {
        "product_slug": payload.product_slug,
        "sku": payload.sku,
        "quantity": payload.quantity,
        "price": variant.get("price"),
        "title": product.get("title"),
        "image": (product.get("images") or [{}])[0].get("url"),
        "selected_options": {
            "Thickness": f"{variant.get('thickness_mm')}mm",
            "Size": variant.get("size"),
            "Color": variant.get("color"),
        },
    }

    if cart:
        # If item with same sku exists, increase quantity
        updated = False
        for it in cart.get("items", []):
            if it.get("sku") == payload.sku:
                it["quantity"] = it.get("quantity", 0) + payload.quantity
                updated = True
                break
        if not updated:
            cart.setdefault("items", []).append(item)
        db["cart"].update_one({"_id": cart["_id"]}, {"$set": cart})
    else:
        db["cart"].insert_one({"cart_id": payload.cart_id, "items": [item], "currency": "USD"})

    return {"status": "ok"}


@app.get("/api/cart/{cart_id}", response_model=Cart)
def get_cart(cart_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    cart = db["cart"].find_one({"cart_id": cart_id})
    if not cart:
        return Cart(cart_id=cart_id, items=[], currency="USD")
    cart["_id"] = str(cart["_id"]) if "_id" in cart else None
    return Cart(**cart)


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
