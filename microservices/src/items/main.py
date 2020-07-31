from flask import current_app, render_template, Flask,redirect, request, url_for, json, jsonify
# from flask_cors import CORS, cross_origin

# import pathlib
import firestore
import storage
import email_helper
from google.cloud import error_reporting


# itemData = 'items'


# itemsDataPath = itemData + "/items.json"

# file = pathlib.Path(itemsDataPath)
# if file.exists():
#     with open(itemsDataPath) as data:
#         getItemJSON = json.load(data)
# else:
#     getItemJSON=json.loads(data)


app = Flask(__name__)

# cors = CORS(app, resources={r"/foo": {"origins": "*"}})

@app.route("/")
def list_items():
    start_after = request.args.get('start_after', None)
    items, last_item_id = firestore.next_page(start_after=start_after)
    return render_template("item_list.html", items=items, last_item_id=last_item_id)


@app.route("/item/detail/<item_id>")
def item_detail(item_id):
    item = firestore.read(item_id)
    return jsonify(item)


@app.route("/items/add", methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        data["price"] = float(data.get("price", 100000))
        data["quantity"] = int(data.get("quantity", 0))
        # If an image was uploaded, update the data to point to the
        image_urls = storage.upload_image_files(request.files.getlist('images'))
        if image_urls:
            data['images'] = image_urls
        item = firestore.create(data)
        return redirect(url_for('.item_detail', item_id=item['id']))

    return render_template("item_entry_form.html", action='Add', item={})


@app.route("/confirm/<item_id>", methods=['GET', 'POST'])
def confirm_item(item_id):
    item = firestore.read(item_id)
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        email = data.get("email")
        if email is None:
            return render_template("confirm.html", error_message="Please enter a valid email")
        if email_helper.send_order_confirmation(email, item):
            firestore.update_inventory(item_id)
        user_data = {
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "email": data.get("email"),
        }
        user = firestore.create_user(user_data)
        order_data = {
            "item_id": item.get("id"),
            "user_id": user.get("id"),
            "units": int(data.get("units")),
        }
        firestore.create_order(order_data)
        return redirect(url_for('.list_items'))
    return render_template("confirm.html", item=item)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6001, debug=True)