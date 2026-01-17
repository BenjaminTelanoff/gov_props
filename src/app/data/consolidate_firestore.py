"""
Consolidate politicians with multiple year entries in Firestore into a single entry.
Merges all propositions from different years into one politician entry.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Try to load from .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    env_paths = [
        os.path.join(script_dir, ".env"),
        os.path.join(script_dir, "..", "..", "..", ".env"),
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            break
except ImportError:
    pass

# Firebase initialization
service_account_path = os.path.join(script_dir, "serviceAccountKey.json")

if not firebase_admin._apps:
    if os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    else:
        firebase_creds = {
            "type": os.getenv("FIREBASE_TYPE") or "service_account",
            "project_id": os.getenv("FIREBASE_PROJECT_ID") or os.getenv("NG_APP_FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": os.getenv("FIREBASE_AUTH_URI") or "https://accounts.google.com/o/oauth2/auth",
            "token_uri": os.getenv("FIREBASE_TOKEN_URI") or "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL") or "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
            "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN") or "googleapis.com",
        }
        if firebase_creds.get("project_id") and firebase_creds.get("private_key") and firebase_creds.get("client_email"):
            cred = credentials.Certificate(firebase_creds)
            firebase_admin.initialize_app(cred)
        else:
            raise Exception("Firebase credentials not found. Set up serviceAccountKey.json or environment variables.")

db = firestore.client()


def consolidate_politicians_in_firestore():
    """Consolidate politicians with the same name across different years in Firestore."""
    
    # Get all politicians from Firestore
    politicians_ref = db.collection("Politicians")
    all_politicians = list(politicians_ref.stream())
    
    print(f"Found {len(all_politicians)} politicians in Firestore")
    
    # Group politicians by Name (case-insensitive)
    politicians_by_name = {}
    for politician_doc in all_politicians:
        data = politician_doc.to_dict() or {}
        name = data.get("Name", "").strip()
        if not name:
            continue
        
        # Use lowercase name as key for case-insensitive matching
        name_key = name.lower()
        
        if name_key not in politicians_by_name:
            politicians_by_name[name_key] = []
        politicians_by_name[name_key].append((politician_doc.id, politician_doc, data))
    
    # Find politicians with multiple entries
    to_consolidate = {k: v for k, v in politicians_by_name.items() if len(v) > 1}
    
    if not to_consolidate:
        print("\n[OK] No duplicates found. All politicians are unique.")
        return
    
    print(f"\nFound {len(to_consolidate)} politicians with multiple entries:")
    for name_key, entries in to_consolidate.items():
        print(f"  - {entries[0][2].get('Name')}: {len(entries)} entries")
    
    print("\nStarting consolidation...")
    
    consolidated_count = 0
    deleted_count = 0
    
    for name_key, entries in to_consolidate.items():
        politician_name = entries[0][2].get("Name")
        print(f"\nConsolidating {politician_name} ({len(entries)} entries)")
        
        # Sort by Year (most recent first, keep the most recent as base)
        entries_sorted = sorted(entries, key=lambda x: x[2].get("Year", 0), reverse=True)
        base_doc_id, base_doc, base_data = entries_sorted[0]
        other_entries = entries_sorted[1:]
        
        # Collect all propositions from all years
        all_propositions = base_data.get("Propositions", {}).copy()
        years_merged = [base_data.get("Year", "")]
        
        for other_doc_id, other_doc, other_data in other_entries:
            year = other_data.get("Year", "")
            years_merged.append(year)
            propositions = other_data.get("Propositions", {})
            
            # Merge propositions, handling ID conflicts
            for prop_id, prop in propositions.items():
                # If ID already exists, find next available ID
                if prop_id in all_propositions:
                    # Find max numeric ID
                    numeric_ids = [int(k) for k in all_propositions.keys() if k.isdigit()]
                    next_id = max(numeric_ids + [0]) + 1
                    prop_id = str(next_id)
                
                all_propositions[prop_id] = prop
        
        # Update base entry with merged propositions
        base_data["Propositions"] = all_propositions
        
        # Update Year to show range if multiple years
        if len(years_merged) > 1:
            years_merged_sorted = sorted([y for y in years_merged if y and isinstance(y, (int, str))], reverse=True)
            if len(years_merged_sorted) > 1:
                try:
                    years_int = [int(y) for y in years_merged_sorted if str(y).isdigit()]
                    if years_int:
                        base_data["Year"] = f"{min(years_int)}-{max(years_int)}"
                    else:
                        base_data["Year"] = years_merged_sorted[0]
                except:
                    base_data["Year"] = years_merged_sorted[0]
        
        # Update the base document in Firestore
        base_doc.reference.update(base_data)
        print(f"  -> Updated base document: {base_doc_id} with {len(all_propositions)} total propositions")
        
        # Delete other duplicate documents
        for other_doc_id, other_doc, other_data in other_entries:
            other_doc.reference.delete()
            print(f"  -> Deleted duplicate document: {other_doc_id}")
            deleted_count += 1
        
        consolidated_count += 1
    
    print(f"\n[OK] Consolidation complete!")
    print(f"  Consolidated {consolidated_count} politicians")
    print(f"  Deleted {deleted_count} duplicate entries")


if __name__ == "__main__":
    consolidate_politicians_in_firestore()
