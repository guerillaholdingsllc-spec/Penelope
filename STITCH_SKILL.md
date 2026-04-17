# STITCH AGENT SKILL
Penelope can build functional web apps using the Stitch pipeline.

## USAGE EXAMPLES

### Research app ideas in a niche:
`python3 stitch_agent.py --research "ecommerce" --count 10`

### Redesign an existing app:
`python3 stitch_agent.py --url https://www.simplyduty.com --prompt "Redesign for 2026, brand for Amazon/eBay/Shopify sellers" --niche "ecommerce sellers"`

### Build from scratch:
`python3 stitch_agent.py --idea "Import duty calculator for Amazon FBA sellers" --niche "Amazon sellers"`

### List built apps:
`python3 stitch_agent.py --list`

## PIPELINE (4 steps like Google Stitch):
1. Research/Scrape — find or analyze existing app
2. Design — Gemini generates complete functional HTML
3. Results page — complementary output page
4. Deploy — local preview + optional Vercel

## GALLERY
View all built apps at: http://206.81.5.241:9001

## MONETIZATION
- Sell redesigned apps to businesses: $2,500-$15,000
- Launch as SaaS with Stripe integration
- White-label for agencies
