"""Demo seed data — a believable slice of a team's context so judges can see
the graph light up immediately. A shared team project (atlas) with multiple
contributors, plus a personal project. Tuples are (project, type, author, text)."""

SEED = [
    # --- project: atlas — the shared TEAM brain, multiple contributors ---
    ("atlas", "decision", "Sourav",
     "We chose Postgres over MongoDB for Atlas because we need relational "
     "integrity for billing and the team already knows SQL."),
    ("atlas", "decision", "Karam",
     "Auth is handled with JWT plus refresh tokens stored in Redis; we dropped "
     "OAuth for the MVP to ship faster."),
    ("atlas", "decision", "Sourav",
     "The knowledge graph is built with Cognee and served through FastAPI. "
     "Frontend is vanilla JavaScript with D3 for the force graph."),
    ("atlas", "note", "Sripad",
     "Sarah owns the billing service and the Stripe webhook integration. "
     "Ping her before touching payment code."),
    ("atlas", "note", "Karam",
     "Deploys go through Docker to AWS. CI runs on every push; CD is manual "
     "for now behind a feature flag."),
    ("atlas", "code", "Sripad",
     "The embeddings use LanceDB locally and pgvector in production. Vector "
     "search is wrapped in memory.search()."),
    ("atlas", "fact", "Sourav",
     "Postgres connection pooling caps at 20; raising it caused Lambda cold "
     "starts to exhaust connections last month."),

    # --- project: personal ---
    ("personal", "note", "You",
     "Trip to Lisbon in September. Budget is 2000 dollars, staying in Alfama."),
    ("personal", "decision", "You",
     "Decided to learn Rust this quarter instead of Go — better fit for the "
     "audio project."),
    ("personal", "note", "You",
     "Mom's birthday is October 14. She likes gardening books and jazz."),
]


def load_into(engine):
    # seed_add populates the local graph only (cloud engines skip the network),
    # so demo data never triggers cognify cost/duplication on every restart.
    for project, mtype, author, text in SEED:
        engine.seed_add(text, type=mtype, project=project, author=author)
