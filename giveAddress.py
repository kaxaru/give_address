from web3 import Web3
from loguru import logger
import os
from enum import Enum
from multiprocessing.dummy import Pool

from bip_utils import (
    AptosAddrEncoder, EthAddrEncoder, OneAddrEncoder
)

from bip_utils import Bip39SeedGenerator, Bip32Slip10Ed25519, Bip32Slip10Secp256k1

RPCS = {
    'optimism' : {'chain': 'OPTIMISM', 'chain_id': 10, 'rpc': 'https://rpc.ankr.com/optimism', 'scan': 'https://optimistic.etherscan.io/tx', 'token': 'ETH'},

    'bsc' : {'chain': 'BSC', 'chain_id': 56, 'rpc': 'https://rpc.ankr.com/bsc', 'scan': 'https://bscscan.com/tx', 'token': 'BNB'},

    'polygon' : {'chain': 'MATIC', 'chain_id': 137, 'rpc': 'https://polygon-rpc.com', 'scan': 'https://polygonscan.com/tx', 'token': 'MATIC'},

    'arbitrum' : {'chain': 'ARBITRUM', 'chain_id': 42161, 'rpc': 'https://rpc.ankr.com/arbitrum', 'scan': 'https://arbiscan.io/tx', 'token': 'ETH'},

    'avaxc' : {'chain': 'AVAXC', 'chain_id': 43114, 'rpc': 'https://rpc.ankr.com/avalanche', 'scan': 'https://snowtrace.io/tx', 'token': 'AVAX'},

    'fantom' : {'chain': 'FANTOM', 'chain_id': 250, 'rpc': 'https://rpc.ankr.com/fantom', 'scan': 'https://ftmscan.com/tx', 'token': 'FTM'},

    'celo' : {'chain': 'CELO', 'chain_id': 42220, 'rpc': 'https://rpc.ankr.com/celo', 'scan': 'https://celoscan.io/tx', 'token': 'CELO'},

    'harmony' : {'chain': 'HARMONY', 'chain_id': 1666600000, 'rpc': 'https://api.harmony.one', 'scan': 'https://explorer.harmony.one/tx', 'token': 'Harmony'},

    'xdai' : {'chain': 'xDai', 'chain_id': 100, 'rpc': 'https://rpc.ankr.com/gnosis', 'scan': 'https://blockscout.com/xdai/mainnet/tx', 'token': 'xDai'}
}


class Chains(Enum):
    EVM = 1
    APTOS = 2
    SUI = 3
    HARMONY = 4


def get_seeds():
    with open(f'{os.path.dirname(__file__)}/seed.txt', 'r') as file:
        _seeds = [row.strip() for row in file]
    return _seeds

def give_address_from_seed(seed, chain, num):
    out_wallets = {"wallets": []}

    account_indexes = [i for i in range(num)]
    seed_bytes = Bip39SeedGenerator(seed).Generate()
    bip32_mst_ctx = Bip32Slip10Ed25519.FromSeed(seed_bytes)

    for i in account_indexes:
        if Chains(chain).name.lower() == 'evm' or Chains(chain).name.lower() == 'harmony':
            bip32_mst_ctx = Bip32Slip10Secp256k1.FromSeed(seed_bytes)
            derive_path = f"m/44'/60'/0'/0/{i}"
        elif Chains(chain).name.lower() == 'aptos':
            bip32_mst_ctx = Bip32Slip10Ed25519.FromSeed(seed_bytes)
            derive_path = f"m/44'/637'/{i}'/0'/0'"
        elif Chains(chain).name.lower() == 'sui':
            bip32_mst_ctx = Bip32Slip10Ed25519.FromSeed(seed_bytes)
            derive_path = f"m/44'/784'/{i}'/0'/0'"

        bip32_der_ctx = bip32_mst_ctx.DerivePath(derive_path)
        private_key = bip32_der_ctx.PrivateKey().Raw().ToHex()

        if Chains(chain).name.lower() == 'evm':
            address = EthAddrEncoder.EncodeKey(bip32_der_ctx.PublicKey().KeyObject())
        elif Chains(chain).name.lower() == 'harmony':
            address = OneAddrEncoder.EncodeKey(bip32_der_ctx.PublicKey().KeyObject())
        else:
            address = AptosAddrEncoder.EncodeKey(bip32_der_ctx.PublicKey().KeyObject())

        out_wallets["wallets"].append({"priv_key": private_key, "address": address, "chain": chain})

    return out_wallets

def write_to_file(data):
    mnemonic = data["seed"]
    wallets = data["wallets"]

    chain = Chains(wallets[0]["chain"]).name
    if os.path.exists(f'{mnemonic}_{chain}_priv_key.txt'):
        os.remove(f'{mnemonic}_{chain}_priv_key.txt')

    if os.path.exists(f'{mnemonic}_{chain}_address.txt'):
        os.remove(f'{mnemonic}_{chain}_address.txt')

    for wal in wallets:
        with open(f'{mnemonic}_{chain}_priv_key.txt', 'a+') as file:
            file.write(f'{wal["priv_key"]}\n')
        with open(f'{mnemonic}_{chain}_address.txt', 'a+') as file:
            file.write(f'{wal["address"]}\n')


def task(data):
    seed = data['seed']
    chain = data['chain']
    num = data['number_of_wallets']

    wallets = give_address_from_seed(seed, chain, num)
    wallets["seed"] = ''.join(seed.split())[:16]

    write_to_file(wallets)


if __name__ == '__main__':
    seeds = get_seeds()

    chain = int(input('EVM - 1, Aptos - 2, Sui - 3, Harmony - 4'))
    number_of_wallets = int(input('number of wallets from seed?'))

    multith = str(input("multithreading? - y/n \n"))
    if multith == 'Y' or multith == 'y':
        threads = int(input("number of threads? \n"))
    else:
        threads = 1

    data = []
    params = {
        'seed': '',
        'chain': chain,
        'number_of_wallets': number_of_wallets,
    }

    for seed in seeds:
        params['seed'] = seed
        data.append(params)

    pool = Pool(threads)
    pool.map(task, data)
