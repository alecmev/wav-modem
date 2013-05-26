from math import floor
import sys

NUL = chr(0x00) # NULL character
SOH = chr(0x01) # 128 bytes
STX = chr(0x02) # 1024 bytes
EOT = chr(0x04) # End Of Transmission
ACK = chr(0x06) # ACKnowledge
NAK = chr(0x15) # Negative AcKnowledge
CAN = chr(0x18) # CANcel
SUB = chr(0x1a) # SUBstitute
C   = chr(0x43) # CRC mode

debug = not ('_MEIPASS' in dir(sys))
blockSize = 128
SXX = SOH if blockSize == 128 else STX

crctable = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
    0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
    0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
    0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
    0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
    0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
    0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
    0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
    0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
    0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
    0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
    0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
    0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
    0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
    0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
    0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
    0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
    0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
    0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
    0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
    0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
    0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0,
]

def checksum(data, chval=0):
    return (sum(map(ord, data)) + chval) % 256

def crc(data, chval=0):
    for char in data:
        chval = (chval << 8) ^ crctable[((chval >> 8) ^ ord(char)) & 0xff]
    return chval & 0xffff

def log(data, incoming=False):
    if not debug:
        return

    if incoming:
        print '<',
    else:
        print '    >',

    print ''.join([hex(ord(char))[2:].zfill(2) for char in str(data)])

def logError(message):
    if debug:
        print message

class MODEM(object):
    def __init__(self, getc, putc, progress, retry=16):
        self.getc = getc
        self.putc = putc
        self.progress = progress
        self.retry = retry

    def __logGet(self):
        data = self.getc(1)
        log(data, True)
        return data

    def __logPut(self, data):
        self.putc(data)
        log(data)

    def __abort(self, message):
        self.__logPut(CAN + CAN)
        logError(message)

    def __getMode(self):
        errors = 0
        while True:
            char = self.__logGet()
            if not len(char):
                logError('getMode: timeout')
                return False
            elif char == NAK:
                self.useCRC = False
                return True
            elif char == C:
                self.useCRC = True
                return True
            elif char == CAN:
                char = self.__logGet()
                if char == CAN:
                    logError('getMode: transmission cancelled')
                    return False

            errors += 1
            if errors >= self.retry:
                self.__abort('getMode: too many unexpected chars')
                return False

    def __getACK(self):
        char = self.__logGet()
        if not len(char):
            logError('getACK: timeout')
            return False
        elif char == ACK:
            return True
        elif char == CAN:
            char = self.__logGet()
            if char == CAN:
                logError('getACK: transmission cancelled')
                return False
        else:
            return None

    def __sendBlock(self, data, sequence=0):
        if self.useCRC:
            chval = crc(data)
        else:
            chval = checksum(data)

        data = (
            (SXX if sequence else SOH) + 
            chr(sequence) + 
            chr(0xff - sequence) +
            data +
            (chr(chval >> 8) + chr(chval & 0xff) if self.useCRC else chr(chval))
        )
        errors = 0
        while True:
            self.__logPut(data)
            res = self.__getACK()
            if res:
                return True
            elif res == False:
                return False
            else:
                errors += 1
                if errors >= self.retry:
                    self.__abort('sendBlock: too many NAKs')
                    return False

    def __sendEOT(self):
        errors = 0
        while True:
            self.__logPut(EOT)
            res = self.__getACK()
            if res:
                return True
            elif res == False:
                return False
            else:
                errors += 1
                if errors >= self.retry:
                    self.__abort('sendEOT: too many NAKs')
                    return False

    def send(self, stream, fileSize, useY=False, filename=None):
        if useY and not isinstance(filename, basestring):
            logError('send: YMODEM requires a filename')
            return False

        if not self.__getMode() or (useY and (
            not self.__sendBlock(filename.ljust(blockSize, NUL)) or 
            not self.__getMode()
        )):
            return False

        total = fileSize / float(blockSize)
        sequence = 1
        while True:
            data = stream.read(blockSize)
            if not data:
                self.progress(100)
                break

            if not self.__sendBlock(data.ljust(blockSize, SUB), sequence % 0x100):
                return False

            self.progress(int(floor((sequence * 100) / total)))
            sequence += 1
        
        if not self.__sendEOT() or (useY and (
            not self.__getMode() or 
            not self.__sendBlock(NUL * blockSize)
        )):
            return False

        return True
