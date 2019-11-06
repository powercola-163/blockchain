# {
#     "index":0,  #�������
#     "timestamp":"",     #ʱ���
#     "transactions":[    #������Ϣ
#         {
#             "sender":"",    #���׵ķ�����
#             "recipient":"",     #���׵Ľ�����
#             "amount":5,     #���׵Ľ��
#         }
#     ],
#     "proof":"",     #������֤��
#     "previous_hash":"",     #��һ������Ĺ�ϣֵ
#
# }

import hashlib
import json
import requests
from uuid import uuid4
from time import time
from flask import Flask, jsonify, request
from  urllib.parse import urlparse
from argparse import ArgumentParser

class Blockchain:

    #���캯��
    def __init__(self):
        # һ��Ԫ�ض�Ӧһ����
        self.chain = []
        # ���浱ǰ�Ľ�����Ϣ��һ��Ԫ�ض�Ӧһ������ʵ��
        self.current_transactions = []
        # ����ڵ���Ϣ��set()��ÿ��ֵ���Ƕ�һ�޶���
        self.nodes = set()

        # �����������飬���ü��㣬û������
        self.new_block(proof = 100,previous_hash = 1)

    #ע��ڵ�
    def register_node(self,address:str):
        #��ַ��ʽ:http://127.0.0.1:5001
        #ͨ��urlparse������ַ
        parsed_url = urlparse(address)
        #����ַ�е�netloc������ȡ����
        self.nodes.add(parsed_url.netloc)

    #��֤hashֵ�����Ƿ�����Ч��
    def valid_chain(self,chain)->bool:
        #ȡ�׿�
        last_block = chain[0]
        #��ǰ����(��һ����������0���ü��㣬��ӵڶ����顪��������1�Ŀ�ʼ����)
        current_index = 1

        #���������
        while current_index <len(chain):
            block = chain[current_index]
            #�����ǰ���ǰһ����ϣֵ����ֵ���������Ǽ����������һ����Ĺ�ϣֵ��˵������٣���֤��ͨ��
            if block['previous_hash'] != self.hash(last_block):
                return False
            #������֤�����ܲ�����涨(�������ĸ�0��ͷ)
            if not self.valid_proof(last_block['proof'],block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    #�����ͻ
    def resolve_conflicts(self)->bool:
        #�õ��ڵ���Ϣ
        neighbours = self.nodes
        #����������
        max_length = len(self.chain)
        #�ݴ�����
        new_chain = None

        #�����ھӵ����ݣ����������ȡ������
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                #���ǽϳ���������Ч����ȡ��
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        #���new_chain���ڵĻ�����˵�������µ����
        if new_chain:
            self.chain = new_chain
            return True

        return False


    # �µ�����
    def new_block(self,proof,previous_hash = None):
        #����json����
        block = {
            'index':len(self.chain) + 1,
            'timestamp':time(),
            'transcations':self.current_transactions,
            'proof':proof,
            # �����Ǵ�������hashֵ�����ǵ���hash()���������hashֵ
            'previous_hash':previous_hash or self.hash(self.last_block)
        }

        #�ѽ�����Ϣ��գ���Ϊ�����Ѿ�����������ˣ���ô��ǰ�Ľ��׾��Ѿ�û����
        self.current_transactions = []

        #�����ɵ�������뵽������
        self.chain.append(block)

        return block

    # �µĽ���(�����ߣ������ߣ����)
    def new_transaction(self,sender,recipient,amount)->int:
        #ÿ��������Ϣ����һ��json��������ӵ�������Ϣ�����
        self.current_transactions.append(
            {
                'sender':sender,
                'recipient':recipient,
                'amount':amount
            }
        )
        #����������ԭ������һ
        return self.last_block['index'] + 1

    # ��̬��������������Ĺ�ϣֵ
    @staticmethod
    def hash(block):
        #block��json�����Ȱ�jsonת��Ϊstring�����ַ����򲢱���
        block_string = json.dumps(block,sort_keys = True).encode()
        #�����ַ����������ֽ�����,����hash��ժҪ��Ϣ
        return hashlib.sha256(block_string).hexdigest()

    # ���ԣ���ȡ�����������һ������
    @property
    def last_block(self):
        #-1��ʾ���������һ��Ԫ��
        return self.chain[-1]

    #������֤��
    def proof_of_work(self,last_proof:int)->int:
        proof = 0
        #��ͣ����proof��ֵ����֤proof�Ƿ���������
        while self.valid_proof(last_proof,proof) is False:
            proof += 1
        print(proof)
        return proof

    #��֤��һ������Ĺ�����֤���͵�ǰ��Ҫ��֤�Ĺ�����֤���Ƿ���������
    def valid_proof(self,last_proof:int,proof:int)->bool:
        #�Ȱ�����ֵת����һ���ַ���������
        guess = f'{last_proof}{proof}'.encode()
        #��ͬ���ķ����õ�hashժҪ
        guess_hash = hashlib.sha256(guess).hexdigest()
        print(guess_hash)
        #�������ǰ����λ����0��ͷ�򷵻�True
        return guess_hash[0:4] == '0000'

#��ʼ��Flask��
app = Flask(__name__)

#ʵ����blockchain
blockchain = Blockchain()

#����uuid������ɽڵ��ID,�滻�����
node_identifier = str(uuid4()).replace('-','')

#����һ������ӽ��׵�·�ɣ���POST���͵�������
@app.route('/transactions/new',methods = ['POST'])
def new_transaction():
    #�õ��ͻ�POST����������
    values = request.get_json()

    #���û��values�����
    if values is None:
        return 'Missing values',400

    #�������ֶν��м�飬������ʱ�Ƿ����������������
    required = ['sender','recipient','amount']
    #���k��������һ������required�еĻ����ش��󣬷���400
    if not all(k in values for k in required):
        return 'Missing values',400

    #��������ʽ���½�һ������,�ѽ�����ӵ���ǰ�����飬���ص����伴�����ڵ���������
    index = blockchain.new_transaction(values['sender'],
                               values['recipient'],
                               values['amount'])
    #������ӵĽ��׵���Ϣ���ظ��û�
    response = {'message':f'Transaction will be added to block:{index}'}
    #ͨ��post����ȥ���һ����¼���Ƿ���201
    return jsonify(response),201

#����һ�������ڿ�(���״��)��API
@app.route('/mine',methods = ['GET'])
def mine():
    #�õ���һ���������Ϣ
    last_block = blockchain.last_block
    #ȡ����һ����Ĺ�����֤��
    last_proof = last_block['proof']
    #�������ǰ��Ĺ�����֤��
    proof = blockchain.proof_of_work(last_proof)

    #���Լ����һ������
    blockchain.new_transaction(sender ='0',
                               recipient = node_identifier,
                               amount = 1)

    #��proof�½�һ���飬��None�Ļ����Լ�������һ�������hashֵ
    block = blockchain.new_block(proof,None)

    #�Ѱ��õ���Ϣ���ظ��û�
    response = {
        "message":"New Block Forged",
        "index":block['index'],
        "transactions":block['transcations'],
        "proof":block['proof'],
        "previous_hash":block['previous_hash']
    }

    return jsonify(response),200

#���巵��������������Ϣ��·��
@app.route('/chain',methods = ['GET'])
def full_chain():
    response = {
        #�����Ϣ
        'chain':blockchain.chain,
        #��������ĳ���
        'length':len(blockchain.chain)
    }
    #��dict����ת��Ϊjson��
    return jsonify(response),200

#�ڵ�ע��·��
#{"nodes":["http://127.0.0.2:5000"]}
@app.route('/nodes/register',methods = ['POST'])
def register_nodes():
    #���ܴ�����������
    values = request.get_json()
    #���ܽڵ���Ϣ
    nodes = values.get("nodes")

    #��ϢΪ���ж�
    if nodes is None:
        return "Error:please supply a valid list of node",400

    #��nodeע��
    for node in nodes:
        blockchain.register_node(node)

    #��Ϣ���ظ��û�
    response = {
        "message":"New nodes have been added",
        #ԭ��������Ǹ�set���ϣ�����ת����list
        "total_node":list(blockchain.nodes)
    }

    return jsonify(response),201

#���Ե��ý����ͻ��·��
@app.route('./nodes/resolve',methods = ['GET'])
def consensus():
    #���ú������鿴�����Ƿ�ȡ����
    replaced = blockchain.resolve_conflicts()
    #�����ȡ����Ҫ����һ���û�
    if replaced:
        response = {
            "message":"Our chain was replaced",
            "new_chain":blockchain.chain
        }
    else:
        response = {
            "message": "Our chain is authoritative",
            "chain":blockchain.chain
        }
    return jsonify(response),200


#����Flask,�ṩ�������
if __name__ == '__main__':
    #ÿ�����п������ڲ�ͬ�Ķ˿���,����Ĭ��һ��������ͨ��������������
    #��ʼ��һ��parser�������������в���
    parser = ArgumentParser()
    #���϶˿����������-p 5001 ����--port 5001
    parser.add_argument('-p','--port',default = 5000,type = int,help = 'port to listen to')
    #�������
    args = parser.parse_args()
    port = args.port

    app.run(host = '0.0.0.0',port = port)