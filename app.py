from flask import Flask, redirect, render_template, request
from database import (
    delete_contact,
    delete_data,
    insert_data,
    search_contact_name,
    search_contact_number,
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


@app.route("/search", methods=["GET"])
def search_view():
    if request.method == "GET":
        search_by = request.args.get("search_by")
        search = request.args.get("search")
        if search_by == "name":
            data = search_contact_name(search)
            if len(data) == 0:
                return render_template("index.html")
            return render_template("index.html", contacts=data)
        elif search_by == "number":
            data = search_contact_number(search)
            if len(data) == 0:
                return render_template("index.html")
            return render_template("index.html", contacts=data)
        else:
            render_template("index.html")
    return render_template("index.html")


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
    if request.method == "POST":
        contact = select_Contact_data(id)
        if len(contact) == 0:
            return redirect("/")
        delete_contact(id)
        return redirect("/")
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
