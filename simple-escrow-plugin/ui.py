from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import electroncash.web as web
import webbrowser
from .multisig_contract import MultisigContract
from electroncash.address import ScriptOutput, OpCodes, Address, Script
from electroncash.transaction import Transaction,TYPE_ADDRESS, TYPE_SCRIPT, SerializationError
from electroncash_gui.qt.amountedit  import BTCAmountEdit
from electroncash.i18n import _
from electroncash_gui.qt.util import *
from electroncash.wallet import Multisig_Wallet
from electroncash.util import NotEnoughFunds
from electroncash_gui.qt.transaction_dialog import show_transaction
from .contract_finder import find_contract_in_wallet
from .multisig_contract import ContractManager, UTXO, CONTRACT, MODE, RECEIVER, SENDER, ARBITER
from .util import *
from math import ceil
import json


class Intro(QDialog, MessageBoxMixin):

    def __init__(self, parent, plugin, wallet_name, password, manager=None):
        QDialog.__init__(self, parent)
        self.main_window = parent
        self.wallet=parent.wallet
        self.plugin = plugin
        self.wallet_name = wallet_name
        self.config = parent.config
        vbox = QVBoxLayout()
        self.setLayout(vbox)
        self.contract_tuple_list=None
        self.contractTx=None
        self.manager=None
        self.password = None
        self.mode=0
        hbox = QHBoxLayout()
        if is_expired():
            l = QLabel(_("Please update your plugin"))
            l.setStyleSheet("QLabel {color:#ff0000}")
            vbox.addWidget(l)
        l = QLabel("<b>%s</b>"%(_("Manage my Sender:")))
        vbox.addWidget(l)

        vbox.addLayout(hbox)
        b = QPushButton(_("Create new Escrow contract"))
        b.clicked.connect(lambda: self.plugin.switch_to(Create, self.wallet_name, None, self.manager))
        hbox.addWidget(b)
        b = QPushButton(_("Find existing Escrow contract"))
        b.clicked.connect(self.handle_finding)
        hbox.addWidget(b)
        vbox.addStretch(1)

    def handle_finding(self):
        self.contract_tuple_list = find_contract_in_wallet(self.wallet, MultisigContract)
        if len(self.contract_tuple_list):
            self.start_manager()
        else:
            self.show_error("You are not a party in any contract yet.")


    def start_manager(self):
        try:
            keypairs, public_keys = self.get_keypairs_for_contracts(self.contract_tuple_list)
            self.manager = ContractManager(self.contract_tuple_list, keypairs, public_keys, self.wallet)
            self.plugin.switch_to(Manage, self.wallet_name, self.password, self.manager)
        except Exception as es:
            print(es)
            # self.show_error("Wrong password.")
            self.plugin.switch_to(Intro,self.wallet_name,None,None)

    def get_keypairs_for_contracts(self, contract_tuple_list):
        if self.wallet.has_password():
            self.main_window.show_error(_(
                "Contract found! Plugin requires password to operate. It will get access to your private keys."))
            self.password = self.main_window.password_dialog()
            if not self.password:
                return
            try:
                self.wallet.keystore.get_private_key((True,0), self.password)
            except:
                self.show_error("Wrong password.")
                return
        keypairs = dict()
        public_keys=[]
        for t in contract_tuple_list:
            public_keys.append(dict())
            for m in t[MODE]:
                my_address=t[CONTRACT].addresses[m]
                i = self.wallet.get_address_index(my_address)
                if not self.wallet.is_watching_only():
                    priv = self.wallet.keystore.get_private_key(i, self.password)
                else:
                    print("watch only")
                    priv = None
                try:
                    public = self.wallet.get_public_keys(my_address)
                    public_keys[contract_tuple_list.index(t)][m]=public[0]
                    keypairs[public[0]] = priv
                except Exception as ex:
                    print(ex)
        return keypairs, public_keys



class Create(QDialog, MessageBoxMixin):

    def __init__(self, parent, plugin, wallet_name, password, manager):
        QDialog.__init__(self, parent)
        self.main_window = parent
        self.wallet=parent.wallet
        self.plugin = plugin
        self.wallet_name = wallet_name
        self.config = parent.config
        self.password=None
        self.contract=None
        self.version=1
        if self.wallet.has_password():
            self.main_window.show_error(_(
                "Plugin requires password. It will get access to your private keys."))
            self.password = parent.password_dialog()
            if not self.password:
                print("no password")
                self.plugin.switch_to(Intro, self.wallet_name,None, None)
        self.fund_domain = None
        self.fund_change_address = None
        self.sender_address = self.wallet.get_unused_address()
        self.receiver_address=None
        self.arbiter_address=None
        self.total_value=0
        index = self.wallet.get_address_index(self.sender_address)
        key = self.wallet.keystore.get_private_key(index,self.password)
        self.privkey = int.from_bytes(key[0], 'big')

        if isinstance(self.wallet, Multisig_Wallet):
            self.main_window.show_error(
                "Simple Escrow Plugin is designed for single signature wallets.")

        vbox = QVBoxLayout()
        self.setLayout(vbox)
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)
        l = QLabel("<b>%s</b>" % (_("Creatin 2-of-3 Multisig contract:")))
        hbox.addWidget(l)
        hbox.addStretch(1)
        b = QPushButton(_("Home"))
        b.clicked.connect(lambda: self.plugin.switch_to(Intro, self.wallet_name, None, None))
        hbox.addWidget(b)
        l = QLabel(_("Refund address") + ": auto (this wallet)")  # self.refreshing_address.to_ui_string())
        vbox.addWidget(l)
        l = QLabel(_("Receiver address: "))
        vbox.addWidget(l)

        self.receiver_address_wid = QLineEdit()
        self.receiver_address_wid.textEdited.connect(self.new_contract_info_changed)
        vbox.addWidget(self.receiver_address_wid)

        l = QLabel(_("Arbiter address: "))
        vbox.addWidget(l)

        self.arbiter_address_wid = QLineEdit()
        self.arbiter_address_wid.textEdited.connect(self.new_contract_info_changed)
        vbox.addWidget(self.arbiter_address_wid)

        self.value_wid = BTCAmountEdit(self.main_window.get_decimal_point)
        self.value_wid.setAmount(1000000)
        self.value_wid.textEdited.connect(self.new_contract_info_changed)
        vbox.addWidget(self.value_wid)
        b = QPushButton(_("Create Escrow Contract"))
        b.clicked.connect(self.create_new_contract)
        vbox.addStretch(1)
        vbox.addWidget(b)
        self.create_button = b
        self.create_button.setDisabled(True)
        vbox.addStretch(1)


    def new_contract_info_changed(self, ):
            # if any of the txid/out#/value changes
        try:
            self.total_value = self.value_wid.get_amount()
            self.receiver_address = Address.from_string(self.receiver_address_wid.text())
            self.arbiter_address = Address.from_string(self.arbiter_address_wid.text())
            addresses = [self.receiver_address, self.sender_address,self.arbiter_address]
        except:
            self.create_button.setDisabled(True)
        else:
            self.create_button.setDisabled(False)
            self.contract = MultisigContract(addresses, v=self.version, data=None)

    def build_otputs(self):
        outputs = []
        outputs.append((TYPE_SCRIPT, ScriptOutput(self.contract.op_return),0))
        for a in self.contract.addresses:
            outputs.append((TYPE_ADDRESS, a, 546))
        outputs.append((TYPE_ADDRESS, self.contract.address, self.total_value))
        return outputs


    def create_new_contract(self, ):
        yorn = self.main_window.question(_(
            "Do you wish to create the Sender Contract?"))
        if not yorn:
            return
        outputs = self.build_otputs()
        receiver_is_mine = self.wallet.is_mine(self.contract.addresses[0])
        escrow_is_mine = self.wallet.is_mine(self.contract.addresses[2])
        if receiver_is_mine and escrow_is_mine:
            self.show_error(
                "All three participants are in your wallet. Such contract will be impossible to terminate. Aborting.")
            return
        try:
            tx = self.wallet.mktx(outputs, self.password, self.config,
                                  domain=self.fund_domain, change_addr=self.fund_change_address)
        except NotEnoughFunds:
            return self.show_critical(_("Not enough balance to fund smart contract."))
        except Exception as e:
            return self.show_critical(repr(e))
        tx.version=2
        try:
            self.main_window.network.broadcast_transaction2(tx)
        except:
            pass
        self.create_button.setText("Creating Escrow Contract...")
        self.create_button.setDisabled(True)
        self.plugin.switch_to(Intro, self.wallet_name, None, None)



class ContractTree(MessageBoxMixin, PrintError, MyTreeWidget):
    update_sig = pyqtSignal()

    def __init__(self, parent, contracts):
        MyTreeWidget.__init__(self, parent, self.create_menu,[
            _('Contract address'),
            _('Amount'),
            _('My role'),
            _('Version')],stretch_column=0, deferred_updates=True)
        self.contract_tuple_list = contracts
        self.monospace_font = QFont(MONOSPACE_FONT)

        self.main_window = parent
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)
        self.update_sig.connect(self.update)

    def create_menu(self, position):
        pass

    def get_selected_id(self):
        utxo = self.currentItem().data(0, Qt.UserRole)
        contract_tuple = self.currentItem().data(1, Qt.UserRole)
        m = self.currentItem().data(2, Qt.UserRole)
        if utxo == None:
            index = -1
        else:
            index = contract_tuple[UTXO].index(utxo)
        return contract_tuple, index, m

    def on_update(self):
        self.clear()
        for t in self.contract_tuple_list:
            for m in t[MODE]:
                ver = str(t[CONTRACT].version)
                a = 0
                for u in t[UTXO]:
                    a+= u.get('value')
                amount = self.parent.format_amount(a, is_diff=False, whitespaces=True)
                contract = QTreeWidgetItem([t[CONTRACT].address.to_ui_string(),"Total: " + amount,role_name(m),ver])
                contract.setData(1, Qt.UserRole, t)
                contract.setData(2,Qt.UserRole, m)
                contract.setFont(0, self.monospace_font)
                contract.setTextAlignment(2, Qt.AlignRight)
                contract.setTextAlignment(3, Qt.AlignRight)
                self.addChild(contract)
                for u in t[UTXO]:
                    item = self.add_item(u, contract, t, m)
                    self.setCurrentItem(item)



    def add_item(self, u, parent_item, t, m):
        amount = self.parent.format_amount(u.get('value'), is_diff=False, whitespaces=True)
        utxo_item = SortableTreeWidgetItem([u['tx_hash'] , amount, '', ''])
        utxo_item.setData(0, Qt.UserRole, u)
        utxo_item.setData(1, Qt.UserRole, t)
        utxo_item.setData(2, Qt.UserRole, m)
        utxo_item.setTextAlignment(2, Qt.AlignRight)
        utxo_item.setTextAlignment(3, Qt.AlignRight)
        parent_item.addChild(utxo_item)
        return utxo_item



class Manage(QDialog, MessageBoxMixin):
    def __init__(self, parent, plugin, wallet_name, password, manager):
        QDialog.__init__(self, parent)
        self.password=password

        self.main_window = parent
        self.wallet=parent.wallet
        self.plugin = plugin
        self.wallet_name = wallet_name
        self.config = parent.config
        self.complete = None
        self.manager=manager
        vbox = QVBoxLayout()
        self.setLayout(vbox)
        self.contract_tree = ContractTree(self.main_window, self.manager.contract_tuple_list)
        self.contract_tree.on_update()
        vbox.addWidget(self.contract_tree)
        hbox = QHBoxLayout()
        hbox.addStretch(1)
        vbox.addLayout(hbox)
        b = QPushButton(_("Home"))
        b.clicked.connect(lambda: self.plugin.switch_to(Intro, self.wallet_name, None, None))
        hbox.addWidget(b)
        b = QPushButton(_("Create new Escrow Contract"))
        b.clicked.connect(lambda: self.plugin.switch_to(Create, self.wallet_name, None, self.manager))
        hbox.addWidget(b)
        vbox.addStretch(1)
        self.load_button = QPushButton(_("Load and sign transaction"))
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addStretch(1)
        hbox.addWidget(self.load_button)
        self.load_button.clicked.connect(self.on_load)
        self.refund_button = QPushButton(_("Refund contract"))
        self.refund_button.clicked.connect(lambda: self.end(SENDER))
        self.forward_button = QPushButton(_("Forward to the receiver"))
        self.forward_button.clicked.connect(lambda: self.end(RECEIVER))
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(self.refund_button)
        hbox.addWidget(self.forward_button)
        self.contract_tree.currentItemChanged.connect(self.update_buttons)
        self.update_buttons()


    def update_buttons(self):
        contract, utxo_index, m = self.contract_tree.get_selected_id()
        self.manager.choice(contract, utxo_index, m)

    def on_load(self):
        tx=None
        try:
            text = text_dialog(self.top_level_window(), _('Input raw transaction'), _("Transaction:"),
                               _("Load transaction"))
            if not text:
                return
            tx = self.main_window.tx_from_text(text)
        except SerializationError as e:
            self.show_critical(_("Electron Cash was unable to deserialize the transaction:") + "\n" + str(e))
        if tx:
            tx.raw = tx.serialize()
            inputs = tx.inputs()
            metadata = inputs[0]['scriptSig'].split('1234567890')
            sig = metadata[1]
            xpub = metadata[0][-66:]
            addr1 = Address.from_pubkey(str(xpub))
            other_party_role = self.manager.contract.addresses.index(addr1)

            for inp in tx.inputs():
                for i, j in self.manager.txin[0].items():
                    inp[i]=j
                inp['pubkeys'] = inp['x_pubkeys'] # problems with signing without it
                inp['sequence'] = 0
                inp['signatures'] = [None]
            tx.raw = tx.serialize()
            self.manager.signtx(tx)
            #self.wallet.sign_transaction(tx, self.password)
            for inp in tx.inputs():
                print(inp['signatures'])
                inp['x_pubkeys'].append(xpub)
                inp['signatures'].append(sig)
                if self.manager.mode > other_party_role:
                    # sender key can be on any place but receiver has to be on the first and arbiter has to be on the second.
                    # see sender_v3.spedn
                    inp['x_pubkeys'][0],inp['x_pubkeys'][1] = inp['x_pubkeys'][1],inp['x_pubkeys'][0]
                    inp['signatures'][0],inp['signatures'][1] = inp['signatures'][1],inp['signatures'][0]
                inp['num_sig'] = 2
            tx.raw = tx.serialize()
            complete = self.manager.complete_method("end")
            complete(tx)
            print("Script Public Key: ", self.manager.script_pub_key)
            show_transaction(tx, self.main_window, "End Sender Contract", prompt_if_unsaved=True)


    def end(self,direction):
        print("end")
        inputs = self.manager.txin
        for i in inputs:
            i['num_sig'] = 2
            i['x_pubkeys'] = [self.manager.pubkeys[self.manager.contract_index][self.manager.mode]]
        tx = self.manager.end_tx(inputs, direction)
        if not self.wallet.is_watching_only():
            self.manager.signtx(tx)
        inputs = tx.inputs()[0]
        sig = inputs['signatures'][0]
        pk = inputs["x_pubkeys"][0]
        print('SIGNATURE', sig)
        print("lensig", len(str(sig)))
        print("lenpk", len(str(pk)))
        inputs['scriptSig']=inputs['scriptSig'][:-(len(sig)+len(pk)+10)]+pk+'1234567890'+sig
        tx.raw = tx.serialize()
        print("ScriptPK", self.manager.script_pub_key)
        self.main_window.show_message("Double click to select and send this to another party:\n\n" + tx.raw)
        self.update_buttons()
        # show_transaction(tx, self.main_window, "End Sender Contract", prompt_if_unsaved=True)


def role_name(i):
    if i == RECEIVER:
        return "Receiver"
    elif i == SENDER:
        return "Sender"
    elif i == ARBITER:
        return "Arbiter"
    else:
        return "unknown role"
