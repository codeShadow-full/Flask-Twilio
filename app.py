import os
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI and Flask
openai_client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

# Load Excel files
def load_data():
    customers = pd.read_excel("customers.xlsx")
    services = pd.read_excel("services.xlsx")
    orders = pd.read_excel("orders.xlsx")
    return customers, services, orders


def save_order(phone_number, service_id):
    orders = pd.read_excel("orders.xlsx")
    new_order = {
        "Order ID": len(orders) + 1,
        "Phone Number": phone_number,
        "Service ID": service_id,
        "Order Date": datetime.now()
    }
    orders = pd.concat([orders, pd.DataFrame([new_order])], ignore_index=True)
    orders.to_excel("orders.xlsx", index=False)

def register_customer(phone, name, address):
    customers = pd.read_excel("customers.xlsx")
    new_customer = {"Phone Number": phone, "Name": name, "Address": address}
    customers = pd.concat([customers, pd.DataFrame([new_customer])], ignore_index=True)
    customers.to_excel("customers.xlsx", index=False)

# OpenAI function to process conversation
def ask_openai(prompt):
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are an office receptionist."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

@app.route("/answer", methods=["POST"])
def answer():
    caller_number = request.form.get("From")
    customers, services, _ = load_data()

    # Check if customer exists
    customer = customers[customers["Phone Number"] == caller_number]
    response = VoiceResponse()

    if not customer.empty:
        name = customer["Name"]
        
        response.say(f"Hello {name}, welcome back. How can I help you today?")

        # response.say(f"Hello {name}, welcome back. How can I help you today? Here are available services:")
        # for service in services["Service Description"]:
        #     response.say(service)

        # response.say("What kind of service do you want?")

        gather = Gather(input="speech", timeout=5, action="/process_order")
        response.append(gather)
    else:
        response.say("Hello, I see you are a new customer. Please say your name and address after the beep.")
        gather = Gather(input="speech", timeout=10, action="/register_customer", method="POST")
        response.append(gather)
    return Response(str(response), mimetype="application/xml")

@app.route("/process_order", methods=["POST"])
def process_order():
    speech_result = request.form.get("SpeechResult")
    caller_number = request.form.get("From")
    customers, services, _ = load_data()

    # for service in services:
    #     if service in speech_result:
    #         price = service["Price"]
    #         service_name = service["Service Description"]
    #         response = VoiceResponse()
    #         response.say(f"The price for {service_name} is {price} dollars. Say 'confirm' to place the order.")
    #         gather = Gather(input="speech", timeout=5, action="/confirm_order", method="POST")
    #         response.append(gather)
    #         response.append("I did not hear your confirmation.")
    #         return Response(str(response), mimetype="application/xml")

    # response = VoiceResponse()
    # response.say("Sorry, I could not identify the service. Please try again.")
    # return Response(str(response), mimetype="application/xml")

    service_prompt = f"Identify the service ID from the following description: {speech_result}. Here are available services: {services.to_dict('records')}"
    service_response = ask_openai(service_prompt)
    
    try:
        service_id = service["Service ID"]
        service = services[services["Service ID"] == service_id]
        price = service["Price"]
        service_name = service["Service Description"]
        response = VoiceResponse()
        response.say(f"The price for {service_name} is {price} dollars. Say 'confirm' to place the order.")
        gather = Gather(input="speech", timeout=5, action="/confirm_order", method="POST")
        response.append(gather)
        response.append("I did not hear your confirmation.")
        return Response(str(response), mimetype="application/xml")
    except Exception:
        response = VoiceResponse()
        response.say("Sorry, I could not identify the service. Please try again.")
        return Response(str(response), mimetype="application/xml")

@app.route("/confirm_order", methods=["POST"])
def confirm_order():
    speech_result = request.form.get("SpeechResult").lower()
    caller_number = request.form.get("From")

    if "confirm" in speech_result:
        _, _, orders = load_data()
        last_order = orders[-1]
        save_order(caller_number, last_order["Service ID"])
        response = VoiceResponse()
        response.say("Your order has been confirmed. Thank you for choosing us. Goodbye!")
    else:
        response = VoiceResponse()
        response.say("Order not confirmed. If you need anything else, please call again. Goodbye!")
    return Response(str(response), mimetype="application/xml")

@app.route("/register_customer", methods=["POST"])
def register():
    speech_result = request.form.get("SpeechResult")
    caller_number = request.form.get("From")
    
    # Extract name and address using OpenAI
    register_prompt = f"Extract name and address from: {speech_result}. Return in the format 'Name: [name], Address: [address]'"
    result = ask_openai(register_prompt)
    name = result.split("Name:")[1].split(", Address:")[0].strip()
    address = result.split("Address:")[1].strip()
    register_customer(caller_number, name, address)

    response = VoiceResponse()
    response.say(f"Thank you {name}. Your information has been saved. Now, please describe the service you want.")

    # response.say(f"Thank you {name}. Your information has been saved. Now, please describe the service you want. Here are available services:")
    # for service in services["Service Description"]:
    #     response.say(service)
    # response.say("What kind of service do you want?")
    
    gather = Gather(input="speech", timeout=5, action="/process_order")
    response.append(gather)
    return Response(str(response), mimetype="application/xml")

@app.route("/")
def home():
    return("Flask server is running. Access the /voice endpoint for Twilio calls.")

if __name__ == "__main__":
    app.run(debug=True)
