import json
import os
import requests

from flask import Flask, session, render_template, request, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    if session.get("Books") is not None:
        uid = session.get("Books")
        user_id = db.execute(f"select id from users where id = :id", {"id": uid}).first()
        if user_id is not None:
            return render_template("search.html")
    return render_template("log-in.html")


@app.route("/sign_in")
def sign_in():
    return render_template("sign-up.html")


@app.route("/register", methods=["Post"])
def register():
    name = request.form.get("inputEmail")
    password = request.form.get("inputPassword")
    cnfpassword = request.form.get("confirmPassword")
    if password == cnfpassword:
        username = db.execute(f"select * from users where username = :name", {"name": name.lower()}).first()
        if not username:
            db.execute(f"insert into users values(DEFAULT, :name, :password)", {"name": name, "password": password})
            db.commit()
            return render_template("Log-in.html")
        else:
            return render_template("sign-up.html", note="*Username already exists")
    else:
        return render_template("sign-up.html", note="*Password does not match")


@app.route("/log_in", methods=["Post"])
def log_in():
    name = request.form.get("inputEmail")
    password = request.form.get("inputPassword")
    user_id = db.execute(f"select id from users where username = :name and password = :password",
                         {"name": name.lower(), "password": password}).fetchone()
    if not user_id:
        return render_template("log-in.html", note="*username or password not found")
    else:
        session["Books"] = user_id.id
        return render_template("search.html")


@app.route("/log_out")
def log_out():
    session.pop('Books')
    return redirect(url_for('index'))


@app.route("/search", methods=["Get"])
def search():
    value = request.args.get("book_search")
    books = db.execute(f"select * from books where isbn like :value or title like :value or author like :value",
                       {"value": f"%{value}%"}).fetchall()
    return render_template("result.html", books=books)


@app.route("/book/<isbn>")
def book(isbn):
    book_detail = db.execute(f"select * from books where isbn = :isbn", {"isbn": isbn}).fetchone()
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "raTcfoXVOEQXvehClbv8xg", "isbns": book_detail.isbn})
    if res.status_code == 200:
        jsonresult = res.json()
        g_rating = f'Average rating : {jsonresult["books"][0]["average_rating"]}, Work rating : {jsonresult["books"][0]["work_ratings_count"]}'
    else:
        g_rating = "No rating found"
    reviews = db.execute(f"select * from reviews where isbn = :isbn", {"isbn": isbn}).fetchall()
    allow_review = "true"
    nreviews = []
    for review in reviews:
        username = db.execute(f"select username from users where id = :id", {"id": review.userid}).fetchone()[0]
        if review.userid == session.get("Books") and review.isbn == isbn:
            allow_review = "false"
            username = "You"
        else:
            for i in range(8):
                username = username[:i] + 'x' + username[i + 1:]
        temprow = {"username": username, "rating": review.rating, "review": review.review}
        nreviews.append(temprow)
    return render_template("book.html", book=book_detail, g_rating=g_rating, allow_review=allow_review, reviews=nreviews)


@app.route("/review_submit<isbn>", methods=["Post"])
def review_submit(isbn):
    rating = request.form.get("rating")
    review = request.form.get("review")
    db.execute(f"insert into reviews values (:userid, :isbn, :rating, :review )",
               dict(userid=session.get("Books"), isbn=isbn, rating=rating, review=review))
    db.commit()
    return redirect(url_for('book', isbn=isbn))


@app.route("/api/<isbn>")
def api(isbn):
    book_detail = db.execute(f"select * from books where isbn = :isbn", {"isbn": isbn}).fetchone()
    review_count = db.execute(f"select count(review) from reviews where isbn = :isbn", {"isbn": isbn}).fetchone()[0]
    average_score = db.execute(f"select avg(rating) from reviews where isbn = :isbn", {"isbn": isbn}).fetchone()[0]
    if book_detail is not None:
        api_result = {"title": book_detail.title,
                      "author": book_detail.author,
                      "year": book_detail.years,
                      "isbn": book_detail.isbn,
                      "review_count": review_count,
                      "average_score": float(average_score)}

        return json.dumps(api_result), 200
    else:
        return "404 error", 404
