#include <LoRaWan.h>
#include <stdlib.h>
#include <string.h>

const float AS2_hybrid_channels[8] = {923.2, 923.4, 923.6, 923.8, 924.0, 924.2, 924.4, 924.6};

char device[256] = "2";
short device_num = 3;
short rssi_send = 0;
bool rssi_check = false;

char buffer[256];
char buff[256];
char message[256];
char message_1[256];
char message_2[256];

char data[256];
short data_cnt = 0;
char data_queue[4][256];
short queue_cnt = 0;

char receive_1[256];
char receive_2[256];


unsigned long time;
unsigned long time_check;
float time_s;

long offset = 0;
long delay_time = 0;

long time1;
long time2;
long time_21;
long time3;
long time4;
long time_43;
long p2p_start_time;

unsigned long time_p;
long time_start;
long time_end;

short length = 0;
short rssi = 0;

char *token;

bool result = false;
bool sync = false;
bool init_sync = true;
short init_sync_cnt = 0;

bool changed_mode = false;
bool msg_get = false;
bool msg_out = true;
bool init_abp = true;

extern volatile uint32_t _ulTickCount;

short mode = 1;
String str;
long downlink_msg = 1;
short lost_downlinkmsg_count = 0;
bool disconnection_test = true;

//setId(char *DevAddr, char *DevEUI, char *AppEUI);
char DevAddr[] = "01adcaae";
char DevEUI[] = "f1740e912443efa0";
char AppEUI[] = "0000000000000000";

//setKey(char *NwkSKey, char *AppSKey, char *AppKey);
char NwkSKey[] = "7181a92649698dace52ce00d4845ebc6";
char AppSKey[] = "7c1fb6804a9e08cba69ab0226d027fc6";
//char AppKey[] = "07aa570f6122da2df62a638d9560cfa3";

void setup(void)
{

  SerialUSB.begin(115200);


  lora.init();

  print_time();

  lora.setId(DevAddr, DevEUI, AppEUI);
  lora.setKey(NwkSKey, AppSKey, NULL);

  lora.setDeciveMode(LWABP);
  lora.setDataRate(DR2, AS923);

  lora.setAdaptiveDataRate(false);
  lora.setDutyCycle(false);
  lora.setJoinDutyCycle(false);
  lora.setPower(5);
  setHybridForTTN(AS2_hybrid_channels);


  init_abp = true;
  init_sync = false;
  memset(message, 0, 256);
  memset(message_1, 0, 256);
  memset(message_2, 0, 256);
  _ulTickCount = 0;
}

void loop(void) {
  time_start = millis();
  memset(message_1, 0, 256);
  strcpy(message_1, device);
  strcat(message_1, ":");
  data_cnt++;
  snprintf(data, sizeof(data), "msg%s_%hd", device, data_cnt);
  if (queue_cnt > 0)
  {
    for (int i = 0; i < queue_cnt; i++)
    {
      strcat(message_1, data_queue[i]);
      strcat(message_1, ",");
    }
  }
  strcat(message_1, data);


  SerialUSB.println();
  print_time();
  SerialUSB.print(" init_sync: ");
  SerialUSB.println(init_sync);

  if (mode != 0)//??
  {
    if (init_sync and init_sync_cnt < 2)
    {
      init_sync_cnt++;
      SerialUSB.println("############ Continue init_sync ############");
    }
    else
    {
      init_sync_cnt = 0;
      SerialUSB.println("############ Switch to abp mode ############");
      memset(message, 0, 256);
      abp_mode();
      memset(message_2, 0, 256);
    }

  }
  else
  {
    if (rssi_send < 2)
    {
      SerialUSB.println("############ Continue broadcast ############");
      msg_out = true;
    }
    else
    {
      rssi_send = 0;
      SerialUSB.println("############ Switch to abp mode ############");
      memset(message, 0, 256);
      abp_mode();

    }
  }
  
  SerialUSB.println();
  SerialUSB.print("MODE: ");
  SerialUSB.println(mode);
  switch (mode)
  {
    case 0:
      SerialUSB.println("######### Switch to send_rssi mode #########");
      changed_mode = true;
      send_rssi();
      msg_out = false;
      break;

    case 1:
      SerialUSB.println("######### Switch to idle time mode #########");
      changed_mode = false;
      break;

    case 2:
      SerialUSB.println("######## Switch to p2p_helper mode #########");
      changed_mode = true;
      memset(message_2, 0, 256);
      p2p_helper_mode();
      break;

    case 3:
      SerialUSB.println("############ Switch to p2p mode ############");
      changed_mode = true;
      memset(message_2, 0, 256);
      p2p_mode();
      if (init_sync == true and sync == false)
      {
        if (init_sync_cnt == 3)
        {
          init_sync_cnt = 0;
          init_sync = false;
        }
      }
      init_sync_cnt++;

      break;

    case 4:
      SerialUSB.println("####### Switch to receive_rssi mode ########");
      changed_mode = true;
      rssi_check = true;
      memset(message_2, 0, 256);
      p2p_helper_mode();
      rssi_check = false;
      msg_get = false;
      break;

  }

  if (msg_out == false)
  {
    if (queue_cnt < 3)
    {
      strcpy(data_queue[queue_cnt], data);
      queue_cnt++;
    }
    else
    {
      for (int i = 0; i < queue_cnt - 1; i++)
      {
        strcpy(data_queue[i], data_queue[i + 1]);
      }
      strcpy(data_queue[queue_cnt - 1], data);
    }
  }
  else
  {
    queue_cnt = 0;
    for (int i = 0; i < queue_cnt; i++)
    {
      memset(data_queue[i], 0, 256);
    }

  }

  print_end();

}
void setHybridForTTN(const float * channels) {
  for (int i = 0; i < 8; i++) {
    if (channels[i] != 0) {
      lora.setChannel(i, channels[i], DR0, DR5);

    }
  }
}

void send_rssi(void) {
  lora.initP2PMode(924, SF7, BW125, 8, 8, 20);
  memset(buffer, 0, 256);
  while (time_check % 30 < 27 and time_check % 30 >= 0)
  {
    print_time();
    strcpy(buffer, device);
    lora.transferPacketP2PMode(buffer, 2);
    SerialUSB.print("[Broadcast message]: ");
    SerialUSB.println(device);
    SerialUSB.println("------------------------------");
    delay(1000);
    time = millis();
    time_check = time / 1000;
  }
  SerialUSB.println("out of send_rssi while loop...");

  rssi_send++;
}


void abp_mode(void) {

  if (init_abp == true or changed_mode == false)
  {
    init_abp = false;
    SerialUSB.println("Wait for initializing time...");
    while (time_check % 30 < 13)
    {
      delay(1000);
      time = millis();
      time_s = float(time) / 1000;
      SerialUSB.print("[Initializing time]: ");
      SerialUSB.println(time_s, 1);
      time_check = time / 1000;

    }
  }
  else
  {
    print_time();
    lora.setDeciveMode(LWABP);
    lora.setDataRate(DR2, AS923);
    setHybridForTTN(AS2_hybrid_channels);
  }
  //send to air
  strcpy(message, message_1);
  strcat(message, "#");
  strcat(message, message_2);



  print_time();
  SerialUSB.print("@@@@@@@@@@ Send to air => ");
  SerialUSB.write(message);
  SerialUSB.println();

  //***********************************************************
  if (disconnection_test == true)
  {
    if (data_cnt > (device_num+4) and data_cnt < (device_num+11) )
    {
      SerialUSB.println("disconnect test!!");
      result = false;
      delay(5000);
    }
    else
    {
      result = lora.transferPacketWithConfirmed(message, 5);
    }
  }
  else
  {
    result = lora.transferPacketWithConfirmed(message, 5);
  }

  //***********************************************************

  if (result)
  {
    print_time();


    SerialUSB.println("GET　ACK !!!");
    mode = 1;
    msg_out = true;
    lost_downlinkmsg_count = 0;
    init_sync = false;

    memset(buffer, 0, 256);
    length = lora.receivePacket(buffer, 256, &rssi);
    //check from air information
    if (length)
    {
      lost_downlinkmsg_count = 0;
      init_sync = false;
      SerialUSB.println("Receive command from air!");
      str = buffer ;
      //SerialUSB.print("str:");
      //SerialUSB.println(str);
      downlink_msg = str.toInt();
      SerialUSB.print("@@@@@ [Downlink_msg]: ");
      SerialUSB.println(downlink_msg);
      mode = downlink_msg;
    }
    else
    {
      SerialUSB.println("No command from air!");
      SerialUSB.println("==============================");
    }
  }
  else
  {
    print_time();
    msg_out = false;
    lost_downlinkmsg_count++;
    SerialUSB.println("Send to air failed !!!");
    SerialUSB.println("==============================");
  }
  SerialUSB.println();
  
  if (lost_downlinkmsg_count == 3)
  {
    mode = 3;
    init_sync = true;
  }
  while (time_check % 30 < 20)
  {
    delay(1000);
    time = millis();
    time_s = float(time) / 1000;
    SerialUSB.print("[Aligning time]: ");
    SerialUSB.println(time_s, 1);
    time_check = time / 1000;

  }
}

void p2p_helper_mode(void) {
  lora.initP2PMode(924, SF7, BW125, 8, 8, 20);

  //time syncronization
  print_time();

  if (sync == false and rssi_check == false)
  {
    synchronize_helper();
  }
  //Receive from p2p
  else
  {
    msg_get = false;
    SerialUSB.println("msg_get");
    while (time_check % 30 < 27 and msg_get == false)
    {
      if (rssi_check == true)
      {
        SerialUSB.println("Receiving rssi...");
      }
      else
      {
        SerialUSB.println("Receiving message...");
      }

      memset(buffer, 0, 256);

      length = lora.receivePacketP2PMode(buffer, 256,  &rssi, 2);
      if (length)
      {
        //receive message
        print_time();
        SerialUSB.print("@@@@ [Receive] text => ");
        SerialUSB.write(buffer);
        SerialUSB.println();
        strcpy(message_2, buffer);

        //strcat(message_2, ":");
        if (rssi_check == true)
        {
          memset(buff, 0, 256);
          itoa(rssi, buff, 10);
          strcat(message_2, ":");
          strcat(message_2, buff);//////?
        }

        msg_get = true;
        SerialUSB.println("==============================");
      }
      else
      {
        print_time();
        SerialUSB.println("[Receive nothing]:############");
        SerialUSB.println("------------------------------");
      }

      time = millis();
      time_check = time / 1000;
    }

    SerialUSB.println("Message: p2p_receive_done");
    SerialUSB.println("==============================");
  }
}

void synchronize_helper(void) {
  time = millis();
  time_check = time / 1000;

  while (time_check % 30 < 27 and sync == false)
  {
    //receive reply
    SerialUSB.println("Receiving time_1...");
    memset(buffer, 0, 256);
    length = lora.receivePacketP2PMode(buffer, 256,  &rssi, 2);
    if (length)
    {
      time2 = millis();
      print_time();

      SerialUSB.print("[Receive] time1 => ");
      SerialUSB.write(buffer);
      SerialUSB.println();

      memset(buff, 0, 256);
      strcpy(buff, buffer);
      time1 = atoi(buff);
      time_21 = time2 - time1;
      memset(buffer, 0, 256);
      itoa(time_21, buffer, 10);
      strcat(buffer, ",");

      time3 = millis();
      itoa(time3, buff, 10);
      strcat(buffer, buff);

      SerialUSB.print("[Reply] time_21, time3 => ");
      SerialUSB.write(buffer);
      SerialUSB.println();

      lora.transferPacketP2PMode(buffer, 2);

      SerialUSB.println("Syncronize: p2p_helper_done!!!");
      SerialUSB.println("==============================");
      p2p_start_time = millis() / 1000;
      sync = true;
      //delay(1000);
    }
    else
    {
      print_time();
      SerialUSB.println("No time_1!!!");
      SerialUSB.println("------------------------------");
      time_check = time / 1000;
    }
    time = millis();
    time_check = time / 1000;
  }
}

void p2p_mode(void) {
  lora.initP2PMode(924, SF7, BW125, 8, 8, 20);
  if (init_sync == true)
  {
    print_time();
    //initial syncronization
    while (time_check % 30 < 27 and init_sync == true)
    {
      syncronize();
    }
  }
  else
  {
    //    //align work
    //    while (time_check % 30 < 23)
    //    {
    //      delay(1000);
    //      time = millis();
    //      time_s = float(time) / 1000;
    //      SerialUSB.print("[Aligning time]: ");
    //      SerialUSB.println(time_s, 1);
    //      time_check = time / 1000;
    //
    //    }
    if (sync == false)
    {
      while (time_check % 30 < 27 and sync == false )
      {
        syncronize();
      }
    }
    else
    {
      while (time_check % 30 < 27)
      {
        print_time();
        memset(buffer, 0, 256);
        strcpy(buffer, message_1);
        lora.transferPacketP2PMode(buffer, 2);
        msg_out = true;
        SerialUSB.print("[Send message]=> ");
        SerialUSB.println(message_1);
        SerialUSB.println("------------------------------");

        delay(2000);
        time = millis();
        time_check = time / 1000;
      }
    }
    SerialUSB.println("Message: p2p_send_done");
    SerialUSB.println("==============================");
  }

}

void syncronize(void)
{
  //time syncronization
  time1 = millis();
  memset(buffer, 0, 256);
  itoa(time1, buffer, 10);

  print_time();
  lora.transferPacketP2PMode(buffer, 10);

  SerialUSB.print("Sending time1: ");
  SerialUSB.println(time1);
  SerialUSB.println("------------------------------");

  //receive time reply
  memset(buffer, 0, 256);
  length = lora.receivePacketP2PMode(buffer, 256,  &rssi, 2);
  if (length)
  {
    time4 = millis();
    print_time();

    SerialUSB.print("[Receive] time(2-1) & time3 => ");
    SerialUSB.write(buffer);
    SerialUSB.println();

    /* get the first token */
    token = strtok(buffer, ",");
    memset(receive_1, 0, 256);
    memset(receive_2, 0, 256);
    strcpy(receive_1, token);
    /* walk through other tokens */
    while ( token != NULL )
    {
      strcpy(receive_2, token);
      token = strtok(NULL, ",");
    }
    time_21 = atoi(receive_1);
    time3 = atoi(receive_2);
    time_43 = time4 - time3;

    offset = (time_21 - time_43) / 2;
    delay_time = (time_21 + time_43) / 2;

    SerialUSB.print(" Time4: ");
    SerialUSB.println(time4);
    //SerialUSB.print(" Time(4-3): ");
    //SerialUSB.println(time_43);

    SerialUSB.print("[Offset]: ");
    SerialUSB.print(offset);
    SerialUSB.print(" ");
    SerialUSB.print("[Delay]: ");
    SerialUSB.println(delay_time);

    time_p = millis();
    noInterrupts ();
    _ulTickCount = time_p + offset;
    interrupts ();
    p2p_start_time = millis() / 1000;

    sync = true;
    init_sync = false;
    init_sync_cnt = 0;
    SerialUSB.println("Syncronize: p2p_helped_done");
    SerialUSB.println("==============================");

  }
  //no time reply
  else
  {
    print_time();
    SerialUSB.println("No time_21, time_3!");
    SerialUSB.println("------------------------------");
    time_check = time / 1000;

  }

}

void print_end(void) {
  print_time();
  while (time_check % 30 != 0)
  {
    delay(1000);
    time = millis();
    time_s = float(time) / 1000;
    //SerialUSB.print("[Pause time]: ");
    //SerialUSB.println(time_s, 1);
    if ((time / 1000 - p2p_start_time) % 240 > 238 and (mode == 2 or mode == 3 ))
    {
      SerialUSB.print("[Clock time]: ");
      SerialUSB.println(time_s, 1);
      SerialUSB.println("Resyncronize!!!");
      SerialUSB.println("------------------------------");
      sync = false;
    }
    time_check = time / 1000;
  }
  time_end = millis();

  SerialUSB.println("------------------------------");
  print_time();
  SerialUSB.print("Time past: ");
  SerialUSB.println(float(time_end - time_start) / 1000, 1);
  SerialUSB.println("Next routine...");
  SerialUSB.println("------------------------------");
}

void print_time(void) {
  time = millis();
  time_check = time / 1000;
  time_s = float(time) / 1000;
  SerialUSB.print("[Clock time]: ");
  SerialUSB.println(time_s, 1);

}
