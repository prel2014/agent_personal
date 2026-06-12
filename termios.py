# Stub de termios para Windows — solo importado por mock_serial (plugin pytest no usado en este proyecto).
# Expone las constantes mínimas para que mock_serial pueda cargarse sin errores.


def tcgetattr(fd):
    return []


def tcsetattr(fd, when, attrs):
    pass


def tcdrain(fd):
    pass


TCSAFLUSH = 2
TCSANOW = 0
TCSADRAIN = 1

B9600 = 13
B19200 = 14
B38400 = 15
B57600 = 4097
B115200 = 4098

ECHO = 8
ICANON = 2
VMIN = 6
VTIME = 5
ISIG = 1

CSIZE = 48
CS8 = 48
CREAD = 128
CLOCAL = 2048
PARENB = 256
CRTSCTS = 2097152
IXON = 1024
IXOFF = 2048
IXANY = 2048
IGNPAR = 4
