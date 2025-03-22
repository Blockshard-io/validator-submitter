import json
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from eth_abi import encode

# Load environment variables
load_dotenv()

# Connect to the Hoodi execution client
RPC_URL = "http://localhost:8545"
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

# Deposit function selector for deposit(bytes, bytes, bytes, bytes)
function_selector = bytes.fromhex("22895118")

# Load deposit data
with open("deposit_data.json") as f:
    deposit_data = json.load(f)

for i, entry in enumerate(deposit_data):
    print(f"Validator {i+1}:")

    pubkey = bytes.fromhex(entry["pubkey"])
    withdrawal_credentials = bytes.fromhex(entry["withdrawal_credentials"])
    signature = bytes.fromhex(entry["signature"])
    deposit_data_root = bytes.fromhex(entry["deposit_data_root"])

    # Encode deposit function arguments
    encoded_args = encode([
        "bytes", "bytes", "bytes", "bytes"
    ], [pubkey, withdrawal_credentials, signature, deposit_data_root])

    calldata = function_selector + encoded_args
    print("Function selector:", function_selector.hex())
    print("Encoded args:", encoded_args.hex())
    print("Calldata:", calldata.hex())

    # Estimate gas with dry-run
    nonce = w3.eth.get_transaction_count(FROM_ADDRESS, "pending")
    print("Nonce:", nonce)

    estimated_gas = w3.eth.estimate_gas({
        'from': FROM_ADDRESS,
        'to': DEPOSIT_CONTRACT,
        'value': Web3.to_wei(32, 'ether'),
        'data': calldata
    })
    print("Estimated gas:", estimated_gas)

    # Query base fee and set max fees
    latest_block = w3.eth.get_block('latest')
    base_fee = latest_block.get("baseFeePerGas", Web3.to_wei(30, 'gwei'))
    max_priority_fee_per_gas = Web3.to_wei(1.5, 'gwei')
    max_fee_per_gas = base_fee + max_priority_fee_per_gas

    print("Base fee:", base_fee)
    print("Max priority fee:", max_priority_fee_per_gas)
    print("Max fee per gas:", max_fee_per_gas)

    tx = {
        'type': 2,
        'chainId': w3.eth.chain_id,
        'from': FROM_ADDRESS,
        'to': DEPOSIT_CONTRACT,
        'nonce': nonce,
        'value': Web3.to_wei(32, 'ether'),
        'data': calldata,
        'gas': estimated_gas + 5000,  # small buffer
        'maxFeePerGas': max_fee_per_gas,
        'maxPriorityFeePerGas': max_priority_fee_per_gas,
    }

    signed_txn = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)

    try:
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print("  Transaction sent:", tx_hash.hex())
    except Exception as e:
        print("  Transaction failed:", str(e))
