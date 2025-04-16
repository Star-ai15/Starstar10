# main.py
import time
from solana.rpc.api import Client
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.transaction import Transaction
from spl.token.instructions import transfer_checked, get_associated_token_address
from spl.token.constants import TOKEN_PROGRAM_ID
from base58 import b58decode
import config

client = Client(config.RPC_ENDPOINT)
tx_seen = set()

def load_wallet(secret_base58):
    secret = b58decode(secret_base58)
    return Keypair.from_secret_key(secret)

def send_star(sender_kp, to_pubkey, amount, mint_pubkey):
    ata = get_associated_token_address(to_pubkey, mint_pubkey)
    tx = Transaction()
    tx.add(
        transfer_checked(
            source=get_associated_token_address(sender_kp.public_key, mint_pubkey),
            dest=ata,
            owner=sender_kp.public_key,
            amount=int(amount),
            decimals=6,
            mint=mint_pubkey,
        )
    )
    res = client.send_transaction(tx, sender_kp)
    print(f"Sent {amount} STAR to {to_pubkey}: {res}")

def check_wallet(wallet_type):
    if wallet_type == "public":
        secret = config.PUBLIC_PRESALE_SECRET
        addr = config.PUBLIC_ADDRESS
        rate = config.PUBLIC_RATE
    else:
        secret = config.VC_PRESALE_SECRET
        addr = config.VC_ADDRESS
        rate = config.VC_RATE

    kp = load_wallet(secret)
    print(f"[{wallet_type.upper()}] Monitoring {addr}...")

    sigs = client.get_signatures_for_address(PublicKey(addr), limit=20)["result"]
    for sig in sigs:
        sig_str = sig["signature"]
        if sig_str in tx_seen:
            continue
        tx_seen.add(sig_str)
        tx = client.get_transaction(sig_str, encoding="json")["result"]
        if tx is None: continue
        account_keys = tx["transaction"]["message"]["accountKeys"]
        sender = account_keys[0]
        post_balances = tx["meta"]["postBalances"]
        pre_balances = tx["meta"]["preBalances"]
        sol_sent = (pre_balances[0] - post_balances[0]) / 1e9
        if sol_sent < 0.001: continue
        net = sol_sent - config.FEE_SOL
        if net <= 0: continue
        star_amount = int(net * rate)
        send_star(kp, PublicKey(sender), star_amount, PublicKey(config.STAR_TOKEN_MINT))

while True:
    check_wallet("public")
    check_wallet("vc")
    time.sleep(20)