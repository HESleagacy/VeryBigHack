import os
import json
from web3 import Web3
from pymongo.database import Database
from datetime import datetime, timezone

# --- Globals ---
w3 = None
contract = None
account = None
threat_log_abi = None


def init_blockchain_logging():
    """
    Initializes Web3 connection, loads the contract and wallet.
    Call ONCE during service startup.
    """
    global w3, contract, account, threat_log_abi

    rpc_url = os.getenv("HARDHAT_RPC_URL")
    contract_address = os.getenv("BLOCKCHAIN_CONTRACT_ADDRESS")
    private_key = os.getenv("PRIVATE_KEY")

    if not all([rpc_url, contract_address, private_key]):
        raise EnvironmentError("Blockchain environment variables not fully set.")

    # 1. Connect to RPC
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to blockchain RPC at {rpc_url}")

    print(f"[Blockchain] Connected to RPC: {rpc_url}")
    
    # 2. Load wallet
    account = w3.eth.account.from_key(private_key)
    w3.eth.default_account = account.address

    print(f"[Blockchain] Wallet loaded: {account.address}")

    # 3. Load ABI — keep minimal but valid
    threat_log_abi = json.loads("""
    [
        {
            "inputs": [
                {"internalType": "string", "name": "_userIdHash", "type": "string"},
                {"internalType": "string", "name": "_attackType", "type": "string"}
            ],
            "name": "logThreat",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "anonymous": false,
            "inputs": [
                {"indexed": false, "internalType": "uint256", "name": "id", "type": "uint256"},
                {"indexed": true, "internalType": "address", "name": "logger", "type": "address"},
                {"indexed": false, "internalType": "string", "name": "userIdHash", "type": "string"},
                {"indexed": false, "internalType": "string", "name": "attackType", "type": "string"},
                {"indexed": false, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
            ],
            "name": "ThreatLogged",
            "type": "event"
        }
    ]
    """)

    # 4. Build contract object
    contract = w3.eth.contract(address=contract_address, abi=threat_log_abi)

    print(f"[Blockchain] Contract loaded at: {contract_address}")


def log_threat_to_blockchain(db: Database, user_id: str, attack_type: str) -> dict:
    """
    Sends logThreat() transaction to the blockchain AND stores entry in MongoDB.
    """
    global w3, contract, account

    if not all([w3, contract, account]):
        raise RuntimeError("Blockchain connector not initialized. Call init_blockchain_logging() first.")

    # 1. Get latest nonce
    nonce = w3.eth.get_transaction_count(account.address)

    # 2. Build transaction
    tx = contract.functions.logThreat(
        user_id,
        attack_type
    ).build_transaction({
        "chainId": w3.eth.chain_id,
        "from": account.address,
        "nonce": nonce,
        "gas": 1_500_000,
        "gasPrice": w3.eth.gas_price
    })

    # 3. Sign
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=account.key)

    # 4. Send
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    print(f"[Blockchain] Sent logThreat() tx: {tx_hash.hex()}")

    # 5. Wait for confirmation
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"[Blockchain] Tx confirmed in block {receipt.blockNumber}")

    # 6. Save to MongoDB
    log_entry = {
        "userId": user_id,
        "attackType": attack_type,
        "timestamp": datetime.now(timezone.utc),
        "blockchainTxHash": tx_hash.hex(),
        "blockNumber": receipt.blockNumber
    }

    db["threat_logs"].insert_one(log_entry)

    return log_entry

