import can
import can.interfaces.usb2can
import struct

class Protocol:
    """
    This Class handels the CAN-Bus connection between the magnet power supply and the usb2can controller.
    """
    def __init__(self):
        """
        The init functions sets up the connection.
        The Channelnumber is the Serialnumber of the USB2CAN Controller (printed on the controller).
        The bitrate is at its maximum of 1 MBps.
        """
        try:
            self.channel = 'ED000200'
            self.bitrate = 1000000
            self.bus = can.interfaces.usb2can.Usb2canBus(channel=self.channel, bitrate=self.bitrate)
        except Exception as e:
            print(e)

    def disconnect(self):
        """ This function disconnects the controller and deletes the class instance """
        if self.bus != None:
            self.bus.shutdown()
            del self

    def query(self, node, cobid, subid):
        """

        """
        try:
            msgdata = struct.pack('bbbbbbbb', 0x40, int(hex(cobid)[0:2]+hex(cobid)[4:6],1), int(hex(cobid)[0:4],16), subid, 0,0,0,0)
            msg = can.Message(extended_id=False, arbitration_id=int(0x0600)+node, data=msgdata)
            self.bus.set_filters(filters=[{"can_id" : 0x0580, "can_mask":0xFFF0}])

            for attempts in range(5):
                self.bus.send(msg)
                ans = self.bus.recv(timeout=.1)
                data = struct.unpack('bbbbbbbb', ans.data)
                if cobid == data[2] + data[1] and  subid == data[3]:
                    data = self.decode(ans)
                    break
                else:
                    data = None
            return data
        except Exception as e:
            print(e)

    def decode(self, msg):
        try:
            data = struct.unpack('bbbbbbbb', msg.data)
            canid = msg.arbitration_id
            subid = data[3]
            cobid = data[2] + data[1]

            if data[0] == 0x43 or data[0] == 0x80:
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
                rdata= data[4], data[5]
            elif data[0] == 0x80:
                data = struct.unpack('bbbbf', msg.data)
                rdata=data[4]
            else:
                rdata = None
            return canid, cobid, subid, rdata #probaly only return rdata
        except Exception as e:
            print(e)


    def write(self, node, cobid, subid, data, dtype):
        try:
            msgdata = self.encode(cobid, subid, data, dtype)
            msg = can.Message(extended_id=False, arbitration_id=int(0x0600)+node, data=msgdata)
            self.bus.set_filters(filters=[{"can_id" : 0x0580, "can_mask":0xFFF0}])

            for attempts in range(5):
                self.bus.send(msg)
                ans = self.bus.recv(timeout=.1)

                data = struct.unpack('bbbbbbbb', ans.data)
                if cobid == data[2] + data[1] and subid == data[3]:
                    recv = True
                    break
                else:
                    recv = False
                return recv

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
        else:
            msgdata = None
        return msgdata




class HMPSU(Protocol):
    """ Class for the Quantum Design Hybrid Magnet Power Suply Unit. """
    def __init__(self):
        super().__init__()
        self.node=6
        

        self.max_field = self.query(self.node, 0x600B, 0x01)
        self.BtoI_Ratio = self.query(self.node, 0x600B, 0x02)
        self.Inductance = self.query(self.node, 0x600B, 0x03)
        self.max_rate_low = self.query(self.node, 0x600B, 0x04)
        self.max_rate_high = self.query(self.node, 0x600B, 0x05)
        self.HiB_field = self.query(self.node, 0x600B, 0x06)
        self.Min_rate = self.query(self.node, 0x600B, 0x07)
        self.lead_resistance = self.query(self.node, 0x600B, 0x08)
        self.shutdown_rate = self.query(self.node, 0x600B, 0x09)
        self.conductance = self.query(self.node, 0x600B, 0x0A)
        self.resistance = self.query(self.node, 0x600B, 0x0B)
        self.Switch = self.query(self.node, 0x600C, 0x02)

        self.SwitchCoolTime = self.query(self.node, 0x600C, 0x02)

    def field(self):
        """ Retruns field at sample position"""
        return self.query(self.node, 0x6000, 0x1)

    def magnet_status(self):
        """ Retruns the Status of the Magnet. """
        return self.query(self.node, 0x6000, 0x2)

    def current(self):
        #Current in the switch?
        return self.query(self.node, 0x6000, 0x03)#, 'f')

    def set_field(self, field, rate, approach='linear', mode='persistent', wait_for_stability=True, delay=1):
        try:
            if abs(field) <= self.max_field:
                float(field)
            #Testing required
            if abs(rate) >= self.max_rate_low and abs(rate) <= self.max_rate_high:
                float(rate)
        except Exception as e:
            print("converstion went wrong", e)

        cobid = 0x6005
        subid = 0x1
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
        """
        Status:
        272 directly after startup => field = none
        17 field set but not excecuted
        1 seems to be persistent stable
        
        """
    def execute(self):
        """ executes the magnet command with the variables set in set_field """
        self.write(self.node, 0x6003, 0x00, 1, 'b')

    def shutdown(self):
        """shutdown field and connection TOBE tested"""
        self.write(self.node, 0x6003, 0x0, 0, 'b')
        self.disconnect()
        del self
