"""Delete ALL tables and create them again (empty).

Use it once after switching to this version, because the old tables had fewer columns.
Run:  python reset_db.py        (it asks you to type YES first)
It works on whatever database your .env points to (local MySQL or Aiven).
"""
from app import app
from extensions import db

with app.app_context():
    target = app.config["SQLALCHEMY_DATABASE_URI"]
    host = getattr(target, "host", None) or str(target)
    print(f"This will DELETE every table in database on: {host}")
    if input("Type YES to continue: ").strip() != "YES":
        raise SystemExit("Cancelled. Nothing was changed.")
    db.session.remove()
    db.drop_all()
    # old tables from the first version of the project may still exist
    from sqlalchemy import text
    for table in ("clicks", "urls", "campaigns", "blocked_domains", "users"):
        db.session.execute(text(f"DROP TABLE IF EXISTS {table}"))
    db.session.commit()
    db.create_all()
    print("Done. Tables created fresh:", ", ".join(sorted(db.metadata.tables)))
