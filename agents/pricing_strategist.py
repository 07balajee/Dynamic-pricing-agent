import os
import requests
import json
from datetime import datetime
from mcp_server.client import SignalsClient

_signals_client = SignalsClient()

def get_groq_recommendation(prompt: str, api_key: str) -> str:
    """
    Calls Groq API to get a price recommendation with reasoning.
    Uses llama-3.3-70b-versatile with fallback to llama3-8b-8192.
    """
    if api_key and api_key.startswith("AQ.gsk_"):
        api_key = api_key[3:]  # Strip AQ. prefix if present

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Try llama-3.3-70b-versatile first
    models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3-8b-8192"]
    
    last_error = None
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],      
            "temperature": 0.2
        }
        try:
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                res_data = res.json()
                return res_data["choices"][0]["message"]["content"]
            else:
                last_error = f"Model {model} returned status {res.status_code}: {res.text}"
        except Exception as e:
            last_error = str(e)
            
    raise Exception(f"All Groq models failed. Last error: {last_error}")


def generate_mock_pricing_decision( 
    product_name: str,
    base_price: float,
    cost_price: float,
    inventory_stock: int,
    competitor_price: float,
    expiry_date,
    city: str,
    weather_signal: str,
    rule_based_price: float
) -> str:
    """
    Generates a high-quality, simulated AI pricing recommendation and reasoning.
    Used as a fallback when the Gemini API key is invalid/truncated.
    """
    # Determine days to expiry
    if isinstance(expiry_date, str):
        try:
            days_left = (datetime.strptime(expiry_date, '%Y-%m-%d').date() - datetime.now().date()).days
        except:
            days_left = 5
    elif hasattr(expiry_date, 'days'):
        days_left = expiry_date.days
    else:
        try:
            days_left = (expiry_date - datetime.now().date()).days
        except:
            days_left = 5

    # Determine recommended price
    # We want to be profitable (above cost_price) and competitive.
    # The rule-based price is rule_based_price (which has a floor of base_price * 0.7)
    suggested_price = max(rule_based_price, cost_price)
    
    # Adjust suggested price slightly for psychological pricing (e.g. $6.99 instead of $7.00)
    if abs(suggested_price - round(suggested_price)) < 0.05 or suggested_price % 1.0 == 0:
        suggested_price = math_floor_pricing(suggested_price)

    profit_margin = ((suggested_price - cost_price) / suggested_price) * 100 if suggested_price > 0 else 0

    # 1. Stock Reasoning
    if inventory_stock > 30:
        stock_reason = f"We have **{inventory_stock} units** in stock, which is considered high stock (greater than 30). We apply a stock discount to increase sales volume."
    else:
        stock_reason = f"We have **{inventory_stock} units** in stock, which is low stock (<= 30). No volume discount is applied."

    # 2. Expiry Reasoning
    if days_left < 3:
        expiry_reason = f"The product is expiring in **{days_left} days** (on {expiry_date}), representing extreme urgency. A heavy clearance discount is applied to avoid a total write-off/loss."
    elif days_left < 7:
        expiry_reason = f"The product is expiring in **{days_left} days** (on {expiry_date}), which is near-expiry (less than 7 days). A clearance discount is applied to accelerate inventory velocity."
    else:
        expiry_reason = f"The product has **{days_left} days** before expiry (on {expiry_date}), so there is no expiry pressure."

    # 3. Competitor Reasoning
    if suggested_price < competitor_price:
        diff_pct = ((competitor_price - suggested_price) / competitor_price) * 100
        comp_reason = f"Our suggested price of **${suggested_price:.2f}** is **{diff_pct:.1f}% cheaper** than the competitor's price of **${competitor_price:.2f}**, giving us a strong competitive advantage."
    elif abs(suggested_price - competitor_price) < 0.01:
        comp_reason = f"Our suggested price of **${suggested_price:.2f}** matches the competitor's price of **${competitor_price:.2f}**, staying aligned with market rates."
    else:
        diff_pct = ((suggested_price - competitor_price) / competitor_price) * 100
        comp_reason = f"Our suggested price of **${suggested_price:.2f}** is **{diff_pct:.1f}% higher** than the competitor's price of **${competitor_price:.2f}**. This premium is maintained to protect our cost floor of **${cost_price:.2f}**."

    # 4. Weather Reasoning
    weather_reason = f"Weather in {city} is reported as: \"{weather_signal}\". "
    if "C" in weather_signal:
        try:
            parts = weather_signal.split(":")
            if len(parts) > 1:
                temp_str = parts[1].strip().split("C")[0].strip()
                temp = float(temp_str)
                if temp > 28:
                    weather_reason += f"The high temperature of {temp}°C increases spoilage rates for fresh/perishable goods like {product_name}, making immediate inventory clearance crucial."
                elif temp < 15:
                    weather_reason += f"The cool weather of {temp}°C helps preserve perishable goods, giving us slightly more buffer, but might shift demand patterns."
                else:
                    weather_reason += f"Moderate temperatures of {temp}°C indicate normal storage conditions and steady demand."
        except:
            weather_reason += f"We monitor these local conditions to adjust pricing based on spoilage risk and foot traffic."
    else:
        weather_reason += f"We monitor these local conditions to adjust pricing based on spoilage risk and foot traffic."

    reasoning = f"""### Final Suggested Price: ${suggested_price:.2f}
### Profit Margin: {profit_margin:.1f}%

### Strategy & Reasoning:
1. **Cost & Profitability Analysis**: 
   - The cost floor is **${cost_price:.2f}**. The proposed price of **${suggested_price:.2f}** yields a profit margin of **{profit_margin:.1f}%**.

2. **Inventory & Expiry Pressures**:
   - {stock_reason}
   - {expiry_reason}

3. **Competitor Comparison**:
   - {comp_reason}

4. **Weather Influence**:
   - {weather_reason}
"""
    return reasoning

def math_floor_pricing(price: float) -> float:
    # Small helper to make prices look nice (e.g. ending in .99 or .95)
    base = int(price)
    if price - base > 0.5:
        return base + 0.99
    elif price - base > 0.0:
        return base + 0.49
    else:
        return price - 0.01

async def suggest_adaptive_price(
    product_name: str,
    base_price: float,
    cost_price: float,
    inventory_stock: int,
    competitor_price: float,
    expiry_date,
    city: str
) -> str:
    """
    Gathers environmental signals, calculates a rule-based baseline price,
    and leverages Gemini AI (with a local fallback) to determine a highly optimal and competitive price.
    Signals and rule-based pricing are fetched through the MCP signals server rather than
    calling agents/signal_collector.py or adaptors/vendor_adaptors.py directly.
    """
    # 1. Fetch weather signal via MCP
    weather_api_key = os.getenv("OPENWEATHER_API_KEY")
    try:
        weather_signal = await _signals_client.get_weather(city, weather_api_key)
    except Exception as e:
        weather_signal = f"Could not fetch weather data: {e}"

    # 2. Get baseline price via MCP (vendor_adaptors rules, run inside the MCP server)
    expiry_str = expiry_date.strftime('%Y-%m-%d') if hasattr(expiry_date, 'strftime') else str(expiry_date)
    rule_based_price = await _signals_client.get_vendor_price(
        base_price=base_price,
        inventory_stock=inventory_stock,
        competitor_price=competitor_price,
        expiry_date=expiry_str
    )

    # 3. Build Prompt for Gemini
    prompt = f"""
You are an expert AI Pricing Strategist for a retail store.
Your goal is to propose an optimal adaptive final selling price for a product that maximizes profit while remaining competitive and clearing stock efficiently when needed.

We have gathered the following signals for the product:
- **Product Name**: {product_name}
- **Original Base/Retail Price**: ${base_price:.2f}
- **Cost Price (Floor limit to ensure profitability)**: ${cost_price:.2f}
- **Current Inventory Stock**: {inventory_stock} units
- **Expiry Date**: {expiry_date.strftime('%Y-%m-%d') if isinstance(expiry_date, datetime) or hasattr(expiry_date, 'strftime') else str(expiry_date)}
- **Competitor Price**: ${competitor_price:.2f}
- **Local Weather Signal**: {weather_signal}
- **Rule-based Baseline Price**: ${rule_based_price:.2f}

Guidelines:
1. **Profitability**: The suggested price should not go below the Cost Price of ${cost_price:.2f} unless absolutely necessary to avoid total loss (e.g., severe expiry pressure).
2. **Competitiveness**: If the competitor price is lower, consider matching or staying close to it to prevent losing customers, but adjust based on stock level and expiry urgency.
3. **Inventory & Expiry**: If stock is high or expiry is very close, apply an appropriate discount to accelerate sales.
4. **Weather Impact**: Consider how weather affects demand for {product_name} (e.g., hot weather might increase demand for ice cream/cold beverages or increase spoilage rates of fresh fruits/vegetables).

Please provide your response in the following format:
### Final Suggested Price: $[amount]
### Profit Margin: [percentage]%
### Strategy & Reasoning:
[Provide a step-by-step reasoning for the final suggested price, highlighting the influence of inventory, expiry, competitor price, and weather signals.]
"""

    # 4. Get Groq recommendation
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("[Warning] GROQ_API_KEY is missing in .env. Falling back to local AI Pricing Strategist simulation...")
        return generate_mock_pricing_decision(
            product_name, base_price, cost_price, inventory_stock, competitor_price, expiry_date, city, weather_signal, rule_based_price
        )

    try:
        recommendation = get_groq_recommendation(prompt, groq_api_key)
        return recommendation
    except Exception as e:
        print(f"[Warning] Groq API call failed: {e}. Falling back to local AI Pricing Strategist simulation...")
        return generate_mock_pricing_decision(
            product_name, base_price, cost_price, inventory_stock, competitor_price, expiry_date, city, weather_signal, rule_based_price
        )
