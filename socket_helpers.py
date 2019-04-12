CLIENT_HEADER_SIZE = 8
SERVER_HEADER_SIZE = 1


def create_client_header(ip, port, flag, seq):
    """
    Create a header for a UDP message
    
    Args:
        ip: IP address of the sender
        port: port number of the sender
        flag: Control flag describing the type of message
        seq: Sequence number, 0 or 1
    """
    
    ip_data = get_ip_numbers(ip)
    port_data = port.to_bytes(2, byteorder='big')
    flag_data = flag.to_bytes(1, byteorder='big')
    seq_data = seq.to_bytes(1, byteorder='big')
    header = ip_data + port_data + flag_data + seq_data

    return header

def create_server_header(seq):
    """
    Creates a header for a server ACK message using the sequence number 
    provided.
    
    Args:
        seq: Sequence number to ACK, 0 or 1
    """

    return seq.to_bytes(1, byteorder='big')
    

def get_ip_numbers(ip):
    """
    Takes a string IP address like 127.0.0.1 and extracts the 4 individual
    numbers and stores them in a 4 byte bytearray
    
    Args:
        ip: The string IP address in IPv4 form
    """
    
    idx_1 = ip.find('.')
    num_1 = int(ip[0:idx_1]).to_bytes(1, byteorder='big')
    idx_2 = ip.find('.', idx_1 + 1)
    num_2 = int(ip[idx_1 + 1:idx_2]).to_bytes(1, byteorder='big')
    idx_1 = idx_2
    idx_2 = ip.find('.', idx_1 + 1)
    num_3 = int(ip[idx_1 + 1:idx_2]).to_bytes(1, byteorder='big')
    idx_1 = idx_2
    idx_2 = ip.find('.', idx_1 + 1)
    num_4 = int(ip[idx_1 + 1:]).to_bytes(1, byteorder='big')

    return num_1 + num_2 + num_3 + num_4

def read_client_header(data):
    """
    Takes a binary datagram and extracts the pieces of information which comprise
    the header of the datagram.
    
    Args:
        data: Binary data of a UDP datagram
    """
    
    # first 4 bytes are the 4 numbers in the ip address
    ip_1 = str(data[0])
    ip_2 = str(data[1])
    ip_3 = str(data[2])
    ip_4 = str(data[3])
    # Convert into string IP address
    ip = ip_1 + '.' + ip_2 + '.' + ip_3 + '.' + ip_4

    # next 2 bytes are the port number
    port = int.from_bytes(data[4:6], byteorder='big')

    # next byte is the flag 
    flag = int(data[6])

    # last byte is the sequence number
    seq = int(data[7])

    return (ip, port, flag, seq)

def read_server_header(data):
    """
    Reads an ACK header from the server, returns the sequence number (0 or 1).
    
    Args:
        data: Binary data received by the client socket
    """
    
    
    seq = int(data[0])
    return seq

def get_next_seq(current_seq):
    """
    Given a current sequence number, returns the next one.
    
    Args:
        current_seq: The current sequence number being used
    """

    if(current_seq == 0):
        return 1
    if(current_seq == 1):
        return 0
    raise Exception('Invalid sequence number: ' + str(current_seq))
    
def is_lead_byte(b):
    """
    Checks if the byte is a lead byte in the UTF-8 encoding.
    
    Args:
        b: The byte to check
    """
     
    # A UTF-8 intermediate byte starts with the bits 10xxxxxx.
    return (b & 0xC0) != 0x80

def truncate_string(text, max_bytes):
    """
    Truncates a given string to a bytearray with max size of max_bytes.
    
    Args:
        text: The string to convert to bytes and truncate
        max_bytes: The max length to truncate to in bytes
    """

    # If text[max_bytes] is not a lead byte, back up until a lead byte is
    # found and truncate before that character.
    utf8 = text.encode('utf8')
    if len(utf8) <= max_bytes:
        return utf8
    i = max_bytes
    while i > 0 and not is_lead_byte(utf8[i]):
        i -= 1
    return utf8[:i]

def fill_fixed_bytes(source, size):
    """
    Converts a source string into a bytearray of exactly size bytes, truncating
    if the source string is too long and padding with spaces if the source string
    is too short.
    
    Args:
        source: The string to convert to bytes
        size: The number of bytes to convert to
    """
    
    # Ensure source is a string
    source = str(source)
    # truncate the string to a max of size bytes
    truncated = truncate_string(source, size)
    # created a bytearray of the correct size
    fixed = bytearray(size)

    for i in range(size):
        # if the truncated string contains this byte, use that value
        if i < len(truncated):
            fixed[i] = truncated[i]
        # otherwise pad with UTF-8 spaces (0x20)
        else:
            fixed[i] =  0x20
    return fixed