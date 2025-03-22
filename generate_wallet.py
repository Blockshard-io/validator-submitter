from web3 import Web3

# Create a new Ethereum account
w3 = Web3()
account = w3.eth.account.create()

# Display wallet details
print("New Wallet Generated:")
print(f"Address: {account.address}")
print(f"Private Key: {account.key.hex()}")

# Save private key securely
with open("wallet.json", "w") as f:
    f.write(f'{{"address": "{account.address}", "private_key": "{account.key.hex()}"}}')

print("Wallet saved to wallet.json")

