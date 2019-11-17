# Simple Escrow Plugin
The plugin that lets you make a simple escrow smart contract that require only normal "bitcoincash:q..." addresses and no awkward xpub exchange ritual.

## Quick Start

### Installing 

Download a zip file from [releases](https://github.com/KarolTrzeszczkowski/Electron-Cash-Simple-Escrow-Plugin/releases). **Not** from **Clone or Dowlnoad**! Turn on Electron Cash desktop and go to **tools -> Installed Plugins... -> Add Plugin** and select the .zip file. Check warning boxes. A new tab tittles **Simple Escrow Plugin** should appear.

### Create escrow contract

In **Simple Escrow Plugin** tab click **Create new Escrow contract** and paste *receiver address* and *arbiter address*. Put amount and click create contract. All participants will be notified by transaction of 546 satoshi. Now the contract is created and it's 

### Managing the contract

To view contracts you participate with click **Find existing Escrow contract** and a list of contracts shou;d appear.
Any of participants can initiate escrow resolving - either **forwarding** funds to recipient or **refunding** the sender. Clicking one of the management buttons will invoke a dialog with a line of text you should send to any of the other parties. Another party should select the entry that is meant to be resolved, click **Load and sign transaction** and paste the text received from the party initiating resolution. The wallet will sign transaction and show preview of the transaction. Then **Broadcast** the transaction.

## Contact the author

With any problems contact me on telegram: **@licho92karol**, reddit: **u/Licho92** e-mail: **name.lastname@gmail.com**, twitter: **@KTrzeszczkowski**. If you wish to contact me via Signal or whatsapp, ask for my phone number on any of this channels.

I want to give credit to **im_uname#102** for the idea of making this plugin, testing it and supporting its creation from his own poket. Also big thank you to Emergent Reasons for help with testing it at the cost of his sleeping time.

I want to acknowledge Huck Finne for his continuaous support of my projects with recurring donations Mecenate.

## Mecenate and donations

If you wish to support development of the [Mecenas plugin](https://github.com/KarolTrzeszczkowski/Mecenas-recurring-payment-EC-plugin), [Last Will plugin](https://github.com/KarolTrzeszczkowski/Electron-Cash-Last-Will-Plugin), [Inter-Wallet transfer plugin](https://github.com/KarolTrzeszczkowski/Inter-Wallet-Transfer-EC-plugin), consider **becoming my mecenas** for the address:

bitcoincash:qq93dq0j3uez8m995lrkx4a6n48j2fckfuwdaqeej2

I will prioritize my patrons feature requests, offer direct support in case of problems or support with integration in their services.

**Or donating**: 

Cash Account: Licho#14431

bitcoincash:qq93dq0j3uez8m995lrkx4a6n48j2fckfuwdaqeej2

Legacy format: 121dPy31QTsxAYUyGRbwEmW2c1hyZy1Xnz

![donate](/pictures/donate.png)






