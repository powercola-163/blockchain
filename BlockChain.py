# {
#     "index":0,  #块的索引
#     "timestamp":"",     #时间戳
#     "transactions":[    #交易信息
#         {
#             "sender":"",    #交易的发送者
#             "recipient":"",     #交易的接收者
#             "amount":5,     #交易的金额
#         }
#     ],
#     "proof":"",     #工作量证明
#     "previous_hash":"",     #上一个区块的哈希值
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

    #构造函数
    def __init__(self):
        # 一个元素对应一个块
        self.chain = []
        # 保存当前的交易信息，一个元素对应一个交易实体
        self.current_transactions = []
        # 保存节点信息，set()中每个值都是独一无二的
        self.nodes = set()

        # 创建创世区块，不用计算，没有内容
        self.new_block(proof = 100,previous_hash = 1)

    #注册节点
    def register_node(self,address:str):
        #地址格式:http://127.0.0.1:5001
        #通过urlparse解析地址
        parsed_url = urlparse(address)
        #将地址中的netloc部分提取出来
        self.nodes.add(parsed_url.netloc)

    #验证hash值，看是否是有效链
    def valid_chain(self,chain)->bool:
        #取首块
        last_block = chain[0]
        #当前索引(第一个块索引是0不用计算，则从第二个块——索引是1的开始计算)
        current_index = 1

        #遍历这个链
        while current_index <len(chain):
            block = chain[current_index]
            #如果当前块的前一个哈希值属性值不等于我们计算出来的上一个块的哈希值，说明链虚假，验证不通过
            if block['previous_hash'] != self.hash(last_block):
                return False
            #工作量证明可能不满足规定(这里是四个0开头)
            if not self.valid_proof(last_block['proof'],block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    #解决冲突
    def resolve_conflicts(self)->bool:
        #拿到节点信息
        neighbours = self.nodes
        #自身链表长度
        max_length = len(self.chain)
        #暂存链条
        new_chain = None

        #遍历邻居的数据，用最长的链条取代该链
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                #若是较长链且是有效链则取代
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        #如果new_chain存在的话，则说明它是新的最长链
        if new_chain:
            self.chain = new_chain
            return True

        return False


    # 新的区块
    def new_block(self,proof,previous_hash = None):
        #构造json对象
        block = {
            'index':len(self.chain) + 1,
            'timestamp':time(),
            'transcations':self.current_transactions,
            'proof':proof,
            # 可以是传过来的hash值或者是调用hash()计算出来的hash值
            'previous_hash':previous_hash or self.hash(self.last_block)
        }

        #把交易信息清空，因为交易已经打包成区块了，那么当前的交易就已经没有了
        self.current_transactions = []

        #把生成的区块加入到链条中
        self.chain.append(block)

        return block

    # 新的交易(发送者，接受者，金额)
    def new_transaction(self,sender,recipient,amount)->int:
        #每个交易信息都是一个json，把它添加到交易信息的最后
        self.current_transactions.append(
            {
                'sender':sender,
                'recipient':recipient,
                'amount':amount
            }
        )
        #返回索引：原索引加一
        return self.last_block['index'] + 1

    # 静态方法，计算区块的哈希值
    @staticmethod
    def hash(block):
        #block是json对象，先把json转化为string并对字符排序并编码
        block_string = json.dumps(block,sort_keys = True).encode()
        #传入字符串编码后的字节数组,返回hash的摘要信息
        return hashlib.sha256(block_string).hexdigest()

    # 属性，获取到区块链最后一个区块
    @property
    def last_block(self):
        #-1表示是数组最后一个元素
        return self.chain[-1]

    #工作量证明
    def proof_of_work(self,last_proof:int)->int:
        proof = 0
        #不停尝试proof的值，验证proof是否满足条件
        while self.valid_proof(last_proof,proof) is False:
            proof += 1
        print(proof)
        return proof

    #验证上一个区块的工作量证明和当前需要验证的工作量证明是否满足条件
    def valid_proof(self,last_proof:int,proof:int)->bool:
        #先把两个值转化成一个字符串并编码
        guess = f'{last_proof}{proof}'.encode()
        #用同样的方法拿到hash摘要
        guess_hash = hashlib.sha256(guess).hexdigest()
        print(guess_hash)
        #如果满足前面四位是以0开头则返回True
        return guess_hash[0:4] == '0000'

#初始化Flask类
app = Flask(__name__)

#实例化blockchain
blockchain = Blockchain()

#利用uuid随机生成节点的ID,替换掉横杠
node_identifier = str(uuid4()).replace('-','')

#定义一个新添加交易的路由，用POST发送到服务器
@app.route('/transactions/new',methods = ['POST'])
def new_transaction():
    #拿到客户POST过来的内容
    values = request.get_json()

    #如果没有values的情况
    if values is None:
        return 'Missing values',400

    #对三个字段进行检查，看请求时是否带上了这三个参数
    required = ['sender','recipient','amount']
    #如果k中内容有一个不在required中的话返回错误，返回400
    if not all(k in values for k in required):
        return 'Missing values',400

    #如果满足格式则新建一个交易,把交易添加到当前的数组，返回的是其即将所在的区块索引
    index = blockchain.new_transaction(values['sender'],
                               values['recipient'],
                               values['amount'])
    #把新添加的交易的信息返回给用户
    response = {'message':f'Transaction will be added to block:{index}'}
    #通常post请求去添加一条记录都是返回201
    return jsonify(response),201

#定义一个用来挖矿(交易打包)的API
@app.route('/mine',methods = ['GET'])
def mine():
    #拿到上一个区块的信息
    last_block = blockchain.last_block
    #取出上一个块的工作量证明
    last_proof = last_block['proof']
    #计算出当前块的工作量证明
    proof = blockchain.proof_of_work(last_proof)

    #给自己添加一个奖励
    blockchain.new_transaction(sender ='0',
                               recipient = node_identifier,
                               amount = 1)

    #用proof新建一个块，传None的话会自己计算上一个区块的hash值
    block = blockchain.new_block(proof,None)

    #把包好的信息返回给用户
    response = {
        "message":"New Block Forged",
        "index":block['index'],
        "transactions":block['transcations'],
        "proof":block['proof'],
        "previous_hash":block['previous_hash']
    }

    return jsonify(response),200

#定义返回整个区块链信息的路由
@app.route('/chain',methods = ['GET'])
def full_chain():
    response = {
        #块的信息
        'chain':blockchain.chain,
        #链条数组的长度
        'length':len(blockchain.chain)
    }
    #将dict类型转换为json串
    return jsonify(response),200

#节点注册路由
#{"nodes":["http://127.0.0.2:5000"]}
@app.route('/nodes/register',methods = ['POST'])
def register_nodes():
    #接受传过来的数据
    values = request.get_json()
    #接受节点信息
    nodes = values.get("nodes")

    #信息为空判断
    if nodes is None:
        return "Error:please supply a valid list of node",400

    #多node注册
    for node in nodes:
        blockchain.register_node(node)

    #信息返回给用户
    response = {
        "message":"New nodes have been added",
        #原来定义的是个set集合，这里转化成list
        "total_node":list(blockchain.nodes)
    }

    return jsonify(response),201

#可以调用解决冲突的路由
@app.route('./nodes/resolve',methods = ['GET'])
def consensus():
    #调用函数并查看链条是否被取代了
    replaced = blockchain.resolve_conflicts()
    #如果被取代了要告诉一下用户
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


#启动Flask,提供运行入口
if __name__ == '__main__':
    #每次运行可以跑在不同的端口上,不是默认一个，而是通过参数传过来的
    #初始化一个parser用来解析命令行参数
    parser = ArgumentParser()
    #加上端口命令，举例：-p 5001 或者--port 5001
    parser.add_argument('-p','--port',default = 5000,type = int,help = 'port to listen to')
    #对其解析
    args = parser.parse_args()
    port = args.port

    app.run(host = '0.0.0.0',port = port)