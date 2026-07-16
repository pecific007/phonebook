from flask import Flask, redirect, render_template, request
from database import (
    delete_contact,
    delete_data,
    insert_data,
    select_Contact_data,
    select_all,
    update_number,
    update_name,
)

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index_view():
    rows = select_all()
    return render_template("index.html", contacts=rows)


@app.route("/add", methods=["GET", "POST"])
def add_endpoint():
    if request.method == "POST":
        name = request.form.get("name")
        number = request.form.get("number")
        if not name or not number:
            return render_template(
                "index.html", error="Please fill out all the fields."
            )
        if len(number) != 10:
            return render_template("index.html", error="Invalid number.")
        insert_data(name, number)
        return redirect("/")
    else:
        return redirect("/")


@app.route("/delete", methods=["GET", "POST"])
def delete_all_endpoint():
    if request.method == "POST":
        delete_data()
        return redirect("/")
    else:
        return redirect("/")


@app.route("/delete/<int:id>", methods=["GET", "POST"])
def delete_one_endpoint(id):
    delete_contact(id)
    return redirect("/")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_endpoint(id):
    contacts = select_Contact_data(id)
    if request.method == "POST":
        name = request.form.get("name")
        number = request.form.get("number")
        if contacts[1] != name:
            update_name(id, name)
        if contacts[2] != number:
            update_number(id, number)
        return redirect("/")
    return render_template("edit.html", contact=contacts)
