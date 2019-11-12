from electroncash.bitcoin import regenerate_key, MySigningKey, Hash
from electroncash.address import Address, Script, OpCodes as Op
from electroncash.transaction import Transaction,TYPE_ADDRESS
import ecdsa
from .contract import Contract
from math import ceil

import time
LOCKTIME_THRESHOLD = 500000000
UTXO=0
CONTRACT=1
MODE=2
PLEDGE_TIME=int((0*3600*24))#0.083
PLEDGE = 1000
RECEIVER = 0
SENDER = 1
ARBITER = 2
MONTH=6*24#5062


def joinbytes(iterable):
    """Joins an iterable of bytes and/or integers into a single byte string"""
    return b''.join((bytes((x,)) if isinstance(x,int) else x) for x in iterable)


class MultisigContract(Contract):
    """Multisig Contract"""

    def __init__(self, addresses, initial_tx=None,v=0, data=None):
        Contract.__init__(self, addresses,initial_tx,v)
        self.participants=3

        self.redeemscript_v1 = joinbytes([
            len(addresses[0].hash160), addresses[0].hash160,
            len(addresses[1].hash160), addresses[1].hash160,
            len(addresses[2].hash160), addresses[2].hash160,
            Op.OP_6, Op.OP_PICK, Op.OP_HASH160, Op.OP_6, Op.OP_PICK, Op.OP_HASH160, Op.OP_OVER, Op.OP_5, Op.OP_PICK,
            Op.OP_EQUAL, Op.OP_2, Op.OP_PICK, Op.OP_5, Op.OP_PICK, Op.OP_EQUAL, Op.OP_BOOLOR, Op.OP_VERIFY, Op.OP_DUP,
            Op.OP_3, Op.OP_PICK, Op.OP_EQUAL, Op.OP_OVER, Op.OP_5, Op.OP_PICK, Op.OP_EQUAL, Op.OP_BOOLOR, Op.OP_VERIFY,
            Op.OP_2DUP, Op.OP_EQUAL, Op.OP_NOT, Op.OP_VERIFY, Op.OP_6, Op.OP_PICK, Op.OP_9, Op.OP_PICK,
            Op.OP_CHECKSIGVERIFY, Op.OP_5, Op.OP_PICK, Op.OP_8, Op.OP_PICK, Op.OP_CHECKSIG, Op.OP_NIP, Op.OP_NIP,
            Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP
        ])



        self.redeemscript=self.redeemscript_v1
        self.set_version(v)
        self.address = Address.from_multisig_script(self.redeemscript)
        data1 = self.address.to_ui_string() + ' ' + str(self.version)
        self.op_return = joinbytes(
            [Op.OP_RETURN, 4, b'>sh\x00', len(data1), data1.encode('utf8')])

        #assert 76 < len(self.redeemscript) <= 255  # simplify push in scriptsig; note len is around 200.
    @staticmethod
    def participants(version):
        if version == 1:
            return 3
        else:
            return 3

    def set_version(self, v):
        if v == 1:
            self.version = 1
            self.redeemscript = self.redeemscript_v1
        else:
            self.version = 1
            self.redeemscript = self.redeemscript_v1
            

class ContractManager:
    """A device that spends from a Multisig Contract in two different ways."""
    def __init__(self, contract_tuple_list, keypairs, public_keys, wallet):
        self.contract_tuple_list = contract_tuple_list
        self.contract_index=0
        self.chosen_utxo = 0
        self.tx = contract_tuple_list[self.contract_index][UTXO][self.chosen_utxo]
        self.contract = contract_tuple_list[self.contract_index][CONTRACT]
        self.mode = contract_tuple_list[self.contract_index][MODE][0]
        self.keypair = keypairs
        self.pubkeys = public_keys
        self.wallet = wallet
        self.dummy_scriptsig = '00'*(110 + len(self.contract.redeemscript))
        self.version = self.contract.version
        self.script_pub_key = Script.P2SH_script(self.contract.address.hash160).hex()
        self.sequence = 0
        self.value = int(self.tx.get('value'))
        self.txin = dict()

    def choice(self, contract_tuple, utxo_index, m):
        self.value=0
        self.txin=[]
        self.chosen_utxo=utxo_index
        self.contract = contract_tuple[CONTRACT]
        self.contract_index = self.contract_tuple_list.index(contract_tuple)
        self.mode = m
        self.version = contract_tuple[CONTRACT].version
        utxo = contract_tuple[UTXO][utxo_index]
        if utxo_index == -1:
            for u in contract_tuple[UTXO]:
                self.value += int(u.get('value'))
                self.txin.append( dict(
                    prevout_hash=u.get('tx_hash'),
                    prevout_n=int(u.get('tx_pos')),
                    sequence=self.sequence,
                    scriptSig=self.dummy_scriptsig,
                    type='unknown',
                    address=self.contract.address,
                    scriptCode=self.contract.redeemscript.hex(),
                    num_sig=1,
                    signatures=[None],
                    x_pubkeys=[self.pubkeys[self.contract_index][self.mode]],
                    value=int(u.get('value')),
                ))
        else:
            self.value = int(utxo.get('value'))
            self.txin = [dict(
                prevout_hash=utxo.get('tx_hash'),
                prevout_n=int(utxo.get('tx_pos')),
                sequence=self.sequence,
                scriptSig=self.dummy_scriptsig,
                type='unknown',
                address=self.contract.address,
                scriptCode=self.contract.redeemscript.hex(),
                num_sig=1,
                signatures=[None],
                x_pubkeys=[self.pubkeys[self.contract_index][self.mode]],
                value=int(utxo.get('value')),
            )]


    def complete_method(self, action='default'):
        return self.completetx_multisig


    def signtx(self, tx):
        """generic tx signer for compressed pubkey"""
        tx.sign(self.keypair)

    def end_tx(self, inputs, direction):
        outputs = [
            (TYPE_ADDRESS, self.contract.addresses[direction], self.value)]
        tx = Transaction.from_io(inputs, outputs, locktime=0)
        tx.version = 2
        fee = 2*(len(tx.serialize(True)) // 2 + 1)
        if fee > self.value:
            raise Exception("Not enough funds to make the transaction!")
        outputs = [
            (TYPE_ADDRESS, self.contract.addresses[direction], self.value - fee)]
        tx = Transaction.from_io(inputs, outputs, locktime=0)
        tx.version = 2
        return tx

    def completetx_multisig(self, tx):
        """
        Completes transaction by creating scriptSig. You need to sign the
        transaction before using this (see `signtx`).
        This works on multiple utxos if needed.
        """
        for txin in tx.inputs():
            # find matching inputs
            if txin['address'] != self.contract.address:
                continue
            sig1 = txin['signatures'][0]
            sig2 = txin['signatures'][1]
            pub1 = txin['x_pubkeys'][0]
            pub2 = txin['x_pubkeys'][1]
            if not (sig1 and sig2 and pub1 and pub2):
                continue
            sig1 = bytes.fromhex(txin['signatures'][0])
            sig2 = bytes.fromhex(txin['signatures'][1])
            pub1 = bytes.fromhex(txin['x_pubkeys'][0])
            pub2 = bytes.fromhex(txin['x_pubkeys'][1])
            if txin['scriptSig'] == self.dummy_scriptsig:
                script = [
                    len(pub1), pub1,
                    len(pub2), pub2,
                    len(sig1), sig1,
                    len(sig2), sig2,
                    76, len(self.contract.redeemscript).to_bytes(1, 'little'), self.contract.redeemscript,
                    ]
                print("scriptSig length " + str(joinbytes(script).hex().__sizeof__()))
                txin['scriptSig'] = joinbytes(script).hex()
        # need to update the raw, otherwise weird stuff happens.
        tx.raw = tx.serialize()


