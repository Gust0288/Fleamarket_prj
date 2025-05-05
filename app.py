from flask import Flask, render_template, session, request, redirect, url_for
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import x
import time
import uuid
import os
import json
import requests
import languages

app = Flask(__name__)

from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)




##############################
@app.context_processor
def utility_processor():
    """Add utility functions to template context"""
    lan = get_language()
    return {
        'getattr': getattr,
        'lan': get_language(),  # This will ensure lan is always available
        'languages': languages,
        'placeholder_search': getattr(languages, f"{lan}_search", "Search")
    }
##############################
@app.get("/rates")
def get_rates():
    try:
        data = requests.get("https://api.exchangerate-api.com/v4/latest/usd")
        ic(data.json())
        rates_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rates.txt")
        with open(rates_path, "w") as file:
            file.write(data.text)
        return data.json()
    except Exception as ex:
        ic(ex)
        return {"error": str(ex)}, 500
#############################
@app.template_filter('timestampToDate')
def timestamp_to_date(timestamp):
    if not timestamp:
        return "N/A"
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')

##############################
def get_language():
    """Get the user's preferred language from session or default to English"""
    languages_allowed = ["en", "dk"]
    
    # Try to get language from session
    lan = session.get("language", "en")
    
    # If invalid language, default to English
    if lan not in languages_allowed:
        lan = "en"
    
    return lan

# Function to set language in session
@app.get("/set-language/<lan>")
def set_language(lan):
    """Set the user's preferred language"""
    languages_allowed = ["en", "dk"]
    if lan not in languages_allowed:
        lan = "en"
    
    session["language"] = lan
    
    # Redirect back to the page they came from, or home if not available
    referrer = request.referrer or url_for("view_index")
    return redirect(referrer)
##############################
def load_rates():
    """Load currency exchange rates from rates.txt"""
    try:
        # Use os.path.join with the application's root directory
        rates_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rates.txt")
        with open(rates_path, "r") as file:
            rates_text = file.read()  # this is text that looks like json
        ic("Rates loaded successfully")
        # Convert the text rates to json
        rates = json.loads(rates_text)
        return rates
    except FileNotFoundError:
        ic("Rates file not found, returning empty rates")
        return {"rates": {"DKK": 7.0}}  # Default value if file is missing
    except json.JSONDecodeError as ex:
        ic(f"Error parsing rates JSON: {ex}")
        return {"rates": {"DKK": 7.0}}  # Default value if JSON is invalid
    except Exception as ex:
        ic(f"Unexpected error loading rates: {ex}")
        return {"rates": {"DKK": 7.0}}  # Default value for any other error


##############################
@app.after_request
def disable_cache(response):
    """
    This function automatically disables caching for all responses.
    It is applied after every request to the server.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response





##############################
@app.get("/")
def view_index():
    try:
        # Get the current language from session
        lan = get_language()
        
        db, cursor = x.db()
        q = "SELECT * FROM items WHERE item_blocked = 0 AND item_deleted_at = 0 ORDER BY item_created_at LIMIT 2"
        cursor.execute(q)
        items = cursor.fetchall()

        rates = load_rates()
        
        # Get language-specific text
        title = getattr(languages, f"{lan}_home", "Home")
        placeholder_search = getattr(languages, f"{lan}_search", "Search")

        return render_template("view_index.html", 
                              title=title, 
                              items=items, 
                              rates=rates, 
                              show_adress=True,
                              lan=lan,
                              languages=languages,
                              placeholder_search=placeholder_search)
    except Exception as ex:
        ic(ex)
        return "Error loading homepage", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/item")
def post_item():
    try:
        # Get the current language
        lan = get_language()
        
        # Define localized error messages
        name_required = getattr(languages, f"{lan}_item_name_required", "Item name is required")
        invalid_values = getattr(languages, f"{lan}_invalid_price_coords", "Invalid price or coordinates")
        image_required = getattr(languages, f"{lan}_image_required", "At least one image is required")
        max_files_error = getattr(languages, f"{lan}_max_files_error", "Cannot upload more than 5 files")
        invalid_extension_error = getattr(languages, f"{lan}_invalid_extension_error", "File extension not allowed")
        file_too_large_error = getattr(languages, f"{lan}_file_too_large_error", "File too large")
        system_error = getattr(languages, f"{lan}_system_error", "System under maintenance")
        item_created_message = getattr(languages, f"{lan}_item_created_message", "Fleamarket Created, Reload page to see it")

        # Validate user is logged in
        user = x.validate_user_logged()

        #form validation
        validated_data = x.validate_post_item_form()
        
        # Get item form data
        # Extract validated fields
        name = validated_data["name"]
        price = validated_data["price"]
        lon = validated_data["lon"]
        lat = validated_data["lat"]
        images_names = validated_data["images"]
        
        # Basic validation
        if not name:
            return name_required, 400
        
        try:
            price = int(price)
            lon = float(lon)
            lat = float(lat)
        except ValueError:
            return invalid_values, 400
        
        # Process images upload
        # images_names = x.validate_item_images()
        # if not images_names:
        #     return image_required, 400
            
        db, cursor = x.db()
        
        # Generate a unique item_pk
        item_pk = uuid.uuid4().hex
        item_created_at = int(time.time())
        
        # Create item record with the first image as the main image
        item_image = images_names[0]
        
        # Insert the item with reference to the logged-in user
        q = """INSERT INTO items 
               (item_pk, item_name, item_image, item_price, item_lon, item_lat, 
                item_created_at, item_blocked, item_user_fk) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
               
        cursor.execute(q, (
            item_pk, name, item_image, price, lon, lat,
            item_created_at, 0, user["user_pk"]
        ))
        
        # Link all uploaded images to the item (stores in images table)
        values = ""
        images = []
        for image_name in images_names:
            image_pk = uuid.uuid4().hex
            img = {"image_pk": image_pk, "image_name": image_name}
            images.append(img)
            # Use item_pk for the image_item_fk column
            values = f"{values}('{image_pk}', '{item_pk}', '{image_name}'),"
        
        if values:
            values = values.rstrip(",")
            q = f"INSERT INTO images (image_pk, image_item_fk, image_name) VALUES {values}"
            cursor.execute(q)
        
        db.commit()
        
        # Generate HTML for uploaded images
        html = ""
        for img in images:
            html += f"""
                <div id="x{img["image_pk"]}">
                    <h3>New Fleamarket created!</h3>
                    <img src="/static/uploads/{img["image_name"]}" style="width: 5rem; height: 5rem;">
                    <button mix-delete="/images/{img["image_pk"]}">
                        Delete
                    </button>
                </div>
            """
        
        
        return f'<mixhtml mix-update="#posted">{item_created_message}</mixhtml>'
    except Exception as ex:
        ic(ex)

        if str(ex) == "company_ex item_name":
            return f'<mixhtml mix-update="#post-item-error">{name_required}</mixhtml>', 400

        if "company_ex at least one file" in str(ex):
            return f'<mixhtml mix-update="#post-item-error">{image_required}</mixhtml>', 400

        if "company_ex max 5 files" in str(ex):
            return f'<mixhtml mix-update="#post-item-error">{max_files_error}</mixhtml>', 400

        if "company_ex file extension not allowed" in str(ex):
            return f'<mixhtml mix-update="#post-item-error">{invalid_extension_error}</mixhtml>', 400

        if "company_ex file too large" in str(ex):
            return f'<mixhtml mix-update="#post-item-error">{file_too_large_error}</mixhtml>', 400

        if "company_ex item_price" in str(ex):
            return f'<mixhtml mix-update="#post-item-error">{invalid_values}</mixhtml>', 400

        if "company_ex item_coordinates" in str(ex):
            return f'<mixhtml mix-update="#post-item-error">{invalid_values}</mixhtml>', 400

        if "db" in locals():
            db.rollback()

        return f'<mixhtml mix-update="#post-item-error">{system_error}</mixhtml>', 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/items/<item_pk>")
def get_item_by_pk(item_pk):
    try:
        lan = get_language()
        db, cursor = x.db()
        q = "SELECT * FROM items WHERE item_pk = %s AND item_blocked = 0 AND item_deleted_at = 0"
        cursor.execute(q, (item_pk,))
        item = cursor.fetchone()

        rates = load_rates()

        show_address = request.args.get('show_address', 'true').lower() == 'true'

        html_item = render_template("_item.html", item=item, rates=rates, is_profile_view=False, lan=lan, languages=languages, show_address=show_address)
        return f"""
            <mixhtml mix-replace="#item">
                {html_item}
            </mixhtml>
        """
    except Exception as ex:
        ic(ex)
        lan = get_language()
        
        if "company_ex page number" in str(ex):
            error_message = getattr(languages, f"{lan}_invalid_page", "Page number invalid")
            return f"""
                <mixhtml mix-top="body">
                    {error_message}
                </mixhtml>
            """
            
        # worst case, we cannot control exceptions
        error_message = getattr(languages, f"{lan}_general_error", "An error occurred")
        return f"""
            <mixhtml mix-top="body">
                {error_message}
            </mixhtml>
        """
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
##############################
@app.get("/items/user/<item_user_fk>")
def get_item_by_user(item_user_fk):
    try:
        # First validate that the logged-in user is requesting their own items
        user = x.validate_user_logged()
        
        lan = get_language()
        # Check if the requested user_fk matches the logged-in user's pk
        if str(user["user_pk"]) != str(item_user_fk):
            error_message = getattr(languages, f"{lan}_no_permission", "You don't have permission to view these items")
            return f"""
                <mixhtml mix-top="body">
                    {error_message}
                </mixhtml>
            """, 403
        
        # Now fetch the items for this user
        db, cursor = x.db()
        q = "SELECT * FROM items WHERE item_user_fk = %s AND item_blocked = 0 AND item_deleted_at = 0"
        cursor.execute(q, (item_user_fk,))
        items = cursor.fetchall()  # Get all items

        # If no items found for this user
        if not items:
            no_items_message = getattr(languages, f"{lan}_no_items_yet", "You haven't created any items yet.")
            return f"""
                <mixhtml mix-replace="#user_items">
                    <p>{no_items_message}</p>
                </mixhtml>
            """

        rates = load_rates()

        # Generate HTML for all items
        items_html = ""
        for item in items:
            items_html += render_template("_item.html", item=item, rates=rates, is_profile_view=True, lan=lan, languages=languages, show_address=False)

        return f"""
            <mixhtml mix-replace="#user_items">
                {items_html}
            </mixhtml>
        """
    except Exception as ex:
        ic(ex)
        lan = get_language()
        
        if "compay_ex user not logged" in str(ex):
            login_required_message = getattr(languages, f"{lan}_login_required", "Please log in to view your items")
            return f"""
                <mixhtml mix-redirect="/login">
                    {login_required_message}
                </mixhtml>
            """
            
        error_load_message = getattr(languages, f"{lan}_error_loading_items", "Error loading your items")
        return f"""
            <mixhtml mix-top="body">
                {error_load_message}
            </mixhtml>
        """
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()




##############################
@app.get("/items/page/<page_number>")
def get_items_by_page(page_number):
    try:
        lan = get_language()
        page_number = x.validate_page_number(page_number)
        items_per_page = 2
        offset = (page_number-1) * items_per_page
        extra_item = items_per_page + 1
        db, cursor = x.db()
        q = "SELECT * FROM items WHERE item_blocked = 0 AND item_deleted_at = 0 ORDER BY item_created_at LIMIT %s OFFSET %s"
        cursor.execute(q, (extra_item, offset))
        items = cursor.fetchall()
        html = ""
        
        rates = load_rates()

        for item in items[:items_per_page]:
            i = render_template("_item_mini.html", item=item, rates=rates)
            html += i
        button = render_template("_button_more_items.html", page_number=page_number + 1, lan=lan ,languages=languages)
        if len(items) < extra_item: button = ""
        return f"""
            <mixhtml mix-bottom="#items">
                {html}
            </mixhtml>
            <mixhtml mix-replace="#button_more_items">
                {button}
            </mixhtml>
            <mixhtml mix-function="add_markers_to_map">
                {json.dumps(items[:items_per_page])}
            </mixhtml>            
        """
    except Exception as ex:
        ic(ex)
        if "company_ex page number" in str(ex):
            return """
                <mixhtml mix-top="body">
                    page number invalid
                </mixhtml>
            """
        # worst case, we cannot control exceptions
        return """
            <mixhtml mix-top="body">
                ups
            </mixhtml>
        """
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
##############################
@app.post("/items/edit")
def edit_item():
    try:
        # Validate user is logged in
        user = x.validate_user_logged()

        lan = get_language()
        
        # Get item data from form
        item_pk = request.form.get("item_pk", "").strip()
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "0").strip()
        lon = request.form.get("lon", "0").strip()
        lat = request.form.get("lat", "0").strip()

         # Basic validation with localized error messages
        required_fields_message = getattr(languages, f"{lan}_required_fields_missing", "Item ID and name are required")
        invalid_values_message = getattr(languages, f"{lan}_invalid_price_coords", "Invalid price or coordinates")
        
        
        # Basic validation
        if not item_pk or not name:
            return required_fields_message, 400
        
        try:
            price = int(price)
            lon = float(lon)
            lat = float(lat)
        except ValueError:
            return invalid_values_message, 400
            
        db, cursor = x.db()
        
        # First verify this item belongs to the current user
        q = "SELECT * FROM items WHERE item_pk = %s AND item_user_fk = %s"
        cursor.execute(q, (item_pk, user["user_pk"]))
        item = cursor.fetchone()

        permission_denied_message = getattr(languages, f"{lan}_item_permission_denied", "Item not found or you don't have permission to edit it")
        
        
        if not item:
            return "Item not found or you don't have permission to edit it", 403
        
        # Process new images if provided
        new_image = item["item_image"]  # Default to current image
        if 'files' in request.files and request.files['files'].filename:
            images_names = x.validate_item_images()
            if images_names:
                new_image = images_names[0]  # Use the first new image as the main image
                
                # Add any new images to the images table
                values = ""
                for image_name in images_names:
                    image_pk = uuid.uuid4().hex
                    values = f"{values}('{image_pk}', '{item_pk}', '{image_name}'),"
                
                if values:
                    values = values.rstrip(",")
                    q = f"INSERT INTO images (image_pk, image_item_fk, image_name) VALUES {values}"
                    cursor.execute(q)
        
        # Add current timestamp for item_updated_at
        item_updated_at = int(time.time())
        
        # Update the item with new information including the update timestamp
        q = """UPDATE items 
                SET item_name = %s, item_price = %s, item_lon = %s, item_lat =    %s, item_image = %s, item_updated_at = %s
                WHERE item_pk = %s AND item_user_fk = %s"""
        
        cursor.execute(q, (name, price, lon, lat, new_image, item_updated_at, item_pk, user["user_pk"]))

        update_failed_message = getattr(languages, f"{lan}_item_update_failed", "Failed to update item")
        
        
        if cursor.rowcount != 1:
            raise Exception(update_failed_message)
        
        db.commit()

        success_message = getattr(languages, f"{lan}_item_updated", "Item updated successfully!")
        
        
        return f"""
            <mixhtml mix-redirect="/profile">
                {success_message}
            </mixhtml>
        """
        
    except Exception as ex:
        ic(ex)
        lan = get_language()

        if "company_ex file extension not allowed" in str(ex):
            extension_error = getattr(languages, f"{lan}_file_extension_invalid", "File extension not allowed")
            return extension_error, 400
        
        if "company_ex file too large" in str(ex):
            size_error = getattr(languages, f"{lan}_file_too_large", "File too large")
            return size_error, 400
            
        if "db" in locals():
            db.rollback()
            
        return str(ex), 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.delete("/items/<item_pk>")
def delete_item(item_pk):
    try:
        # Validate user is logged in
        user = x.validate_user_logged()

        lan = get_language()
        
        db, cursor = x.db()
        
        # First verify this item belongs to the current user
        q = "SELECT * FROM items WHERE item_pk = %s AND item_user_fk = %s AND item_deleted_at = 0"
        cursor.execute(q, (item_pk, user["user_pk"]))
        item = cursor.fetchone()

        permission_denied_message = getattr(languages, f"{lan}_item_permission_denied", "Item not found or you don't have permission to delete it")
        
        
        if not item:
            return "Item not found or you don't have permission to delete it", 403
        
        # Soft delete the item (update item_deleted_at timestamp)
        current_time = int(time.time())
        q = "UPDATE items SET item_deleted_at = %s WHERE item_pk = %s AND item_user_fk = %s"
        cursor.execute(q, (current_time, item_pk, user["user_pk"]))

        delete_failed_message = getattr(languages, f"{lan}_item_delete_failed", "Failed to delete item")
        
        
        if cursor.rowcount != 1:
            raise Exception(delete_failed_message)
        
        db.commit()

        success_message = getattr(languages, f"{lan}_item_deleted", "Item deleted successfully!")
        
        
        return f"""
            <mixhtml mix-redirect="/profile">
               {success_message}
            </mixhtml>
        """
        
    except Exception as ex:
        ic(ex)
        if "db" in locals():
            db.rollback()
            
        return str(ex), 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/search")
def search():
    try:
        search_for = request.args.get("q", "") 
        # TODO: validate search_for
        db, cursor = x.db()
        q = "SELECT * FROM items WHERE item_name LIKE %s AND item_blocked = 0 AND item_deleted_at = 0"
        cursor.execute(q, (f"{search_for}%",))
        rows = cursor.fetchall()
        ic(rows)
        return rows # [{'item_name': 'aa1', 'item_pk': '193e055791ed4f...
    except Exception as ex:
        ic(ex)
        return "x", 400

##############################
def ___USER___(): pass

##############################
@app.get("/signup")
def show_signup():
    try:
        # Get the current language from session
        lan = get_language()
        
        # Define language-specific placeholders
        placeholders = {
            "username": getattr(languages, f"{lan}_user_username", "username"),
            "name": getattr(languages, f"{lan}_user_name", "name"),
            "last_name": getattr(languages, f"{lan}_user_last_name", "last name"),
            "email": getattr(languages, f"{lan}_user_email", "email"),
            "password": getattr(languages, f"{lan}_user_password", "password"),
            "button": getattr(languages, f"{lan}_signup_button", "Sign Up"),
        }

        active_signup = "active"
        error_message = request.args.get("error_message", "")
        return render_template("view_signup.html", 
                          title="Signup", 
                          active_signup=active_signup, 
                          error_message=error_message,
                          old_values={},
                          languages=languages,
                          lan=lan,
                          placeholders=placeholders)
    except Exception as ex:
        ic(ex)
        return redirect(url_for("view_index"))

##############################
@app.post("/signup")
def signup():
    try:
        # Get the current language from session
        lan = get_language()
        
        # Get translations for error messages
        username_invalid = getattr(languages, f"{lan}_user_username_invalid", "Invalid username")
        name_invalid = getattr(languages, f"{lan}_user_name_invalid", "Invalid name")
        last_name_invalid = getattr(languages, f"{lan}_user_last_name_invalid", "Invalid last name")
        email_invalid = getattr(languages, f"{lan}_user_email_invalid", "Invalid email")
        password_invalid = getattr(languages, f"{lan}_user_password_invalid", "Invalid password")
        email_exists = getattr(languages, f"{lan}_user_email_exists", "Email already exists")
        #TODO add
        username_exists = getattr(languages, f"{lan}_user_username_exists", "Username already exists")
        system_error = getattr(languages, f"{lan}_system_error", "System under maintenance")
        
        user_username = x.validate_user_username()
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email = x.validate_user_email()
        user_password = x.validate_user_password()
        hashed_password = generate_password_hash(user_password)
        
        user_verification_key = str(uuid.uuid4())
        user_created_at = int(time.time())

        db, cursor = x.db()
        check_query = "SELECT user_email FROM users WHERE user_email = %s AND user_deleted_at = 0"
        cursor.execute(check_query, (user_email,))
        if cursor.fetchone():
            raise Exception("company_ex duplicate_email")

        q = """INSERT INTO users 
        (user_pk, user_username, user_name, user_last_name, user_email, 
        user_password, user_verification_key, user_created_at, user_updated_at, user_deleted_at,
        user_is_admin, user_blocked) 
        VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""

        cursor.execute(q, (user_username, user_name, user_last_name, user_email, hashed_password, user_verification_key, user_created_at, 0, 0, 0, 0))

        if cursor.rowcount != 1: raise Exception("System under maintenance")

        db.commit()
        x.send_email(user_name, user_last_name, user_verification_key)
        
        # Success message in selected language
        success_msg = getattr(languages, f"{lan}_user_success", "User successfully created")
        return redirect(url_for("show_login", message=success_msg))
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        old_values = request.form.to_dict()
        error_message = str(ex)
        
        # Get the current language from session
        lan = get_language()
        
        # Define placeholders for form fields
        placeholders = {
            "username": getattr(languages, f"{lan}_user_username", "username"),
            "name": getattr(languages, f"{lan}_user_name", "name"),
            "last_name": getattr(languages, f"{lan}_user_last_name", "last name"),
            "email": getattr(languages, f"{lan}_user_email", "email"),
            "password": getattr(languages, f"{lan}_user_password", "password"),
            "button": getattr(languages, f"{lan}_signup_button", "Sign Up"),
        }
        
        # Handle specific validation errors
        if "company_ex user_username" in error_message:
            old_values.pop("user_username", None)
            return render_template("view_signup.html",                                   
                error_message=username_invalid, 
                old_values=old_values, 
                user_username_error="input_error", 
                lan=lan, 
                placeholders=placeholders,
                languages=languages)
        
        elif "company_ex user_name" in error_message:
            old_values.pop("user_name", None)
            return render_template("view_signup.html",
                error_message=name_invalid, 
                old_values=old_values, 
                user_name_error="input_error", 
                lan=lan, 
                placeholders=placeholders,
                languages=languages)
        
        elif "company_ex user_last_name" in error_message or "last name" in error_message:
            old_values.pop("user_last_name", None)
            return render_template("view_signup.html",
                error_message=last_name_invalid, 
                old_values=old_values, 
                user_last_name_error="input_error", 
                lan=lan, 
                placeholders=placeholders,
                languages=languages)
        
        elif "company_ex email" in error_message:
            old_values.pop("user_email", None)
            return render_template("view_signup.html",
                error_message=email_invalid, 
                old_values=old_values, 
                user_email_error="input_error", 
                lan=lan, 
                placeholders=placeholders,
                languages=languages)
        
        elif "company_ex duplicate_email" in error_message:
            old_values.pop("user_email", None)
            return render_template("view_signup.html",
                error_message=email_exists, 
                old_values=old_values, 
                user_email_error="input_error", 
                lan=lan, 
                placeholders=placeholders,
                languages=languages)
            
        elif "password" in error_message:
            old_values.pop("user_password", None)
            return render_template("view_signup.html",
                error_message=password_invalid, 
                old_values=old_values, 
                user_password_error="input_error", 
                lan=lan, 
                placeholders=placeholders,
                languages=languages)
        
        else:
            # Generic error handler
            return render_template("view_signup.html",
                error_message=system_error, 
                old_values=old_values, 
                lan=lan, 
                placeholders=placeholders,
                languages=languages)
                
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/login")
def show_login():
    try:
        # Get the current language from session
        lan = get_language()
        
        # Define language-specific placeholders
        placeholders = {
            "email": getattr(languages, f"{lan}_user_email", "email"),
            "password": getattr(languages, f"{lan}_user_password", "password"),
            "button": getattr(languages, f"{lan}_login_button", "Log In"),
            "forgot_password": getattr(languages, f"{lan}_forgot_password", "Forgot password?")
        }
        
        active_login = "active"
        message = request.args.get("message", "")
        
        # Get title in the current language
        title = getattr(languages, f"{lan}_login_button", "Login")
        
        return render_template("view_login.html", 
                              title=title, 
                              active_login=active_login, 
                              message=message, 
                              lan=lan, 
                              languages=languages,
                              placeholders=placeholders)
    except Exception as ex:
        ic(ex)
        return redirect(url_for("view_index"))
##############################
@app.post("/login")
def login():
    try:
        # Get the current language from session
        lan = get_language()
        
        # Get translations for error messages
        invalid_credentials = getattr(languages, f"{lan}_login_invalid_credentials", "Invalid email or password")
        account_not_verified = getattr(languages, f"{lan}_login_account_not_verified", "Please verify your email before logging in")
        account_blocked = getattr(languages, f"{lan}_login_account_blocked", "Your account has been blocked. Please contact support")
        email_empty = getattr(languages, f"{lan}_email_empty", "Email cannot be empty")
        email_invalid = getattr(languages, f"{lan}_email_invalid", "Invalid email format")
        

        
        user_email = x.validate_user_email()
        user_password = x.validate_user_password()

        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()

        if not user:
            raise Exception(invalid_credentials)

        if not check_password_hash(user["user_password"], user_password):
            raise Exception(invalid_credentials)
        
        if user["user_verified_at"] == 0:
            raise Exception(account_not_verified)
        
        if user.get("user_blocked", 0) == 1:
            raise Exception(account_blocked)
        
        session["user"] = user
        session["is_admin"] = bool(user.get("user_is_admin", 0))

        return redirect(url_for("profile"))
    except Exception as ex:
        ic(ex)

        if str(ex) == "company_ex email_empty":
            return redirect(url_for("show_login", message=email_empty))
        if str(ex) == "company_ex email_invalid":
            return redirect(url_for("show_login", message=email_invalid))
        
        # Check if the exception is one of our known errors
        if str(ex) in [invalid_credentials, account_not_verified, account_blocked]:
            return redirect(url_for("show_login", message=str(ex)))
        
        # For unknown errors
        error_message = getattr(languages, f"{lan}_login_failed", "Login failed")
        return redirect(url_for("show_login", message=f"{error_message}: {str(ex)}"))
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/verify/<verification_key>")
def verify_user(verification_key):
    try:

        db, cursor = x.db()

        q = "SELECT * FROM users WHERE user_verification_key = %s"

        cursor.execute(q ,(verification_key,)) 
        user = cursor.fetchone()

        if not user:
            return "Invalid verification key or user not found", 400
        
        if user.get("user_verified_at", 0) > 0:
            return "Account already verified", 200
        
        current_time = int(time.time())
        q = "UPDATE users SET user_verified_at = %s WHERE user_verification_key = %s"
        cursor.execute(q, (current_time, verification_key))

        db.commit()
        return "Account succefully Verified"

        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return f"Verification failed: {str(ex)}", 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/logout")
def logout():
    try:
        # Clear the user from session
        session.pop('user', None)
        return redirect(url_for('login'))
    except Exception as ex:
        ic(ex)
        return redirect(url_for('profile'))
##############################
@app.get("/profile")
def profile():
    try:
        lan = get_language()

        
        is_session = False
        if session["user"]: is_session = True  
        active_profile = "active"      


        title = getattr(languages, f"{lan}_profile_title", "Profile")
        error_default = getattr(languages, f"{lan}_error_occurred", "An error occurred")
        

        return render_template("view_profile.html", title="Profile", user=session["user"], is_session=is_session, active_profile=active_profile,
                               lan=lan,
                               languages=languages,
                               error_default=error_default,
                               show_address=False)
    
    except Exception as ex:
        ic(ex)
        return redirect(url_for("show_login"))
##############################
##############################
@app.get("/edit-profile")
def show_edit_profile():
    try:
        lan = get_language()
        
        title = getattr(languages, f"{lan}_edit_profile", "Edit Profile")

        if not session.get("user"):
            return redirect(url_for("show_login"))
            
        return render_template(
            "view_edit_profile.html", 
            title="Edit Profile", 
            user=session["user"],
            error_message="",
            old_values = {},
            lan=lan,
            languages=languages
        )
    except Exception as ex:
        ic(ex)
        return redirect(url_for("profile"))

##############################
@app.post("/edit-profile")
def edit_profile():
    try:
        lan = get_language()

        if not session.get("user"):
            return redirect(url_for("show_login"))
            
        user_pk = session["user"]["user_pk"]

    
        name_invalid = getattr(languages, f"{lan}_user_name_invalid", "Invalid name")
        last_name_invalid = getattr(languages, f"{lan}_user_last_name_invalid", "Invalid last name")
        email_invalid = getattr(languages, f"{lan}_user_email_invalid", "Invalid email")
        email_exists = getattr(languages, f"{lan}_user_email_exists", "Email already in use by another account")
        #TODO add <<<>>>>
        update_failed = getattr(languages, f"{lan}_profile_update_failed", "Failed to update profile")
        update_success = getattr(languages, f"{lan}_profile_update_success", "Profile updated successfully")
       
       
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email = x.validate_user_email()
        
       
        db, cursor = x.db()
        
        # Check if email is already taken by another user
        if user_email != session["user"]["user_email"]:
            q = "SELECT * FROM users WHERE user_email = %s AND user_pk != %s AND user_deleted_at = 0"
            cursor.execute(q, (user_email, user_pk))
            if cursor.fetchone():
                raise Exception("Email already in use by another account")
        
        # Update user information
        current_time = int(time.time())
        q = """UPDATE users 
               SET user_name = %s, 
                   user_last_name = %s, 
                   user_email = %s,
                   user_updated_at = %s 
               WHERE user_pk = %s"""
               
        cursor.execute(q, (user_name, user_last_name, user_email, current_time, user_pk))
        
        if cursor.rowcount != 1:
            raise Exception("Failed to update profile")
        
        db.commit()
        
        # Update session with new user information
        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        user = cursor.fetchone()
        session["user"] = user
        
        return redirect(url_for("profile", message="Profile updated successfully"))
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        old_values = request.form.to_dict()
        error_message = str(ex)

        title = getattr(languages, f"{lan}_edit_profile", "Edit Profile")
        
        if "company_ex user_name" in str(ex):
            return render_template("view_edit_profile.html", 
                title=title,
                error_message=name_invalid,
                user=session["user"],
                old_values=old_values,
                user_name_error="input_error",
                lan=lan,
                languages=languages)
                
        if "company_ex user_last_name" in str(ex) or "last name" in str(ex):
            return render_template("view_edit_profile.html", 
                title=title,
                error_message=last_name_invalid,
                user=session["user"],
                old_values=old_values,
                user_last_name_error="input_error",
                lan=lan,
                languages=languages)
                
        if "company_ex user_email" in str(ex):
            return render_template("view_edit_profile.html", 
                title=title,
                error_message=email_invalid,
                user=session["user"],
                old_values=old_values,
                user_email_error="input_error",
                lan=lan,
                languages=languages)
        
        if "company_ex duplicate_email" in str(ex):
            return render_template("view_edit_profile.html", 
                title=title,
                error_message=email_exists,
                user=session["user"],
                old_values=old_values,
                user_email_error="input_error",
                lan=lan,
                languages=languages)
        
        return render_template("view_edit_profile.html", 
            title=title,
            error_message=error_message,
            user=session["user"],
            old_values=old_values,
            lan=lan,
            languages=languages)
            
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
##############################  
@app.get("/forgot-password")
def show_forgot_password():
    try:
        lan = get_language()

        message = request.args.get("message", "")
        title = getattr(languages, f"{lan}_forgot_password", "Forgot Password")
        

        return render_template("view_forgot_password.html", title="Forgot Password", message=message, lan=lan, languages=languages)
    except Exception as ex:
        ic(ex)
        return redirect(url_for("view_index"))
##############################
@app.post("/forgot-password")
def forgot_password():
    try:
        lan = get_language()
        user_email = x.validate_user_email()
        
        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()
        
        success_message = getattr(languages, f"{lan}_password_reset_email_sent", "If your email is registered, you will receive a password reset link.")
        
        if not user:
            return redirect(url_for("show_forgot_password", message=success_message))
        
        # Generate a reset token
        reset_token = str(uuid.uuid4())
        
        # Store the token and its expiry time in the database
        current_time = int(time.time())
        expiry_time = current_time + (24 * 60 * 60)  # 24 hours from now
        
        q = "UPDATE users SET user_reset_token = %s, user_reset_token_expiry = %s WHERE user_pk = %s"
        cursor.execute(q, (reset_token, expiry_time, user["user_pk"]))
        
        if cursor.rowcount != 1:
            system_error = getattr(languages, f"{lan}_system_error", "System under maintenance")
            raise Exception(system_error)
        
        db.commit()
        
        # Send an email with the reset link
        x.send_reset_password_email(user["user_name"], user["user_last_name"], reset_token)
        
        return redirect(url_for("show_forgot_password", message=success_message))
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        error_message = getattr(languages, "en_error_occurred", "An error occurred")
        return redirect(url_for("show_forgot_password", message=f"{error_message}: {str(ex)}"))
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/reset-password/<reset_token>")
def show_reset_password(reset_token):
    try:
        lan = get_language()

        db, cursor = x.db()
        current_time = int(time.time())
        
        q = "SELECT * FROM users WHERE user_reset_token = %s AND user_reset_token_expiry > %s AND user_deleted_at = 0"
        cursor.execute(q, (reset_token, current_time))
        user = cursor.fetchone()
        
        if not user:
            invalid_token_message = getattr(languages, f"{lan}_password_reset_invalid_token", "Invalid or expired reset token")
            return invalid_token_message, 400
        
        return render_template("view_reset_password.html", title="Reset Password", reset_token=reset_token, lan=lan, languages=languages)
        
    except Exception as ex:
        ic(ex)
        lan = get_language()
        error_message = getattr(languages, f"{lan}_error_occurred", "An error occurred")
        return f"{error_message}: {str(ex)}", 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/reset-password/<reset_token>")
def reset_password(reset_token):
    try:
        lan = get_language()

        user_password = x.validate_user_password()
        
        db, cursor = x.db()
        current_time = int(time.time())
        
        # Check if token is valid and not expired
        q = "SELECT * FROM users WHERE user_reset_token = %s AND user_reset_token_expiry > %s AND user_deleted_at = 0"
        cursor.execute(q, (reset_token, current_time))
        user = cursor.fetchone()
        
        if not user:
            invalid_token_message = getattr(languages, f"{lan}_password_reset_invalid_token", "Invalid or expired reset token")
            return invalid_token_message, 400
        
        # Update the password
        hashed_password = generate_password_hash(user_password)
        
        # Clear the reset token and update the password
        q = "UPDATE users SET user_password = %s, user_reset_token = NULL, user_reset_token_expiry = NULL WHERE user_pk = %s"
        cursor.execute(q, (hashed_password, user["user_pk"]))
        
        if cursor.rowcount != 1:
            system_error = getattr(languages, f"{lan}_system_error", "System under maintenance")
            raise Exception(system_error)
        
        db.commit()
        
        success_message = getattr(languages, f"{lan}_password_reset_success", "Password reset successful. You can now login with your new password.")
        
        return redirect(url_for("show_login", message=success_message))
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        lan = get_language()
        error_message = getattr(languages, f"{lan}_error_occurred", "An error occurred")
        return f"{error_message}: {str(ex)}", 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.delete("/user")
def delete_user():
    try:
        lan = get_language()
        
        # Get translations for messages
        not_logged_in = getattr(languages, f"{lan}_user_not_logged_in", "User not logged in")
        password_required = getattr(languages, f"{lan}_delete_required_password", "Password is required to confirm deletion")
        incorrect_password = getattr(languages, f"{lan}_delete_incorrect_password", "Incorrect password")
        delete_success = getattr(languages, f"{lan}_delete_success", "Account deleted successfully") 
        email_sent = getattr(languages, f"{lan}_confirmation_email_sent", "A confirmation email has been sent")
        
        # Make sure user is logged in
        if not session.get("user"):
            return not_logged_in, 401
        
        user_pk = session["user"]["user_pk"]
        user_password = request.form.get("password", "")
        
        if not user_password:
            return f"""
                <div id="error-message">{password_required}</div>
            """
        
        # Connect to database
        db, cursor = x.db()
        
        # First verify the password
        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        user = cursor.fetchone()
        
        # Check if password matches
        if not check_password_hash(user["user_password"], user_password):
            return f"""
                <div id="error-message">{incorrect_password}</div>
            """
        
        # Store user info before deleting for email confirmation
        user_name = user["user_name"]
        user_email = user["user_email"]
        user_last_name = user["user_last_name"]
        
        # Soft delete the user (update user_deleted_at timestamp)
        current_time = int(time.time())
        q = "UPDATE users SET user_deleted_at = %s WHERE user_pk = %s"
        cursor.execute(q, (current_time, user_pk))
        
        if cursor.rowcount != 1:
            raise Exception("company_ex cannot delete user")
        
        db.commit()
        
        # Send confirmation email
        try:
            x.send_account_deletion_email(user_name, user_last_name, user_email)
        except Exception as email_ex:
            ic(f"Failed to send account deletion confirmation email: {email_ex}")
        
        session.pop("user")
        
        # Change this to make it clearer for the JS detection
        return f"""
            <mixhtml mix-redirect="/login?message={delete_success}">
                <div id="success-message">Account deleted successfully</div>
            </mixhtml>
        """
        
    except Exception as ex:
        ic(ex)     
        if "db" in locals(): db.rollback()  
        
        lan = get_language() if 'lan' not in locals() else lan
        
        if "company_ex cannot delete user" in str(ex):
            delete_unable = getattr(languages, f"{lan}_delete_unable", "Unable to delete your account")
            return f"""
                <div id="error-message">{delete_unable}</div>
            """        
        # worst case, we cannot control exceptions
        delete_error = getattr(languages, f"{lan}_delete_error", "An error occurred. Please try again later")
        return f"""
                <div id="error-message">{delete_error}</div>
        """
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
def ___ADMIN___(): pass
##############################
@app.get("/admin")
@x.admin_required
def admin_dashboard():
    try:
        lan = get_language()
        title = getattr(languages, f"{lan}_admin_dashboard", "Admin Dashboard")
        return render_template(
            "view_adminDashboard.html", 
            title=title, 
            user=session["user"],
            lan=lan,
            languages=languages
        )
    except Exception as ex:
        ic(ex)
        return redirect(url_for("view_index"))
##############################
@app.get("/admin/users")
@x.admin_required
def admin_users():
    try:
        lan = get_language()
        title = getattr(languages, f"{lan}_admin_manage_users", "Manage Users")
        
        db, cursor = x.db()
        q = """SELECT user_pk, user_name, user_last_name, user_email, 
               user_created_at, user_verified_at, user_is_admin, user_deleted_at, user_blocked 
               FROM users ORDER BY user_created_at DESC"""
        cursor.execute(q)
        users = cursor.fetchall()
        
        return render_template(
            "view_adminUsers.html", 
            title="Manage Users", 
            users=users, 
            user=session["user"],lan=lan,
            languages=languages
        )
    except Exception as ex:
        ic(ex)
        return redirect(url_for("admin_dashboard"))
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/admin/block-user/<user_pk>")
@x.admin_required
def block_user(user_pk):
    try:
        lan = get_language()
        db, cursor = x.db()
        

        q = "SELECT * FROM users WHERE user_pk = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_pk,))
        user = cursor.fetchone()
        
        if not user:
            raise Exception(getattr(languages, f"{lan}_user_not_found", "User not found or already deleted"))
        
        if user.get("user_is_admin", 0):
            raise Exception(getattr(languages, f"{lan}_cannot_block_admin", "Cannot block admin users"))
        
        

        q = "UPDATE users SET user_blocked = 1 WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        
        if cursor.rowcount != 1:
            raise Exception("Failed to block user")
        
        db.commit()
        
        try:
            x.send_blocked_email(
                user["user_name"], 
                user["user_last_name"], 
                user["user_email"]
            )
        except Exception as email_ex:
            ic(f"Failed to send block notification email: {email_ex}")
        
        
        success_message = getattr(languages, f"{lan}_admin_user_blocked", "User blocked successfully")
        return f"""
            <mixhtml mix-redirect="/admin/users">
                {success_message} and notification email sent.
            </mixhtml>
        """
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return f"Error: {str(ex)}", 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/admin/unblock-user/<user_pk>")
@x.admin_required
def unblock_user(user_pk):
    try:
        lan = get_language()
        db, cursor = x.db()
        
        
        q = "SELECT * FROM users WHERE user_pk = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_pk,))
        user = cursor.fetchone()
        
        if not user:
            raise Exception(getattr(languages, f"{lan}_user_not_found", "User not found or already deleted"))
        
        
        q = "UPDATE users SET user_blocked = 0 WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        
        if cursor.rowcount != 1:
            raise Exception(getattr(languages, f"{lan}_unblock_user_failed", "Failed to unblock user"))
        
        db.commit()
        

        try:
            x.send_unblocked_email(
                user["user_name"], 
                user["user_last_name"], 
                user["user_email"]
            )
        except Exception as email_ex:
            ic(f"Failed to send unblock notification email: {email_ex}")
        
        success_message = getattr(languages, f"{lan}_admin_user_unblocked", "User unblocked successfully")
        return f"""
            <mixhtml mix-redirect="/admin/users">
                {success_message} and notification email sent.
            </mixhtml>
        """
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return f"Error: {str(ex)}", 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
##############################
@app.get("/admin/items")
@x.admin_required
def admin_items():
    try:
        lan = get_language()
        title = getattr(languages, f"{lan}_admin_manage_items", "Manage Items")


        db, cursor = x.db()
        q = "SELECT * FROM items ORDER BY item_created_at DESC"
        cursor.execute(q)
        items = cursor.fetchall()

        rates = load_rates()
        
        return render_template(
            "view_adminItems.html", 
            title="Manage Items", 
            items=items, 
            user=session["user"],
            rates = rates,
            lan=lan,
            languages=languages
        )
    except Exception as ex:
        ic(ex)
        return redirect(url_for("admin_dashboard"))
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
##############################
@app.post("/admin/block-item/<item_pk>")
@x.admin_required
def block_item(item_pk):
    try:
        lan = get_language()
        db, cursor = x.db()
        
        # Check if the item exists
        q = "SELECT * FROM items WHERE item_pk = %s"
        cursor.execute(q, (item_pk,))
        item = cursor.fetchone()
        
        if not item:
            raise Exception(getattr(languages, f"{lan}_item_not_found", "Item not found"))
            
        # Get the item owner's information - use item_user_fk (the correct column name)
        if item["item_user_fk"]:  # Check if the user FK exists and is not empty
            q = "SELECT * FROM users WHERE user_pk = %s AND user_deleted_at = 0"
            cursor.execute(q, (item["item_user_fk"],))
            user = cursor.fetchone()
        else:
            user = None
            ic("No owner associated with this item")
        
        # Block the item
        q = "UPDATE items SET item_blocked = 1 WHERE item_pk = %s"
        cursor.execute(q, (item_pk,))
        
        if cursor.rowcount != 1:
            raise Exception(getattr(languages, f"{lan}_block_item_failed", "Failed to block item"))
        
        db.commit()
        
        # Send notification email if we have a valid user
        if user:
            try:
                x.send_item_blocked_email(
                    user["user_name"], 
                    user["user_last_name"], 
                    user["user_email"],
                    item["item_name"]
                )
                success_message = getattr(languages, f"{lan}_admin_item_blocked_email_sent", "Item blocked successfully and notification email sent to owner.")
                msg = success_message
            except Exception as email_ex:
                ic(f"Failed to send item block notification email: {email_ex}")
                fail_message = getattr(languages, f"{lan}_admin_item_blocked_email_fail", "Item blocked successfully but failed to send notification email.")
                msg = fail_message
        else:
            no_owner_message = getattr(languages, f"{lan}_admin_item_blocked_no_owner", "Item blocked successfully. No owner found to notify.")
            msg = no_owner_message
        
        return f"""
            <mixhtml mix-redirect="/admin/items">
                {msg}
            </mixhtml>
        """
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return f"Error: {str(ex)}", 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/admin/unblock-item/<item_pk>")
@x.admin_required
def unblock_item(item_pk):
    try:
        lan = get_language()
        db, cursor = x.db()
        
        # Check if the item exists
        q = "SELECT * FROM items WHERE item_pk = %s"
        cursor.execute(q, (item_pk,))
        item = cursor.fetchone()
        
        if not item:
            raise Exception(getattr(languages, f"{lan}_item_not_found", "Item not found"))
            
        # Get the item owner's information - use item_user_fk (the correct column name)
        if item["item_user_fk"]:  # Check if the user FK exists and is not empty
            q = "SELECT * FROM users WHERE user_pk = %s AND user_deleted_at = 0"
            cursor.execute(q, (item["item_user_fk"],))
            user = cursor.fetchone()
        else:
            user = None
            ic("No owner associated with this item")
        
        # Unblock the item
        q = "UPDATE items SET item_blocked = 0 WHERE item_pk = %s"
        cursor.execute(q, (item_pk,))
        
        if cursor.rowcount != 1:
            raise Exception(getattr(languages, f"{lan}_unblock_item_failed", "Failed to unblock item"))
        
        db.commit()
        
        
        # Send notification email if have a valid user
        if user:
            try:
                x.send_item_unblocked_email(
                    user["user_name"], 
                    user["user_last_name"], 
                    user["user_email"],
                    item["item_name"]
                )
                success_message = getattr(languages, f"{lan}_admin_item_unblocked_email_sent", "Item unblocked successfully and notification email sent to owner.")
                msg = success_message
            except Exception as email_ex:
                ic(f"Failed to send item unblock notification email: {email_ex}")
                fail_message = getattr(languages, f"{lan}_admin_item_unblocked_email_fail", "Item unblocked successfully but failed to send notification email.")
                msg = fail_message
        else:
            no_owner_message = getattr(languages, f"{lan}_admin_item_unblocked_no_owner", "Item unblocked successfully. No owner found to notify.")
            msg = no_owner_message
        
        return f"""
            <mixhtml mix-redirect="/admin/items">
                {msg}
            </mixhtml>
        """
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return f"Error: {str(ex)}", 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()