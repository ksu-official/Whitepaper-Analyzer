FACTS_PROMPT = """Extract ONLY facts from this whitepaper. If missing, write NOT FOUND.

PROJECT_NAME: [name or NOT FOUND]
BLOCKCHAIN: [chain or NOT FOUND]
TOTAL_SUPPLY: [number or NOT FOUND]
COMMUNITY_ALLOCATION: [% or NOT FOUND]
TEAM_ALLOCATION: [% or NOT FOUND]
INVESTOR_ALLOCATION: [% or NOT FOUND]
VESTING_PERIOD: [months or NOT FOUND]
TESTNET_MENTIONED: [YES or NO]
POINTS_SYSTEM: [YES or NO]

Whitepaper text:
{text}"""

SUMMARY_PROMPT = """You are a crypto research analyst. Based ONLY on facts below, write analysis.
NEVER invent or guess. If something is NOT FOUND — say "Not mentioned in whitepaper".

EXTRACTED FACTS:
{facts}

AIRDROP INFO:
{airdrop_context}

Write analysis:

1. PROJECT OVERVIEW — What exactly does the project do?
2. PROBLEM & SOLUTION FIT — What exact problem does it solve? Is it clearly defined or vague?
3. TECHNOLOGY — Blockchain, infrastructure, and technical approach.
4. COMPETITIVE ADVANTAGE — What makes this project different? Real innovation or just a copy?
5. TOKEN UTILITY — What is the token actually used for?
6. TOKEN NECESSITY — Is the token required for the product, or could it exist without it?
7. TOKENOMICS QUALITY — Based on allocation and vesting, is distribution fair? Any insider advantages?
8. PRODUCT STAGE & REALITY CHECK — Is this an idea, testnet, or working product? Does it sound realistic?
9. TARGET AUDIENCE — Who will actually use this? Is there a clear user base?
10. TEAM & TRANSPARENCY — Are team members identified? Is info verifiable or missing?
11. GREEN FLAGS — List strong positive signals based only on available data.
12. RED FLAGS — List specific warning signs (vague language, missing data, unrealistic claims).
13. AIRDROP — Use AIRDROP INFO exactly. If not mentioned: "Airdrop not mentioned in whitepaper. Check official Twitter/Discord."
14. VERDICT:
    - Innovation score: X/10
    - Tokenomics fairness: X/10
    - Overall credibility: X/10

Be honest. Never hallucinate. Use only available data."""
