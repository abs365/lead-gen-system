import models
from database import engine, Base
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS prospect_signals CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS matches CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS demand_prospects CASCADE;"))
    conn.commit()

Base.metadata.create_all(bind=engine)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'demand_prospects'
        ORDER BY ordinal_position;
    """))
    cols = [row[0] for row in result]
    print(cols)