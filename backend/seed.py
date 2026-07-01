"""Demo seed data — a believable slice of a team's context so judges can see
the graph light up immediately. Two projects: an AI product build + personal."""

SEED = [
    # --- project: atlas (an AI coding-agent memory story) ---
    ("atlas", "decision",
     "We chose Postgres over MongoDB for Atlas because we need relational "
     "integrity for billing and the team already knows SQL."),
    ("atlas", "decision",
     "Auth is handled with JWT plus refresh tokens stored in Redis; we dropped "
     "OAuth for the MVP to ship faster."),
    ("atlas", "decision",
     "The knowledge graph is built with Cognee and served through FastAPI. "
     "Frontend is vanilla JavaScript with D3 for the force graph."),
    ("atlas", "note",
     "Sarah owns the billing service and the Stripe webhook integration. "
     "Ping her before touching payment code."),
    ("atlas", "note",
     "Deploys go through Docker to AWS. CI runs on every push; CD is manual "
     "for now behind a feature flag."),
    ("atlas", "code",
     "The embeddings use LanceDB locally and pgvector in production. Vector "
     "search is wrapped in memory.search()."),
    ("atlas", "fact",
     "Postgres connection pooling caps at 20; raising it caused Lambda cold "
     "starts to exhaust connections last month."),

    # --- project: personal ---
    ("personal", "note",
     "Trip to Lisbon in September. Budget is 2000 dollars, staying in Alfama."),
    ("personal", "decision",
     "Decided to learn Rust this quarter instead of Go — better fit for the "
     "audio project."),
    ("personal", "note",
     "Mom's birthday is October 14. She likes gardening books and jazz."),
]


def load_into(engine):
    for project, mtype, text in SEED:
        engine.add(text, type=mtype, project=project)
