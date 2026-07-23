from app.database import Base, engine
import app.models  # noqa: F401  imported so every model registers with Base.metadata


def main():
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully in MySQL.")
    for table in Base.metadata.sorted_tables:
        print(" -", table.name)


if __name__ == "__main__":
    main()