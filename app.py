from flask import Flask, render_template, request
import os
import phonenumbers
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
from models import User, Entry, db, initialize_db
from peewee import DoesNotExist
import html

# Load environment variables
load_dotenv()

# Initialize the db
initialize_db()
app = Flask(__name__)

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_NUMBER = os.getenv('TWILIO_NUMBER')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.route('/')
def index():
    return render_template('index.html')

# given a phone number, get all text entries
@app.route('/get_diary', methods=['POST'])
def get_diary():
    phone_number = request.form['phone']

    # clean & validate phone number
    phone_number = phone_number.replace("-", "")
    if not phone_number.startswith("+1"):
        phone_number = "+1"+phone_number
    try:
        parsed_number = phonenumbers.parse(phone_number, None)
        if not phonenumbers.is_valid_number(parsed_number):
            return render_template('index.html', error_msg="Please enter a phone number to begin.")
    except phonenumbers.phonenumberutil.NumberParseException:
        return render_template('index.html', error_msg="Please enter a phone number to begin.")

    # Fetch entries from the database associated with the phone number
    try:
        user = User.get(phone_number=phone_number)
        entries = user.entries
    except DoesNotExist:
        return render_template('index.html', error_msg="We don't have any entries associated with this number. You can text us at +1-888-255-4551 to record your first entry.")

    # format entries for display
    formatted_entries = []
    for entry in entries:
        escaped_content = html.escape(entry.content)
        formatted_date = entry.created.strftime('%b %d, %Y')
        formatted = {"id": entry.id, "content": escaped_content, "date": formatted_date}
        formatted_entries.append(formatted)
    return render_template('index.html', entries=formatted_entries, phone_number=phone_number)

# given an entry ID, view entry details
@app.route('/view_entry', methods=['POST'])
def view_entry():
    entry_id = request.form['entry_id']
    try:
        entry = Entry.get(id=entry_id)
        user = entry.user
    except DoesNotExist:
        return render_template('index.html', error_msg="We're sorry--something went wrong.")

    # format entry for display
    escaped_content = html.escape(entry.content)
    formatted_date = entry.created.strftime('%b %d, %Y at %I:%M%p')
    formatted = {"id": entry.id, "content": escaped_content, "date": formatted_date}
    return render_template('index.html', entry=formatted, phone_number=user.phone_number)

# webhook exposed to twilio that saves any incoming messages to db
@app.route('/sms', methods=['POST'])
def sms_reply():
    from_number = request.form['From']
    body = request.form['Body']
    with db.atomic():
        # get or create user associated to the phone number
        user, _ = User.get_or_create(phone_number=from_number)
        # create a diary entry with their message
        _ = Entry.create(user=user, content=body)
        # send ack with link
        resp = MessagingResponse()
        resp.message(
            'Noted! Visit [link] to view all of your entries.')
        return str(resp)

# take 10-digit phone number and turn it into our display format
def format_phone_for_display(phone):
    if phone.startswith('+1'):
        phone = phone[2:]
    if len(phone) < 8:
        return ''
    formatted = f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
    return formatted

# make format_phone_for_display a jinja filter
@app.template_filter('format_phone')
def format_phone_filter(phone):
    return format_phone_for_display(phone)

if __name__ == '__main__':
    app.run(debug=True)