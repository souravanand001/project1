import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


def main():
    f = open("books.csv")
    cont = 1
    reader = csv.reader(f)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, years) VALUES (:isbn, :title, :author, :years)",
                   {"isbn": isbn, "title": title, "author": author, "years": year})
        print(cont)
        cont += 1
    db.commit()


if __name__ == "__main__":
    main()
