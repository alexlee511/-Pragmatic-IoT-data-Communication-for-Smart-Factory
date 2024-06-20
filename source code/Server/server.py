import paho.mqtt.client as mqtt
import os
import sys
import grpc
import json
import time
import datetime
from chirpstack_api.as_pb.external import api
import requests
from operator import itemgetter, attrgetter
import threading

# Configuration.

# This must point to the API interface.
server = "140.122.184.235:8080"
device_all = 3
outputFile = "demo2.txt"
device_num = 2

dev_eui = [None] * (device_all+1)
dev_sub = [None] * (device_all+1)
dev_name = [None] * (device_all+1)

# The DevEUI for which you want to enqueue the downlink.
dev_name[1] = "Seeeduino1"
dev_sub[1] = "application/11/device/f1740e912443efa0/#"
dev_eui[1] = bytes([0xf1, 0x74, 0x0e, 0x91, 0x24, 0x43, 0xef, 0xa0])

dev_name[2] = "Seeeduino2"
dev_sub[2] = "application/11/device/3c75a37b1d9cd5fe/#"
dev_eui[2] = bytes([0x3c, 0x75, 0xa3, 0x7b, 0x1d, 0x9c, 0xd5, 0xfe])

dev_name[3] = "Seeeduino3"
dev_sub[3] = "application/11/device/8cde5536622a5b1e/#"
dev_eui[3] = bytes([0x8c, 0xde, 0x55, 0x36, 0x62, 0x2a, 0x5b, 0x1e])

class Device:
    def __init__(self, name, eui, data, rssi, last_time, helper_list, state):
        self.name = name
        self.eui = eui
        self.data = data
        self.rssi = rssi
        self.last_time = last_time
        self.helper_list = helper_list
        self.state = state


def data_inf(delay, run_event):
    global print_start
    global helplist_finish
    global connect_num
    cycle = 0
    msg = [None] * (connect_num+1)
    for i in range(connect_num+1):
        msg[i] = "No message !"
    
    print("in data_inf")
   
    time.sleep(1.0)
    print("Start printing to file process...")
    print("Start printing !")
    f = open(outputFile, 'w')
    
    
    while run_event.is_set():
        print("")
        print("@ Print Cycle: {:>2}".format(cycle))
        
        if helplist_finish:
            row = 4
        else:
            row = 2
            

        for i in range(1, connect_num+1):
            if dev_list[dev_seq[i]].last_time: 
                if time.time() - dev_list[dev_seq[i]].last_time > 29.5:
                    print("********************************************************************************")
                    print("Data information:")
                    print("{} don't have new massage!".format(dev_list[dev_seq[i]].name))
                    print(" Ignore previous data: {}".format(dev_list[dev_seq[i]].data))
                    print("********************************************************************************")
                    msg[dev_seq[i]] = "No message"
                else:
                    msg[dev_seq[i]] = dev_list[dev_seq[i]].data
            else:
                msg[dev_seq[i]] = "No message ! #Find Helper..."
                
        for i in range(1, connect_num+1):
            print("{}'s message: {}".format(dev_list[dev_seq[i]].name, msg[dev_seq[i]]))
            
        for i in range(row):
            for j in range(connect_num+1):
                if i==0:
                    if cycle == 0:
                        if j==0:
                            print("{:^9} ||".format("Cycle"), end="", file = f)
                        else:
                            print("{:^44}|".format(dev_list[dev_seq[j]].name), end ="", file = f)
                    else:
                        if j==0:
                            print(" {:<6}".format("Cycle"), end="", file = f)
                            print("{:>2} ||".format(cycle), end ="", file = f)
                        else:
                            print(" {:<42} |".format(msg[dev_seq[j]]), end ="", file = f)
               
                elif i == 2:
                    if j==0:
                        print("{:^9} ||".format("Helper:"), end="", file = f)
                    else:
                        print(" ({:<11}{:<31}|".format(dev_list[dev_list[dev_seq[j]].helper_list[0][0]].name, ")"),end ="", file = f)
                   
                else:
                    if j==0:
                        print("==========||", end="", file = f)
                    else:
                        print("============================================|", end="", file = f)
                        
            print("", file = f)
        print("@ Print Cycle: {:>2} end".format(cycle))
        print("")
           
        if helplist_finish:
            helplist_finish = False

        cycle += 1
        
        if cycle > 15:
            print("Print process finish !")
            print("")
            break;
            
        if cycle != 1:
            time.sleep(delay)
         
    f.close()

    print("Stopping as you wish...")
    print("")
    
    
def init_device(num):
    d_list = []
    d_list.append(Device(None, None, num, None, None, None, None))
    for i in range(1,num+1):
        d_list.append(Device( dev_name[i], dev_eui[i], None, None, None, [], 1))
        
        print(str(d_list[i].name) + " initialized" )

    
    return d_list

# The API token (retrieved using the web-interface).
headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}
s = requests.Session()
def get_jwt():
    global api_token

    data = '{"password": "alex2511", "username": "Alex"}'
    response = requests.post('http://140.122.184.235:8080/api/internal/login', headers = headers, data = data)
    response_data = json.loads(response.content)
    if (response_data.get("jwt")):
        headers['Authorization'] = response_data.get("jwt")
        str1 =  headers['Authorization']
        return str1
    else:
        print('Login Fail')
        return False
    
def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        print("Connected to broker")
        connected = True

        for i in range(1, device_num+1):
            client.subscribe(dev_sub[i])
        
    else:
        print("Connection failed")
    

# 當接收到從伺服器發送的訊息時要進行的動作
def on_message(client, userdata, msg):
    global init_sequence
    global print_start
    
    print("================================================================================")
    print("On message...")

    rawdata = msg.payload.decode('utf8')
    # turn into JSON
    unpacked_json = json.loads(str(rawdata))
    #print(unpacked_json)
    name = unpacked_json["deviceName"]
    fCnt = int(unpacked_json["fCnt"])
    rssi = int(unpacked_json["rxInfo"][0]["rssi"])
    data = unpacked_json["objectJSON"].replace('{"data":"', '').replace('"}', '').strip()
    print(" Device: " + name)
    d_id = int(name.strip("Seeeduino"))
    print(" Uplink fCnt: " + str(fCnt))
    print(" Data: " + data)
    print(" State:", dev_list[d_id].state)
    try:
        if init_sequence == True:
            for i in range(1, device_num+1):
                if name == dev_list[i].name and not seq_check[i]:
                    seq_check[0] += 1 
                    
                    if seq_check[0] == 1:
                        print_start = time.time()
                        
                    dev_seq[seq_check[0]] = i
                    seq_check[i] = True
            
            print(" init_sequence:", seq_check[0])
            
            if seq_check[0] == device_num:
                init_sequence = False

        dev_list[d_id].data = data
        dev_list[d_id].rssi = rssi
        dev_list[d_id].last_time = time.time()
        
        if dev_list[d_id].state == 3:
            dev_list[d_id].state = 1
            print("")
            print(str(dev_list[d_id].name) + " is connected again !!!")
            print(" State:", dev_list[d_id].state)
            dev_list[ dev_list[d_id].helper_list[0][0] ].state = 1
            
        elif dev_list[d_id].state == 2:
            downlink([0x32], d_id)
        # print("Helper: ")
        # print(" d_id:", dev_list[d_id].helper_list[0][0], end=" ")
        # print(" "+str(dev_list[ dev_list[d_id].helper_list[0][0] ].name), end=" " )
        # print(" state:", dev_list[ dev_list[d_id].helper_list[0][0] ].state)
        print("================================================================================")
    except:
        pass

def downlink(data, dev_id):
    print("")
    print("Downlink")
    print(" Downlink " + str(data) + " to " + dev_list[dev_id].name)
    dev_eui_id = dev_list[dev_id].eui
    # Connect without using TLS.
    channel = grpc.insecure_channel(server)
    # Device-queue API client.
    client = api.DeviceQueueServiceStub(channel)
    # Define the API key meta-data.
    auth_token = [("authorization", "Bearer %s" % api_token)]

    # Construct request.
    req = api.EnqueueDeviceQueueItemRequest()
    req.device_queue_item.confirmed = False

    req.device_queue_item.data = bytes(data)
    req.device_queue_item.dev_eui = dev_eui_id.hex()
    req.device_queue_item.f_port = 8
    resp = client.Enqueue(req, metadata=auth_token)
    
    print(" Downlink fCnt: " + str(resp.f_cnt))

def select_helper(dev_list):
    global start_time
    global connect_num
    global helplist_finish

    print("Time before first uplink: {}".format(round(30 - (time.time()-dev_list[ dev_seq[1] ].last_time),1)))
    time_trigger = float(time.time() - dev_list[ dev_seq[1] ].last_time)
    c = 0
    while True:
        time_trigger = float(time.time() - dev_list[ dev_seq[1] ].last_time)
        if time_trigger > 29:
            break;
        time.sleep(0.5)
        c +=1
        if c%2 == 0:
            print("[Now time: {:>5} ]".format(round(time.time() - start_time, 1)), end=" ")
            print("Select helper downlink start in {:>2} sec".format(int(30-time_trigger)))
    
    print("connect_num:", connect_num)
    for i in range(1, connect_num+1):
        for j in range(1, connect_num+1):
            if i==j:
                downlink([0x30], dev_seq[j])
            else:
                downlink([0x34], dev_seq[j])
    print("--------------------------------------------------------------------------------")

    select_time_start = time.time()
    auto_helper_receive(select_time_start)
    
    helplist_finish = True
    
    print("HELPER LIST ==> ")
    for j in range(0, connect_num):
        for i in range(0, connect_num+1):
            if j==0:
                if i==0:
                    print("{:^10}".format("Device"),end ="")
                else:
                    print("{:^12}".format(dev_list[dev_seq[i]].name), end="")
            else:
                if i==0:
                    print("{:>8}".format("Helper_"), end="")
                    print("{} ".format(j), end="")
                else:
                    print("{:^12}".format(dev_list[dev_list[dev_seq[i]].helper_list[j-1][0]].name), end="")
        print("")

    print("")    
    print("********************************************************************************")
    
    
    
    return
            
def auto_helper_receive(select_start):
    global start_time
    finish = False
    
    check = [True] * (device_num+1)
    for i in range(1, device_num+1):

        check[i] = [True] * (device_num+1)
        for j in range(1, connect_num+1):
            if dev_seq[j] != i:
                check[i][ dev_seq[j] ] = False

   # print("check: ", check)
    #print("")
    ri = [None] * (device_num+1)
    for i in range(device_num+1):
        ri[i] = [None]*(device_num+1)

    wait_time = int(0)
    print("Waiting for response( about 60 sec)...")
    
    while True:
        if wait_time > 59 :
            break;
        print("[Now time: {:>5} ]".format(round(time.time() - start_time, 1)), end=" ")
        print("Wait for response... Finish in {:>2} sec".format(59 - wait_time))
        time.sleep(1.0)
        wait_time += 1
    print("")
    limit_start = time.time()    

    while True:
        finish = True
        print("[Now time: {:>5} ]".format(round(time.time() - start_time, 1)), end=" ")
        print("Select helper process will finish in {:>3} sec".format(30*(connect_num+1)+1 - int(time.time()-limit_start)))
        if int(time.time()- limit_start) % 5 == 0:
            print("--------------------------------------------------------------------------------")
            for t in range(1, connect_num+1):
                print("{} data: {}".format(dev_list[dev_seq[t]].name, dev_list[dev_seq[t]].data ))
            print("--------------------------------------------------------------------------------")
        for i in range(1, connect_num+1):

            if dev_list[dev_seq[i]].data:
                receive = dev_list[dev_seq[i]].data.split("#")

            if receive[1]:
                
                s_id, recv_rssi = receive[1].split(":")
                s_id = int(s_id)
                recv_rssi = int(recv_rssi)

                if check[s_id][dev_seq[i]] == False:
                    print("--------------------------------------------------------------------------------")
                    print("Update helper rssi...")
                    print("")
                    print(" {} receive: {}".format(dev_list[dev_seq[i]].name, receive))
                    total_rssi = recv_rssi + dev_list[dev_seq[i]].rssi
                    ri[s_id][dev_seq[i]] = (recv_rssi, total_rssi - recv_rssi)
                    print(" For {} from {}".format(dev_list[s_id].name, dev_list[dev_seq[i]].name), end = " ")
                    print(" total rssi:", total_rssi)
                    dev_list[s_id].helper_list.append((dev_seq[i], total_rssi))
                    print(" {}'s helper_list: {}".format(dev_list[s_id].name, dev_list[s_id].helper_list))
                    check[s_id][dev_seq[i]] = True
                    print("--------------------------------------------------------------------------------")

        for i in range(1, connect_num+1):
            if any(data is False for data in check[i]):
                finish = finish * False
                print(" {}'s helper list is forming...".format(dev_list[dev_seq[i]].name), end=" ")
                
            else:
                finish = finish * True
                print(" {}'s helper list is complete !".format(dev_list[dev_seq[i]].name), end=" ")
            print("[", end="")
            for j in range(1, device_num+1):
                if check[i][j]:
                    print("{:^3}".format("Y"), end=" ")
                else:
                    print("{:^3}".format("N"), end=" ")

            print("]")
        print("")
        
        if finish == True:
            print("********************************************************************************")
            print("   All device finish collecting rssi!   ")
            print("")
            break

        if int(time.time() - limit_start) > (30*(connect_num+1) + 1):
            print("********************************************************************************")
            print("   Waiting rssi process time's up !!!   ")
            print("")
            break;

        time.sleep(1.0)       
            
    if not finish:
        for i in range(1, device_num+1):
            if not all(data is True for data in check[i]):
                print("{}'s helper list is not complete !".format(dev_list[i].name))
                print(" Lack of Helper:", end =" ")
                for idx, x in enumerate(check[i]):
                    if x == False:
                        print(str(dev_list[idx].name), end=" ")
                print("")
    
    print("Rssi map:")
    for i in range(1, device_num+1):
        for j in range(1, device_num+1):
            if ri[i][j] == None:
                print("{:^10}".format("None"), end ="")
            else:
                print(ri[i][j], end=" ")
        print("") 
    print("")
    
    print("Start sorting...")
    for i in range(1, connect_num+1):
        print(" {}'s pre-help_list: {}".format(dev_list[ dev_seq[i] ].name, dev_list[ dev_seq[i] ].helper_list))
        dev_list[ dev_seq[i] ].helper_list = sorted(dev_list[ dev_seq[i] ].helper_list, key = itemgetter(1, 0), reverse=True)
    print("")
        
    for i in range(1, connect_num+1):
        print(" {}'s final helper_list: {}".format(dev_list[dev_seq[i]].name, dev_list[dev_seq[i]].helper_list))
    print("")    
   
    
    return
           
def check_device(dev_list):
    global init_sequence
    
    check_connect = [ False] * (device_num + 1)
    check_connect[0] = True
    dev_connect = 0
    #print(check_connect)
    while True:
        print("[Now time: {:>5} ]".format(round(time.time() - start_time, 1)), end=" ")
        print("Checking connected device...", end=" ")
        print("Finish in " + str(int(60 - (time.time()-start_time))+1) + " sec")
        for i in range(1, device_num+1):
            #print(dev_list[i].last_time)
            if dev_list[i].last_time != None:
                
                check_connect[i] = True
                

        if all(data is True for data in check_connect):
            print("################################################################################")
            print("         Device all connected !         ")
            print("")
            #init_sequence = False
            break
        else:
            if int(time.time() - start_time) > 60:
                print("################################################################################")
                print("Check device process time out !!!")
                #print(check_connect)
                for i in range(1, device_num+1):
                    if check_connect[i] == False:
                        print(str(dev_list[i].name) + " fail to connect !")
                init_sequence = False
                break
        time.sleep(1.0)
        

    for i in range(1, device_num+1):
        if check_connect[i] == True:
            dev_connect += 1
        
        
    return dev_connect

def downlinkflush():
    print("Downlink queue flush...")
    # Connect without using TLS.
    channel = grpc.insecure_channel(server)

    # Device-queue API client.
    client = api.DeviceQueueServiceStub(channel)

    # Define the API key meta-data.
    api_token = get_jwt()
    auth_token = [("authorization", "Bearer %s" % api_token)]

    # Construct request.
    req = api.FlushDeviceQueueRequest()
    for i in range(1, device_num+1):
        d_eui = dev_eui[i] 
        req.dev_eui = d_eui.hex()
        client.Flush(req, metadata=auth_token)
        print(" {}'s downlink queue is empty".format(dev_list[i].name))
    print("")
    
###############################################################################################################################
    
if __name__ == "__main__":
    
    global helplist_finish
    helplist_finish = False
    
    run_event = threading.Event()
    run_event.set()
    cycle = 30
    
    api_token = get_jwt()
    start_time = time.time()

    global connected 
    connected = False
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.username_pw_set("Alex","alex2511")
    client.connect("140.122.184.235", 1883, 20)

    dev_list = []
    dev_list = init_device(device_num)
    
    downlinkflush()

    global mqtt_looping
    global connect_num
    
    
    try:
        client.loop_start()
        while True:
            time.sleep(1.0)
            if not connected:
                print("Not connected")
            else:
                # print("Connected")
                break;
           
        global init_sequence
        init_sequence = True
        
        seq_check = [False] * (device_num + 1)
        seq_check[0] = 0
        dev_seq = [None] * (device_num + 1)
        dev_seq[0] = 0
        print("################################################################################")
        print("Start checking device...")
        connect_num = check_device(dev_list)
        dev_seq[0] = connect_num
         
        t = threading.Thread(target = data_inf, args = (cycle, run_event))
        t.start()
        # print("t_start")
        
        print("Device sequence: ", dev_seq)
        print("Device connected number: " + str(connect_num))
        print("")
        print("################################################################################")
        if connect_num > 2:
            print("Start selecting helper process...")
            select_helper(dev_list)
            print("Finish selecting helper list process ! ! !")
        else:
            dev_list[dev_seq[0]].helper_list.append((dev_seq[1], 0))
            dev_list[dev_seq[1]].helper_list.append((dev_seq[0], 0))
            helplist_finish = True
        
        mqtt_looping = True    

    
        while mqtt_looping:
            print("[Now time: {:>5} ]".format(round(time.time() - start_time, 1)))
            if not connected:
                print("Not connected")
            else:
                for i in range(1, connect_num+1):
                    if dev_list[ dev_seq[i] ].last_time and time.time() - dev_list[ dev_seq[i] ].last_time > 90:
                        print("################################################################################")
                        print(str(dev_list[ dev_seq[i] ].name) + " is disconnected !")
                        print("")
                        print("Dealing with disconnect process... ")
                        dev_list[dev_seq[i]].state = 3
                        # print(str(dev_list[ dev_seq[i] ].name)+ " state: " + str(dev_list[ dev_seq[i] ].state) )
                        # print("i:", i, end =" ")
                        # print("Dev_id:", dev_seq[i])
                        print(dev_list[dev_seq[i]].name)
                        print(" state:", dev_list[dev_seq[i]].state)
                        dev_list[dev_seq[i]].last_time = None
                        
                        print(" help_list:", dev_list[dev_seq[i]].helper_list[0])
                        # print(" help_id:", dev_list[dev_seq[i]].helper_list[0][0], end="" )
                        print(" helper:", dev_list[dev_list[dev_seq[i]].helper_list[0][0] ].name)
                        dev_list[ dev_list[dev_seq[i]].helper_list[0][0] ].state = 2
                        downlink([0x32], dev_list[dev_seq[i]].helper_list[0][0])
                        print("################################################################################")
                 
            for i in range(1, connect_num+1):
                if dev_list[ dev_seq[i] ].last_time:
                    test = int(time.time() - dev_list[ dev_seq[i] ].last_time)
                    print(" {} pass time: {} sec".format(dev_list[ dev_seq[i] ].name, test))
                else:
                    print(" {} is disconnected !".format(dev_list[ dev_seq[i] ].name))
            
            print("")    
            
     
            time.sleep(1.0)    
    except KeyboardInterrupt:
        client.loop_stop()
        print("*******Quit mqtt thread*******")
        
        print("Attempting to close threads. Max wait =", cycle)
        run_event.clear()
        t.join()
        print("threads successfully closed")
        
        
    except Exception:
        client.loop_stop()
        print("*****Something went wrong*****")
        
        print("Attempting to close threads. Max wait =", cycle)
        run_event.clear()
        t.join()
        print("threads successfully closed")
    
    