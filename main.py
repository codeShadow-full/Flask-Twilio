from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import pandas as pd

main = Flask(__name__)

def loadData():
    customers = pd.read_excel("customers.xlsx")
    services = pd.read_excel("services.xlsx")
    orders = pd.read_excel("orders.xlsx")
    return customers, services, orders

@main.route("/voice", methods=['GET', 'POST'])
def voice():
    resp = VoiceResponse()
    caller_number = request.form.get("From")
    customers, services, _ = loadData()

    customer = customers[customers["Phone Number"] == caller_number]

    if not customer.empty:
        name = customer["Name"]
        resp.say(f"Hello {name}, welcome, How can I help you today? Here are available services:")
        for service in services["Service Description"]:
            resp.say(service)
        
        resp.record(
            transcribe=True,
            transcribe_callback="/order",
            max_length=60,  # Max recording length in seconds
            play_beep=True
        )
        resp.say("Thank you. Goodbye!")
        return str(resp)

@main.route("/order", methods=['POST'])
def transcription():
    transcription_text = request.form.get('TranscriptionText', '')
    from_number = request.form.get('From', '')
    print(f"Received transcription from {from_number}: {transcription_text}")

    customers, services, _ = loadData()

    for service in services["Service Description"]:
        if service in transcription_text.lower():
            pass
    # Custom response based on transcription
    if "price" in transcription_text.lower():
        response_text = "The price for our service starts at 50 dollars. Let us know if you need more details."
    elif "hours" in transcription_text.lower():
        response_text = "Our working hours are from 9 AM to 5 PM, Monday through Friday."
    else:
        response_text = "Thank you for your message. We will get back to you shortly."

    # Call back the user with the response
    call = client.calls.create(
        to=from_number,
        from_='your_twilio_number',  # Your Twilio phone number
        twiml=f'<Response><Say voice="alice">{response_text}</Say></Response>'
    )

    print(f"Responded with: {response_text}")
    return ('', 204)

   

@main.route("/")
def home():
    return("Flask server is running. Access the /voice endpoint for Twilio calls.")

if __name__ == "__main__":
    main.run(debug=True)