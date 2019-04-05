'''
Created on Aug 22, 2017

@author: ADonoghue
'''
import select, socket, sys, Queue


PORT = 50088
HOST = 'localhost' #local host
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(0)
server.bind((HOST, PORT))
server.listen(1)
inputs = [server]
outputs = []
message_queues = {}
timeout = 2
kill = 'False'
replyDict = {'get 1':"Temp 99\nName: AA",
     'get 2':"Temp 10\nName: bang",
     'get 3':"Temp 30\nName: Shorts",
     'get 4':"Temp 44\nName: My",
     'get 5':"Temp 00\nName: Eat",
    }

def formatReply(cmd):

    try:
        reply = replyDict[cmd]
    except KeyError:
        reply = "%s Not a Valid Command"%repr(cmd)
    if cmd == 'kill':
        global kill
        kill = 'True'
        reply = "Killing"
        
    cleanReply = reply.replace('\n','|')
    return cleanReply

def cleanCmd(cmd):
    return cmd.replace('\n','')     

while inputs:
    readable, writable, exceptional = select.select(inputs, outputs, inputs,timeout)
    for item in readable:
        if item is server:
            connection, client_address = item.accept()
            print "Got Socket"
            connection.setblocking(0)

            inputs.append(connection)
            message_queues[connection] = Queue.Queue()
        else:
            data = item.recv(1024)
            if data:              
                cleanData = cleanCmd(data)
                reply = formatReply(cleanData)
                message_queues[item].put(reply+'\n') #add return to make sure receiver reads all the 
                if item not in outputs:
                    outputs.append(item)
            else:
                if item in outputs:
                    outputs.remove(item)
                inputs.remove(item)
                item.close()
                del message_queues[item]
                
    
        
    for item in writable:
        try:
            next_msg = message_queues[item].get_nowait()
        except Queue.Empty:
            outputs.remove(item)
        else:
            print "Sending:",next_msg
            item.send(next_msg)

    for item in exceptional:
        print "Exception"
        inputs.remove(item)
        if item in outputs:
            outputs.remove(item)
        item.close()
        del message_queues[item]
    
    if kill == 'True':
        print 'Leaving!'
        break
    else:
        print "KILL:",kill

    