from web3 import Web3
import json
import dotenv
import os

# Načtení proměnných prostředí
dotenv.load_dotenv(override=True)

# Konfigurace
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ACCOUNT_PASSWORD = os.getenv("ACCOUNT_PASSWORD")
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")
#RPC_URL = "http://127.0.0.1:8545"
RPC_URL = os.getenv("RPC_URL")

# Kontrola proměnných
if not all([CONTRACT_ADDRESS, ACCOUNT_PASSWORD, ACCOUNT_ADDRESS]):
    print("Chyba: Nastavte všechny proměnné v .env souboru!")
    exit()

# Inicializace Web3
web3 = Web3(Web3.HTTPProvider(RPC_URL))
if not web3.is_connected():
    print("Nelze připojit k Ethereum nodu!")
    exit()

print(f"✅ Připojeno k {RPC_URL}, Chain ID: {web3.eth.chain_id}")

# Načtení kontraktu
print(CONTRACT_ADDRESS)
contract_address = web3.to_checksum_address(CONTRACT_ADDRESS)
ACCOUNT_ADDRESS = web3.to_checksum_address(ACCOUNT_ADDRESS)
print(f"🔗 Kontroluji kontrakt na adrese: {contract_address}")

# Kontrola existence kontraktu
if web3.eth.get_code(contract_address) == b'':
    print("⛔ Žádný kód kontraktu na této adrese!")
    exit()

with open('StringStorage_abi.json') as f:
    contract_abi = json.load(f)

contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# Kontrola vlastníka
contract_owner = contract.functions.owner().call()
if contract_owner.lower() != ACCOUNT_ADDRESS.lower():
    print(f"⛔ Účet {ACCOUNT_ADDRESS} není vlastníkem kontraktu!")
    print(f"Vlastník kontraktu je: {contract_owner}")
    exit()

def store_string(value: str) -> int:
    """Uloží string do blockchainu"""
    try:
        # Odemčení účtu
        unlock_response = web3.provider.make_request(
            "personal_unlockAccount", 
            [ACCOUNT_ADDRESS, ACCOUNT_PASSWORD, 60]
        )
        
        if 'error' in unlock_response:
            print(f"⛔ Chyba při odemykání: {unlock_response['error']['message']}")
            return None

        # Příprava transakce
        gas_estimate = contract.functions.storeString(value).estimate_gas({
            'from': ACCOUNT_ADDRESS
        })
        
        tx_params = {
            'from': ACCOUNT_ADDRESS,
            'nonce': web3.eth.get_transaction_count(ACCOUNT_ADDRESS),
            'gas': gas_estimate + 5000,  # Buffer
            'gasPrice': web3.eth.gas_price,
            'chainId': web3.eth.chain_id
        }

        # Build a sign transaction
        tx = contract.functions.storeString(value).build_transaction(tx_params)
        
        # Odeslání
        tx_hash = web3.eth.send_transaction(tx)
        print(f"📤 Transakce odeslána: {tx_hash.hex()}")
        
        # Čekání na potvrzení
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            print("⛔ Transakce selhala!")
            return None
            
        new_id = contract.functions.stringCount().call()
        print(f"✅ Uloženo pod ID: {new_id}")
        return new_id
        
    except Exception as e:
        print(f"⛔ Kritická chyba: {str(e)}")
        return None

def get_string(string_id: int) -> str:
    """Získá uložený string"""
    try:
        return contract.functions.getString(string_id).call()
    except Exception as e:
        print(f"⛔ Chyba při čtení: {str(e)}")
        return None

if __name__ == "__main__":
    # Testovací data
    test_data = "Ahoj blockchainu!"
    
    # Kontrola zůstatku
    balance = web3.eth.get_balance(ACCOUNT_ADDRESS)
    print(f"💰 Zůstatek: {web3.from_wei(balance, 'ether')} ETH")
    
    # Uložení
    new_id = store_string(test_data)
    
    if new_id:
        # Čtení
        print(f"\n🔍 Pokouším se načíst string s ID: {new_id}")
        retrieved = get_string(new_id)
        
        if retrieved is not None:
            print(f"📄 Načtený text: '{retrieved}'") # <--- PŘIDANÝ ŘÁDEK PRO VÝPIS TEXTU
            if retrieved == test_data:
                print("✅ Ověření úspěšné! Data se shodují.")
            else:
                print(f"⛔ Nesouhlasí! Uloženo: '{retrieved}', Očekáváno: '{test_data}'")
        else:
            print(f"⛔ Nepodařilo se načíst string s ID {new_id} zpět z kontraktu.")
            
        print(f"📊 Celkem uloženo: {contract.functions.stringCount().call()}")
    else:
        print("⛔ Uložení se nezdařilo, čtení se neprovádí.")