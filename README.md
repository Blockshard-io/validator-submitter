
# 🦉 Ethereum Validator Depositor for Hoodi Testnet

This script automates Ethereum validator deposits to the **Hoodi testnet** Deposit Contract. It uses EIP-1559 transactions, dynamically adjusts gas pricing, and tracks successful deposits to avoid duplication.

## 🔧 Features

* Connects to an Ethereum RPC endpoint (e.g., Hoodi testnet)
* Submits `deposit(bytes, bytes, bytes, bytes32)` transactions
* Dynamically adjusts gas pricing using `eth_feeHistory`
* Skips previously successful deposits
* Tracks successful pubkeys in `successful_deposits.json`
* Retries failed transactions with exponential backoff

## 📦 Dependencies

Minimal external dependencies:

```
web3>=6.0.0  
python-dotenv>=1.0.0
```

Install with:

```
pip install -r requirements.txt
```

## 🛠️ Environment Variables

Create a `.env` file in the root directory with the following variables:

```
RPC_URL=https://your-hoodi-endpoint  
PRIVATE_KEY=0xyourprivatekey  
DEPOSIT_DATA_FILE=./deposit_data.json
```

⚠️ **Never commit your private key** to GitHub or any public repository.

## 📁 Input Format

The `deposit_data.json` file must contain a list of deposit entries:

```
[
  {
    "pubkey": "abcd...",
    "withdrawal_credentials": "1234...",
    "signature": "dead...",
    "deposit_data_root": "beef..."
  }
]
```

Each field must be a valid hex string without the `0x` prefix.

## 🚀 Running the Script

Activate your virtual environment (if applicable), then run:

```
python deposit.py
```

The script will:

* Connect to the Ethereum node
* Check your wallet balance
* Process as many 32 ETH deposits as possible
* Skip pubkeys that were already deposited successfully

## ✅ Output

* Console output shows transaction status, gas price, and confirmations
* `successful_deposits.json` stores completed pubkeys to prevent duplicates

---

Feel free to contribute or open an issue if you have questions or suggestions.

---

