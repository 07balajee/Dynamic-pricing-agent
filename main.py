import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from agents.pricing_strategist import suggest_adaptive_price

load_dotenv()

async def main():
    print("Initializing Adaptive Pricing Agent...")
    print("=" * 60)
    
    # Inputs for the pricing run
    product_name = "Fresh Organic Strawberries"
    base_price = 100.00
    cost_price = 95
    inventory_stock = 50
    competitor_price = 95.0
    expiry_date = datetime.now().date() + timedelta(days=5)  # 5 days from now
    city = "Coimbatore"
    
    print(f"Running pricing strategy for: {product_name}")
    print(f"- Base Price: ${base_price:.2f}")
    print(f"- Cost Price: ${cost_price:.2f}")
    print(f"- Inventory Stock: {inventory_stock} units")
    print(f"- Competitor Price: ${competitor_price:.2f}")
    print(f"- Expiry Date: {expiry_date}")
    print(f"- Target City: {city}")
    print("=" * 60)
    
    # Get suggested adaptive price from Groq
    recommendation = await suggest_adaptive_price(
        product_name=product_name,
        base_price=base_price,
        cost_price=cost_price,
        inventory_stock=inventory_stock,
        competitor_price=competitor_price,
        expiry_date=expiry_date,
        city=city
    )
    
    print("\nGroq AI Recommendation and Reasoning:\n")
    print(recommendation)

if __name__ == "__main__":
    asyncio.run(main())
