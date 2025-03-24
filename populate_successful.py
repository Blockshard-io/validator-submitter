import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# File to track successful deposits
SUCCESSFUL_DEPOSITS_FILE = "successful_deposits.json"

def load_successful_deposits():
    """Load the set of successfully deposited validator pubkeys."""
    try:
        if os.path.exists(SUCCESSFUL_DEPOSITS_FILE):
            with open(SUCCESSFUL_DEPOSITS_FILE, 'r') as f:
                return set(json.load(f))
    except Exception as e:
        print(f"Error loading successful deposits: {e}")
    return set()

def save_successful_deposits(pubkeys):
    """Save a list of successfully deposited validator pubkeys."""
    try:
        # Load existing successful deposits
        successful = load_successful_deposits()
        
        # Add the new pubkeys
        successful.update(pubkeys)
        
        # Save back to file
        with open(SUCCESSFUL_DEPOSITS_FILE, 'w') as f:
            json.dump(list(successful), f)
        print(f"Successfully saved {len(pubkeys)} validator pubkeys to {SUCCESSFUL_DEPOSITS_FILE}")
        print(f"Total successful deposits: {len(successful)}")
    except Exception as e:
        print(f"Error saving successful deposits: {e}")
        exit(1)

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
save_successful_deposits(successful_deposits) 