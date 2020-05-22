#!/usr/bin/env python

import daemon
import time
import logging
import datetime
import pigpio
import wiegand
import RPi.GPIO as GPIO
import mysql.connector

RELAY = 23
LED = 22
RTE = 24

mydb = mysql.connector.connect(
        host = "localhost",
        user="json",
        passwd="WangChung!",
        database="access"
)

GPIO.setmode(GPIO.BCM)
GPIO.setup(LED, GPIO.OUT)
GPIO.output(LED, GPIO.HIGH)
#GPIO.setup(RELAY, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(RTE, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

OPEN, ERROR = 1, 2
def check_time(time_to_check, on_time, off_time):
        if on_time > off_time:
                if time_to_check > on_time or time_to_check < off_time:
                        return ERROR, True
        elif on_time < off_time:
                if time_to_check > on_time and time_to_check < off_time:
                        return OPEN, True
        elif time_to_check == on_time:
                return OPEN, True
        return None, False

GPIO.add_event_detect(RTE, GPIO.RISING)
def my_callback():
        print 'PUSHED!'
GPIO.add_event_callback(RTE, my_callback)

#cards id user_id card permissions
#permissions pk permission_id start1 stop1

def callback(bits, code):
        #print("bits={} code={}".format(bits, code))
        localtime = time.asctime( time.localtime(time.time()) )
        ts = time.time()
        timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        print(int(bin(code)[3:27],2))
        decode_number = int(bin(code)[3:27],2)
        CardExists = False;
        cardstr = str(decode_number)
        query = "SELECT A.user_id, A.card, A.permissions, B.permission_id, DATE_FORMAT(B.start1,'%H:%i:%s') TIMEONLY,  DATE_FORMAT(B.stop1,'%H:%i:%s') TIMEONLY FROM cards A INNER $
        cur = mydb.cursor()
        cur.execute(query)
        row = cur.fetchone()
        if not row:
                print localtime," - Card isn't in DB - Access Denied"
                sql = "INSERT INTO log (card, success, start) VALUES (%s, %s, %s)"
                val = (decode_number, 0, timestamp)
                cur.execute(sql, val)
                mydb.commit()
        else:
                print "Card is in DB"
                CardExists = True
                user_id = row[0]
                card_id = row[1]
                permission_id = row[3]
                row4 = row[4]
                sthours, stminutes, stseconds = map(int, row4.split(':'))
                row5 = row[5]
                sphours, spminutes, spseconds = map(int, row5.split(':'))
        if CardExists:
                start_time = datetime.time(sthours,stminutes)
                stop_time = datetime.time(sphours,spminutes)

        if CardExists:
                current_time = datetime.datetime.now().time()
                print("Determining if {1} is between {0} and {2}".format(start_time, current_time, stop_time))
                when, matching = check_time(current_time, start_time, stop_time)
                if matching:
                        if when == ERROR:
                                print("Your time is not formatted correctly.")
                        elif when == OPEN:
                                print("Access Granted.")
                                GPIO.output(LED, GPIO.LOW)
                                time.sleep(10)
                                GPIO.output(LED, GPIO.HIGH)
                                #unlock door or whatever
                                #do logging
                                sql = "INSERT INTO log (card, success, user_id, start) VALUES (%s, %s, %s, %s)"
                                val = (decode_number, 1, user_id, timestamp)
                                cur.execute(sql, val)
                                mydb.commit()

                if (matching == False):
                        print("Access Failed.")
                        #do logging here bad time here
                        #done w/ CardExists
                        sql = "INSERT INTO log (card, success, start) VALUES (%s, %s, %s)"
                        val = (decode_number, 0, timestamp)
                        cur.execute(sql, val)
                        mydb.commit()
        cur.close


def do_cp():
    name = 'cpdaemon'
    logger = logging.getLogger(name)
    handler = logging.FileHandler('/tmp/%s.log' % (name))
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler) 
    logger.setLevel(logging.WARNING)

    while True:
        try:
			pi = pigpio.pi()
			w = wiegand.decoder(pi, 27, 17, callback)
			localtime = time.asctime( time.localtime(time.time()) )
			print "Started Localtime: ",  localtime
			while 1:
				time.sleep(1)
        except Exception, ex:
            logger.error(ex)
			w.cancel()
			pi.stop()
			GPIO.cleanup()

def run():
    with daemon.DaemonContext():
        do_cp()

if __name__ == "__main__":
    run()