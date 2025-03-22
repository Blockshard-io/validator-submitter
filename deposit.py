import json
import os
import time
from typing import Dict, Any
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
    print(f"Waiting for transaction confirmation: {tx_hash.hex()}")
    for _ in range(max_attempts):
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt["status"] == 1:
                print(f"Transaction confirmed in block {receipt['blockNumber']}")
                print(f"Gas used: {receipt['gasUsed']}")
                return True
            else:
                print("Transaction failed!")
                return False
        except TransactionNotFound:
            time.sleep(2)  # Wait 2 seconds before next attempt
    print("Transaction confirmation timeout")
    return False

def get_gas_price():
    """Get current gas price with a small buffer."""
    try:
        # Get the current gas price
        current_gas_price = w3.eth.gas_price
        # Add 20% buffer
        return int(current_gas_price * 1.2)
    except Exception as e:
        print(f"Error getting gas price: {e}")
        # Fallback to a reasonable default
        return Web3.to_wei(30, 'gwei')

def send_transaction(tx: dict, max_retries: int = 3) -> bytes:
    """Send transaction with retry logic."""
    for attempt in range(max_retries):
        try:
            # Sign and send transaction
            signed_txn = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"\nTransaction sent (attempt {attempt + 1}): {tx_hash.hex()}")
            return tx_hash
        except Exception as e:
            print(f"Error sending transaction (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                # Increase gas price by 20% for next attempt
                tx['maxFeePerGas'] = int(tx['maxFeePerGas'] * 1.2)
                print(f"Retrying with higher gas price: {tx['maxFeePerGas']}")
                time.sleep(2)
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

for i, entry in enumerate(deposit_data):
    print(f"\nProcessing validator {i+1}:")
    
    if not validate_deposit_data(entry):
        print(f"Skipping invalid deposit data for validator {i+1}")
        continue

    try:
        # Convert hex strings to bytes without padding
        pubkey = bytes.fromhex(entry["pubkey"])
        withdrawal_credentials = bytes.fromhex(entry["withdrawal_credentials"])
        signature = bytes.fromhex(entry["signature"])
        deposit_data_root = bytes.fromhex(entry["deposit_data_root"])

        # Print the raw bytes for debugging
        print("Raw bytes:")
        print(f"Pubkey: {pubkey.hex()}")
        print(f"Withdrawal credentials: {withdrawal_credentials.hex()}")
        print(f"Signature: {signature.hex()}")
        print(f"Deposit data root: {deposit_data_root.hex()}")

        # Encode the arguments using ABI encoding
        # The contract expects:
        # - pubkey: bytes (48 bytes)
        # - withdrawal_credentials: bytes (32 bytes)
        # - signature: bytes (96 bytes)
        # - deposit_data_root: bytes32 (32 bytes)
        encoded_args = encode(
            ["bytes", "bytes", "bytes", "bytes32"],
            [pubkey, withdrawal_credentials, signature, deposit_data_root]
        )

        calldata = function_selector + encoded_args
        print("\nEncoded data:")
        print("Function selector:", function_selector.hex())
        print("Encoded args:", encoded_args.hex())
        print("Calldata:", calldata.hex())

        # Get current nonce and gas price
        nonce = w3.eth.get_transaction_count(FROM_ADDRESS, "latest")
        max_fee_per_gas = get_gas_price()
        print("\nTransaction details:")
        print("Nonce:", nonce)
        print("Max fee per gas:", max_fee_per_gas)

        try:
            estimated_gas = w3.eth.estimate_gas({
                'from': FROM_ADDRESS,
                'to': DEPOSIT_CONTRACT,
                'value': Web3.to_wei(32, 'ether'),
                'data': calldata,
                'nonce': nonce
            })
            print("Estimated gas:", estimated_gas)
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
            'gas': int(estimated_gas * 1.1),  # 10% buffer
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': Web3.to_wei(1.5, 'gwei'),
        }

        try:
            tx_hash = send_transaction(tx)
            
            # Wait for confirmation
            if wait_for_transaction(tx_hash):
                print(f"Successfully deposited validator {i+1}")
            else:
                print(f"Failed to confirm deposit for validator {i+1}")
                
        except Exception as e:
            print(f"Transaction failed: {str(e)}")
            continue

    except Exception as e:
        print(f"Error processing validator {i+1}: {str(e)}")
        continue
