from plibsqlite import Database, table, C


class Contact(table):
    id = table.Int(pk=True)
    name = table.Text(null=False)
    number = table.Text()


def db_manage(func):
    def wrapper(*args):
        db = Database("Contacts.db", check_same_thread=False)
        table.use(db)
        Contact.create()
        value = func(*args)
        db.close()
        return value

    return wrapper


@db_manage
def insert_data(name: str, number: str = ""):
    Contact.query().insert(name=name, number=number).exec()


@db_manage
def select_all():
    data = Contact.query().select("*").exec().fetchall()
    return data


@db_manage
def select_Contact_data(id):
    data = Contact.query().select("*").where(C("id", "=", id)).exec().fetchone()
    return data


@db_manage
def search_contact_name(term):
    data = (
        Contact.query()
        .select("*")
        .where(C("name", "LIKE", "%" + term + "%"))
        .exec()
        .fetchall()
    )
    return data


@db_manage
def search_contact_number(term):
    data = (
        Contact.query()
        .select("*")
        .where(C("number", "LIKE", "%" + term + "%"))
        .exec()
        .fetchall()
    )
    return data


@db_manage
def delete_data():
    Contact.query().delete().exec()


@db_manage
def delete_contact(id):
    Contact.query().delete().where(C("id", "=", id)).exec()


@db_manage
def update_name(id, name):
    Contact.query().update(name=name).where(C("id", "=", id)).exec()


@db_manage
def update_number(id, number):
    Contact.query().update(number=number).where(C("id", "=", id)).exec()
