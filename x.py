from flask import request, session
import mysql.connector
import re
import os
import uuid
import json

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

from functools import wraps
from flask import abort


##############################
def db():
    db = mysql.connector.connect(
        host = "mysql",      # Replace with your MySQL server's address or docker service name "mysql"
        user = "root",  # Replace with your MySQL username
        password = "password",  # Replace with your MySQL password
        database = "company"   # Replace with your MySQL database name
    )
    cursor = db.cursor(dictionary=True)
    return db, cursor


##############################
def validate_admin():
    """Check if the current user is logged in and is an admin"""
    user = validate_user_logged()  # raises an exception if the user is not logged in
    if not session.get("is_admin", False):
        raise Exception("Access denied: Admin privileges required")
    return user
##############################
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            validate_admin()
            return f(*args, **kwargs)
        except Exception:
            return abort(403)  # Forbidden
    return decorated_function

##############################
def validate_user_logged():
    if not session.get("user"): raise Exception("compay_ex user not logged")
    return session.get("user")


##############################
USER_USERNAME_MIN = 2
USER_USERNAME_MAX = 20
USER_USERNAME_REGEX = f"^.{{{USER_USERNAME_MIN},{USER_USERNAME_MAX}}}$"
def validate_user_username():
    error = f"company_ex user_username"
    user_username = request.form.get("user_username", "").strip()
    if not re.match(USER_USERNAME_REGEX, user_username): raise Exception(error)
    return user_username
##############################
USER_NAME_MIN = 2
USER_NAME_MAX = 20
USER_NAME_REGEX = f"^.{{{USER_NAME_MIN},{USER_NAME_MAX}}}$"
def validate_user_name():
    error = "company_ex user_name"
    user_name = request.form.get("user_name", "").strip()
    if not re.match(USER_NAME_REGEX, user_name): raise Exception(error)
    return user_name
##############################
USER_LAST_NAME_MIN = 2
USER_LAST_NAME_MAX = 20
USER_LAST_NAME_REGEX = f"^.{{{USER_LAST_NAME_MIN},{USER_LAST_NAME_MAX}}}$"
def validate_user_last_name():
    error = f"last name {USER_LAST_NAME_MIN} to {USER_LAST_NAME_MAX} characters"
    user_last_name = request.form.get("user_last_name", "").strip()
    if not re.match(USER_LAST_NAME_REGEX, user_last_name): raise Exception(error)
    return user_last_name

##############################
REGEX_EMAIL = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
def validate_user_email():
    error = f"company_ex email"
    email = request.form.get("user_email", "").strip()
    if not email:
        raise Exception("company_ex email_empty")  # Specific error for empty email
    if not re.match(REGEX_EMAIL, email):
        raise Exception("company_ex email_invalid")  # Specific error for invalid email format
    return email

##############################
USER_PASSWORD_MIN = 2
USER_PASSWORD_MAX = 20
def validate_user_password():
    error = f"password {USER_PASSWORD_MIN} to {USER_PASSWORD_MAX} characters"
    user_password = request.form.get("user_password", "").strip()
    if len(user_password) < USER_PASSWORD_MIN: raise Exception(error)
    if len(user_password) > USER_PASSWORD_MAX: raise Exception(error)
    return user_password

##############################
REGEX_PAGE_NUMBER = "^[1-9][0-9]*$"
def validate_page_number(page_number):
    error = "company_ex page number"
    page_number = page_number.strip()
    if not re.match(REGEX_PAGE_NUMBER, page_number): raise Exception(error)
    return int(page_number)
##############################
#post_item Validation
ITEM_NAME_MIN = 3
ITEM_NAME_MAX = 30
ITEM_NAME_REGEX = f"^.{{{ITEM_NAME_MIN},{ITEM_NAME_MAX}}}$"

ITEM_PRICE_MIN = 0.01  # Minimum price
ITEM_PRICE_MAX = 1000000  # Maximum price

ITEM_COORDINATES_MIN_LON = -180
ITEM_COORDINATES_MAX_LON = 180
ITEM_COORDINATES_MIN_LAT = -90
ITEM_COORDINATES_MAX_LAT = 90

def validate_post_item_form():
    # Validate item name
    error_name = f"company_ex item_name"
    item_name = request.form.get("name", "").strip()
    if not re.match(ITEM_NAME_REGEX, item_name):
        raise Exception(error_name)

    # Validate item price
    error_price = f"company_ex item_price"
    item_price = request.form.get("price", "").strip()
    try:
        item_price = float(item_price)
        if item_price < ITEM_PRICE_MIN or item_price > ITEM_PRICE_MAX:
            raise Exception(error_price)
    except ValueError:
        raise Exception(error_price)

    # Validate longitude and latitude
    error_coordinates = f"company_ex item_coordinates"
    item_lon = request.form.get("lon", "").strip()
    item_lat = request.form.get("lat", "").strip()
    try:
        item_lon = float(item_lon)
        item_lat = float(item_lat)
        if not (ITEM_COORDINATES_MIN_LON <= item_lon <= ITEM_COORDINATES_MAX_LON) or not (ITEM_COORDINATES_MIN_LAT <= item_lat <= ITEM_COORDINATES_MAX_LAT):
            raise Exception(error_coordinates)
    except ValueError:
        raise Exception(error_coordinates)

    # Validate images
    images_names = validate_item_images()  # Reuse the existing `validate_item_images` function

    return {
        "name": item_name,
        "price": item_price,
        "lon": item_lon,
        "lat": item_lat,
        "images": images_names
    }
##############################
ALLOWED_EXTENSIONS = ["png", "jpg", "jpeg", "gif"]
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB - size in bytes
MAX_FILES = 5

def validate_item_images():
    images_names = []
    if "images" not in request.files:
         raise Exception("company_ex at least one file")
    
    files = request.files.getlist('images')
    
    if len(files) > MAX_FILES:
        raise Exception("company_ex max 5 files")

    # Get the application root directory
    app_dir = os.path.dirname(os.path.abspath(__file__))
    upload_dir = os.path.join(app_dir, "static", "uploads")
    
    # Ensure the upload directory exists
    os.makedirs(upload_dir, exist_ok=True)
    
    for the_file in files:
        if not the_file or the_file.filename == '':
            continue  # Skip empty file inputs
            
        file_size = len(the_file.read()) # size is in bytes                 
        file_name, file_extension = os.path.splitext(the_file.filename)
        the_file.seek(0)
        file_extension = file_extension.lstrip(".")
        
        if file_extension not in ALLOWED_EXTENSIONS:
            raise Exception("company_ex file extension not allowed")  
            
        if file_size > MAX_FILE_SIZE:
            raise Exception("company_ex file too large")  
            
        new_file_name = f"{uuid.uuid4().hex}.{file_extension}"
        images_names.append(new_file_name)
        
        file_path = os.path.join(upload_dir, new_file_name)
        the_file.save(file_path)
        
        ic(f"Saved file to {file_path}")
        
    if not images_names:
        raise Exception("company_ex at least one file")
        
    return images_names


##############################
def send_email(user_name, user_last_name, user_verification_key):
    try:
        # Email and password of the sender's Gmail account
        sender_email = "boeghgustav@gmail.com"
        password = "chbo zuza cvso rqha"  # If 2FA is on, use an App Password instead

        # Receiver email address
        receiver_email = "boeghgustav@gmail.com"
        
        # Create the email message
        message = MIMEMultipart()
        message["From"] = "My company name"
        message["To"] = receiver_email
        message["Subject"] = "Welcome"

        # Body of the email REMEBER TO REPLACE 127.0.0.1 with https://gust0288.eu.pythonanywhere.com
        body = f"""
                Thank you {user_name} {user_last_name} for signing up. Welcome.

                To verify your account, please <a href="http://127.0.0.1/verify/{user_verification_key}">click here</a>
                
                """
        message.attach(MIMEText(body, "html"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        ic("Email sent successfully!")

        return "email sent"
    except Exception as ex:
        ic(ex)
        raise Exception("cannot send email")
    finally:
        pass
##############################
def send_reset_password_email(user_name, user_last_name, reset_token):
    try:
        # Email and password of the sender's Gmail account
        sender_email = "boeghgustav@gmail.com"
        password = "chbo zuza cvso rqha"  # If 2FA is on, use an App Password instead

        # Receiver email address
        receiver_email = "boeghgustav@gmail.com"  
        
        # Create the email message
        message = MIMEMultipart()
        message["From"] = "My company name"
        message["To"] = receiver_email
        message["Subject"] = "Password Reset Request"

        # Body of the email REMEBER TO REPLACE 127.0.0.1 with https://gust0288.eu.pythonanywhere.com
        body = f"""
                Hello {user_name} {user_last_name},
                
                You requested to reset your password.
                
                To reset your password, please <a href="http://127.0.0.1/reset-password/{reset_token}">click here</a> 
                
                This link will expire in 24 hours.
                
                If you did not request a password reset, please ignore this email.
                """
        message.attach(MIMEText(body, "html"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        ic("Password reset email sent successfully!")

        return "email sent"
    except Exception as ex:
        ic(ex)
        raise Exception("cannot send email")
    finally:
        pass


##############################
def send_blocked_email(user_name, user_last_name, user_email):
    try:
        # Email and password of the sender's Gmail account
        sender_email = "boeghgustav@gmail.com"
        password = "chbo zuza cvso rqha"  # If 2FA is on, use an App Password instead

      
        receiver_email = "boeghgustav@gmail.com" 
        
        # Create the email message
        message = MIMEMultipart()
        message["From"] = "Fleamarket Admin"
        message["To"] = receiver_email
        message["Subject"] = "Account Blocked Notification"

        # Body of the email
        body = f"""
                Hello {user_name} {user_last_name},
                
                We regret to inform you that your account has been blocked by an administrator.
                
                If you believe this action was taken in error, please contact our support team.
                
                Thank you,
                Fleamarket Team
                """
        message.attach(MIMEText(body, "html"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        ic(f"Block notification email sent to {user_email}")

        return "email sent"
    except Exception as ex:
        ic(ex)
        raise Exception("cannot send email")

##############################
def send_unblocked_email(user_name, user_last_name, user_email):
    try:
        # Email and password of the sender's Gmail account
        sender_email = "boeghgustav@gmail.com"
        password = "chbo zuza cvso rqha"  # If 2FA is on, use an App Password instead

       
        receiver_email = "boeghgustav@gmail.com"
        
        # Create the email message
        message = MIMEMultipart()
        message["From"] = "Fleamarket Admin"
        message["To"] = receiver_email
        message["Subject"] = "Account Access Restored"

        # Body of the email
        body = f"""
                Hello {user_name} {user_last_name},
                
                Good news! Your account has been unblocked by an administrator.
                
                You can now log in and continue using our services.
                
                Thank you,
                Fleamarket Team
                """
        message.attach(MIMEText(body, "html"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        ic(f"Unblock notification email sent to {user_email}")

        return "email sent"
    except Exception as ex:
        ic(ex)
        raise Exception("cannot send email")

##############################
def send_item_blocked_email(user_name, user_last_name, user_email, item_name):
    try:
        # Email and password of the sender's Gmail account
        sender_email = "boeghgustav@gmail.com"
        password = "chbo zuza cvso rqha"  # If 2FA is on, use an App Password instead

        # Receiver email address - in production, use the actual user's email
        receiver_email = "boeghgustav@gmail.com" # In production, use user_email
        
        # Create the email message
        message = MIMEMultipart()
        message["From"] = "Fleamarket Admin"
        message["To"] = receiver_email
        message["Subject"] = f"Your Item '{item_name}' Has Been Blocked"

        # Body of the email
        body = f"""
                Hello {user_name} {user_last_name},
                
                We regret to inform you that your item '{item_name}' has been blocked by an administrator.
                
                This item is no longer visible in the marketplace. If you believe this action was taken in error, 
                please contact our support team.
                
                Thank you,
                Fleamarket Team
                """
        message.attach(MIMEText(body, "html"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        ic(f"Item block notification email sent to owner of item: {item_name}")

        return "email sent"
    except Exception as ex:
        ic(ex)
        raise Exception("cannot send email")
##############################
def send_item_unblocked_email(user_name, user_last_name, user_email, item_name):
    try:
        # Email and password of the sender's Gmail account
        sender_email = "boeghgustav@gmail.com"
        password = "chbo zuza cvso rqha"  # If 2FA is on, use an App Password instead

        # Receiver email address - in production, use the actual user's email
        receiver_email = "boeghgustav@gmail.com" # In production, use user_email
        
        # Create the email message
        message = MIMEMultipart()
        message["From"] = "Fleamarket Admin"
        message["To"] = receiver_email
        message["Subject"] = f"Your Item '{item_name}' Has Been Unblocked"

        # Body of the email
        body = f"""
                Hello {user_name} {user_last_name},
                
                Good news! Your item '{item_name}' has been unblocked by an administrator.
                
                This item is now visible in the marketplace again.
                
                Thank you,
                Fleamarket Team
                """
        message.attach(MIMEText(body, "html"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        ic(f"Item unblock notification email sent to owner of item: {item_name}")

        return "email sent"
    except Exception as ex:
        ic(ex)
        raise Exception("cannot send email")
##############################
def send_account_deletion_email(user_name, user_last_name, user_email):
    try:
        # Email and password of the sender's Gmail account
        sender_email = "boeghgustav@gmail.com"
        password = "chbo zuza cvso rqha"  # If 2FA is on, use an App Password instead

        # Receiver email address - in production, use the actual user's email
        receiver_email = "boeghgustav@gmail.com" # In production, use user_email
        
        # Create the email message
        message = MIMEMultipart()
        message["From"] = "Fleamarket Admin"
        message["To"] = receiver_email
        message["Subject"] = "Account Deletion Confirmation"

    # Email content
        body = f"""
            Hello {user_name} {user_last_name},
    
            This email confirms that your account has been deleted from our system.
    
            If you did not request this deletion, please contact us immediately.
    
            Thank you,
            Fleamarket Team
            """
        message.attach(MIMEText(body, "html"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        ic(f"Account deletion confirmation email sent to {user_email}")

        return "email sent"
    except Exception as ex:
        ic(ex)
        raise Exception("cannot send email")




