"""
Consolidate politicians with multiple year entries into a single entry.
Merges all propositions from different years into one politician entry.
"""

import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
data_file = os.path.join(script_dir, "data.json")

# Read the data
with open(data_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

politicians = data.get("Politician", [])

# Group politicians by Name (case-insensitive)
politicians_by_name = {}
for politician in politicians:
    name = politician.get("Name", "").strip()
    if not name:
        continue
    
    # Use lowercase name as key for case-insensitive matching
    name_key = name.lower()
    
    if name_key not in politicians_by_name:
        politicians_by_name[name_key] = []
    politicians_by_name[name_key].append(politician)

# Consolidate politicians with multiple entries
consolidated = []
consolidated_count = 0
merged_propositions_count = 0

for name_key, entries in politicians_by_name.items():
    if len(entries) == 1:
        # Only one entry, keep as is
        consolidated.append(entries[0])
    else:
        # Multiple entries, consolidate them
        print(f"Consolidating {entries[0].get('Name')} ({len(entries)} entries)")
        
        # Sort by Year (most recent first, then keep the most recent as base)
        entries_sorted = sorted(entries, key=lambda x: x.get("Year", 0), reverse=True)
        base_entry = entries_sorted[0].copy()
        
        # Collect all propositions from all years
        all_propositions = {}
        years_merged = []
        
        for entry in entries_sorted:
            year = entry.get("Year", "")
            years_merged.append(year)
            propositions = entry.get("Propositions", {})
            
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
        base_entry["Propositions"] = all_propositions
        
        # Update Year to show range if multiple years, or keep single year
        if len(years_merged) > 1:
            years_merged_sorted = sorted([y for y in years_merged if y], reverse=True)
            if len(years_merged_sorted) > 1:
                base_entry["Year"] = f"{min(years_merged_sorted)}-{max(years_merged_sorted)}"
            else:
                base_entry["Year"] = years_merged_sorted[0] if years_merged_sorted else base_entry.get("Year", "")
        
        # Add note about consolidation
        if "Notes" not in base_entry:
            base_entry["Notes"] = ""
        base_entry["Notes"] += f"Consolidated from {len(entries)} entries. " if base_entry["Notes"] else f"Consolidated from {len(entries)} entries. "
        
        consolidated.append(base_entry)
        consolidated_count += len(entries) - 1  # Count how many entries were merged
        merged_propositions_count += len(all_propositions)
        
        print(f"  -> Merged {len(entries)} entries into one with {len(all_propositions)} total propositions")

# Update data
data["Politician"] = consolidated

# Backup original file
backup_file = data_file + ".backup"
with open(backup_file, 'w', encoding='utf-8') as f:
    json.dump({"Politician": politicians}, f, indent=2, ensure_ascii=False)
print(f"\nBackup saved to: {backup_file}")

# Write consolidated data
with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] Consolidation complete!")
print(f"  Original entries: {len(politicians)}")
print(f"  Consolidated entries: {len(consolidated)}")
print(f"  Merged {consolidated_count} duplicate entries")
print(f"  Total propositions across all politicians: {sum(len(p.get('Propositions', {})) for p in consolidated)}")
