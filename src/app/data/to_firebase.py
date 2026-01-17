import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# 1. Initialize Firebase with your service account key
service_account_path = os.path.join(script_dir, "serviceAccountKey.json")
cred = credentials.Certificate(service_account_path)
firebase_admin.initialize_app(cred)

# 2. Get Firestore client
db = firestore.client()

def upload_politicians():
    # 3. Load your data.json file
    data_json_path = os.path.join(script_dir, "data.json")
    with open(data_json_path, 'r') as f:
        data = json.load(f)

    # 4. Access the 'Politician' array in your JSON
    # If your JSON root is different, adjust this line
    politicians = data.get('Politician', [])

    print(f"Starting upload of {len(politicians)} politicians...")

    for person in politicians:
        name = person.get('Name')
        year = person.get('Year')
        if not name or not year:
            continue
            
        # Create a unique Document ID using Name and Year (e.g., "Gavin Newsom" 2018 -> "Gavin_Newsom_2018")
        doc_id = f"{name.replace(' ', '_')}_{year}"
        
        # 5. Upload to the 'Politicians' collection
        db.collection('Politicians').document(doc_id).set(person)
        print(f"Successfully uploaded: {name}")

    print("Data upload complete!")

if __name__ == "__main__":
    upload_politicians()