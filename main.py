from datetime import timedelta
from flask import Flask, request, jsonify, render_template
import firebase_admin
from firebase_admin import credentials, firestore, storage
import requests
from datetime import datetime

app = Flask(__name__)

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {"storageBucket": "bobthebuilders1234.appspot.com"})

db = firestore.client()
bucket = storage.bucket()


@app.route("/", methods=["GET"])
def home():
    users_ref = db.collection("Conversations")
    docs = users_ref.stream()
    data = []
    for doc in docs:
        user_data = doc.to_dict()
        user_id = doc.id
        data.append({user_id: user_data})
        print(data)

    return render_template("index.html", data=data)


def create_folder_in_storage(folder_name):
    blob = bucket.blob(f"{folder_name}/")
    blob.upload_from_string(
        "", content_type="application/x-www-form-urlencoded;charset=UTF-8"
    )


@app.route("/create_user", methods=["POST"])
def create_user():
    data = request.json
    user_id = data.get("user_id")
    user_profile = data.get("user_profile", {})

    # Create user document with the specified structure
    user_data = {
        "Conversations": [],
        "UserProfile": {
            "UserName": user_profile.get("UserName", ""),
            "PhoneNumber": user_profile.get("PhoneNumber"),
            "Email": user_profile.get("Email", ""),
            "BusinessName": user_profile.get("BusinessName", ""),
            "Location": user_profile.get("Location", ""),
            "YearsInBusiness": user_profile.get("YearsInBusiness"),
            "BankingHistory": user_profile.get("BankingHistory", []),
            "created_at": firestore.SERVER_TIMESTAMP
        }
    }

    db.collection("Conversations").document(user_id).set(user_data)

    create_folder_in_storage(f"conversations/{user_id}")
############################### Throw error if user already exists ###############################
    return jsonify({"message": "User created successfully!", "user_id": user_id}), 201


@app.route("/create_conversation", methods=["POST"])
def create_conversation():
    data = request.json
    user_id = data.get("user_id")
    conversation = data.get("conversation")
    conversation_id = conversation.get("ConversationId")

    user_ref = db.collection("Conversations").document(user_id)

    try:
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            conversations = user_data.get("Conversations", [])

            existing_conv = next((conv for conv in conversations if conv.get("ConversationId") == conversation_id), None)
 
            if existing_conv:
                existing_conv.update(conversation)
                user_ref.update({"Conversations": conversations})
            else:
                user_ref.update({"Conversations": firestore.ArrayUnion([conversation])})
        else:
            user_ref.set({"Conversations": [conversation]})

        folder_path = f"conversations/{user_id}/{conversation_id}/"
        folder_blob = bucket.blob(folder_path)
        if not folder_blob.exists():
            create_folder_in_storage(folder_path.rstrip('/'))

        return jsonify({
            "message": "Conversation created or updated successfully!",
            "conversation_id": conversation_id,
        }), 201

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/get_conversation/<user_id>/<conversation_id>", methods=["GET"])
def get_conversation(user_id, conversation_id):
    user_ref = db.collection("Conversations").document(user_id).get()
    if user_ref.exists():
        user_data = user_ref.to_dict()
        conversations = user_data.get("Conversations", [])
        for conversation in conversations:
            if conversation.get("ConversationId") == conversation_id:
                return jsonify(conversation), 200
    return jsonify({"message": "Conversation not found"}), 404


@app.route("/get_message/<user_id>/<conversation_id>/<message_id>", methods=["GET"])
def get_message(user_id, conversation_id, message_id):
    user_ref = db.collection("Conversations").document(user_id).get()
    if user_ref.exists():
        user_data = user_ref.to_dict()
        conversations = user_data.get("Conversations", [])
        for conversation in conversations:
            if conversation.get("ConversationId") == conversation_id:
                messages = conversation.get("ConversationMessages", {}).get(
                    "Messages", []
                )
                for message in messages:
                    if message.get("MessageId") == message_id:
                        return jsonify(message), 200
    return jsonify({"message": "Message not found"}), 404


@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    print("Request JSON:", request.json)
    print("Request Form:", dict(request.form))
    print("Request Files:", {key: file.filename for key, file in request.files.items()})
    return jsonify({"a": "a"}), 200

    # file = request.files["file"]
    # user_id = request.form["user_id"]
    # conversation_id = request.form["conversation_id"]
    # message_id = request.form["message_id"]

    # # Get the file extension
    # file_extension = file.filename.split(".")[-1]

    # # Generate file name
    # timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # file_name = f"{message_id}_{timestamp}.{file_extension}"

    # # Upload file to Firebase Storage
    # blob = bucket.blob(f"conversations/{user_id}/{conversation_id}/{file_name}")
    # blob.upload_from_file(file)
    # blob.make_public()

    # # Update message with audio URL in Firestore
    # try:
    #     user_ref = db.collection("Conversations").document(user_id)
    #     user_snapshot = user_ref.get()

    #     if user_snapshot.exists:
    #         user_data = user_snapshot.to_dict()
    #         conversations = user_data.get("Conversations", [])
            
    #         # Find the specific conversation and message to update
    #         for conversation in conversations:
    #             if conversation.get("ConversationId") == conversation_id:
    #                 messages = conversation.get("ConversationMessages", {}).get("Messages", [])
    #                 for message in messages:
    #                     if message.get("MessageId") == message_id:
    #                         message["MessageAudio"] = blob.public_url
            
    #         # Update Firestore with new data
    #         user_ref.set(user_data)
    #         return jsonify({"message": "File uploaded successfully!", "url": blob.public_url}), 201
    #     else:
    #         return jsonify({"error": "User not found"}), 404

    # except Exception as e:
    #     return jsonify({"error": str(e)}), 500



@app.route("/upload_audio2", methods=["POST"])
def upload_audio2():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    if "user_id" not in request.form or "conversation_id" not in request.form or "message_id" not in request.form:
        return jsonify({"error": "Missing form data"}), 400
    
    file = request.files["file"]
    user_id = request.form["user_id"]
    conversation_id = request.form["conversation_id"]
    message_id = request.form["message_id"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Get the file extension
    file_extension = file.filename.split(".")[-1]

    # Generate file name
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f"{message_id}_{timestamp}.{file_extension}"

    # Upload file to Firebase Storage
    blob = bucket.blob(f"conversations/{user_id}/{conversation_id}/{file_name}")
    blob.upload_from_file(file)
    blob.make_public()

    # Update message with audio URL in Firestore
    try:
        user_ref = db.collection("Conversations").document(user_id)
        user_snapshot = user_ref.get()

        if user_snapshot.exists:
            user_data = user_snapshot.to_dict()
            conversations = user_data.get("Conversations", [])
            
            # Find the specific conversation and message to update
            for conversation in conversations:
                if conversation.get("ConversationId") == conversation_id:
                    messages = conversation.get("ConversationMessages", {}).get("Messages", [])
                    for message in messages:
                        if message.get("MessageId") == message_id:
                            message["MessageAudio"] = blob.public_url
                            break
                    else:
                        # If message not found, add a new message
                        messages.append({
                            "MessageId": message_id,
                            "MessageText": "",
                            "MessageAudio": blob.public_url,
                            "MessageTimeStamp": timestamp,
                            "MessageType": "User"  # or "Agent" based on your logic
                        })
                    conversation["ConversationMessages"]["Messages"] = messages
                    break
            else:
                # If conversation not found, add a new conversation
                new_conversation = {
                    "ConversationId": conversation_id,
                    "ConversationMessages": {
                        "DefaultMessage": {
                            "DefaultMessageText": "Namaste, main aapki kaise madad kar sakta hoon?",
                            "DefaultMessageAudioURL": "https://example.com/default-audio.mp3"
                        },
                        "Messages": [{
                            "MessageId": message_id,
                            "MessageText": "",
                            "MessageAudio": blob.public_url,
                            "MessageTimeStamp": timestamp,
                            "MessageType": "User"  # or "Agent" based on your logic
                        }]
                    }
                }
                conversations.append(new_conversation)
            user_data["Conversations"] = conversations

            # Update Firestore with new data
            user_ref.set(user_data)
            return jsonify({"message": "File uploaded successfully!", "url": blob.public_url}), 201
        else:
            # If user not found, create a new user document
            new_user_data = {
                "Conversations": [{
                    "ConversationId": conversation_id,
                    "ConversationMessages": {
                        "DefaultMessage": {
                            "DefaultMessageText": "Namaste, main aapki kaise madad kar sakta hoon?",
                            "DefaultMessageAudioURL": "https://example.com/default-audio.mp3"
                        },
                        "Messages": [{
                            "MessageId": message_id,
                            "MessageText": "",
                            "MessageAudio": blob.public_url,
                            "MessageTimeStamp": timestamp,
                            "MessageType": "User"  # or "Agent" based on your logic
                        }]
                    }
                }],
                "UserProfile": {
                    "UserName": "",
                    "BusinessName": "",
                    "Location": "",
                    "YearsInBusiness": 0,
                    "BankingHistory": []
                }
            }
            user_ref.set(new_user_data)
            return jsonify({"message": "User and file created successfully!", "url": blob.public_url}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get_audio/<filename>", methods=["GET"])
def get_audio(filename):
    blob = bucket.blob(filename)
    if blob.exists():
        audio_url = blob.generate_signed_url(timedelta(minutes=15))
        return jsonify({"audio_url": audio_url}), 200
    return jsonify({"message": "Audio file not found"}), 404


@app.route("/ai_response", methods=["POST"])
def ai_response():
    data = request.json
    user_id = data.get("user_id")
    conversation_id = data.get("conversation_id")
    message_id = data.get("message_id")
    message = data.get("message")

    # Call AI conversation service (replace with actual AI service URL and parameters)
    ai_service_url = "https://api.example.com/ai_conversation"
    response = requests.post(ai_service_url, json={"message": message})

    if response.status_code == 200:
        ai_message = response.json().get("response")
        # Save AI response in the conversation
        user_ref = db.collection("Conversations").document(user_id).get()
        if user_ref.exists():
            user_data = user_ref.to_dict()
            conversations = user_data.get("Conversations", [])
            for conversation in conversations:
                if conversation.get("ConversationId") == conversation_id:
                    messages = conversation.get("ConversationMessages", {}).get(
                        "Messages", []
                    )
                    messages.append(
                        {
                            "MessageId": message_id,
                            "MessageText": ai_message,
                            "MessageAudio": "",
                            "MessageTimeStamp": datetime.now().isoformat(),
                            "MessageType": "Agent",
                        }
                    )
            db.collection("Conversations").document(user_id).set(user_data)
        return jsonify({"ai_response": ai_message}), 200
    return jsonify({"message": "AI service failed"}), 500


@app.route("/get_user/<user_id>", methods=["GET"])
def get_user(user_id):
    user_ref = db.collection("users").document(user_id).get()
    if user_ref.exists():
        return jsonify(user_ref.to_dict()), 200
    return jsonify({"message": "User not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)
