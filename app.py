from flask import Flask, jsonify, render_template, request, redirect, url_for
import os
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from random import randint
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

@app.route('/send_code', methods=['POST'])
def send_code():
    phone = request.form['phone']
    code = randint(000000, 999999)  # Generate a random 6-digit code
    message = client.messages.create(
        body=f"Your verification code is {code}",
        from_=TWILIO_NUMBER,
        to=phone
    )
    with db.atomic():
        user, created = User.get_or_create(phone_number=phone.replace("-", ""))
        user.verification_code = code
        user.code_sent_at = datetime.now()
        user.save()
    return jsonify(success=True), 200

@app.route('/get_entries', methods=['POST'])
def get_entries():
    phone_number = request.form['phone']
    phone_number = phone_number.replace("-", "")
    phone_number = "+1"+phone_number
    if len(phone_number) == 2:
        return jsonify(error = "Please enter a phone number to begin"), 404
    # Fetch entries from the database associated with the phone number
    with db.atomic():
        try:
            user = User.get(phone_number=phone_number)
            entries = user.entries
            print(entries)
        except DoesNotExist:
            return jsonify(error = "We don't have any entries associated with this number. You can text us at +1-888-255-4551 to record your first entry."), 404
    
    formatted_entries = []
    for entry in entries:
        escaped_content = html.escape(entry.content)
        print(escaped_content)
        formatted = {"id": entry.id, "content": escaped_content, "date": entry.created}
        formatted_entries.append(formatted)
    return jsonify(entries=formatted_entries), 200


@app.route('/sms', methods=['POST'])
def sms_reply():
    from_number = request.form['From']
    body = request.form['Body']
    print(from_number)
    print(body)
    with db.atomic():
        user, _ = User.get_or_create(phone_number=from_number)
        new_entry = Entry.create(user=user, content=body)
        resp = MessagingResponse()
        resp.message(
            'Noted! Visit [link] to view all of your entries.')
        return str(resp)
    return 'Number not recognized', 400


if __name__ == '__main__':
    app.run(debug=True)