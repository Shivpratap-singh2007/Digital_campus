import sqlite3

con = sqlite3.connect('campusvoice.db')
cur = con.cursor()

tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
print(f"Total Tables: {len(tables)}")
print(f"Tables List: {tables}\n")

for t in tables:
    count = cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})").fetchall()]
    print(f"Table '{t}': {count} records | Columns ({len(cols)}): {', '.join(cols)}")

print("\n--- Users in DB ---")
for u in cur.execute("SELECT id, email, role, is_verified, is_synthetic_fixture FROM users").fetchall():
    print(f"  User #{u[0]}: email={u[1]}, role={u[2]}, verified={u[3]}, fixture={u[4]}")

