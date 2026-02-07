from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
import re

load_dotenv()
app = FastAPI()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

CATEGORY_MAP = {
    2: {"name": "Food", "subcategories": ["Bakery", "Cafe", "Restaurant", "Juice Bar", "Street Food Stall", "Ice Cream Parlour", "Organic Food Store", "Grocery Store"]},
    3: {"name": "Clothing", "subcategories": ["Men's Wear", "Women's Wear", "Kids Wear", "Boutique", "Ethnic Wear", "Casual Wear", "Sportswear", "Undergarments"]},
    5: {"name": "FMCG", "subcategories": ["Supermarket", "General Store", "Departmental Store", "Cosmetics Store", "Packaged Food Store", "Convenience Store"]},
    4: {"name": "Accessories", "subcategories": ["Footwear Store", "Bags & Luggage", "Watches & Jewelry", "Eyewear Store", "Mobile Accessories", "Fashion Accessories"]}
}

PRICE_SUGGESTIONS = {
    "Bakery": ["₹99", "₹149", "₹199"],
    "Cafe": ["₹129", "₹179", "₹229"],
    "Restaurant": ["₹199", "₹299", "₹399"],
    "Juice Bar": ["₹79", "₹119", "₹159"],
    "Street Food Stall": ["₹49", "₹79", "₹99"],
    "Ice Cream Parlour": ["₹89", "₹129", "₹169"],
    "Organic Food Store": ["₹149", "₹199", "₹249"],
    "Grocery Store": ["₹99", "₹149", "₹199"],
    "Men's Wear": ["₹499", "₹799", "₹1199"],
    "Women's Wear": ["₹599", "₹899", "₹1299"],
    "Kids Wear": ["₹399", "₹599", "₹899"],
    "Boutique": ["₹999", "₹1499", "₹1999"],
    "Ethnic Wear": ["₹899", "₹1299", "₹1899"],
    "Casual Wear": ["₹499", "₹699", "₹999"],
    "Sportswear": ["₹799", "₹1199", "₹1799"],
    "Undergarments": ["₹199", "₹299", "₹399"],
    "Supermarket": ["₹199", "₹299", "₹399"],
    "General Store": ["₹99", "₹149", "₹199"],
    "Departmental Store": ["₹299", "₹399", "₹599"],
    "Cosmetics Store": ["₹199", "₹299", "₹499"],
    "Packaged Food Store": ["₹99", "₹149", "₹199"],
    "Convenience Store": ["₹99", "₹149", "₹199"],
    "Footwear Store": ["₹699", "₹999", "₹1499"],
    "Bags & Luggage": ["₹899", "₹1299", "₹1899"],
    "Watches & Jewelry": ["₹999", "₹1999", "₹2999"],
    "Eyewear Store": ["₹799", "₹1199", "₹1799"],
    "Mobile Accessories": ["₹199", "₹299", "₹399"],
    "Fashion Accessories": ["₹199", "₹299", "₹499"]
}

class DealState(BaseModel):
    title: str | None = None
    price: str | None = None
    discount: str | None = None
    description: str | None = None
    
    # Track completion status
    title_done: bool = False
    price_done: bool = False
    discount_done: bool = False
    description_done: bool = False

class ChatRequest(BaseModel):
    message: str | None = None
    stage: str | None = "start"
    categoryId: int | None = None
    subcategory: str | None = None
    deal: DealState | None = None

class ChatResponse(BaseModel):
    reply: str
    options: list[str]
    next_stage: str
    deal: DealState
    action: str | None = None

def clean_text(text: str) -> str:
    text = re.sub(r"[*•\-]", "", text)
    text = re.sub(r"\d+\.", "", text)
    text = text.replace("**", "")  # Remove markdown bold
    return text.strip()

def ask_gemini(prompt: str) -> list[str]:
    response = model.generate_content(prompt)
    lines = (response.text or "").split("\n")
    return [clean_text(line) for line in lines if len(clean_text(line)) > 3][:4]

def generate_ai_titles(subcategory: str) -> list[str]:
    return ask_gemini(f"Business type: {subcategory}\nGenerate 3 short catchy deal titles (max 5 words). No numbers. No prices.")

def generate_description(subcategory: str, deal: DealState) -> str:
    prompt = f"Business: {subcategory}\nTitle: {deal.title or 'Special Offer'}\nDiscount: {deal.discount or 'Great Discount'}\nWrite a short, professional 2-line promotional description. Do NOT use headings."
    response = model.generate_content(prompt)
    return clean_text(response.text)

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    deal = req.deal or DealState()
    
    # 1. Start -> Select Business Subtype
    if req.stage == "start":
        cat = CATEGORY_MAP.get(req.categoryId)
        if not cat:
            return ChatResponse(
                reply="Please select a valid category first.",
                options=[],
                next_stage="start",
                deal=deal
            )
        return ChatResponse(
            reply=f"Select your {cat['name']} business type:",
            options=cat["subcategories"],
            next_stage="select_subcategory",
            deal=deal
        )

    # 2. Select Subtype -> Main Menu
    if req.stage == "select_subcategory":
        # The user has selected a subtype, stored in req.subcategory
        # Just acknowledge and go to menu
        return get_menu_response(req.subcategory, deal, "Let's start building your deal. Select a section to fill:")

    # 3. Main Menu Logic
    if req.stage == "menu":
        selection = req.message
        
        if selection == "Deal Title" or selection == "Edit Title":
            return start_title_flow(req.subcategory, deal)
        elif selection == "Cost" or selection == "Edit Cost":
            return start_cost_flow(req.subcategory, deal)
        elif selection == "Discount" or selection == "Edit Discount":
            return start_discount_flow(req.subcategory, deal)
        elif selection == "Deal Description" or selection == "Edit Description":
            return start_description_flow(req.subcategory, deal)
        elif selection == "Move to Add Deal":
            return show_final_summary(req.subcategory, deal)
        elif selection == "Continue Building":
             # Should show remaining options
             return get_menu_response(req.subcategory, deal, "What would you like to add next?")
        else:
            # Fallback for unrecognized input
             return get_menu_response(req.subcategory, deal, "Please select an option:")

    # --- TITLE FLOW ---
    if req.stage == "title_input":
        deal.title = clean_text(req.message)
        deal.title_done = True
        return show_intermediate_menu(req.subcategory, deal, "title")

    if req.stage == "title_intermediate":
        return handle_intermediate_selection(req.message, req.subcategory, deal, "title")

    # --- COST FLOW ---
    if req.stage == "cost_input":
        deal.price = clean_text(req.message)
        deal.price_done = True
        return show_intermediate_menu(req.subcategory, deal, "cost")
    
    if req.stage == "cost_intermediate":
        return handle_intermediate_selection(req.message, req.subcategory, deal, "cost")

    # --- DISCOUNT FLOW ---
    if req.stage == "discount_input":
        deal.discount = clean_text(req.message)
        deal.discount_done = True
        return show_intermediate_menu(req.subcategory, deal, "discount")

    if req.stage == "discount_intermediate":
        return handle_intermediate_selection(req.message, req.subcategory, deal, "discount")

    # --- DESCRIPTION FLOW ---
    if req.stage == "description_generated":
        if req.message == "Accept Description":
            deal.description_done = True
            # For description, we don't necessarily show intermediate menu if it's the last step, 
            # but consistently showing it is safer.
            return show_intermediate_menu(req.subcategory, deal, "description")
        elif req.message == "Edit Description":
             # Regenerate
             return start_description_flow(req.subcategory, deal)
        else:
             # Assume manual input or unrecognized
             deal.description = clean_text(req.message)
             deal.description_done = True
             if req.message == "Accept Description":
                 # Fallback if cleaner missed it
                 pass
             return show_intermediate_menu(req.subcategory, deal, "description")

    if req.stage == "description_intermediate":
        return handle_intermediate_selection(req.message, req.subcategory, deal, "description")


    # --- FINAL SUBMIT ---
    if req.stage == "final_summary":
        if req.message == "Yes, Apply Deal":
             return ChatResponse(
                reply="Deal saved successfully! Redirecting...",
                options=[],
                next_stage="done",
                deal=deal,
                action="go_to_add_deal"
            )
        elif req.message == "Edit Something":
             return get_menu_response(req.subcategory, deal, "What would you like to edit?", show_all=True)
        else:
             return show_final_summary(req.subcategory, deal)

    # Default fallback
    return get_menu_response(req.subcategory, deal, "I didn't catch that. Please select an option:")


def get_menu_response(subcategory: str, deal: DealState, text: str, show_all: bool = False) -> ChatResponse:
    options = []
    
    sections = [
        ("Deal Title", deal.title_done),
        ("Cost", deal.price_done),
        ("Discount", deal.discount_done),
        ("Deal Description", deal.description_done)
    ]
    
    for label, is_done in sections:
        if show_all:
            # In edit mode/show_all, we show all options with "Edit" prefix if appropriate
            # or just show the labels that Main Menu logic accepts.
            # "Deal Title" -> "Edit Title"
            # "Cost" -> "Edit Cost"
            # "Discount" -> "Edit Discount"
            # "Deal Description" -> "Edit Description"
            if label == "Deal Title": key = "Edit Title"
            elif label == "Deal Description": key = "Edit Description"
            else: key = f"Edit {label}"
            options.append(key)
        elif not is_done:
            # specific requirement: reduce sections one by one
            options.append(label)
    
    # If not showing all and nothing left, go to summary
    if not show_all and not options:
        return show_final_summary(subcategory, deal)

    # Add "Move to Add Deal" always
    options.append("Move to Add Deal")
    
    return ChatResponse(
        reply=text,
        options=options,
        next_stage="menu",
        deal=deal
    )


def start_title_flow(subcategory: str, deal: DealState) -> ChatResponse:
    titles = generate_ai_titles(subcategory)
    return ChatResponse(
        reply="Here are some catchy titles for you:",
        options=titles,
        next_stage="title_input",
        deal=deal
    )

def start_cost_flow(subcategory: str, deal: DealState) -> ChatResponse:
    suggestions = PRICE_SUGGESTIONS.get(subcategory, ["₹99", "₹149", "₹199"])
    return ChatResponse(
        reply="Great! Select a price or type your own:",
        options=suggestions,
        next_stage="cost_input",
        deal=deal
    )

def start_discount_flow(subcategory: str, deal: DealState) -> ChatResponse:
    return ChatResponse(
        reply="Select a discount percentage:",
        options=["20%", "30%", "40%", "50%", "60%"],
        next_stage="discount_input",
        deal=deal
    )

def start_description_flow(subcategory: str, deal: DealState) -> ChatResponse:
    desc = generate_description(subcategory, deal)
    deal.description = desc # Store it tentatively
    return ChatResponse(
        reply=f"{desc}", # Only description text
        options=["Accept Description", "Edit Description"],
        next_stage="description_generated",
        deal=deal
    )

def show_intermediate_menu(subcategory: str, deal: DealState, current_section: str) -> ChatResponse:
    # "After completing any section... show Continue Building, Move to Add Deal, Edit [Section]"
    section_name = current_section.title()
    options = ["Continue Building", "Move to Add Deal", f"Edit {section_name}"]
    
    return ChatResponse(
        reply=f"{section_name} saved!",
        options=options,
        next_stage=f"{current_section}_intermediate",
        deal=deal
    )

def handle_intermediate_selection(selection: str, subcategory: str, deal: DealState, current_section: str) -> ChatResponse:
    if selection == "Continue Building":
        return get_menu_response(subcategory, deal, "What's next?")
    elif selection == "Move to Add Deal":
        return show_final_summary(subcategory, deal)
    elif selection.startswith("Edit"):
        # "Edit Title" -> start_title_flow
        # But we need to support the "Edit Mode" from prompt:
        # "Show summary... then ask ONLY for the section"
        
        # We can just construct the summary string and call the start flow
        summary = f"So far, you have selected:\n• Title: {deal.title or '-'}\n• Cost: {deal.price or '-'}\n• Discount: {deal.discount or '-'}\n• Description: {deal.description or '-'}\n\nEditing {current_section.title()}..."
        
        if current_section == "title":
            resp = start_title_flow(subcategory, deal)
        elif current_section == "cost":
            resp = start_cost_flow(subcategory, deal)
        elif current_section == "discount":
            resp = start_discount_flow(subcategory, deal)
        elif current_section == "description":
            resp = start_description_flow(subcategory, deal)
        else:
            return get_menu_response(subcategory, deal, "Error: Unknown section")
            
        resp.reply = summary + "\n\n" + resp.reply
        return resp
        
    else:
        # Fallback
        return get_menu_response(subcategory, deal, "Please select a valid option.")

def show_final_summary(subcategory: str, deal: DealState) -> ChatResponse:
    summary = f"Deal Summary:\nTitle: {deal.title or '-'}\nCost: {deal.price or '-'}\nDiscount: {deal.discount or '-'}\nDescription: {deal.description or '-'}"
    return ChatResponse(
        reply=summary,
        options=["Yes, Apply Deal", "Edit Something"],
        next_stage="final_summary",
        deal=deal
    )

