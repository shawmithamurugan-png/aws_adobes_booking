import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import uuid
from flask import Flask, render_template, request, redirect, url_for, session
import os
from werkzeug.utils import secure_filename
from sns_notifier import send_sns_message
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()

SNS_TOPIC_ARN = os.getenv("arn:aws:sns:us-east-1:539247489202:Booking_confirmation")


AWS_REGION = "us-east-1"
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

users_table = dynamodb.Table('Users')
bookings_table = dynamodb.Table('Bookings')

bookings = []


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

@app.route("/ping")
def ping():
    return "FLASK IS WORKING"

# =========================
# GLOBAL HOTEL DATA
# =========================
hotels = [
    {"name": "Grand Chennai Suites", "location": "Chennai", "price": 7500, "rating": 4.8, "image": "images/img3.jpg"},
    {"name": "Beach View Chennai", "location": "Chennai", "price": 9000, "rating": 4.9, "image": "images/img4.jpg"},

    {"name": "Bangalore Palace Hotel", "location": "Bangalore", "price": 5800, "rating": 4.6, "image": "images/img5.jpg"},
    {"name": "City Comfort Inn Bangalore", "location": "Bangalore", "price": 74200, "rating": 4.8, "image": "images/img6.jpg"},
    {"name": "Silicon Valley Stay Bangalore", "location": "Bangalore", "price": 6800, "rating": 4.1, "image": "images/img7.jpg"},

    {"name": "Comfort Inn Delhi", "location": "Delhi", "price": 7900, "rating": 4.0, "image": "images/img8.jpg"},
    {"name": "Goa Cozy Cottage Delhi", "location": "Delhi", "price": 6200, "rating": 4.0, "image": "images/img9.jpg"},

    {"name": "Ocean View Resort Mumbai", "location": "Mumbai", "price": 6500, "rating": 4.9, "image": "images/img10.jpg"},
    {"name": "City Lights Hotel Mumbai", "location": "Mumbai", "price": 7000, "rating": 4.5, "image": "images/img11.jpg"},

    {"name": "Kochi Riverside Hotel Hyderabad", "location": "Hyderabad", "price": 7800, "rating": 4.7, "image": "images/pune.jpg"},
    {"name": "Kochi Budget Stay Hyderabad", "location": "Hyderabad", "price": 8500, "rating": 3.8, "image": "images/goa.jpg"},
]


# DynamoDB table name (MUST match AWS exactly)
TABLE_NAME = 'Users'

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table(TABLE_NAME)


# Configuration for File Uploads
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory database (dictionary)
users = {}
admin_users = {}
projects = []  # List of dictionaries: {'id': 1, 'title': '...', 'desc': '...', 'image': '...', 'doc': '...'}
enrollments = {} # Dictionary: {'username': [project_id_1, project_id_2]}


@app.route('/')
def index():




    # 🔹 Read filters from URL
    place= request.args.get('place')
    price = request.args.get('price')
    rating = request.args.get('rating')

    filtered_hotels = hotels

    # 🔹 place filter
    if place:
        filtered_hotels = [h for h in filtered_hotels if h['location'] == place]

    # 🔹 Price sorting
    if price == 'low':
        filtered_hotels = sorted(filtered_hotels, key=lambda x: x['price'])
    elif price == 'high':
        filtered_hotels = sorted(filtered_hotels, key=lambda x: x['price'], reverse=True)

    # 🔹 Rating filter
    if rating == 'high':
        filtered_hotels = [h for h in filtered_hotels if h['rating'] >= 4.0]
    elif rating == 'low':
        filtered_hotels = [h for h in filtered_hotels if h['rating'] < 4.0]

    return render_template("index.html", hotels=filtered_hotels)




@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/debug-users')
def debug_users():
    return users

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']  # ❌ no hashing

        users_table.put_item(
            Item={
                'email': email,
                'password': password,  # stored as plain text
                'created_at': datetime.now().isoformat()
            }
        )

        session['email'] = email
        return redirect(url_for('index'))

    return render_template('signup.html')


@app.route('/book/<hotel_name>', methods=['GET', 'POST'])
@app.route('/book/<hotel_name>', methods=['GET', 'POST'])
def book_hotel(hotel_name):
    if 'email' not in session:
        return redirect(url_for('login'))

    hotel = next((h for h in hotels if h['name'] == hotel_name), None)
    if not hotel:
        return "Hotel not found", 404

    if request.method == 'POST':
        guest_name = request.form.get('guest_name')
        members = request.form.get('members')
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')

        if not check_in or not check_out:
            return "Check-in and Check-out dates are required", 400

        booking = {
            "booking_id": str(uuid.uuid4()),
            "user_email": session['email'],
            "guest_name": guest_name,
            "members": int(members),
            "hotel_name": hotel['name'],
            "location": hotel['location'],
            "check_in": check_in,
            "check_out": check_out,
            "status": "Booked",
            "created_at": datetime.now().isoformat()
        }

        # ✅ SAVE ONCE (CORRECT TABLE)
        bookings_table.put_item(Item=booking)

        # ✅ SNS notification (optional)
        message = f"""
Booking Confirmed – Blissful Abodes

Hotel   : {hotel['name']}
Location: {hotel['location']}
Check-in: {check_in}
Check-out: {check_out}

Thank you for choosing Blissful Abodes!
"""
        send_sns_message("Booking Confirmation", message)

        return redirect(url_for('booking_success', hotel_name=hotel_name))

    return render_template('book.html', hotel=hotel)


sns = boto3.client("sns", region_name="us-east-1")

TOPIC_ARN = "arn:aws:sns:us-east-1:539247489202:Booking_confirmed"

def subscribe_user_email(email):
    response = sns.subscribe(
        TopicArn=TOPIC_ARN,
        Protocol="email",
        Endpoint=email,
        ReturnSubscriptionArn=True
    )
    return response

def send_sns_message(subject, message):
    try:
        sns = boto3.client('sns', region_name='us-east-1')

        response = sns.publish(
            TopicArn="arn:aws:sns:us-east-1:539247489202:Booking_confirmation",
            Subject=subject,
            Message=message
        )

        print("SNS MESSAGE SENT:", response)

    except Exception as e:
        print("SNS ERROR:", e)


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    response = bookings_table.scan()
    bookings = response.get('Items', [])
    total_bookings = len(bookings)

    return render_template(
        'admin_dashboard.html',
        bookings=bookings,
        total_bookings=total_bookings
    )

# =========================
# STAFF LOGIN (FINAL)
# =========================
STAFF_EMAIL = "staff2adbobes@gmail.com"
STAFF_PASSWORD = "hotels"

@app.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == STAFF_EMAIL and password == STAFF_PASSWORD:
            session['staff'] = email
            return redirect(url_for('staff_dashboard'))

        return render_template('staff_login.html', error="Invalid staff credentials")

    return render_template('staff_login.html')


@app.route('/staff/dashboard')
def staff_dashboard():
    if 'staff' not in session:
        return redirect(url_for('staff_login'))

    today = datetime.now().strftime("%Y-%m-%d")

    response = bookings_table.scan()
    bookings = response.get('Items', [])

    todays_bookings = [
        b for b in bookings if b.get('created_at') == today
    ]

    summary = {
        "Booked": 0,
        "Checked-In": 0,
        "Checked-Out": 0
    }

    for b in todays_bookings:
        summary[b.get('status', 'Booked')] += 1

    return render_template(
        'staff_dashboard.html',
        bookings=todays_bookings,
        summary=summary
    )

@app.route('/staff/logout')
def staff_logout():
    session.pop('staff', None)
    return redirect(url_for('index'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        response = users_table.get_item(Key={'email': email})

        if 'Item' not in response:
            return "User not found", 401

        stored_password = response['Item']['password']

        # ✅ PLAIN TEXT COMPARISON
        if stored_password == password:
            session['email'] = email
            return redirect(url_for('home'))
        else:
            return "Invalid password", 401

    return render_template('login.html')


@app.route('/booking-success')
def booking_success():
    return render_template('booking_success.html')




@app.route('/home')
def home():
    if 'email' in session:
        username = session['email']
        user_enrollments_ids = enrollments.get(username, [])

        # Filter projects to get full details of enrolled ones
        my_projects = [p for p in projects if p['id'] in user_enrollments_ids]

        return render_template(
            'home.html',
            username=username,
            my_projects=my_projects,
            hotels=hotels      # ✅ THIS LINE FIXES IT
        )

    return redirect(url_for('login'))





@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # FIXED ADMIN CREDENTIALS
        if email == "admin@gmail.com" and password == "1234":
            session['admin'] = email
            return redirect(url_for('admin_dashboard'))

        return render_template(
            'admin_login.html',
            error="Invalid admin credentials"
        )

    return render_template('admin_login.html')





@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

def send_booking_email(to_email, name):
    ses.send_email(
        Source='your_verified_email@gmail.com',
        Destination={'ToAddresses': [to_email]},
        Message={
            'Subject': {'Data': 'Hotel Booking Confirmed'},
            'Body': {
                'Text': {
                    'Data': f"""
Hello {name},

Your hotel booking is confirmed ✅
We are excited to host you!

Thank you,
Blissful Abodes
"""
                }
            }
        }
    )
@app.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        admin_users[email] = password
        return redirect(url_for('admin_login'))

    return render_template('admin_signup.html')




@app.route('/book', methods=['POST'])
def book():
    user_email = request.form['user_email']
    username = request.form['username']
    booking_details = "Room: Deluxe, Date: 30-Jan-2026"  # Example
    
    # Send confirmation email
    email_status = send_booking_email(user_email, username, booking_details)
    
    if email_status:
        flash("Booking successful! Confirmation email sent.", "success")
    else:
        flash("Booking successful, but email could not be sent.", "warning")
    
    return redirect(url_for('home'))
@app.route('/Staff')
def staff_uppercase_redirect():
    return redirect(url_for('staff_login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)



