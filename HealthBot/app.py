import streamlit as st
import spacy
from spacy.matcher import Matcher
from spacy.lang.en import STOP_WORDS
import random
import sqlite3
import time
from hashlib import sha256
from PIL import Image
import io
import base64
import os

# Load spaCy model for NLP
@st.cache_resource
def load_nlp_model():
    return spacy.load('en_core_web_sm')

nlp = load_nlp_model()

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )''')
    conn.commit()
    conn.close()

# Hash password
def hash_password(password):
    return sha256(password.encode()).hexdigest()

# Check user credentials
def check_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    stored_password = c.fetchone()
    conn.close()
    return stored_password and stored_password[0] == hash_password(password)

# Register a new user
def register_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# Custom background for the Streamlit app
def set_background(image_url):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{image_url}");
            background-size: cover;
            background-position: center;
            animation: slide 10s infinite alternate;
        }}
        @keyframes slide {{
            0% {{ background-position: 0% 0%; }}
            100% {{ background-position: 100% 100%; }}
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Basic conversation responses
greetings = {
    'hi': 'Hello! How can I assist you today?',
    'hello': 'Hi there! How can I help you?',
    'how are you': "I'm functioning well, thank you! How can I assist you with your health questions?",
    'bye': "Take care! Remember, I'm here if you need any health information.",
    'thanks': "You're welcome! Is there anything else I can help you with?"
}

# Expanded health advice with additional conditions
health_advice = {
    'fever': {
        'symptoms': 'Elevated body temperature, chills, sweating, dehydration, weakness.',
        'causes': 'Viral or bacterial infections, heat exhaustion, certain medications.',
        'treatment': 'Rest, stay hydrated, take over-the-counter fever reducers like acetaminophen or ibuprofen. Seek medical attention if fever is high or persistent.',
        'prevention': 'Practice good hygiene, stay up to date on vaccinations, maintain a healthy lifestyle.',
    },
    'headache': {
        'symptoms': 'Pain in the head or face, sensitivity to light or sound, nausea.',
        'causes': 'Stress, dehydration, lack of sleep, eye strain, sinus congestion, or more serious conditions.',
        'treatment': 'Over-the-counter pain relievers, rest in a dark quiet room, stay hydrated, apply cold or warm compress.',
        'prevention': 'Manage stress, maintain regular sleep schedule, stay hydrated, limit screen time.',
    },
    
    'common cold': {
        'symptoms': 'Runny or stuffy nose, sore throat, cough, mild fever, fatigue.',
        'causes': 'Viral infection, most commonly rhinoviruses.',
        'treatment': 'Rest, stay hydrated, over-the-counter decongestants and pain relievers, throat lozenges, nasal sprays.',
        'prevention': 'Wash hands frequently, avoid close contact with infected individuals, boost immune system.'
    },
    'flu': {
        'symptoms': 'Sudden onset of fever, aches, fatigue, cough, sore throat, runny nose.',
        'causes': 'Influenza viruses.',
        'treatment': 'Rest, stay hydrated, antiviral medications if caught early, over-the-counter pain relievers and decongestants.',
        'prevention': 'Annual flu vaccination, good hygiene practices, boosting immune system.'
    },
    'allergies': {
        'symptoms': 'Sneezing, runny nose, itchy eyes, skin rashes.',
        'causes': 'Reaction to allergens like pollen, dust, pet dander, certain foods.',
        'treatment': 'Antihistamines, nasal corticosteroids, decongestants.',
        'prevention': 'Identify and avoid triggers, keep living spaces clean, use air purifiers.'
    },
    'stomach ache': {
        'symptoms': 'Pain or discomfort in the stomach, nausea, bloating.',
        'causes': 'Indigestion, overeating, gastritis, food poisoning.',
        'treatment': 'Over-the-counter antacids, rest, avoid heavy foods, stay hydrated.',
        'prevention': 'Eat slowly, avoid trigger foods, manage stress.'
    },
    'sore throat': {
        'symptoms': 'Pain or irritation in the throat, difficulty swallowing.',
        'causes': 'Viral infections, bacterial infections, allergies, dry air.',
        'treatment': 'Gargle with salt water, throat lozenges, over-the-counter pain relievers.',
        'prevention': 'Practice good hygiene, avoid smoking, stay hydrated.'
    },
    'cough': {
        'symptoms': 'Forceful expulsion of air from the lungs, can be dry or productive.',
        'causes': 'Infections, allergies, asthma, acid reflux.',
        'treatment': 'Over-the-counter cough medicines, honey, stay hydrated.',
        'prevention': 'Avoid irritants, quit smoking, treat underlying conditions.'
    },
    'rash': {
        'symptoms': 'Skin irritation, redness, itching, bumps.',
        'causes': 'Allergic reactions, infections, heat, stress.',
        'treatment': 'Anti-itch creams, cool compresses, antihistamines.',
        'prevention': 'Identify and avoid triggers, use gentle skincare products.'
    },
    'earache': {
        'symptoms': 'Pain in the ear, reduced hearing, fever.',
        'causes': 'Ear infections, wax buildup, sinus infections.',
        'treatment': 'Over-the-counter pain relievers, warm compress, see a doctor if severe.',
        'prevention': 'Avoid inserting objects in ears, treat allergies and colds promptly.'
    },
    'toothache': {
        'symptoms': 'Pain in or around a tooth, sensitivity to hot or cold.',
        'causes': 'Cavities, gum disease, cracked tooth, infection.',
        'treatment': 'Over-the-counter pain relievers, cold compress, see a dentist.',
        'prevention': 'Regular dental hygiene, avoid sugary foods, regular dental check-ups.'
    },
    'backache': {
        'symptoms': 'Pain in the back, stiffness, limited range of motion.',
        'causes': 'Poor posture, lifting heavy objects, sedentary lifestyle.',
        'treatment': 'Rest, gentle stretches, over-the-counter pain relievers, heat or cold therapy.',
        'prevention': 'Maintain good posture, exercise regularly, use proper lifting techniques.'
    },
    'nausea': {
        'symptoms': 'Feeling of sickness with an inclination to vomit, stomach discomfort.',
        'causes': 'Food poisoning, motion sickness, pregnancy, medications.',
        'treatment': 'Rest, stay hydrated, eat bland foods, ginger tea, anti-nausea medications.',
        'prevention': 'Eat slowly, avoid trigger foods, practice good food hygiene.'
    },
    'diarrhea': {
        'symptoms': 'Loose, watery stools, abdominal cramps, urgency to use the bathroom.',
        'causes': 'Viral or bacterial infections, food intolerances, medications.',
        'treatment': 'Stay hydrated, eat bland foods, probiotics, over-the-counter anti-diarrheal medications.',
        'prevention': 'Practice good hygiene, avoid contaminated food and water.'
    },
    'constipation': {
        'symptoms': 'Infrequent bowel movements, difficulty passing stools, abdominal discomfort.',
        'causes': 'Low fiber diet, dehydration, lack of physical activity, certain medications.',
        'treatment': 'Increase fiber intake, stay hydrated, exercise, over-the-counter laxatives if needed.',
        'prevention': 'Eat a high-fiber diet, stay hydrated, regular exercise.'
    },
    'indigestion': {
        'symptoms': 'Discomfort in upper abdomen, feeling of fullness, burning sensation.',
        'causes': 'Overeating, eating too quickly, fatty or spicy foods, stress.',
        'treatment': 'Over-the-counter antacids, avoid trigger foods, eat slowly.',
        'prevention': 'Eat smaller meals, avoid trigger foods, manage stress.'
    },
    'sunburn': {
        'symptoms': 'Red, painful skin that feels hot to the touch, possible blistering.',
        'causes': 'Overexposure to UV radiation from the sun.',
        'treatment': 'Cool compresses, aloe vera gel, moisturizer, over-the-counter pain relievers.',
        'prevention': 'Use sunscreen, wear protective clothing, limit sun exposure during peak hours.'
    },
    'insomnia': {
        'symptoms': 'Difficulty falling asleep or staying asleep, daytime fatigue.',
        'causes': 'Stress, anxiety, caffeine, irregular sleep schedule.',
        'treatment': 'Improve sleep hygiene, relaxation techniques, cognitive behavioral therapy.',
        'prevention': 'Regular sleep schedule, avoid screens before bedtime, manage stress.'
    },
    'sprain': {
        'symptoms': 'Pain, swelling, bruising, limited mobility in the affected joint.',
        'causes': 'Sudden twisting or force on a joint.',
        'treatment': 'RICE (Rest, Ice, Compression, Elevation), over-the-counter pain relievers.',
        'prevention': 'Proper warm-up before exercise, wear supportive shoes, strengthen muscles.'
    },
    'acne': {
        'symptoms': 'Pimples, blackheads, whiteheads, oily skin.',
        'causes': 'Hormonal changes, excess oil production, bacteria, clogged pores.',
        'treatment': 'Over-the-counter acne products, proper skincare routine, prescription medications if severe.',
        'prevention': 'Regular face washing, non-comedogenic products, healthy diet.'
    },
    'motion sickness': {
        'symptoms': 'Nausea, dizziness, cold sweats, vomiting.',
        'causes': 'Conflicting sensory signals to the brain during movement.',
        'treatment': 'Over-the-counter motion sickness medications, focus on a stable object, get fresh air.',
        'prevention': 'Sit in areas with less motion, look at the horizon, avoid reading while in motion.'
    },
    'eye strain': {
        'symptoms': 'Sore or irritated eyes, difficulty focusing, headaches.',
        'causes': 'Prolonged screen time, reading without proper lighting, need for vision correction.',
        'treatment': 'Rest eyes, adjust lighting, use artificial tears.',
        'prevention': '20-20-20 rule (every 20 minutes, look at something 20 feet away for 20 seconds), proper lighting.'
    },
    'dehydration': {
        'symptoms': 'Thirst, dry mouth, dark urine, fatigue, dizziness.',
        'causes': 'Not drinking enough water, excessive sweating, diarrhea, vomiting.',
        'treatment': 'Drink water or electrolyte solutions, rest, seek medical attention if severe.',
        'prevention': 'Drink adequate water throughout the day, increase intake during hot weather or exercise.'
    },
    'heartburn': {
        'symptoms': 'Burning sensation in the chest or throat, bitter taste in mouth.',
        'causes': 'Acid reflux, certain foods, obesity, pregnancy.',
        'treatment': 'Over-the-counter antacids, avoid trigger foods, eat smaller meals.',
        'prevention': 'Maintain healthy weight, avoid lying down after meals, limit acidic and spicy foods.'
    },
    'muscle strain': {
        'symptoms': 'Pain, swelling, limited range of motion in affected muscle.',
        'causes': 'Overexertion, improper lifting, sudden movements.',
        'treatment': 'Rest, ice, compression, elevation, over-the-counter pain relievers.',
        'prevention': 'Proper warm-up before exercise, use correct form when lifting, gradual increase in activity.'
    },
    'nose bleed': {
        'symptoms': 'Blood flowing from one or both nostrils.',
        'causes': 'Dry air, nose picking, injury, blood thinners.',
        'treatment': 'Pinch nostrils, lean forward, apply cold compress to nose.',
        'prevention': 'Use a humidifier, avoid nose picking, use saline nasal spray to keep nasal passages moist.'
    },
    'anxiety': {
        'symptoms': 'Excessive worry, restlessness, difficulty concentrating, sleep problems.',
        'causes': 'Stress, traumatic experiences, genetic factors, brain chemistry.',
        'treatment': 'Therapy, relaxation techniques, medications in severe cases.',
        'prevention': 'Regular exercise, adequate sleep, stress management techniques, limit caffeine and alcohol.'
    },
    'burns': {
        'symptoms': 'Skin redness, pain, swelling, blistering (depending on severity).',
        'causes': 'Contact with heat, chemicals, electricity, or radiation.',
        'treatment': 'Cool the burn with running water, apply aloe vera, cover with sterile gauze.',
        'prevention': 'Use caution around hot objects, wear protective gear when handling chemicals.'
    },
    'food poisoning': {
        'symptoms': 'Nausea, vomiting, diarrhea, abdominal pain, fever.',
        'causes': 'Consuming contaminated food or drink.',
        'treatment': 'Rest, stay hydrated, eat bland foods when able, seek medical attention if severe.',
        'prevention': 'Practice good food hygiene, cook foods thoroughly, avoid risky foods.'
    },
    'migraine': {
        'symptoms': 'Severe headache, often one-sided, sensitivity to light and sound, nausea.',
        'causes': 'Hormonal changes, certain foods, stress, environmental factors.',
        'treatment': 'Rest in dark quiet room, over-the-counter pain relievers, prescription medications.',
        'prevention': 'Identify and avoid triggers, maintain regular sleep and meal schedules, manage stress.'
    },
    'pink eye': {
        'symptoms': 'Redness, itching, and discharge in one or both eyes.',
        'causes': 'Viral or bacterial infection, allergies.',
        'treatment': 'Artificial tears, warm compresses, antibiotic eye drops if bacterial.',
        'prevention': 'Practice good hygiene, avoid touching or rubbing eyes, do not share personal items.'
    },
    'urinary tract infection': {
        'symptoms': 'Frequent urination, burning sensation when urinating, cloudy urine.',
        'causes': 'Bacteria entering the urinary tract.',
        'treatment': 'Antibiotics, drink plenty of water, urinate frequently.',
        'prevention': 'Stay hydrated, urinate after sexual activity, wipe from front to back.'
    }
}
symptom_weights = {
    "fever": 2,
    "cough": 2,
    "sore throat": 1.5,
    "headache": 2,
    "fatigue": 1.5,
    "nasal congestion": 1.5,
    "runny nose": 1.5,
    "sneezing": 1.5,
    "itchy eyes": 1.5,
    "skin rash": 1.5,
    "stomach ache": 2,
    "nausea": 2,
    "vomiting": 2,
    "diarrhea": 2,
    "constipation": 1.5,
    "indigestion": 1.5,
    "sunburn": 2,
    "insomnia": 1.5,
    "sprain": 2,
    "acne": 1.5,
    "motion sickness": 1.5,
    "eye strain": 1.5,
    "dehydration": 2,
    "heartburn": 1.5,
    "muscle strain": 2,
    "nosebleed": 1.5,
    "anxiety": 2,
    "burns": 2,
    "food poisoning": 2,
    "migraine": 2,
    "pink eye": 1.5,
    "urinary tract infection": 2,
    "back pain": 2,
    "chest pain": 2,
    "shortness of breath": 2,
    "swelling": 1.5,
    "bruising": 1.5,
    "weakness": 1.5,
    "numbness": 1.5,
    "tingling": 1.5,
    "loss of appetite": 1.5,
    "weight loss": 1.5,
    "weight gain": 1.5,
    "changes in vision": 1.5,
    "changes in hearing": 1.5,
    "difficulty swallowing": 1.5,
    "difficulty urinating": 1.5,
    "changes in bowel habits": 1.5,
    "skin changes": 1.5,
    "hair loss": 1.5,
    "nail changes": 1.5,
    "frequent urination": 1.5,
    "night sweats": 1.5,
    "cold sweats": 1.5,
    "chills": 1.5,
    "fever": 2,
    "fatigue": 1.5,
    "joint pain": 2,
    "stiffness": 1.5,
    "swelling": 1.5,
    "redness": 1.5,
    "itching": 1.5,
    "pain": 2,
    "discomfort": 2,
    "tenderness": 1.5
}
def get_response(user_input):
    if "hello" in user_input:
        if "logged_in" in st.session_state and st.session_state.logged_in:
            return "Welcome back!"
        else:
            return "Hello! How can I assist you today?"
    elif "bye" in user_input:
        return "Goodbye!"

    user_input = user_input.lower()

    # Check for basic conversational responses
    for key in greetings:
        if key in user_input:
            return greetings[key]

    # Check for detailed health advice
    for condition, info in health_advice.items():
        if condition in user_input:
            response = f"Here's what I know about {condition}:\n\n"
            for key, value in info.items():
                response += f"{key.capitalize()}: {value}\n\n"
            return response

    # Extract symptoms from user input using NLP
    extracted_symptoms = extract_symptoms(user_input)

    # Calculate a likelihood score for each condition based on symptom weights
    condition_scores = {}
    for condition, info in health_advice.items():
        condition_score = 0
        for symptom in extracted_symptoms:
            if symptom in info['symptoms']:
                condition_score += symptom_weights[symptom]
        condition_scores[condition] = condition_score

    # Find the condition with the highest score
    most_likely_condition = max(condition_scores, key=condition_scores.get)
    # Identify conditions with scores above a threshold
    threshold = 2  # Adjust threshold as needed
    possible_conditions = [condition for condition, score in condition_scores.items() if score >= threshold]

    if len(possible_conditions) > 1:
        response = "Based on your symptoms, you might have:\n"
        for condition in possible_conditions:
            response += f"- {condition}\n"
        response += "\nIt's important to consult a healthcare professional for a proper diagnosis and treatment plan."
    else:

    # Return the most likely condition and its information
        return f"Based on your symptoms, the most likely condition is: {most_likely_condition}\n\n{health_advice[most_likely_condition]}"

def extract_symptoms(user_input):
    nlp = spacy.load("en_core_web_sm")
    matcher = Matcher(nlp.vocab)

    # Define patterns for common symptom expressions
    patterns = [
        [{"POS": "ADJ", "DEP": "amod"}, {"POS": "NOUN"}],  # Example: "high fever"
        [{"POS": "VERB", "DEP": "ROOT"}, {"POS": "NOUN"}],  # Example: "have a headache"
        [{"POS": "NOUN"}, {"POS": "ADJ"}],  # Example: "painful throat"
        [{"POS": "VERB"}, {"POS": "ADJ"}],  # Example: "feel dizzy"
    ]
    matcher.add("SYMPTOM", patterns)

    doc = nlp(user_input)
    matches = matcher(doc)

    extracted_symptoms = []
    for match_id, start, end in matches:
        span = doc[start:end]
        extracted_symptoms.append(span.text)
    # Remove stop words and duplicates
    extracted_symptoms = [entity for entity in extracted_symptoms if entity not in STOP_WORDS]
    extracted_symptoms = list(set(extracted_symptoms))

    return extracted_symptoms

    # If no match found, provide a general response
    general_responses = [
        "I'm not sure about that specific condition. Could you provide more details or symptoms?",
        "I don't have information on that particular issue. Is there a related health topic you'd like to know about?",
        "I'm afraid I don't have specific advice for that. Remember, it's always best to consult a healthcare professional for personalized medical advice.",
        "I don't have data on that. Can you rephrase your question or ask about a different health topic?"
    ]
    return random.choice(general_responses)

# Streamlit app
st.title("Health Chatbot with Authentication")

# Initialize database and session state
init_db()

# Authentication Section
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # Set a default background for login and registration
    set_background('https://media.giphy.com/media/3o7TKz2eMXx7dn95FS/giphy.gif?cid=ecf05e47480rkr9agsiw1mtgfndovyg2roi2a73efbha4ji1&ep=v1_gifs_related&rid=giphy.gif&ct=g')  # Example image URL

    # Check if the image file exists
    image_path = 'C:/Users/Dev Vyas/Downloads/1726302958547.png'
    if os.path.exists(image_path):
        # Create a sidebar with a centered image
        st.sidebar.markdown(
            f"""
            <style>
            .sidebar-image {{
                display: flex;
                justify-content: center;
                margin-bottom: 20px;
            }}
            </style>
            <div class="sidebar-image">
                <img src="data:image/png;base64,{base64.b64encode(open(image_path, "rb").read()).decode()}" width="150" />
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.sidebar.error("Image file not found.")

    # Choose between login and registration
    st.sidebar.title("Login / Register")
    option = st.sidebar.selectbox("Select an option", ["Login", "Register"])

    if option == "Register":
        st.header("Register")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        register_button = st.button("Register")

        if register_button:
            if register_user(username, password):
                st.success("Registration successful! You can now log in.")
            else:
                st.error("Username already exists or registration failed.")

    elif option == "Login":
        st.header("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.button("Login")

        if login_button:
            if check_user(username, password):
                st.session_state.logged_in = True
               # st.experimental_rerun()
            else:
                st.error("Invalid username or password.")

else:
    # Main Chatbot Interface
    # Set background for chatbot (Only if needed)
    # if 'background' not in st.session_state:
    #    st.session_state.background = 'https://media.giphy.com/media/3o7TKz2eMXx7dn95FS/giphy.gif?cid=ecf05e47480rkr9agsiw1mtgfndovyg2roi2a73efbha4ji1&ep=v1_gifs_related&rid=giphy.gif&ct=g'  # Default background

    # set_background(st.session_state.background)

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("What's your health question?"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        response = get_response(prompt)

        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    
    # Advanced HealthBot Section
    st.sidebar.title("Advanced HealthBot")
    advanced_option = st.sidebar.selectbox("Select an advanced feature", ["None", "Health Tips", "Recent Health Trends", "Symptom Checker", "Fitness Tracker", "Nutrition Advice"])

    if advanced_option == "Health Tips":
        st.header("Health Tips")
        st.markdown("Here are some general health tips to help you stay healthy and active:")
        st.markdown(
            """
            - *Stay Hydrated*: Drink plenty of water throughout the day to keep your body hydrated and support various bodily functions.
            - *Exercise Regularly*: Aim for at least 30 minutes of moderate exercise, like brisk walking or cycling, most days of the week to maintain cardiovascular health.
            - *Eat a Balanced Diet*: Include a variety of fruits, vegetables, lean proteins, and whole grains in your diet to ensure you get essential nutrients.
            - *Get Adequate Sleep*: Aim for 7-9 hours of quality sleep each night to support mental and physical health.
            - *Manage Stress*: Practice relaxation techniques such as deep breathing, meditation, or yoga to manage stress effectively.
            - *Maintain Good Hygiene*: Wash your hands regularly, and practice good oral hygiene to prevent infections.
            - *Regular Health Check-ups*: Schedule regular check-ups with your healthcare provider to monitor and maintain your health.
            """
        )

    elif advanced_option == "Recent Health Trends":
        st.header("Recent Health Trends")
        st.markdown("Stay updated with the latest health trends and news. Here's a snapshot of recent trends in health and wellness:")
        st.markdown(
            """
            - *Telehealth Expansion*: The use of telemedicine has significantly increased, offering patients virtual consultations and remote monitoring.
            - *Mental Health Awareness*: There is a growing focus on mental health, with more resources and support available for mental well-being.
            - *Wearable Health Tech*: Advances in wearable technology are helping individuals track their health metrics like heart rate, sleep patterns, and physical activity.
            - *Personalized Nutrition*: New research is highlighting the benefits of personalized nutrition plans based on individual health data and genetic information.
            - *Sustainable Health Practices*: There is a rising trend towards sustainable health practices, including plant-based diets and eco-friendly health products.
            """
        )

    elif advanced_option == "Symptom Checker":
        st.header("Symptom Checker")
        st.markdown("Enter your symptoms to get more information. This feature helps you understand possible causes and next steps.")
        symptoms = st.text_input("Describe your symptoms")
        if symptoms:
            st.markdown(f"Analyzing your symptoms: {symptoms}")
            st.markdown(
                """
                Based on your description, here are some potential causes and advice:
                - *Common Cold*: Symptoms like a runny nose and cough might indicate a common cold. Rest and stay hydrated.
                - *Flu*: If you have high fever and body aches, it could be the flu. Consider visiting a healthcare provider.
                - *Allergies*: Symptoms like sneezing and itchy eyes might be due to allergies. Avoid known allergens and consider antihistamines.
                - *Consult a Doctor*: For persistent or severe symptoms, it's important to consult a healthcare professional for a proper diagnosis.
                """
            )

    elif advanced_option == "Fitness Tracker":
        st.header("Fitness Tracker")
        st.markdown("Track your fitness activities and set goals to improve your physical health.")
        st.markdown(
            """
            - *Set Fitness Goals*: Define your fitness goals, whether it's to lose weight, build muscle, or improve endurance.
            - *Track Activities*: Log your daily physical activities, including workouts, steps, and active minutes.
            - *Monitor Progress*: Regularly review your progress and adjust your goals as needed.
            - *Get Recommendations*: Based on your activity levels, get personalized workout and fitness recommendations.
            """
        )

    elif advanced_option == "Nutrition Advice":
        st.header("Nutrition Advice")
        st.markdown("Get personalized nutrition advice to help you maintain a balanced diet and meet your health goals.")
        st.markdown(
            """
            - *Understand Macronutrients*: Learn about the importance of carbohydrates, proteins, and fats in your diet.
            - *Plan Balanced Meals*: Get tips on how to create balanced meals that include a variety of nutrients.
            - *Monitor Portion Sizes*: Understand portion sizes to avoid overeating and maintain a healthy weight.
            - *Stay Informed*: Keep up with the latest research on nutrition and dietary guidelines.
            """
        )


        # Add a sidebar with some information about the chatbot
    st.sidebar.title("About HealthBot")
    st.sidebar.info(
        "This HealthBot is designed to provide general health information and advice. "
        "Remember, it's not a substitute for professional medical advice. "
        "Always consult with a qualified healthcare provider for personalized medical guidance."
    )
    if st.session_state.logged_in:
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False