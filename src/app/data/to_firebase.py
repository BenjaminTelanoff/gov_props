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
    
    # Check for duplicates in the data and track which ones to process
    seen_in_batch = {}
    duplicates_in_data = []
    politicians_to_upload = []
    
    for i, person in enumerate(politicians):
        name = person.get('Name')
        year = person.get('Year')
        if not name or not year:
            continue
            
        key = f"{name}|{year}"
        if key in seen_in_batch:
            duplicates_in_data.append((i, name, year))
        else:
            seen_in_batch[key] = True
            politicians_to_upload.append(person)
    
    if duplicates_in_data:
        print(f"Warning: Found {len(duplicates_in_data)} duplicate Name/Year combinations in data.json:")
        for idx, name, year in duplicates_in_data:
            print(f"  - {name} ({year}) at index {idx}")
        print(f"Will upload {len(politicians_to_upload)} unique politicians...\n")

    uploaded = 0
    skipped = 0
    
    for person in politicians_to_upload:
        name = person.get('Name')
        year = person.get('Year')
        
        # Create a unique Document ID using Name and Year (e.g., "Gavin Newsom" 2018 -> "Gavin_Newsom_2018")
        doc_id = f"{name.replace(' ', '_')}_{year}"
        
        # Check if document already exists in Firestore
        existing_doc = db.collection('Politicians').document(doc_id).get()
        if existing_doc.exists:
            print(f"Skipping {name} ({year}) - already exists in Firestore")
            skipped += 1
            continue
        
        # Upload to the 'Politicians' collection
        db.collection('Politicians').document(doc_id).set(person)
        print(f"Successfully uploaded: {name} ({year})")
        uploaded += 1
    
    print(f"\nUpload complete! Uploaded: {uploaded}, Skipped: {skipped}")

    print("Data upload complete!")

if __name__ == "__main__":
    upload_politicians()