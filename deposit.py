import json
import os
import time
from typing import Dict, Any, Set
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from eth_abi import encode
from web3.exceptions import TransactionNotFound

# Load environment variables
load_dotenv()

# Connect to the Hoodi execution client
RPC_URL = os.getenv("RPC_URL")
assert RPC_URL, "Missing RPC_URL in environment"
w3 = Web3(Web3.HTTPProvider(RPC_URL))
assert w3.is_connected(), "Web3 provider not connected."

# Load private key from environment and derive wallet address
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
assert PRIVATE_KEY, "Missing PRIVATE_KEY in environment"
acct = Account.from_key(PRIVATE_KEY)
FROM_ADDRESS = acct.address
print("Using wallet address:", FROM_ADDRESS)

# Deposit contract address on Hoodi
DEPOSIT_CONTRACT = Web3.to_checksum_address("0x00000000219ab540356cBB839Cbe05303d7705Fa")

# Deposit function selector for deposit(bytes, bytes, bytes, bytes32)
function_selector = bytes.fromhex("22895118")

# File to track successful deposits
SUCCESSFUL_DEPOSITS_FILE = "successful_deposits.json"

def load_successful_deposits() -> Set[str]:
    """Load the set of successfully deposited validator pubkeys."""
    try:
        if os.path.exists(SUCCESSFUL_DEPOSITS_FILE):
            with open(SUCCESSFUL_DEPOSITS_FILE, 'r') as f:
                return set(json.load(f))
    except Exception as e:
        print(f"Error loading successful deposits: {e}")
    return set()

def save_successful_deposit(pubkey: str):
    """Save a successfully deposited validator pubkey."""
    try:
        # Load existing successful deposits
        successful = load_successful_deposits()
        
        # Add the new pubkey
        successful.add(pubkey)
        
        # Save back to file
        with open(SUCCESSFUL_DEPOSITS_FILE, 'w') as f:
            json.dump(list(successful), f)
        print(f"Saved successful deposit for pubkey: {pubkey[:10]}...")
    except Exception as e:
        print(f"Error saving successful deposit: {e}")

def validate_deposit_data(entry: Dict[str, Any]) -> bool:
    """Validate deposit data entry has all required fields with correct format."""
    required_fields = ["pubkey", "withdrawal_credentials", "signature", "deposit_data_root"]
    try:
        for field in required_fields:
            if field not in entry:
                print(f"Missing required field: {field}")
                return False
            # Validate hex format
            bytes.fromhex(entry[field])
        return True
    except ValueError:
        print(f"Invalid hex format in field: {field}")
        return False

def wait_for_transaction(tx_hash: bytes, max_attempts: int = 50) -> bool:
    """Wait for transaction confirmation."""
    print(f"Waiting for transaction confirmation...")
    for _ in range(max_attempts):
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt["status"] == 1:
                print(f"✓ Transaction confirmed in block {receipt['blockNumber']}")
                return True
            else:
                print("✗ Transaction failed!")
                return False
        except TransactionNotFound:
            time.sleep(2)  # Wait 2 seconds before next attempt
    print("✗ Transaction confirmation timeout")
    return False

def get_gas_price():
    """Get current gas price using eth_feeHistory."""
    try:
        # Get fee history for the last 5 blocks
        fee_history = w3.eth.fee_history(
            block_count=5,
            newest_block='latest',
            reward_percentiles=[50, 75, 90]  # Get median, 75th percentile, and 90th percentile
        )
        
        # Get the base fee for the latest block
        base_fee = fee_history['baseFeePerGas'][-1]
        
        # Get the median priority fee from recent blocks
        priority_fees = [reward[0] for reward in fee_history['reward'] if reward]  # Get median (50th percentile) rewards
        median_priority_fee = sum(priority_fees) / len(priority_fees) if priority_fees else Web3.to_wei(2, 'gwei')
        
        # Calculate max fee per gas (base fee + priority fee)
        max_fee_per_gas = base_fee + median_priority_fee
        
        return max_fee_per_gas
    except Exception as e:
        print(f"Warning: Error getting gas price: {e}")
        # Fallback to a reasonable default
        return Web3.to_wei(50, 'gwei')

def send_transaction(tx: dict, max_retries: int = 3) -> bytes:
    """Send transaction with retry logic."""
    for attempt in range(max_retries):
        try:
            # Sign and send transaction
            signed_txn = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"Transaction sent: 0x{tx_hash.hex()}")
            return tx_hash
        except Exception as e:
            print(f"Error sending transaction (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                # Increase gas price by 50% for next attempt
                tx['maxFeePerGas'] = int(tx['maxFeePerGas'] * 1.5)
                print(f"Retrying with higher gas price...")
                # Wait longer between retries to allow network to stabilize
                time.sleep(5)
            else:
                raise
    raise Exception("Failed to send transaction after all retries")

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

# Load successful deposits
successful_deposits = load_successful_deposits()
print(f"\nFound {len(successful_deposits)} previously successful deposits")

# Check wallet balance
balance = w3.eth.get_balance(FROM_ADDRESS)
required_balance = Web3.to_wei(32, 'ether')  # 32 ETH per validator
max_validators = balance // required_balance
print(f"Wallet balance: {Web3.from_wei(balance, 'ether')} ETH")
print(f"Can process up to {max_validators} validators")

# Counter for non-deposited validators
processed_count = 0

for i, entry in enumerate(deposit_data):
    print(f"\nProcessing validator {i+1}/{len(deposit_data)}:")
    
    # Skip if already successfully deposited
    if entry["pubkey"] in successful_deposits:
        print(f"Skipping validator {i+1} - already successfully deposited")
        continue
    
    # Check if we've processed enough non-deposited validators
    if processed_count >= max_validators:
        print(f"\nInsufficient funds to process more validators. Stopping at validator {i+1}.")
        break
    
    if not validate_deposit_data(entry):
        print(f"Skipping invalid deposit data for validator {i+1}")
        continue

    try:
        # Convert hex strings to bytes without padding
        pubkey = bytes.fromhex(entry["pubkey"])
        withdrawal_credentials = bytes.fromhex(entry["withdrawal_credentials"])
        signature = bytes.fromhex(entry["signature"])
        deposit_data_root = bytes.fromhex(entry["deposit_data_root"])

        # Encode the arguments using ABI encoding
        encoded_args = encode(
            ["bytes", "bytes", "bytes", "bytes32"],
            [pubkey, withdrawal_credentials, signature, deposit_data_root]
        )

        calldata = function_selector + encoded_args

        # Get current nonce and gas price
        nonce = w3.eth.get_transaction_count(FROM_ADDRESS, "latest")
        max_fee_per_gas = get_gas_price()

        try:
            estimated_gas = w3.eth.estimate_gas({
                'from': FROM_ADDRESS,
                'to': DEPOSIT_CONTRACT,
                'value': Web3.to_wei(32, 'ether'),
                'data': calldata,
                'nonce': nonce
            })
        except Exception as e:
            print(f"Gas estimation failed: {str(e)}")
            continue

        tx = {
            'type': 2,
            'chainId': w3.eth.chain_id,
            'from': FROM_ADDRESS,
            'to': DEPOSIT_CONTRACT,
            'nonce': nonce,
            'value': Web3.to_wei(32, 'ether'),
            'data': calldata,
            'gas': int(estimated_gas * 1.2),  # 20% buffer
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': Web3.to_wei(2, 'gwei'),
        }

        try:
            tx_hash = send_transaction(tx)
            
            # Wait for confirmation
            if wait_for_transaction(tx_hash):
                print(f"✓ Successfully deposited validator {i+1}")
                # Save successful deposit
                save_successful_deposit(entry["pubkey"])
                processed_count += 1
            else:
                print(f"✗ Failed to confirm deposit for validator {i+1}")
                
        except Exception as e:
            print(f"✗ Transaction failed: {str(e)}")
            continue

    except Exception as e:
        print(f"✗ Error processing validator {i+1}: {str(e)}")
        continue
