from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# ---------------- GEMINI CONFIG ----------------

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

# ---------------- CATEGORY MAP (ID BASED) ----------------

CATEGORY_MAP = {
    1: {
        "name": "Food",
        "subcategories": [
            "Bakery", "Cafe", "Restaurant", "Juice Bar",
            "Street Food Stall", "Ice Cream Parlour",
            "Organic Food Store", "Grocery Store"
        ]
    },
    2: {
        "name": "Clothing",
        "subcategories": [
            "Men's Wear", "Women's Wear", "Kids Wear",
            "Boutique", "Ethnic Wear", "Casual Wear",
            "Sportswear", "Undergarments"
        ]
    },
    3: {
        "name": "FMCG",
        "subcategories": [
            "Supermarket", "General Store", "Departmental Store",
            "Cosmetics Store", "Hygiene Products Store",
            "Packaged Food Store", "Cleaning Supplies",
            "Convenience Store"
        ]
    },
    4: {
        "name": "Accessories",
        "subcategories": [
            "Footwear Store", "Bags & Luggage",
            "Watches & Jewelry", "Eyewear Store",
            "Mobile Accessories", "Hair Accessories",
            "Fashion Accessories"
        ]
    }
}

# ---------------- REQUEST MODEL ----------------

class ChatRequest(BaseModel):
    message: str | None = None
    stage: str | None = "start"
    categoryId: int | None = None
    subcategory: str | None = None

# ---------------- GEMINI HELPERS ----------------

def ask_gemini(prompt: str) -> list[str]:
    response = model.generate_content(prompt)
    text = response.text or ""

    titles = []
    for line in text.split("\n"):
        line = line.strip("•- ").strip()
        if len(line) > 3:
            titles.append(line)

    return titles[:3]

def wants_more_titles(msg: str):
    if not msg:
        return False
    keywords = ["more", "again", "another", "different", "new", "creative"]
    msg = msg.lower()
    return any(k in msg for k in keywords)

def generate_ai_titles(subcategory: str):
    prompt = f"""
You are a marketing expert.

Business type: {subcategory}

Generate 3 UNIQUE and CREATIVE deal titles.

Rules:
- Short and catchy
- Mix styles (fun, premium, festive)
- Do NOT explain
- Return ONLY the titles as bullet points
"""
    return ask_gemini(prompt)

# ---------------- CHAT API ----------------

@app.post("/chat")
def chat(req: ChatRequest):

    # 1️⃣ START → DIRECTLY SHOW SUBCATEGORIES
    if req.stage == "start":
        cat = CATEGORY_MAP.get(req.categoryId)
        if not cat:
            return {
                "reply": "Invalid category selected ❌",
                "options": [],
                "next_stage": "done"
            }

        return {
            "reply": f"Select your {cat['name']} business type:",
            "options": cat["subcategories"],
            "next_stage": "select_subcategory"
        }

    # 2️⃣ SUBCATEGORY
    if req.stage == "select_subcategory":
        return {
            "reply": f"You run a {req.subcategory}. What do you want help with?",
            "options": ["Suggest deal titles"],
            "next_stage": "business_help"
        }

    # 3️⃣ AI TITLES
    if req.stage == "business_help":
        titles = generate_ai_titles(req.subcategory)
        return {
            "reply": "Here are some creative deal titles 👇 Choose one or type your own:",
            "options": titles,
            "next_stage": "title_selection"
        }

    # 4️⃣ TITLE SELECTION
    if req.stage == "title_selection":

        if req.message and wants_more_titles(req.message):
            titles = generate_ai_titles(req.subcategory)
            return {
                "reply": "Here are some fresh ideas 👇",
                "options": titles,
                "next_stage": "title_selection"
            }

        return {
            "reply": "Nice 👍 Now enter a price (or pick one):",
            "options": ["₹999", "₹1499", "₹1999"],
            "next_stage": "price_selection"
        }

    # 5️⃣ PRICE
    if req.stage == "price_selection":
        return {
            "reply": "Looks good 👍 Select a discount:",
            "options": ["30%", "40%", "50%"],
            "next_stage": "discount_selection"
        }

    # 6️⃣ DISCOUNT
    if req.stage == "discount_selection":
        return {
            "reply": "All set ✅ Shall I save this deal?",
            "options": ["Yes, save", "Edit again"],
            "next_stage": "confirm_submit"
        }

    # 7️⃣ CONFIRM
    if req.stage == "confirm_submit":

        if req.message == "Edit again":
            return {
                "reply": "Okay 👍 Let’s refine the deal again.",
                "options": [],
                "next_stage": "business_help"
            }

        return {
            "reply": "Perfect 👍 Sending this deal to Add Deal screen.",
            "options": [],
            "next_stage": "done"
        }

    return {
        "reply": "Let’s continue 👍",
        "options": [],
        "next_stage": req.stage
    }

# ---------------- HEALTH CHECK ----------------

@app.get("/")
def home():
    return {"status": "SmartAlerts Gemini API Running"}
