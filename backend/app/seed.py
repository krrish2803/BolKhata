from datetime import datetime, timedelta
from typing import List, Dict, Any
from bson import ObjectId

# 8 fake customers with common Indian names (includes Sharma ji and Sharma Sir, with aliases; 3 with existing udhaar)
SEED_CUSTOMERS = [
    {
        "name": "Sharma ji",
        "aliases": ["sharmaji", "ramesh sharma", "sharma"],
        "phone": "9874961805",
        "balance": 1800,  # existing udhaar
    },
    {
        "name": "Sharma Sir",
        "aliases": ["sharma sir", "prof sharma", "masterji"],
        "phone": "9812345678",
        "balance": 0,
    },
    {
        "name": "Verma ji",
        "aliases": ["vermaji", "suresh verma", "verma"],
        "phone": "9823456789",
        "balance": 3500,  # existing udhaar
    },
    {
        "name": "Gupta Hardware",
        "aliases": ["gupta ji", "guptaji", "anil gupta"],
        "phone": "9834567890",
        "balance": 0,
    },
    {
        "name": "Mishra Cloth",
        "aliases": ["mishra ji", "mishraji", "rajesh mishra"],
        "phone": "9845678901",
        "balance": 2400,  # existing udhaar
    },
    {
        "name": "Khan Bhai",
        "aliases": ["khanbhai", "salman khan", "khan saab"],
        "phone": "9856789012",
        "balance": 0,
    },
    {
        "name": "Patel Tailor",
        "aliases": ["patel bhai", "patelji", "patel"],
        "phone": "9867890123",
        "balance": 0,
    },
    {
        "name": "Chopra Saab",
        "aliases": ["chopra", "sunil chopra", "chopra ji"],
        "phone": "9878901234",
        "balance": 0,
    },
]

# 12 men's-wear items with plausible prices, stock, and aliases (e.g. shirt: "kameez", trouser: "pant")
SEED_ITEMS = [
    {
        "name": "Formal Shirt",
        "aliases": ["shirt", "kameez", "cotton shirt", "formal shirt"],
        "price": 1200,
        "stock": 45,
    },
    {
        "name": "Trouser",
        "aliases": ["pant", "trouser", "formal pant", "trousers"],
        "price": 1800,
        "stock": 30,
    },
    {
        "name": "Denim Jeans",
        "aliases": ["jeans", "denim", "jean"],
        "price": 2200,
        "stock": 25,
    },
    {
        "name": "Cotton Kurta",
        "aliases": ["kurta", "cotton kurta", "khadi kurta"],
        "price": 1500,
        "stock": 20,
    },
    {
        "name": "Linen Pajama",
        "aliases": ["pajama", "pyjama", "white pajama"],
        "price": 800,
        "stock": 35,
    },
    {
        "name": "Leather Belt",
        "aliases": ["belt", "leather belt", "kamarbandh"],
        "price": 650,
        "stock": 40,
    },
    {
        "name": "Silk Tie",
        "aliases": ["tie", "silk tie", "necktie"],
        "price": 450,
        "stock": 18,
    },
    {
        "name": "Casual Blazer",
        "aliases": ["blazer", "coat", "jacket"],
        "price": 4500,
        "stock": 12,
    },
    {
        "name": "Innerwear Vest",
        "aliases": ["innerwear", "baniyan", "vest", "underwear"],
        "price": 250,
        "stock": 60,
    },
    {
        "name": "Cotton Socks",
        "aliases": ["socks", "moja", "cotton socks"],
        "price": 120,
        "stock": 80,
    },
    {
        "name": "Linen Handkerchief",
        "aliases": ["handkerchief", "rumal", "rumaal", "hanky"],
        "price": 60,
        "stock": 150,
    },
    {
        "name": "Cotton Shorts",
        "aliases": ["shorts", "half pant", "boxer shorts", "boxer"],
        "price": 500,
        "stock": 28,
    },
]

async def seed_workspace(database, workspace_id: str):
    """
    Populates the newly created demo workspace with customers and items.
    """
    # 1. Customers
    customer_docs = []
    for c in SEED_CUSTOMERS:
        customer_docs.append({
            "_id": ObjectId(),
            "workspaceId": workspace_id,
            "name": c["name"],
            "aliases": c["aliases"],
            "phone": c["phone"],
            "balance": c["balance"],
            "createdAt": datetime.utcnow(),
        })
    if customer_docs:
        await database.customers.insert_many(customer_docs)

    # 2. Items
    item_docs = []
    for item in SEED_ITEMS:
        item_docs.append({
            "_id": ObjectId(),
            "workspaceId": workspace_id,
            "name": item["name"],
            "aliases": item["aliases"],
            "price": item["price"],
            "stock": item["stock"],
            "createdAt": datetime.utcnow(),
        })
    if item_docs:
        await database.items.insert_many(item_docs)
