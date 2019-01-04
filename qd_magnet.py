import can
import can.interfaces.usb2can
import struct
import logging
import time

"""experimental logging"""
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


#import binascii

"""
Protokoll:  Verbindungsaufbau
            Standardeinstellungen
            Senden & Empfangen
            Query & write
            Connectionstatus
            Error handling

HMPSU Kommandos:
            Allgemein:  Startup / Shutdown
                        Konvertierung
                        Systemstatus

            Magnet:     Feld (query)
                        Set Field
                        Scan Field
                        Configs

Die erste Nachricht nach dem Verbindungsaufbau wird immer Ignoriert!!

Todo:
    Propper Errorhandling
    Propper Documentation
    Logging function

    auf github in slave api hochladen, den slave-Befehl set_field deactivieren und
    scan field mit qd_magnet packet importieren.

    resolve conflicts
"""
#Find out more about read and write flag!!
#0x80 seems ti be Abort message to reset bus
#Impliment datatype read from bus!!!
class Protocol:
    class Error(Exception):
        """Generic baseclass for all protocol errors."""
        pass

    def __init__(self):
        """
        The Channelnumber is the Serialnumber of the USB2CAN Controller.
        The bitrate is at its maximum of 1 MBps.
        """
        self.channel = 'ED000200'
        self.bitrate = 1000000
        self.bus=can.interfaces.usb2can.Usb2canBus(channel=self.channel, bitrate=self.bitrate)

    def disconnect(self):
        if self.bus != None:
            self.bus.shutdown()
            del self #perhaps del class instance, check with slave api

    def clear_bus(self,node):
        """ This function is experimental and should reset the bus after an Error"""
        try:
            msgdata = struct.pack('bbbbbbbb', 0x80, 0,0,0,0,0,0,0)
            msg = can.Message(extended_id=False, arbitration_id=int(0x0600)+node, data=msgdata)
            self.bus.send(msg)
        except Exception as e:
            print(e)

    def query(self, node, cobid, subid):
        try:
            msgdata = struct.pack('bbbbbbbb', 0x40, int(hex(cobid)[0:2]+hex(cobid)[4:6],16), int(hex(cobid)[0:4],16), subid, 0,0,0,0)
            msg = can.Message(extended_id=False, arbitration_id=int(0x0600)+node, data=msgdata)

            self.bus.set_filters(filters=[{"can_id" : 0x0580, "can_mask":0xFFF0}])                        #Might be arbitrary
            self.bus.send(msg)
            ans = self.bus.recv(timeout=.1)

            self.bus.send(msg)               #Only receving reliably on second try, perhaps if statement
            ans = self.bus.recv(timeout=.1)
            #print(ans)
            data = self.decode(ans)
            return data

        except Exception as e:
            #self.disconnect()
            print(e)
            #Set Bus in safestate

    def write(self, node, cobid, subid, data, dtype):
        try:
            msgdata = self.encode(cobid, subid, data, dtype)
            msg = can.Message(extended_id=False, arbitration_id=int(0x0600)+node, data=msgdata)
            self.bus.set_filters(filters=[{"can_id" : 0x0580, "can_mask":0xFFF0}])                        #Might be arbitrary
            self.bus.send(msg)
            ans = self.bus.recv(timeout=.1)          #Further investigation for answer content.

            self.bus.send(msg)
            ans = self.bus.recv(timeout=.1)
            #read ans message to check if correctly recieved.
            print(msg)
            #print(ans)
            return ans
        except Exception as e:
            print(e)

    """pdo is at best left not implemented"""
   # def pdo_reader(self, node):
    #    try:

    def te(self, node):
        try:
            msgdata = struct.pack('bbbbbbbb', 0x60,0,0,0,0,0,0,0)
            msg = can.Message(extended_id=False, arbitration_id=int(0x0600)+node, data=msgdata)
            self.bus.send(msg)
            self.bus.send(msg)
            print(msg)
            
            msgdata = struct.pack('bbbbbbbb', 0x70,0,0,0,0,0,0,0)
            msg = can.Message(extended_id=False, arbitration_id=int(0x0600)+node, data=msgdata)
            self.bus.send(msg)
            self.bus.send(msg)
            print(msg)
            time.sleep(0.1)
        except Exception as e:
            print(e)
    #Add automated type detection from canmsg.
    def decode(self, msg):
        try:
            data = struct.unpack('bbbbbbbb', msg.data)
            canid = msg.arbitration_id          #Extrat Node nummber and message type   
            subid = data[3]
            cobid = data[2] + data[1]
            
            if data[0] == 0x43:
                data = struct.unpack('bbbbf', msg.data)
                rdata = data[4]
            elif data[0] == 0x40:
                data = struct.unpack('bbbbbbbb', msg.data)
                rdata = data[4]
            elif data[0] == 0x50:
                data = struct.unpack('bbbbhh', msg.data)
                rdata = data[4]
            elif data[0] == 0x4b:
                data = struct.unpack('bbbbHH', msg.data)
                rdata= data[4]
            else:
                rdata = None
            return canid, cobid, subid, rdata
        except Exception as e:
            print(e)

    def encode(self, cobid, subid, data, dtype):
        if dtype == 'f':
            msgdata = struct.pack('bbbbf', 0x23, int(hex(cobid)[0:2]+hex(cobid)[4:6],16), int(hex(cobid)[0:4],16), subid, data)
        elif dtype == 'b':
            msgdata = struct.pack('bbbbbbbb', 0x2f, int(hex(cobid)[0:2]+hex(cobid)[4:6],16), int(hex(cobid)[0:4],16), subid, data,0,0,0)
        elif dtype == 'H':
            msgdata = struct.pack('bbbbHH', 0x21, int(hex(cobid)[0:2]+hex(cobid)[4:6],16), int(hex(cobid)[0:4],16), subid, data,0)
        elif dtype == 'L':
            msgdata = struct.pack('bbbbL', 0x21, int(hex(cobid)[0:2]+hex(cobid)[4:6],16), int(hex(cobid)[0:4],16), subid, data)
        elif dtype == "user":
            msgdata = struct.pack('bbbbBbbb', 0x2b, int(hex(cobid)[0:2]+hex(cobid)[4:6],16), int(hex(cobid)[0:4],16), subid, data,0,0,0)
        elif dtype == "user2":
            msgdata = struct.pack('bbbbBbbb', 0x23, int(hex(cobid)[0:2]+hex(cobid)[4:6],16), int(hex(cobid)[0:4],16), subid, 0x86, 0x01,0,0)
            
            
        else:
            msgdata = None
        return msgdata





class HMPSU(Protocol):
    def __init__(self):
        super().__init__()
        self.node=6
        self.te(self.node)

        self.query(self.node,0x1000,0x0)
        self.query(self.node,0x2000,0x0)
        self.query(self.node,0x1008,0x0)
        self.query(self.node,0x1009,0x0)
        self.query(self.node,0x100a,0x0)
        

                
        #0x60 is receved as type
        self.max_field = self.query(self.node, 0x600B, 0x01)
        self.BtoI_Ratio = self.query(self.node, 0x600B, 0x02)#, 'f')
        self.Inductance = self.query(self.node, 0x600B, 0x03)#, 'f')
        self.max_rate_low = self.query(self.node, 0x600B, 0x04)#, 'f')
        self.max_rate_high = self.query(self.node, 0x600B, 0x05)#, 'f')
        self.HiB_field = self.query(self.node, 0x600B, 0x06)#, 'f')
        self.Min_rate = self.query(self.node, 0x600B, 0x07)#, 'f')
        self.lead_resistance = self.query(self.node, 0x600B, 0x08)#, 'f')
        self.shutdown_rate = self.query(self.node, 0x600B, 0x09)#, 'f')
        self.conductance = self.query(self.node, 0x600B, 0x0A)#, 'L') #unsigned 32-bit
        self.resistance = self.query(self.node, 0x600B, 0x0B)#, 'f')
        self.write(self.node, 0x6001,0x1,250, "user")
        self.write(self.node, 0x1800,0x1,0, "user2")
        self.write(self.node, 0x1800,0x2,-2, 'b')
    #@Protpery
    def field(self):
        #Field at sample position.
        return self.query(self.node, 0x6000, 0x1)#, 'f')

    #@property
    def magnet_status(self):
        #Research the exact statuses for persistent and linear etc.
        #Magnet status number, further investigation what it means. currently 17
        return self.query(self.node, 0x6000, 0x02)#, 'u16') #unsigned16

    def current(self):
        #Current in the switch?
        return self.query(self.node, 0x6000, 0x03)#, 'f')

    #Add propper sequence similar to slave api
    def set_field(self, field, rate, approach='linear', mode='persistent', wait_for_stability=True, delay=1):
        #try:
            #Float(field, min=-self.max_field, max=self.max_field)
        #    if abs(field) <= self.max_field:
        #        float(field)
        #except Exception as e:
        #    print("converstion went wrong", e)

        cobid = 0x6005
        subid = 0x1 #23
        self.write(self.node, cobid, subid, field, 'f')

        subid = 0x2 #23
        self.write(self.node, cobid, subid, rate, 'f')

        if approach == 'linear':
            ap = 0
        else:
            ap = 1
        subid = 0x3 #2f
        self.write(self.node, cobid, subid, ap, 'b')

        if mode == 'persistent':
            m = 0
        else:
            m = 1
        subid = 0x4 #2f
        self.write(self.node, cobid, subid, m, 'b')
        self.execute()
        while wait_for_stability:
           print(self.field())
           print(self.magnet_status())
           time.sleep(delay)
        """
        Status:
        272 directly after startup => field = none
        17 field set but not excecuted
        1 seems to be persistent stable
        
        """

        #if wait_for_stability and self.magnet_status[..].startswith('persist'):
        #    time.sleep(self.magnet_config[5])

        #while wait_for_stability:
        #    status = self.system_status['magnet']
        #    if status in ('persistent, stable', 'driven, stable'):
        #        break
        #    time.sleep(delay)
   
    
    def scan_field(self):
        #import measure function.
        #maybe import qd_hybrid to ppms.py or import everything i need.
        print("hey")
    #Voltage too?
    def execute(self):#2f
        self.write(self.node, 0x6003, 0x00, 1, 'b')
        
    #def magnet_shutdown(self):






test = HMPSU()
test.set_field(0.0, 10.0)
#test.execute()
time.sleep(1)
print(test.field())
print(test.magnet_status())
test.disconnect()
