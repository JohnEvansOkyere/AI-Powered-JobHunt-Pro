"""
Tech job keyword catalogue used by scheduled scraping.

Scrapers such as RemoteOK, Arbeitnow, and SerpAPI only use the first ~15 keywords
for search/filter, so the leading entries mix roles with experience levels. The
remainder provides breadth for deduplication/routing in other flows.
"""

TECH_JOB_KEYWORDS = [
    # Core tech roles + levels (first 10–15 used by RemoteOK/Arbeitnow/SerpAPI)
    "software engineer", "software developer", "developer", "engineer",
    "internship", "entry level", "junior", "senior", "backend", "frontend",
    "full stack", "data scientist", "data engineer", "devops", "product manager",

    # More experience levels & role types
    "intern", "entry-level", "graduate", "new grad", "new graduate", "associate",
    "mid level", "mid-level", "intermediate", "staff engineer", "principal engineer",
    "lead engineer", "experienced",

    # Software Engineering - General
    "backend engineer", "backend developer", "frontend engineer", "frontend developer",
    "full stack developer", "full stack engineer", "fullstack developer",
    "web developer", "web engineer", "application developer",

    # Entry-level & junior tech (explicit)
    "junior software engineer", "junior developer", "junior engineer",
    "entry level developer", "entry level engineer", "graduate developer",
    "graduate engineer", "software engineer internship", "developer internship",
    "engineering internship", "tech internship", "co-op", "coop",

    # Mobile Development
    "mobile developer", "mobile engineer", "ios developer", "ios engineer",
    "android developer", "android engineer", "react native developer",
    "flutter developer", "mobile app developer", "swift developer",
    "kotlin developer",

    # Frontend & JavaScript
    "react developer", "react engineer", "vue developer", "angular developer",
    "javascript developer", "typescript developer", "nextjs developer",
    "frontend architect",

    # Backend & Languages
    "python developer", "python engineer", "java developer", "java engineer",
    "node developer", "nodejs developer", ".net developer", "c# developer",
    "golang developer", "go developer", "ruby developer", "rails developer",
    "php developer", "rust developer", "scala developer",

    # Data Science & Analytics (all levels)
    "data scientist", "data analyst", "senior data scientist",
    "junior data scientist", "junior data analyst", "entry level data analyst",
    "data science engineer", "data science internship", "analytics internship",
    "quantitative analyst", "research scientist", "research intern",
    "business intelligence analyst", "bi analyst", "bi developer",
    "analytics engineer", "data analytics", "statistical analyst",

    # AI & Machine Learning (all levels)
    "ai engineer", "ai developer", "ai/ml engineer", "ml engineer",
    "machine learning engineer", "machine learning scientist",
    "junior ml engineer", "ml internship", "ai internship",
    "deep learning engineer", "nlp engineer", "natural language processing",
    "computer vision engineer", "cv engineer", "ai researcher",
    "applied scientist", "research engineer", "llm engineer",
    "generative ai engineer", "prompt engineer",

    # Data Engineering
    "data engineer", "big data engineer", "etl developer",
    "data pipeline engineer", "data platform engineer",
    "dataops engineer", "analytics engineer",

    # DevOps & Infrastructure (all levels)
    "devops engineer", "site reliability engineer", "sre",
    "junior devops", "devops internship", "platform engineer",
    "infrastructure engineer", "cloud engineer", "aws engineer",
    "azure engineer", "gcp engineer", "kubernetes engineer", "k8s engineer",
    "docker engineer", "systems engineer", "linux engineer", "unix administrator",
    "network engineer", "network administrator",

    # Design & UX (all levels)
    "ux designer", "ui designer", "ui/ux designer", "ux/ui designer",
    "product designer", "senior product designer", "junior designer",
    "design internship", "ux internship", "ui internship",
    "lead designer", "graphic designer", "web designer", "visual designer",
    "interaction designer", "motion designer", "ux researcher",
    "design lead", "design manager", "creative director",
    "brand designer", "digital designer",

    # Product & Management
    "product manager", "senior product manager", "technical product manager",
    "product owner", "program manager", "project manager",
    "engineering manager", "tech lead", "technical lead",
    "team lead", "director of engineering", "vp engineering",
    "cto", "chief technology officer", "head of engineering",

    # Quality & Testing (all levels)
    "qa engineer", "quality assurance engineer", "test engineer",
    "junior qa engineer", "qa internship", "automation engineer",
    "test automation engineer", "sdet", "performance engineer",
    "qa analyst", "quality engineer", "test lead", "qa lead",

    # Security
    "security engineer", "cybersecurity engineer", "infosec engineer",
    "security analyst", "penetration tester", "security architect",
    "application security engineer", "devsecops engineer",
    "cloud security engineer", "soc analyst",

    # Specialized Engineering
    "embedded engineer", "embedded software engineer", "firmware engineer",
    "hardware engineer", "robotics engineer", "iot engineer",
    "game developer", "game engineer", "unity developer",
    "unreal developer", "graphics engineer",

    # Blockchain & Web3
    "blockchain developer", "blockchain engineer", "smart contract developer",
    "solidity developer", "web3 developer", "crypto developer",
    "defi developer",

    # Database & Architecture
    "database engineer", "database administrator", "dba",
    "sql developer", "database developer",
    "solutions architect", "software architect", "system architect",
    "enterprise architect", "cloud architect", "technical architect",

    # Support & Operations
    "technical support engineer", "support engineer", "it support",
    "systems administrator", "sysadmin", "it administrator",
    "helpdesk engineer", "technical consultant",

    # Emerging Tech
    "ar/vr developer", "xr developer", "metaverse developer",
    "quantum computing engineer", "edge computing engineer",
]
