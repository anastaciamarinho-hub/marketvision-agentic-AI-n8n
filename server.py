import os
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from fastmcp import FastMCP
from serpapi import GoogleSearch

# Load environment variables from .env file
load_dotenv()

# Get SerpAPI key from .env
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
if not SERPAPI_API_KEY:
    raise ValueError("Please set SERPAPI_API_KEY in your .env file.")

# MCP Server scaffold
mcp = FastMCP(name="MarketIntel")

# Helper function to handle SerpAPI search requests
def _serpapi_search(query: str, **kwargs) -> Dict[str, Any]:
    search = GoogleSearch({
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "num": kwargs.get("max_results", 10),
        "engine": kwargs.get("engine", "google"),
        "tbm": kwargs.get("tbm", "nws") if "topic" in kwargs and kwargs["topic"] == "news" else None,
    })
    
    results = search.get_dict()
    
    # Extract only the relevant parts
    organic_results = results.get("organic_results", [])
    answer_box = results.get("answer_box", {})
    
    return {
        "query_used": query,
        "answer": answer_box.get("answer", ""),
        "results": [
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "content": item.get("snippet", ""),
                "score": item.get("score", ""),
                "published_date": item.get("date", "")
            }
            for item in organic_results
        ],
    }

@mcp.resource("resource://market/topics")
def market_topics() -> List[str]:
    return [
        "Competitor overview", "Pricing snapshot",
        "Product portfolio mapping", "Market landscape",
        "Feature comparison", "Regional GTM"
    ]

@mcp.tool(annotations={"title": "Company Overview"})
def company_overview(name: str, region: Optional[str] = None, max_results: int = 8):
    reg = f" in {region}" if region else ""
    q = f"Company overview of {name}{reg}: founding, HQ, products, business model, recent news"
    return _serpapi_search(q, max_results=max_results)

@mcp.tool(annotations={"title": "List Competitors"})
def list_competitors(name: str, category: Optional[str] = None, region: Optional[str] = None, max_results: int = 10):
    cat = f" in {category}" if category else ""
    reg = f" in {region}" if region else ""
    q = f"Top competitors of {name}{cat}{reg}; include upstart challengers"
    return _serpapi_search(q, max_results=max_results)

@mcp.tool(annotations={"title": "Product Portfolio Map"})
def product_portfolio(company: str, focus_keywords: Optional[List[str]] = None, max_results: int = 12):
    kws = f" ({', '.join(focus_keywords)})" if focus_keywords else ""
    q = f"{company} product portfolio{kws}: product list, suites, tiers, segments"
    return _serpapi_search(q, max_results=max_results)

@mcp.tool(annotations={"title": "Pricing Snapshot"})
def pricing_snapshot(product_or_company: str, region: Optional[str] = None, currency_hint: Optional[str] = None, max_results: int = 10):
    reg = f" in {region}" if region else ""
    cur = f" in {currency_hint}" if currency_hint else ""
    q = f"Pricing for {product_or_company}{reg}{cur}: list price, tiers, billing cycles, discounts, hidden fees"
    return _serpapi_search(q, max_results=max_results)

@mcp.tool(annotations={"title": "Recent News Pulse"})
def recent_news_pulse(company: str, days: int = 30, max_results: int = 10):
    q = f"Recent news about {company}: funding, acquisitions, launches, leadership"
    # Use the news engine for recent news
    return _serpapi_search(q, max_results=max_results, topic="news")

@mcp.prompt
def competitor_analysis_prompt(company: str, region: str = "", category: str = "") -> str:
    return (
        f"Build a competitor brief for '{company}'"
        + (f" in '{region}'" if region else "")
        + (f" within '{category}'" if category else "")
        + ". Steps: 1) Company Overview 2) List Competitors 3) Portfolio & Pricing 4) News Pulse 5) SWOT+Five Forces."
    )

def main():
    print("\n🚀 Starting MarketIntel MCP Server (SerpAPI)...")
    mcp.run(transport="sse", port=8005)  # 👈 CHANGE THIS TO 8005

if __name__ == "__main__":
    main()