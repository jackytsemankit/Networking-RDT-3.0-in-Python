#!/usr/bin/python3
"""Implementation of RDT3.0

functions: rdt_network_init(), rdt_socket(), rdt_bind(), rdt_peer()
           rdt_send(), rdt_recv(), rdt_close()

Student name: Tse Man Kit
Student No. : 3035477757
Date and version: 2/4/2021
Development platform: Windows 10
Python version: Python 3.9.2
"""

import socket
import random
import struct
import select


#some constants
PAYLOAD = 1000		#size of data payload of the RDT layer
CPORT = 100			#Client port number - Change to your port number
SPORT = 200			#Server port number - Change to your port number
TIMEOUT = 0.05		#retransmission timeout duration
TWAIT = 10*TIMEOUT 	#TimeWait duration

#store peer address info
__peeraddr = ()		#set by rdt_peer()
#define the error rates
__LOSS_RATE = 0.0	#set by rdt_network_init()
__ERR_RATE = 0.0

__my_seqno=0
__peer_seqno=0


#internal functions - being called within the module
def __udt_send(sockd, peer_addr, byte_msg):
	"""This function is for simulating packet loss or corruption in an unreliable channel.

	Input arguments: Unix socket object, peer address 2-tuple and the message
	Return  -> size of data sent, -1 on error
	Note: it does not catch any exception
	"""
	global __LOSS_RATE, __ERR_RATE
	if peer_addr == ():
		print("Socket send error: Peer address not set yet")
		return -1
	else:
		#Simulate packet loss
		drop = random.random()
		if drop < __LOSS_RATE:
			#simulate packet loss of unreliable send
			print("WARNING: udt_send: Packet lost in unreliable layer!!")
			return len(byte_msg)

		#Simulate packet corruption
		corrupt = random.random()
		if corrupt < __ERR_RATE:
			err_bytearr = bytearray(byte_msg)
			pos = random.randint(0,len(byte_msg)-1)
			val = err_bytearr[pos]
			if val > 1:
				err_bytearr[pos] -= 2
			else:
				err_bytearr[pos] = 254
			err_msg = bytes(err_bytearr)
			print("WARNING: udt_send: Packet corrupted in unreliable layer!!")
			return sockd.sendto(err_msg, peer_addr)
		else:
			#print("***************************success: __udt_send returns: ",sockd.sendto(byte_msg, peer_addr))
			return sockd.sendto(byte_msg, peer_addr)

def __udt_recv(sockd, length):
	"""Retrieve message from underlying layer

	Input arguments: Unix socket object and the max amount of data to be received
	Return  -> the received bytes message object
	Note: it does not catch any exception
	"""
	(rmsg, peer) = sockd.recvfrom(length)
	return rmsg

def __IntChksum(byte_msg):
	"""Implement the Internet Checksum algorithm

	Input argument: the bytes message object
	Return  -> 16-bit checksum value
	Note: it does not check whether the input object is a bytes object
	"""
	total = 0
	length = len(byte_msg)	#length of the byte message object
	i = 0
	while length > 1:
		total += ((byte_msg[i+1] << 8) & 0xFF00) + ((byte_msg[i]) & 0xFF)
		i += 2
		length -= 2

	if length > 0:
		total += (byte_msg[i] & 0xFF)

	while (total >> 16) > 0:
		total = (total & 0xFFFF) + (total >> 16)

	total = ~total

	return total & 0xFFFF


#These are the functions used by appliation

def rdt_network_init(drop_rate, err_rate):
	"""Application calls this function to set properties of underlying network.

    Input arguments: packet drop probability and packet corruption probability
	"""
	random.seed()
	global __LOSS_RATE, __ERR_RATE
	__LOSS_RATE = float(drop_rate)
	__ERR_RATE = float(err_rate)
	print("Drop rate:", __LOSS_RATE, "\tError rate:", __ERR_RATE)


def rdt_socket():
	"""Application calls this function to create the RDT socket.

	Null input.
	Return the Unix socket object on success, None on error

	Note: Catch any known error and report to the user.
	"""
	######## Your implementation #######
	try:
		sd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	except socket.error as emsg:
		print("Socket creation error: ", emsg)
		return None
	return sd


def rdt_bind(sockd, port):
	"""Application calls this function to specify the port number
	used by itself and assigns them to the RDT socket.

	Input arguments: RDT socket object and port number
	Return	-> 0 on success, -1 on error

	Note: Catch any known error and report to the user.
	"""
	######## Your implementation #######
	try:
		sockd.bind(("",port))
	except socket.error as emsg:
		print("Socket bind error: ", emsg)
		return -1
	return 0


def rdt_peer(peer_ip, port):
	"""Application calls this function to specify the IP address
	and port number used by remote peer process.

	Input arguments: peer's IP address and port number
	"""
	######## Your implementation #######

	global __peeraddr
	__peeraddr = (peer_ip, port)


def rdt_send(sockd, byte_msg):
	"""Application calls this function to transmit a message to
	the remote peer through the RDT socket.

	Input arguments: RDT socket object and the message bytes object
	Return  -> size of data sent on success, -1 on error

	Note: Make sure the data sent is not longer than the maximum PAYLOAD
	length. Catch any known error and report to the user.
	"""
	######## Your implementation #######
	global PAYLOAD, __peeraddr

	global __my_seqno
	



	while True:

		if (len(byte_msg) > PAYLOAD):
			msg = byte_msg[0:PAYLOAD]
		else:
			msg = byte_msg

		if len(msg)==0:	#ACK
			typeval=11

		else:	#DATA
			typeval=12

		


		header = struct.pack('BBHH', typeval, __my_seqno, 0, socket.htons(len(msg)))
		pkt = header + msg
		checksum=__IntChksum(pkt)
		header = struct.pack('BBHH', typeval, __my_seqno, checksum, socket.htons(len(msg)))
		pkt = header + msg


		try:
			length = __udt_send(sockd, __peeraddr, pkt)
			
			print("rdt_send: Sent one message of size %d" % len(msg))
			#print("__my_seqno: ",__my_seqno)

		except socket.error as emsg:
			print("rdt_send: Socket send error: ", emsg)
			#return -1

		RList = [sockd]

		# create an empty WRITE socket list
		WList = []

		try:
			Rready, Wready, Eready = select.select(RList, [], [], TIMEOUT)
		except select.error as emsg:
			print("rdt_send: At select, caught an exception:", emsg)
			sys.exit(1)
		except KeyboardInterrupt:
			print("rdt_send: At select, caught the KeyboardInterrupt")
			sys.exit(1)

		# if has incoming activities
		if Rready:
			try:
				rmsg = __udt_recv(Rready[0],1006)
			except socket.error as emsg:
				print("rdt_send: Socket recv error: ", emsg)
			#return -1

			header=rmsg[0:6]
			message_format = struct.Struct('BBHH')
			(val1, val2, val3, val4) = message_format.unpack(header)
			checksum = __IntChksum(rmsg)



			#if corrupted, drop
			if checksum!=0:
				if val1==11:
					t="ACK"
				else:
					t="DATA"
				print("rdt_send: Received a corrupted packet: Type = %s, Length = %d"%(t, (socket.ntohs(val4)) ))
				print("rdt_send: Drop the packet")
				

			if val1==11 and checksum==0 :
				#ACK, expected ACK received, change state
				#print( "*********************rmsg Checksum result: ",__IntChksum(rmsg))
				if val2==__my_seqno:
					print( "rdt_send: Received the expected ACK")
					__my_seqno= (__my_seqno+1)%2
					#print("***********rdt_send now returns")										
					return len(msg)

				else:
					#different state
					continue
			
			elif val1==12 and checksum==0:
				#DATA, resend ACK of previous sent packet
				print("rdt_send: I am expecting an ACK packet, but received a DATA packet")
				
				if val2==__peer_seqno:
					print("rdt_send: Peer sent me a new DATA packet!!")
					print("rdt_send: Drop the packet as I cannot accept it at this point")
					

				else:
					print("rdt_send: Received a retransmission DATA packet from peer!!")
					print("rdt_send: Retransmit the ACK packet")
					pkt = struct.pack('BBHH',11, val2, 0, socket.htons(0))
					pkt = struct.pack('BBHH',11, val2, __IntChksum(pkt), socket.htons(0))
					try:
						__udt_send(sockd, __peeraddr, pkt)
					except socket.error as emsg:
						print("Socket send error: ", emsg)
						#return -1

				'''
				pkt = struct.pack('BBHH',11, val2, 0, socket.htons(0))
				pkt = struct.pack('BBHH',11, val2, __IntChksum(pkt), socket.htons(0))
				try:
					__udt_send(sockd, __peeraddr, pkt)
				except socket.error as emsg:
					print("Socket send error: ", emsg)
					#return -1
				'''


					

		# else did not have activity after TIMOUT, retransmit
		else:
			print("rdt_send: Timeout!! Retransmitt the packet %d again"% __my_seqno)
			'''
			if len(msg)==0:	#ACK
				typeval=11

			else:	#DATA
				typeval=12				
			header = struct.pack('BBHH', typeval, __send_seqno, 0, socket.htons(len(msg)))
			pkt = header + msg
			header = struct.pack('BBHH', typeval, __send_seqno, __IntChksum(pkt), socket.htons(len(msg)))
			pkt = header + msg
			try:
				__udt_send(sockd, __peeraddr, pkt)
			except socket.error as emsg:
				print("Socket send error: ", emsg)
				#return -1
			'''
				




def rdt_recv(sockd, length):
	"""Application calls this function to wait for a message from the
	remote peer; the caller will be blocked waiting for the arrival of
	the message. Upon receiving a message from the underlying UDT layer,
    the function returns immediately.

	Input arguments: RDT socket object and the size of the message to
	received.
	Return  -> the received bytes message object on success, b'' on error

	Note: Catch any known error and report to the user.
	"""
	######## Your implementation #######
	global __peer_seqno


	while True:
		try:
			#receving, with buffer of size length+6 (6 bytes extra to accommadate the header)
			#print("***************recv blocked waiting to recv")
			rmsg = __udt_recv(sockd, length+6)
			#print("***************recv releasesd")
		except socket.error as emsg:
			print("Socket recv error: ", emsg)
			return b''


		header = rmsg[0:6]
		message_format = struct.Struct('BBHH')
		(val1, val2, val3, val4) = message_format.unpack(header)

		msglen=socket.ntohs(val4)
		data=rmsg[6:]


		checksum=__IntChksum(rmsg)

		#corrupted, send ACK with the alternative seq no
		if checksum!=0:
			if val1==11:
				t="ACK"
			else:
				t="DATA"
			print("rdt_recv: Received a corrupted packet: Type = %s, Length = %d"%(t, (socket.ntohs(val4)) ))
			print("rdt_recv: Drop the packet")
			'''
			pkt = struct.pack('BBHH',11, (val2+1)%2, 0, socket.htons(0))
			pkt = struct.pack('BBHH',11, (val2+1)%2, __IntChksum(pkt), socket.htons(0))
			try:
				__udt_send(sockd, __peeraddr, pkt)
			except socket.error as emsg:
				print("Socket send error: ", emsg)
				#return -1
			#continue
			'''

		#print ("val2: %d ; __peer_seqno: %d" % (val2,__peer_seqno))

		elif val1==12: #DATA			
			#got expected packet, change state and return data to application layer
			if val2 == __peer_seqno:
				#print("__peer_seqno: ",__peer_seqno)
				print ("rdt_recv: Got an expected packet")
				print("rdt_recv: Received a message of size %d" % (msglen))
				pkt = struct.pack('BBHH',11, val2, 0, socket.htons(0))
				pkt = struct.pack('BBHH',11, val2, __IntChksum(pkt), socket.htons(0))
				__peer_seqno=(__peer_seqno+1) %2
				try:
					__udt_send(sockd, __peeraddr, pkt)
				except socket.error as emsg:
					print("rdt_recv: Socket send error: ", emsg)
					continue				
				#print("__peer_seqno: ",__peer_seqno)
				return data


			#retransmit ACK if received retransmitted data
			if val2 != __peer_seqno:
				print ("rdt_recv: Received a retransmission DATA packet from peer!!")
				print("rdt_recv: Retransmit the ACK packet")
				pkt = struct.pack('BBHH',11, val2, 0, socket.htons(0))
				pkt = struct.pack('BBHH',11, val2,  __IntChksum(pkt), socket.htons(0))
				try:
					__udt_send(sockd, __peeraddr, pkt)
				except socket.error as emsg:
					print("Socket send error: ", emsg)
					#return -1				

		elif val1==11: #ACK received, ignore
			#if val2!=__peer_seqno:
			print("rdt_recv: Received a ACK from peer ")
			#return 0
			#pkt = struct.pack('BBHH',11, val2, 0, socket.htons(0))
			#pkt = struct.pack('BBHH',11, val2, __IntChksum(pkt), socket.htons(0))
			#__udt_send(sockd, __peeraddr, pkt)
			#__peer_seqno=(__peer_seqno+1) %2
					

		

		
	

def rdt_close(sockd):
	"""Application calls this function to close the RDT socket.

	Input argument: RDT socket object

	Note: (1) Catch any known error and report to the user.
	(2) Before closing the RDT socket, the reliable layer needs to wait for TWAIT
	time units before closing the socket.
	"""
	######## Your implementation #######
	

	RList = [sockd]

	# create an empty WRITE socket list
	WList = []

	while True:
		# use select to wait for any incoming connection requests or
		# incoming messages or TWAIT seconds
		try:
			Rready, Wready, Eready = select.select(RList, [], [], TWAIT)
		except select.error as emsg:
			print("At select, caught an exception:", emsg)
			sys.exit(1)
		except KeyboardInterrupt:
			print("At select, caught the KeyboardInterrupt")
			sys.exit(1)

		# if has incoming activities
		if Rready:
			rmsg = __udt_recv(sockd, PAYLOAD+6)

			
			message_format = struct.Struct('BBHH')
			(val1, val2, val3, val4) = message_format.unpack(rmsg[0:6])

			#retransmit ACK of the incoming data, to inform peer that it is received, in case the previously sent ACK got lost
			if val1==12 and __IntChksum(rmsg)==0:
				pkt = struct.pack('BBHH',11, val2, 0, socket.htons(0))
				pkt = struct.pack('BBHH',11, val2, __IntChksum(pkt), socket.htons(0))
				try:
					__udt_send(sockd, __peeraddr, pkt)
				except socket.error as emsg:
					print("Socket send error: ", emsg)
					#return -1


		# else did not have activity for TWAIT seconds, close
		else:
			try:			
				print("Nothing happened for %f second"% TWAIT)
				print("Release the socket")
				sockd.close()
				return True
			except socket.error as emsg:
				print("Socket close error: ", emsg)

