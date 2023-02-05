# module 2 create a Cryptocurrency

import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse

# Part 1 building a blockchain

class Blockchain:
    
    # initialize the blockchain
    def __init__(self):
        # create blockchain
        self.chain = []
        # create list of transactions
        self.transactions = []
        # mine the genesis block
        self.create_block(proof = 1, previous_hash = '0')
        # create list of nodes
        self.nodes = set()

    # Create a new block and append it to the chain
    # Also commit the new transactions
    #
    # input: proof - proof of work for the new block
    # input: previous_hash - the previous hash from the chain
    # output: the mined block
    def create_block(self, proof, previous_hash):
        # create the block
        block = {'index': len(self.chain) + 1,
                 'timestamp': str(datetime.datetime.now()),
                 'proof': proof,
                 'previous_hash': previous_hash,
                 'transactions': self.transactions}
        # the transactions has been added to block
        # so now we clear the transactions list
        self.transactions = []
        # append newly created block to the blockchain
        self.chain.append(block)
        return block
    
    # Get the previous block from the current chain
    #
    # output: the previous block
    def get_previous_block(self):
        return self.chain[-1]
    
    # Start mining and get the proof of work for a new block
    #
    # input: previous_proof - the proof of work of the previous block
    # output: the proof of work for the new block
    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        while check_proof is False:
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof
    
    # Get the sha256 hash of a block
    #
    # input: block - the block to be checked
    # output: sha256 hash of the block
    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
    
    # Check if a chain is valid by looping through all
    # the block and check the validity of the hash
    #
    # input: chain - the chain to be checked
    # output: True if chain is valid, otherwise False
    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            # check previous hash of each block is
            # equal to hash of previous block
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                return False
            
            # check proof of each block is valid
            # by checking the hash target (4 leading zeros)            
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            previous_block = block
            block_index += 1
        return True
    
    # Add a new transaction to our transaction list
    #
    # input: sender - public key of the sender
    # input: receiver - public key of the receiver
    # input: amount - the amount of coins to be sent
    # output: index of the block the the transaction is to be added
    def add_transaction(self, sender, receiver, amount):
        self.transactions.append({'sender': sender,
                                  'receiver': receiver,
                                  'amount': amount})
        previous_block = self.get_previous_block()
        return previous_block['index'] + 1
    
    # Add a new node to our blockchain
    #
    # input: address - the address of the new node
    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    #　Replace the current chain if there is a new
    # longest chain in the network
    #
    # output: True if the current chain was replaced, otherwise False
    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        # check each nodes in network
        for node in network:
            # send request to get chain from each nodes
            response = requests.get(f'https://{node}/get_chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                # check if length of the node is longer than current max length
                # and the chain is valid
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        # if chain is replaced
        if longest_chain:
            self.chain = longest_chain
            return True
        return False

# Part 2 mining our blockchain

# Creating a web app
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Creating an address for node on Port 5000
node_address = str(uuid4()).replace('-', '')

# Creating a blockchain
blockchain = Blockchain()

# Mining a new block
@app.route('/mine_block', methods=['GET'])
def mine_block():
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    # fee for block miner
    blockchain.add_transaction(sender = node_address, receiver = 'hoang', amount = 1)
    block = blockchain.create_block(proof, previous_hash)
    response = {'message': 'Congratulations, you just mine a block!',
                'index': block['index'],
                'timestamp': block['timestamp'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
                'transactions': block['transactions']}
    return jsonify(response), 200

# Add new transaction
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    json = request.get_json()
    transaction_keys = ['sender', 'receiver', 'amount']
    # check if all transaction keys are valid
    if not all (key in json for key in transaction_keys):
        return 'Some elements of the transaction are missing', 400
    # add transaction to current blockchain
    index = blockchain.add_transaction(json['sender'],
                                       json['receiver'],
                                       json['amount'])
    response = {'message': f'Transaction will be added to block {index}',
                'sender': json['sender'],
                'receiver': json['receiver'],
                'amount': json['amount']}
    return jsonify(response), 201
    

# Gettings the full blockchain
@app.route('/get_chain', methods = ['GET'])
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200

# Checking if the blockchain is valid
@app.route('/is_valid', methods = ['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message': 'All good. The blockchain is valid'}
    else:
        response = {'message': 'NG. The blockchain is not valid'}
    return jsonify(response), 200

# Part 3 decentralizing our blockchain

# Connecting new nodes
@app.route('/connect_node', methods=['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    if nodes is None:
        return 'No node', 400
    # add all the nodes from the request
    for node in nodes:
        blockchain.add_node(node)
    response = {'message': 'All the nodes are now connected!',
                'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201

# Replacing the chain by the longest chain if needed
@app.route('/replace_chain', methods = ['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message': 'The blockchain was replaced by the longest chain',
                    'new_chain': blockchain.chain,
                    'new_length': len(blockchain.chain)}
    else:
        response = {'message': 'The current blockchain is the largest one',
                    'chain': blockchain.chain,
                    'length': len(blockchain.chain)}
    return jsonify(response), 200

# For testing
@app.route('/')
def test():
    return 'The app works!'

# Run app
app.run(host = '0.0.0.0', port = 5000, ssl_context='adhoc')


