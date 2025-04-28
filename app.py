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

app = Flask(__name__)

from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)




##############################
@app.get("/rates")
def get_rates():
    try:
        data = requests.get("https://api.exchangerate-api.com/v4/latest/usd")
        ic(data.json())
        with open("rates.txt", "w") as file:
            file.write(data.text)
        return data.json()
    except Exception as ex:
        ic(ex)
#############################
@app.template_filter('timestampToDate')
def timestamp_to_date(timestamp):
    if not timestamp:
        return "N/A"
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')


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
        db, cursor = x.db()
        q = "SELECT * FROM items WHERE item_blocked = 0 AND item_deleted_at = 0 ORDER BY item_created_at LIMIT 2"
        cursor.execute(q)
        items = cursor.fetchall()

        rates = x.load_rates()

        return render_template("view_index.html", title="Company", items=items, rates=rates)
    except Exception as ex:
        ic(ex)
        return "ups"
    finally:
        pass

##############################
@app.post("/item")
def post_item():
    try:
        # Validate user is logged in
        user = x.validate_user_logged()
        
        # Get item form data
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "0").strip()
        lon = request.form.get("lon", "0").strip()
        lat = request.form.get("lat", "0").strip()
        
        # Basic validation
        if not name:
            return "Item name is required", 400
        
        try:
            price = int(price)
            lon = float(lon)
            lat = float(lat)
        except ValueError:
            return "Invalid price or coordinates", 400
        
        # Process images upload
        images_names = x.validate_item_images()
        if not images_names:
            return "At least one image is required", 400
            
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
        
        # Return success message with image previews
        return f"""
            <mixhtml mix-top="#images">
                {html}
            </mixhtml>
            <mixhtml mix-top="main">
                Item created successfully!
            </mixhtml>
        """
        
    except Exception as ex:
        ic(ex)

        if "company_ex at least one file" in str(ex):
            return "Upload at least 1 file", 400        

        if "company_ex max 5 files" in str(ex):
            return "Cannot upload more than 5 files", 400
                
        if "company_ex file extension not allowed" in str(ex):
            return "File extension not allowed", 400
        
        if "company_ex file too large" in str(ex):
            return "File too large", 400

        if "db" in locals():
            db.rollback()
            
        return str(ex), 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/items/<item_pk>")
def get_item_by_pk(item_pk):
    try:
        db, cursor = x.db()
        q = "SELECT * FROM items WHERE item_pk = %s AND item_blocked = 0 AND item_deleted_at = 0"
        cursor.execute(q, (item_pk,))
        item = cursor.fetchone()

        rates= ""
        with open("rates.txt", "r") as file:
            rates = file.read() # this is text that looks like json
            rates = json.loads(rates)

        html_item = render_template("_item.html", item=item, rates=rates, is_profile_view=False)
        return f"""
            <mixhtml mix-replace="#item">
                {html_item}
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
@app.get("/items/user/<item_user_fk>")
def get_item_by_user(item_user_fk):
    try:
        # First validate that the logged-in user is requesting their own items
        user = x.validate_user_logged()
        
        # Check if the requested user_fk matches the logged-in user's pk
        if str(user["user_pk"]) != str(item_user_fk):
            return """
                <mixhtml mix-top="body">
                    You don't have permission to view these items
                </mixhtml>
            """, 403
        
        # Now fetch the items for this user
        db, cursor = x.db()
        q = "SELECT * FROM items WHERE item_user_fk = %s AND item_blocked = 0 AND item_deleted_at = 0"
        cursor.execute(q, (item_user_fk,))
        items = cursor.fetchall()  # Get all items

        # If no items found for this user
        if not items:
            return f"""
                <mixhtml mix-replace="#user_items">
                    <p>You haven't created any items yet.</p>
                </mixhtml>
            """

        rates = x.load_rates()

        # Generate HTML for all items
        items_html = ""
        for item in items:
            items_html += render_template("_item.html", item=item, rates=rates, is_profile_view=True)

        return f"""
            <mixhtml mix-replace="#user_items">
                {items_html}
            </mixhtml>
        """
    except Exception as ex:
        ic(ex)
        if "compay_ex user not logged" in str(ex):
            return """
                <mixhtml mix-redirect="/login">
                    Please log in to view your items
                </mixhtml>
            """
        return """
            <mixhtml mix-top="body">
                Error loading your items
            </mixhtml>
        """
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()




##############################
@app.get("/items/page/<page_number>")
def get_items_by_page(page_number):
    try:
        page_number = x.validate_page_number(page_number)
        items_per_page = 2
        offset = (page_number-1) * items_per_page
        extra_item = items_per_page + 1
        db, cursor = x.db()
        q = "SELECT * FROM items WHERE item_blocked = 0 AND item_deleted_at = 0 ORDER BY item_created_at LIMIT %s OFFSET %s"
        cursor.execute(q, (extra_item, offset))
        items = cursor.fetchall()
        html = ""
        
        rates= ""
        with open("rates.txt", "r") as file:
            rates = file.read() # this is text that looks like json
            rates = json.loads(rates)

        for item in items[:items_per_page]:
            i = render_template("_item_mini.html", item=item, rates=rates)
            html += i
        button = render_template("_button_more_items.html", page_number=page_number + 1)
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


        
        # Get item data from form
        item_pk = request.form.get("item_pk", "").strip()
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "0").strip()
        lon = request.form.get("lon", "0").strip()
        lat = request.form.get("lat", "0").strip()
        
        # Basic validation
        if not item_pk or not name:
            return "Item ID and name are required", 400
        
        try:
            price = int(price)
            lon = float(lon)
            lat = float(lat)
        except ValueError:
            return "Invalid price or coordinates", 400
            
        db, cursor = x.db()
        
        # First verify this item belongs to the current user
        q = "SELECT * FROM items WHERE item_pk = %s AND item_user_fk = %s"
        cursor.execute(q, (item_pk, user["user_pk"]))
        item = cursor.fetchone()
        
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
        
        if cursor.rowcount != 1:
            raise Exception("Failed to update item")
        
        db.commit()
        
        return f"""
            <mixhtml mix-redirect="/profile">
                Item updated successfully!
            </mixhtml>
        """
        
    except Exception as ex:
        ic(ex)
        if "company_ex file extension not allowed" in str(ex):
            return "File extension not allowed", 400
        
        if "company_ex file too large" in str(ex):
            return "File too large", 400
            
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
        
        db, cursor = x.db()
        
        # First verify this item belongs to the current user
        q = "SELECT * FROM items WHERE item_pk = %s AND item_user_fk = %s AND item_deleted_at = 0"
        cursor.execute(q, (item_pk, user["user_pk"]))
        item = cursor.fetchone()
        
        if not item:
            return "Item not found or you don't have permission to delete it", 403
        
        # Soft delete the item (update item_deleted_at timestamp)
        current_time = int(time.time())
        q = "UPDATE items SET item_deleted_at = %s WHERE item_pk = %s AND item_user_fk = %s"
        cursor.execute(q, (current_time, item_pk, user["user_pk"]))
        
        if cursor.rowcount != 1:
            raise Exception("Failed to delete item")
        
        db.commit()
        
        return f"""
            <mixhtml mix-redirect="/profile">
                Item deleted successfully!
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
        active_signup ="active"
        error_message = request.args.get("error_message", "")
        return render_template("view_signup.html", 
                           title="Signup", 
                           active_signup=active_signup, 
                           error_message=error_message,
                           old_values={})
    except Exception as ex:
        ic(ex) 

##############################
@app.post("/signup")
def signup():
    try:
        user_username = x.validate_user_username()
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email = x.validate_user_email()
        user_password = x.validate_user_password()
        hashed_password = generate_password_hash(user_password)

        #TO DO
        #user_verified_at = int(time.time());
    
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

        db, cursor = x.db()
        cursor.execute(q, (user_username, user_name, user_last_name, user_email, hashed_password, 
                  user_verification_key, user_created_at, 0, 0, 0, 0))

        if cursor.rowcount != 1: raise Exception("System under maintenance")

        db.commit()
        x.send_email(user_name, user_last_name, user_verification_key)
        return redirect(url_for("show_login", message="Signup ok"))
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        old_values = request.form.to_dict()
        error_message = str(ex)
        
        # Fix the exception handling for user validation
        if "company_ex user_username" in error_message:
            old_values.pop("user_username", None)
            return render_template("view_signup.html",                                   
                error_message="Invalid username", old_values=old_values, user_username_error="input_error")
        if "company_ex user_name" in error_message:
            old_values.pop("user_name", None)
            return render_template("view_signup.html",
                error_message="Invalid name", old_values=old_values, user_name_error="input_error")
        if "company_ex user_last_name" in error_message or "last name" in error_message:
            old_values.pop("user_last_name", None)
            return render_template("view_signup.html",
                error_message="Invalid last name", old_values=old_values, user_last_name_error="input_error")
        if "company_ex email" in error_message:
            old_values.pop("user_email", None)
            return render_template("view_signup.html",
                error_message="Invalid email", old_values=old_values, user_email_error="input_error")
        if "company_ex user_password" in error_message or "password" in error_message:
            old_values.pop("user_password", None)
            return render_template("view_signup.html",
                error_message="Invalid password", old_values=old_values, user_password_error="input_error")
        #duplicate
        if "company_ex duplicate_email" in error_message:
            old_values.pop("user_email", None)
            return render_template("view_signup.html",
                error_message="Email already exists", old_values=old_values, user_email_error="input_error")
        if "user_username" in error_message: 
            return render_template("view_signup.html", 
                error_message="Username already exists", old_values=old_values, user_username_error="input_error")
                
        # Default case - handle any other exceptions
        return render_template("view_signup.html",
            error_message=f"An error occurred: {error_message}", 
            old_values=old_values)
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/login")
def show_login():
    active_login = "active"
    message = request.args.get("message", "")
    return render_template("view_login.html", title="Login", active_login=active_login, message=message)
##############################
@app.post("/login")
def login():
    try:
        user_email = x.validate_user_email()
        user_password = x.validate_user_password()

        db,cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()

        if not user:
            raise Exception("Wrong email or password")

        if not check_password_hash(user["user_password"], user_password):
            raise Exception("Invalid credentials")
        
        if user["user_verified_at"] == 0:
            raise Exception("Please Verify your email before loggin in!")
        
        if user.get("user_blocked", 0) == 1:
            raise Exception("Your account has been blocked. Please contact support.")
        

        # user.pop("user_password") Use this or remove the users password from the session
        # ic(user) 

        session["user"] = user
        session["is_admin"] = bool(user.get("user_is_admin", 0))

        return redirect(url_for("profile"))
    except Exception as ex:
        ic(ex)

        if "Invalid credentials" in str(ex):
            return redirect(url_for("show_login", message="Invalid email or password"))
        
        return redirect(url_for("show_login", message=f"Login failed: {str(ex)}"))
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
        is_session = False
        if session["user"]: is_session = True  
        active_profile = "active"      
        return render_template("view_profile.html", title="Profile", user=session["user"], is_session=is_session, active_profile=active_profile)
    

        # user_name = session["user"]["user_name"]
        # user_last_name = session["user"]["user_last_name"]
        # return render_template("profile.html", title="Profile", user_name=user_name, user_last_name=user_last_name)
    except Exception as ex:
        ic(ex)
        return redirect(url_for("show_login"))
    finally:
        pass
##############################
##############################
@app.get("/edit-profile")
def show_edit_profile():
    try:
        
        if not session.get("user"):
            return redirect(url_for("show_login"))
            
        return render_template(
            "view_edit_profile.html", 
            title="Edit Profile", 
            user=session["user"],
            error_message="",
            old_values = {}
        )
    except Exception as ex:
        ic(ex)
        return redirect(url_for("profile"))

##############################
@app.post("/edit-profile")
def edit_profile():
    try:
       
        if not session.get("user"):
            return redirect(url_for("show_login"))
            
        user_pk = session["user"]["user_pk"]
        
       
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
        
        if "user_name" in str(ex):
            return render_template("view_edit_profile.html", 
                title="Edit Profile",
                error_message="Invalid name format",
                user=session["user"],
                old_values=old_values,
                user_name_error="input_error")
                
        if "last name" in str(ex):
            return render_template("view_edit_profile.html", 
                title="Edit Profile",
                error_message="Invalid last name format",
                user=session["user"],
                old_values=old_values,
                user_last_name_error="input_error")
                
        if "email" in str(ex):
            return render_template("view_edit_profile.html", 
                title="Edit Profile",
                error_message="Invalid email format",
                user=session["user"],
                old_values=old_values,
                user_email_error="input_error")
        
        return render_template("view_edit_profile.html", 
            title="Edit Profile",
            error_message=error_message,
            user=session["user"],
            old_values=old_values)
            
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
##############################  
@app.get("/forgot-password")
def show_forgot_password():
    try:
        message = request.args.get("message", "")
        return render_template("view_forgot_password.html", title="Forgot Password", message=message)
    except Exception as ex:
        ic(ex)
        return redirect(url_for("view_index"))
##############################
@app.post("/forgot-password")
def forgot_password():
    try:
        user_email = x.validate_user_email()
        
        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()
        
        if not user:
            return redirect(url_for("show_forgot_password", message="If your email is registered, you will receive a password reset link."))
        
        # Generate a reset token
        reset_token = str(uuid.uuid4())
        
        # Store the token and its expiry time in the database
        current_time = int(time.time())
        expiry_time = current_time + (24 * 60 * 60)  # 24 hours from now
        
        q = "UPDATE users SET user_reset_token = %s, user_reset_token_expiry = %s WHERE user_pk = %s"
        cursor.execute(q, (reset_token, expiry_time, user["user_pk"]))
        
        if cursor.rowcount != 1:
            raise Exception("System under maintenance")
        
        db.commit()
        
        # Send an email with the reset link
        x.send_reset_password_email(user["user_name"], user["user_last_name"], reset_token)
        
        return redirect(url_for("show_forgot_password", message="If your email is registered, you will receive a password reset link."))
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return redirect(url_for("show_forgot_password", message=f"An error occurred: {str(ex)}"))
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/reset-password/<reset_token>")
def show_reset_password(reset_token):
    try:
        db, cursor = x.db()
        current_time = int(time.time())
        
        q = "SELECT * FROM users WHERE user_reset_token = %s AND user_reset_token_expiry > %s AND user_deleted_at = 0"
        cursor.execute(q, (reset_token, current_time))
        user = cursor.fetchone()
        
        if not user:
            return "Invalid or expired reset token", 400
        
        return render_template("view_reset_password.html", title="Reset Password", reset_token=reset_token)
        
    except Exception as ex:
        ic(ex)
        return f"Error: {str(ex)}", 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/reset-password/<reset_token>")
def reset_password(reset_token):
    try:
        user_password = x.validate_user_password()
        
        db, cursor = x.db()
        current_time = int(time.time())
        
        # Check if token is valid and not expired
        q = "SELECT * FROM users WHERE user_reset_token = %s AND user_reset_token_expiry > %s AND user_deleted_at = 0"
        cursor.execute(q, (reset_token, current_time))
        user = cursor.fetchone()
        
        if not user:
            return "Invalid or expired reset token", 400
        
        # Update the password
        hashed_password = generate_password_hash(user_password)
        
        # Clear the reset token and update the password
        q = "UPDATE users SET user_password = %s, user_reset_token = NULL, user_reset_token_expiry = NULL WHERE user_pk = %s"
        cursor.execute(q, (hashed_password, user["user_pk"]))
        
        if cursor.rowcount != 1:
            raise Exception("System under maintenance")
        
        db.commit()
        
        return redirect(url_for("show_login", message="Password reset successful. You can now login with your new password."))
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return f"Error: {str(ex)}", 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.delete("/user")
def delete_user():
    try:
        # Make sure user is logged in
        if not session.get("user"):
            return "User not logged in", 401
        
        user_pk = session["user"]["user_pk"]
        
        # Connect to database
        db, cursor = x.db()
        
        # Soft delete the user (update user_deleted_at timestamp)
        current_time = int(time.time())
        q = "UPDATE users SET user_deleted_at = %s WHERE user_pk = %s"
        cursor.execute(q, (current_time, user_pk))
        
        if cursor.rowcount != 1:
            raise Exception("company_ex cannot delete user")
        
        db.commit()
        session.pop("user")
        

        return """
            <mixhtml mix-redirect="/login">
                Account deleted successfully
            </mixhtml>
        """
        
    except Exception as ex:
        ic(ex)     
        db.rollback()  
        session.pop("user") 
        if "company_ex cannot delete user" in str(ex):
            return """
                <mixhtml mix-redirect="/login">
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
def ___ADMIN___(): pass
##############################
@app.get("/admin")
@x.admin_required
def admin_dashboard():
    try:
        return render_template(
            "view_adminDashboard.html", 
            title="Admin Dashboard", 
            user=session["user"]
        )
    except Exception as ex:
        ic(ex)
        return redirect(url_for("view_index"))
##############################
@app.get("/admin/users")
@x.admin_required
def admin_users():
    try:
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
            user=session["user"]
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
        
        db, cursor = x.db()
        

        q = "SELECT * FROM users WHERE user_pk = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_pk,))
        user = cursor.fetchone()
        
        if not user:
            raise Exception("User not found or already deleted")
        
        
        if user.get("user_is_admin", 0):
            raise Exception("Cannot block admin users")
        

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
        
        
        return """
            <mixhtml mix-redirect="/admin/users">
                User blocked successfully and notification email sent.
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
        
        db, cursor = x.db()
        
        
        q = "SELECT * FROM users WHERE user_pk = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_pk,))
        user = cursor.fetchone()
        
        if not user:
            raise Exception("User not found or already deleted")
        
        
        q = "UPDATE users SET user_blocked = 0 WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        
        if cursor.rowcount != 1:
            raise Exception("Failed to unblock user")
        
        db.commit()
        

        try:
            x.send_unblocked_email(
                user["user_name"], 
                user["user_last_name"], 
                user["user_email"]
            )
        except Exception as email_ex:
            ic(f"Failed to send unblock notification email: {email_ex}")
        
        return """
            <mixhtml mix-redirect="/admin/users">
                User unblocked successfully and notification email sent.
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
        db, cursor = x.db()
        q = "SELECT * FROM items ORDER BY item_created_at DESC"
        cursor.execute(q)
        items = cursor.fetchall()

        rates = x.load_rates()
        
        return render_template(
            "view_adminItems.html", 
            title="Manage Items", 
            items=items, 
            user=session["user"],
            rates = rates
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
        db, cursor = x.db()
        
        # Check if the item exists
        q = "SELECT * FROM items WHERE item_pk = %s"
        cursor.execute(q, (item_pk,))
        item = cursor.fetchone()
        
        if not item:
            raise Exception("Item not found")
            
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
            raise Exception("Failed to block item")
        
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
                msg = "Item blocked successfully and notification email sent to owner."
            except Exception as email_ex:
                ic(f"Failed to send item block notification email: {email_ex}")
                msg = "Item blocked successfully but failed to send notification email."
        else:
            msg = "Item blocked successfully. No owner found to notify."
        
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
        db, cursor = x.db()
        
        # Check if the item exists
        q = "SELECT * FROM items WHERE item_pk = %s"
        cursor.execute(q, (item_pk,))
        item = cursor.fetchone()
        
        if not item:
            raise Exception("Item not found")
            
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
            raise Exception("Failed to unblock item")
        
        db.commit()
        
        # Send notification email if we have a valid user
        if user:
            try:
                x.send_item_unblocked_email(
                    user["user_name"], 
                    user["user_last_name"], 
                    user["user_email"],
                    item["item_name"]
                )
                msg = "Item unblocked successfully and notification email sent to owner."
            except Exception as email_ex:
                ic(f"Failed to send item unblock notification email: {email_ex}")
                msg = "Item unblocked successfully but failed to send notification email."
        else:
            msg = "Item unblocked successfully. No owner found to notify."
        
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