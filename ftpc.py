import socket
from socket import IPPROTO_TCP
import sys
import ipaddress
import os
import time
import socket_helpers
import select


def get_inputs():
    """
    Gets user inputs of server IP address, server port number, local troll port number, and file path, and checks to 
    ensure they are valid.
    """
    
    # Test that all inputs are present
    if len(sys.argv) <= 4:
        print('Must specify server IP address, server port number, troll port number, and file path')
        sys.exit()

    # Check local IP address
    server_ip = sys.argv[1]
    try:
        # Looks up a hostname to IP address if necessary, if not just returns
        # the same IP address
        server_ip = socket.gethostbyname(server_ip)
    except:
        print('IP address is not valid')
        sys.exit()

    # Ensure server port number is valid
    try:
        server_port = int(sys.argv[2])
    except ValueError:
        print('Server port is not an integer')
        sys.exit()

    # Ensure troll port number is valid
    try:
        troll_port = int(sys.argv[3])
    except ValueError:
        print('Troll port is not an integer')
        sys.exit()

    # Ensure input file exists
    file_path = sys.argv[4]
    if not os.path.isfile(file_path):
        print('Input file is not a valid file path')
        sys.exit()

    return (server_ip, server_port, troll_port, file_path)



def send_metadata(file_path, sock, troll_port, client_ip, client_port):
    """
    Sends metadata about a given file over a TCP connection.
    
    Args:
        file_path: The file to send information about
        connection: The TCP connection to send the data over
        troll_port: The local port number on which troll is running
        client_ip: IP address of the client machine
        client_port: The local port number on which the client is running
    """
    seg_1_acked = False
    send_file_size(client_ip, client_port, file_path, troll_port, 0)

    while True:
        # The timeout is set to be 1 sec.
        read, write, err = select.select([sock], [], [], 1)
        if len(read) > 0:
            # The socket has received data.
            data = sock.recv(1000)
            seq = socket_helpers.read_server_header(data)

            if seq == 0:
                # Server received seg 1
                seg_1_acked = True
                print('seg 1 ACKed')
                send_file_name(client_ip, client_port, file_path, troll_port, 1)
            elif seq == 1:
                # Server received seg 2
                print('seg 2 ACKed')
                break                
        else:
            # Timeout, resend the current segment
            if not seg_1_acked:
                send_file_size(client_ip, client_port, file_path, troll_port, 0)
            else:
                send_file_name(client_ip, client_port, file_path, troll_port, 1)

        # Sleep to avoid overrunning UDP buffers
        time.sleep(0.01)

def send_file_size(client_ip, client_port, file_path, troll_port, seq):
    # Send the first segment with header and 4 byte file size
    header = socket_helpers.create_client_header(client_ip, client_port, 1, seq)
    # Get the size of the file in bytes
    file_size = os.path.getsize(file_path).to_bytes(4, byteorder='big')
    segment_1 = header + file_size
    sock.sendto(segment_1, ('', troll_port))

def send_file_name(client_ip, client_port, file_path, troll_port, seq):
    # Send the second segment with header and 20 byte file name
    header = socket_helpers.create_client_header(client_ip, client_port, 2, seq)
    # Get the file name (without path)
    file_name = socket_helpers.fill_fixed_bytes(os.path.basename(file_path), 20) 
    segment_2 = header + file_name
    sock.sendto(segment_2, ('', troll_port))

def send_file(file_path, sock, troll_port, client_ip, client_port):
    """
    Sends the data inside a given file using a UDP socket.
    
    Args:
        file_path: The file to send
        sock: The UDP socket to send data over.
        troll_port: The local port number on which troll is running
        client_ip: The IP of the client machine
        client_port: The local port number on which the client is running
    Raises:
        Exception: raised if there are any errors during file transfer
    """
    
    try:
        # Open the file in binary read mode
        f = open(file_path, 'rb')

        # Initialize sequence number and send first chunk of data
        current_seq = 0
        # Get data to send
        header = socket_helpers.create_client_header(client_ip, client_port, 3, current_seq)
        chunk = f.read(1000)
        sock.sendto(header + chunk, ('', troll_port))
   
        while True:
            # The timeout is set to be 1 sec.
            read, write, err = select.select([sock], [], [], 1)
            if len(read) > 0:
                # The socket received an ACK from the server.
                data = sock.recv(socket_helpers.SERVER_HEADER_SIZE)
                seq = socket_helpers.read_server_header(data)
                print('Received ACK with seq ' + str(seq))
                if seq == current_seq:
                    # Received an ACK for the current chunk, move to next sequence number
                    # and read the next chunk of the file
                    current_seq = socket_helpers.get_next_seq(current_seq)
                    chunk = f.read(1000)
            else:
                # Timeout, do not update any state, we will resend the same chunk and sequence 
                # number.
                print('Timeout ocurred')
   
            
            header = socket_helpers.create_client_header(client_ip, client_port, 3, current_seq)
            # If the chunk is an empty byte, we've reached the end of the file
            if chunk == b'':
                break

            # Send data
            sock.sendto(header + chunk, ('', troll_port))

            # Sleep to avoid overrunning UDP buffers, move to next sequence number
            time.sleep(0.01)
    except Exception as e:
        raise
    finally:
        f.close()

# Begin main code
if __name__ == '__main__':

    # User inputs
    LOCAL_IP, SERVER_PORT, TROLL_PORT, FILENAME = get_inputs()
    # Constant client ip and port
    CLIENT_PORT = 5555

    # Create the UDP socket and bind to client port (required for troll)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', CLIENT_PORT))

    print('client socket binded to ip ' + socket.gethostbyname(socket.gethostname()) + ', port ' + str(CLIENT_PORT))
    print('sending all packets to troll port ' + str(TROLL_PORT))

    try:
        # Send meta data
        send_metadata(FILENAME, sock, TROLL_PORT, LOCAL_IP, CLIENT_PORT)

        # Send file
        send_file(FILENAME, sock, TROLL_PORT, LOCAL_IP, CLIENT_PORT)
    except Exception as e:
        print('Error while sending file: ' + str(e))
    else:
        print('File transferred successfully')
    finally:
        # Close the connection
        sock.close()  

    

    
