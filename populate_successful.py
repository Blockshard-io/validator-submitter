import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load deposit data
try:
    deposit_data_file = os.getenv("DEPOSIT_DATA_FILE")
    assert deposit_data_file, "Missing DEPOSIT_DATA_FILE in environment"
    with open(deposit_data_file) as f:
        deposit_data = json.load(f)
    if not isinstance(deposit_data, list):
        raise ValueError("Deposit data must be a list")
except Exception as e:
    print(f"Error loading deposit data: {str(e)}")
    exit(1)

# Get pubkeys of first 10 validators
successful_deposits = [entry["pubkey"] for entry in deposit_data[:10]]

# Save to successful_deposits.json
try:
    with open("successful_deposits.json", 'w') as f:
        json.dump(successful_deposits, f)
    print(f"Successfully saved {len(successful_deposits)} validator pubkeys to successful_deposits.json")
except Exception as e:
    print(f"Error saving successful deposits: {e}")
    exit(1) 