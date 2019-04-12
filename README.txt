How to run the program: 

On the server machine, run: 
python3 ftps.py <server_port>
Example:
python3 ftps.py 7000

On the client machine, open one terminal window and start troll with:
troll -C 127.0.0.1 -S <server_IP_address> -a 5555 -b <server_port> -r -s 1 -t -x 0 <troll_port>
Example:
troll -C 127.0.0.1 -S 164.107.113.21 -a 5555 -b 7000 -r -s 1 -t -x 0 6790

On the client machine, open a separate terminal window and start the client with:
python3 ftpc.py <client_IP_address> <server_port> <troll_port> <file_path>
Example:
python3 ftpc.py 164.107.113.22 7000 6790 test_image.jpg

I accounted for packet loss and reordering in a couple ways. For the initial transfer
setup where the client sends the file size and file name to the server, I required the 
server to send explicit "ACK" messages back to the client. The client continually tries
to send the file size and file name until it receives successful ACKs for both. During the
file transfer itself, each chunk of the file is sent in a datagram and marked with a sequence
number in my header. If the server detects that it has received a datagram with an incorrect
sequence number, it sends a message back to the client with its next expected sequence number.
The client will see this message, then move its sending window back to that sequence number and
resume sending data. 