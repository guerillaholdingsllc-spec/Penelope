
# PENELOPE NICHED REVENUE MISSIONS
# Drop-in replacement for REVENUE_MISSIONS in autonomous_engine.py
# Each mission is hyper-specific to Guerilla Holdings industries

REVENUE_MISSIONS = [

    # ── CADAVER / MEDICAL TRANSPORT ─────────────────────────────────────────
    {
        "name": "Cadaver Transport Compliance Kit",
        "category": "cadaver",
        "price": 197,
        "platform": "gumroad",
        "prompt": """Create a COMPLETE, ready-to-sell California Cadaver Transport Compliance Kit for funeral homes and coroner offices.

Target buyer: Funeral home directors and independent cadaver transport operators in California (Sacramento, Bay Area, Northern California).

Deliver ALL of the following:

COMPLIANCE CHECKLIST:
- Complete CDPH cadaver transport requirements checklist (itemized, checkbox format)
- Vehicle requirements under California Health & Safety Code 7500-7510
- Driver certification requirements by transport type
- Documentation required per transport (chain of custody, release forms)
- Refrigeration/storage requirements and timeframes
- Interstate transport requirements and permits

BUSINESS SETUP GUIDE:
- California business license requirements for cadaver transport
- Insurance minimums (commercial auto, general liability, professional liability)
- CBRN/Hazmat certification requirements
- Coroner office contract requirements - what they look for
- Rate schedule template ($95-$350 depending on distance/complexity)

CONTRACT TEMPLATES:
- Funeral home service agreement template
- Driver independent contractor agreement template
- Chain of custody form template
- Incident report template

OPERATIONS SOP:
- Standard pickup procedure (step by step)
- After-hours emergency protocol
- Difficult access situations (no elevator, multiple floors)
- Decomposed/bariatric case protocols

MARKETING ONE-PAGER:
- Cold outreach email template to funeral homes
- What funeral homes actually care about (response time, discretion, reliability)
- How to price competitively in Sacramento market

Make every section complete enough that a new operator could hand this to a lawyer and a driver and start operating next week. This kit sells for $197 - make it worth it.""",
    },

    {
        "name": "Funeral Home AI Automation Package",
        "category": "cadaver",
        "price": 297,
        "platform": "gumroad",
        "prompt": """Create a COMPLETE AI automation package specifically for small funeral homes (1-5 staff) in California.

Target buyer: Funeral home owners who are overwhelmed with admin work and want to modernize without hiring.

Deliver ALL of the following:

AUTOMATION PLAYBOOK:
- 10 specific tasks funeral homes can automate TODAY with free/cheap AI tools
- Family communication templates (first call, arrangement conference follow-up, thank you)
- Obituary drafting system using ChatGPT (step-by-step with prompts)
- Pre-need inquiry response automation
- Review request automation (Google, Yelp, Facebook)

TOOL STACK RECOMMENDATION:
- Which tools to use (Zapier, Make, ChatGPT, Google Workspace) with funeral home-specific setup
- Cost breakdown (most under $50/month total)
- What NOT to automate (keep human touch here)

IMPLEMENTATION GUIDE:
- 30-day rollout plan (week by week)
- Which staff member owns each automation
- How to test before going live
- Compliance considerations (FTC funeral rule, state board requirements)

READY-TO-USE ASSETS:
- 5 family communication email templates (fully written)
- 3 obituary prompt templates for ChatGPT
- Social media content calendar (30 days, pre-written posts)
- Google Business Profile optimization checklist

ROI CALCULATOR:
- Hours saved per week by task
- Dollar value of time saved
- Breakeven analysis

Format everything as a professional PDF-ready document. This sells for $297.""",
    },

    # ── CRYPTO / DEVVE ───────────────────────────────────────────────────────
    {
        "name": "DEVVE Investor Intelligence Brief",
        "category": "crypto",
        "price": 47,
        "platform": "gumroad",
        "prompt": """Create a COMPLETE DEVVE investor intelligence brief for existing and prospective DEVVE holders.

Target buyer: Crypto investors who hold or are researching DEVVE and want institutional-quality research without paying for Bloomberg.

Deliver ALL of the following:

DEVVE DEEP DIVE:
- What DEVVE actually is (clear explanation no jargon)
- The development team - who are they, track record, red flags or green flags
- Tokenomics breakdown - supply, distribution, vesting, inflation
- What problem it solves and whether the market cares
- Competitive landscape - what else does what DEVVE does

CURRENT MARKET ANALYSIS:
- Price action analysis (trend, support, resistance)
- Volume analysis and what it signals
- Whale wallet activity and concentration risk
- Exchange listings and liquidity depth
- Risk score 1-10 with explanation

INVESTMENT FRAMEWORK:
- Bull case (specific price targets and catalysts)
- Bear case (specific risks and red flags)
- Base case (most likely 6-12 month scenario)
- Position sizing framework for different risk tolerances
- Entry zones, target zones, stop loss levels

WEEKLY MONITORING CHECKLIST:
- 10 specific things to watch every week as a DEVVE holder
- Which on-chain metrics matter most
- News sources that move DEVVE price
- When to add, hold, reduce, exit

COMPARISON TABLE:
- DEVVE vs 3 comparable projects (head to head on key metrics)

Make this the definitive resource for anyone researching DEVVE. This sells for $47.""",
    },

    {
        "name": "Crypto Risk Management Playbook",
        "category": "crypto",
        "price": 97,
        "platform": "gumroad",
        "prompt": """Create a COMPLETE crypto portfolio risk management playbook for retail investors with $1k-$50k in crypto.

Target buyer: Retail crypto investors who are tired of losing money and want a systematic approach to managing risk.

Deliver ALL of the following:

RISK FRAMEWORK:
- Position sizing formula (exact math, not theory)
- Portfolio allocation by risk tier (Bitcoin/ETH core vs mid caps vs small caps vs degen)
- Maximum allocation rules per coin
- Correlation matrix - which crypto assets move together and why this matters
- How to calculate your actual risk exposure right now

ENTRY AND EXIT SYSTEM:
- Technical analysis for non-analysts (3 indicators, that's it)
- Dollar cost averaging strategy (exact schedule and amounts)
- Profit taking ladder (take X% at Y gain, example portfolios)
- Stop loss placement (where exactly, never move it down)
- Tax-loss harvesting basics for crypto

PORTFOLIO TRACKER TEMPLATE:
- Google Sheets template (fully built, formula-ready)
- What to track daily vs weekly vs monthly
- Performance metrics that actually matter

PSYCHOLOGY AND DISCIPLINE:
- The 5 mistakes that kill retail portfolios (with real examples)
- How to handle a 50% drawdown without panic selling
- FOMO checklist (run before making any trade)
- Monthly portfolio review process (30 minute routine)

EMERGENCY PROTOCOLS:
- What to do when the market crashes 30% in a day
- Exchange insolvency protocol (FTX lessons)
- Security checklist (hardware wallet, 2FA, recovery phrases)

This playbook sells for $97 - make it thorough enough that buyers say it paid for itself on the first trade.""",
    },

    # ── CALLUX PLATFORM ──────────────────────────────────────────────────────
    {
        "name": "CALLUX Driver Certification Study Guide",
        "category": "callux",
        "price": 47,
        "platform": "gumroad",
        "prompt": """Create a COMPLETE driver certification study guide for the CALLUX specialty transport platform.

CALLUX is a gig-economy dispatch marketplace for specialty transport (medical, cadaver, sensitive cargo) with a 6-tier driver certification system.

Target buyer: Independent contractors and drivers who want to get certified on CALLUX to access higher-paying specialty transport jobs.

Deliver ALL of the following:

CALLUX PLATFORM OVERVIEW:
- What CALLUX is and how it works
- The 6 certification tiers (Basic → Standard → Advanced → Specialized → Expert → Elite)
- What jobs each tier unlocks and the pay differential
- The 65/35 revenue split model (driver keeps 65%)
- How dispatch works (job notification, acceptance window, GPS tracking)

CERTIFICATION TIER BREAKDOWN:
For each of the 6 tiers:
- Requirements (hours, training, background check, equipment)
- Jobs unlocked at this tier
- Average pay per job
- How to advance to the next tier
- Estimated time to achieve this tier from scratch

STUDY GUIDE BY TIER:
- Basic: Vehicle requirements, documentation, professional conduct standards
- Standard: Medical transport protocols, HIPAA basics, patient dignity
- Advanced: Cadaver transport procedures, chain of custody, CDPH requirements
- Specialized: Hazmat basics, biohazard handling, PPE requirements
- Expert: Multi-vehicle coordination, subcontracting rules, quality audits
- Elite: Platform ambassador role, training other drivers, premium client access

EXAM PREP:
- 50 practice questions with answers (matching real certification content)
- Key terms and definitions flashcard format
- Common mistakes that fail certification

BUSINESS OPTIMIZATION:
- How to maximize earnings on CALLUX
- Which jobs to accept vs decline (ROI calculator)
- Building a 5-star rating systematically
- Tax tips for gig drivers (mileage, vehicle expenses, self-employment)

EQUIPMENT CHECKLIST:
- Required vs recommended equipment by tier
- Where to source equipment at best price
- Maintenance requirements and documentation

Format as a professional study guide. Sells for $47.""",
    },

    {
        "name": "Specialty Transport Business Launch Kit",
        "category": "callux",
        "price": 297,
        "platform": "gumroad",
        "prompt": """Create a COMPLETE business launch kit for someone starting a specialty transport company in California.

Target buyer: Entrepreneurs who want to start a medical transport, cadaver transport, or specialty logistics company and need a step-by-step launch system.

This is based on the CALLUX model of independent specialty transport operators.

Deliver ALL of the following:

BUSINESS STRUCTURE:
- Entity formation guide (LLC vs S-Corp for transport operators)
- California-specific requirements (Secretary of State filing, EIN, business license)
- Four-entity structure for liability protection (operations LLC, management LLC, IP holding, driver entity)
- Operating agreement template for transport LLC
- Why keeping operations and management separate protects you

LICENSING AND COMPLIANCE:
- California DMV requirements for commercial transport
- CDPH permits for medical/cadaver transport
- Federal motor carrier safety requirements (if applicable)
- Drug testing program setup
- Background check requirements and process
- Insurance requirements (commercial auto minimums, general liability, cargo)

FINANCIAL SETUP:
- Startup cost breakdown (realistic, Sacramento market)
- Revenue projections by vehicle count (Year 1-3)
- Pricing strategy (per mile, flat rate, after-hours premium)
- Invoicing and net terms for funeral homes and hospitals
- QuickBooks setup for transport companies

OPERATIONS LAUNCH:
- First 30 days checklist
- How to land your first 3 funeral home contracts
- Driver recruitment and onboarding process
- Dispatch system setup (using tools like CALLUX or building your own)
- Quality control and incident management

GROWTH PLAYBOOK:
- When to add the second vehicle (specific metrics)
- How to bid on county coroner contracts
- Hospital transport partnerships
- Scaling from local to regional

LEGAL TEMPLATES:
- Client service agreement
- Driver independent contractor agreement
- Non-disclosure agreement
- Incident report form

Make this a complete business-in-a-box. Sells for $297.""",
    },

    # ── AI SERVICES (BROAD) ──────────────────────────────────────────────────
    {
        "name": "AI Automation for Medical Transport Companies",
        "category": "ai_services",
        "price": 197,
        "platform": "gumroad",
        "prompt": """Create a COMPLETE AI automation implementation guide specifically for medical transport and ambulance companies.

Target buyer: Operations managers and owners of NEMT (non-emergency medical transport), ambulance services, and specialty transport companies with 2-20 vehicles.

Deliver ALL of the following:

DISPATCH AUTOMATION:
- AI-powered route optimization setup (specific tools, step-by-step)
- Automated driver notification system
- Real-time GPS tracking integration (free and paid options)
- No-show prediction and proactive rebooking
- Multi-vehicle coordination workflows

BILLING AND INSURANCE:
- Medical billing automation for NEMT (CMS 1500, prior auth)
- Insurance verification automation
- Claims denial prediction and prevention
- Patient eligibility checking automation
- ERA/EOB posting automation

SCHEDULING:
- Online booking system setup for NEMT
- Recurring ride automation for dialysis/chemo patients
- Cancellation and rebooking workflows
- Driver schedule optimization

COMPLIANCE AUTOMATION:
- Driver qualification file management (expiration alerts)
- Vehicle inspection reminder system
- Incident reporting automation
- HIPAA-compliant communication workflows

CUSTOMER COMMUNICATION:
- Ride confirmation and reminder texts
- Driver ETA notifications
- Post-ride satisfaction surveys
- Complaint escalation workflows

TOOL STACK:
- Recommended tools with transport-specific setup guides
- Cost comparison (total under $200/month for 10-vehicle operation)
- Integration map (what connects to what)

ROI CALCULATOR:
- Hours saved per dispatcher per week
- Missed trips prevented
- Billing error reduction
- Total monthly ROI

Makes a great upsell to the compliance kit. Sells for $197.""",
    },
]
