from db.mysql import engine
from db.models import Base

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Done!")