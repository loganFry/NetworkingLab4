import socket
import sys
import os
import socket_helpers
import time
from enum import Enum


# Enum to represent states of the server
class ServerState(Enum):
    AwaitingFileSize = 1
    AwaitingFileName = 2
    AwaitingFile = 3

# globals state variables
CLIENT_IP = ''
CLIENT_PORT = 0
IP = ''
SERVER_PORT = 0
state = ServerState.AwaitingFileSize

def get_inputs():
    """
    Gets the port numbers entered by the user and ensures they are valid.
    """
    
    # Ensure a port argument was provided
    if len(sys.argv) <= 2:
        print('Insufficient number of args, please provide server port and troll port')
        sys.exit()
    else:
        server_port = 0
        troll_port = 0

        # Ensure the server port number is a valid integer
        try:
            server_port = int(sys.argv[1])
        except ValueError:
            print('Server port must be a valid integer')
            sys.exit()

        # Ensure the port number is a valid integer
        try:
            troll_port = int(sys.argv[2])
        except ValueError:
            print('Troll port must be a valid integer')
            sys.exit()
        return (server_port, troll_port)

def receive_file(sock, file_size, file_name, troll_port):
    """
    Receives file data over a TCP connection.
    
    Args:
        sock: The UDP socket to receive data over.
        file_size: Size of the file in bytes.
        file_name: Name of the file.
        troll_port: The local port number troll is running on.
    """
    
    # Ensure that the output directory exists
    output_dir = 'recv'
    create_output_dir(output_dir)

    current_seq = 0
    total_read = 0.0

    # Open the new file in binary write mode
    with open(os.path.join(output_dir, file_name), 'wb') as f:
        # Read chunks of the file until we reach the file size
        while total_read < file_size:
            data = s.recv(1000 + socket_helpers.CLIENT_HEADER_SIZE)
            ip, port, flag, seq = socket_helpers.read_client_header(data)

            if flag == 2:
                # ACK sent for file name was lost, resend it
                header = socket_helpers.create_server_header(1)
                sock.sendto(header, ('', TROLL_PORT))
                print('Resent ACK for file name')

            if not ensure_correct_client(ip, port):
                continue

            if seq != current_seq:
                print('Seq mismatch, expected ' + str(current_seq) + ', got ' + str(seq))
                # ACK the previous packet
                prev_seq = socket_helpers.get_other_seq(current_seq)
                ack = socket_helpers.create_server_header(prev_seq)
                sock.sendto(ack, ('', troll_port))
                print('Sent repeat ACK for seq ' + str(current_seq))
            else:
                # ACK the received packet
                ack = socket_helpers.create_server_header(current_seq)
                sock.sendto(ack, ('', troll_port))
                print('Sent ACK for seq ' + str(current_seq))

                # Write the chunk to the new file and update server state
                f.write(data[socket_helpers.CLIENT_HEADER_SIZE:])
                total_read += 1000.0
                current_seq = socket_helpers.get_other_seq(current_seq)
                if int(total_read) % 500000 == 0:
                    print('Received another 500,000 bytes of the file')

def create_output_dir(output_dir):
    """
    Creates the output directory if it does not yet exist.
    
    Args:
        output_dir: Name of the output directory
    """

    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

def ensure_correct_client(ip, port):
    # Set client ip and port if not set yet
    global CLIENT_IP
    global CLIENT_PORT
    if CLIENT_IP == '' or CLIENT_PORT == 0:
        CLIENT_IP = ip
        CLIENT_PORT = port

    # Only accept data from the client we're currently communicating with
    if CLIENT_IP != ip or CLIENT_PORT != port:
        print('Received data from different client. IP: ' + ip + ', port: ' + port)
        return False
    else:
        return True


# Begin main code
if __name__ == '__main__':
    # Get port number to open socket on
    SERVER_PORT, TROLL_PORT = get_inputs()
    IP = socket.gethostbyname(socket.gethostname())

    # Create the socket and bind to port
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', SERVER_PORT))
    print('Server socket binded to IP ' + IP + ', port ' + str(SERVER_PORT))
    print('Sending all packets to troll port ' + str(TROLL_PORT))

    # Initialize server state
    file_size = 0
    file_name = ''

    # Main state loop
    while True:
        try:
            if state == ServerState.AwaitingFileSize:
                # Get data and read header
                data = s.recv(1000 + socket_helpers.CLIENT_HEADER_SIZE)
                ip, port, flag, seq = socket_helpers.read_client_header(data)
                if not ensure_correct_client(ip, port):
                    continue

                if flag == 1:
                    # Client sent file size
                    size_data = data[socket_helpers.CLIENT_HEADER_SIZE:socket_helpers.CLIENT_HEADER_SIZE + 4]
                    file_size = int.from_bytes(size_data, byteorder='big')
                    print('Segment 1 received, file size is ' + str(file_size) + ' bytes')
                    state = ServerState.AwaitingFileName
                    header = socket_helpers.create_server_header(seq)
                    s.sendto(header, ('', TROLL_PORT))
                    print('Sent file size ACK')
            elif state == ServerState.AwaitingFileName:
                # Get data and read header
                data = s.recv(1000 + socket_helpers.CLIENT_HEADER_SIZE)
                ip, port, flag, seq = socket_helpers.read_client_header(data)
                if not ensure_correct_client(ip, port):
                    continue

                # Client sent file name
                if flag == 2:
                    # Read the file name
                    name_data = data[socket_helpers.CLIENT_HEADER_SIZE:socket_helpers.CLIENT_HEADER_SIZE + 20]
                    file_name = name_data.decode('utf-8', 'ignore').strip()
                    print('Segment 2 received, file name is ' + file_name)

                    # ACK the file name
                    header = socket_helpers.create_server_header(seq)
                    s.sendto(header, ('', TROLL_PORT))
                    print('Sent file name ACK')

                    # Move to waiting for file state
                    state = ServerState.AwaitingFile
                elif flag == 1:
                    # ACK sent for file size was lost, resend it
                    header = socket_helpers.create_server_header(socket_helpers.get_other_seq(seq))
                    s.sendto(header, ('', TROLL_PORT))
                    print('Resent ACK for file size')
            elif state == ServerState.AwaitingFile:
                receive_file(s, file_size, file_name, TROLL_PORT)
                print('File transferred successfully')
                break
        except Exception as e:
            print('Error while receiving data: ' + str(e))