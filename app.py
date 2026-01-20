from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b"

# ---------------- DATA ----------------

CATEGORIES = {
    "Food": [
        "Bakery", "Cafe", "Restaurant", "Juice Bar",
        "Street Food Stall", "Ice Cream Parlour",
        "Organic Food Store", "Grocery Store"
    ],
    "Clothing": [
        "Men's Wear", "Women's Wear", "Kids Wear",
        "Boutique", "Ethnic Wear", "Casual Wear",
        "Sportswear", "Undergarments"
    ],
    "FMCG": [
        "Supermarket", "General Store", "Departmental Store",
        "Cosmetics Store", "Hygiene Products Store",
        "Packaged Food Store", "Cleaning Supplies",
        "Convenience Store"
    ],
    "Accessories": [
        "Footwear Store", "Bags & Luggage",
        "Watches & Jewelry", "Eyewear Store",
        "Mobile Accessories", "Hair Accessories",
        "Fashion Accessories"
    ]
}

# ---------------- REQUEST MODEL ----------------

class ChatRequest(BaseModel):
    message: str | None = None
    stage: str | None = "start"
    category: str | None = None
    subcategory: str | None = None

# ---------------- OLLAMA HELPER ----------------

def ask_ollama(prompt: str) -> list[str]:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    res = requests.post(OLLAMA_URL, json=payload, timeout=120)
    text = res.json()["response"]

    # extract clean bullet lines
    titles = []
    for line in text.split("\n"):
        line = line.strip("•- ").strip()
        if len(line) > 3:
            titles.append(line)

    return titles[:3]

def wants_more_titles(msg: str):
    keywords = [
        "more", "again", "another", "different",
        "not good", "bad", "boring", "creative", "new"
    ]
    msg = msg.lower()
    return any(k in msg for k in keywords)

# ---------------- AI TITLE GENERATOR ----------------

def generate_ai_titles(subcategory: str):
    prompt = f"""
You are a marketing expert.

Business type: {subcategory}

Generate 3 UNIQUE and CREATIVE deal titles.
Rules:
- Do NOT repeat previous titles
- Mix styles (fun, premium, festive)
- Short and catchy
- Return ONLY the titles as bullet points
"""
    return ask_ollama(prompt)

# ---------------- CHAT API ----------------

@app.post("/chat")
def chat(req: ChatRequest):

    # 1️⃣ START
    if req.stage == "start":
        return {
            "reply": "Let’s start 👍 Choose your business category:",
            "options": list(CATEGORIES.keys()),
            "next_stage": "select_category"
        }

    # 2️⃣ CATEGORY
    if req.stage == "select_category":
        return {
            "reply": f"Great! Select your {req.category} business type:",
            "options": CATEGORIES.get(req.category, []),
            "next_stage": "select_subcategory"
        }

    # 3️⃣ SUBCATEGORY
    if req.stage == "select_subcategory":
        return {
            "reply": f"You run a {req.subcategory}. What do you want help with?",
            "options": ["Suggest deal titles"],
            "next_stage": "business_help"
        }

    # 4️⃣ GENERATE TITLES (AI)
    if req.stage == "business_help":
        titles = generate_ai_titles(req.subcategory)
        return {
            "reply": "Here are some creative deal titles 👇 Choose one or type your own:",
            "options": titles,
            "next_stage": "title_selection"
        }

    # 5️⃣ TITLE SELECTION
    if req.stage == "title_selection":

        if req.message and wants_more_titles(req.message):
            titles = generate_ai_titles(req.subcategory)
            return {
                "reply": "Got it 👍 Here are some fresh AI-generated ideas:",
                "options": titles,
                "next_stage": "title_selection"
            }

        return {
            "reply": "Nice choice 👍 Now enter a price (or pick one):",
            "options": ["₹999", "₹1499", "₹1999"],
            "next_stage": "price_selection"
        }

    # 6️⃣ PRICE
    if req.stage == "price_selection":
        return {
            "reply": "Looks good 👍 Enter or select a discount:",
            "options": ["30%", "40%", "50%"],
            "next_stage": "discount_selection"
        }

    # 7️⃣ DISCOUNT
    if req.stage == "discount_selection":
        return {
            "reply": "All set ✅ Shall I save this deal?",
            "options": ["Yes, save", "Edit again"],
            "next_stage": "confirm_submit"
        }

    # 8️⃣ CONFIRM
    if req.stage == "confirm_submit":

        if req.message == "Edit again":
            return {
                "reply": "No problem 👍 Let’s refine the deal again.",
                "options": [],
                "next_stage": "business_help"
            }

        return {
            "reply": "Perfect 👍 Sending this deal to Add Deal screen.",
            "options": [],
            "next_stage": "done"
        }

    # FALLBACK
    return {
        "reply": "Let’s continue 👍",
        "options": [],
        "next_stage": req.stage
    }
