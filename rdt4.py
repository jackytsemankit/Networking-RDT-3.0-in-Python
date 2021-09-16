#!/usr/bin/python3
"""Implementation of RDT4.0

functions: rdt_network_init, rdt_socket(), rdt_bind(), rdt_peer()
           rdt_send(), rdt_recv(), rdt_close()

Student name: Tse Man Kit
Student No. : 3035477757
Date and version: 3/5/2021 version 3
Development platform: Windows 10
Python version: Python 3.9.2
"""

import socket
import random
import math
import struct
import select

#some constants
PAYLOAD = 1000		#size of data payload of each packet
CPORT = 100			#Client port number - Change to your port number
SPORT = 200			#Server port number - Change to your port number
TIMEOUT = 0.05		#retransmission timeout duration
TWAIT = 10*TIMEOUT 	#TimeWait duration

#store peer address info
__peeraddr = ()		#set by rdt_peer()
#define the error rates and window size
__LOSS_RATE = 0.0	#set by rdt_network_init()
__ERR_RATE = 0.0
__W = 1

S = 0
__nextseqnum=0
__expectedseqnum=0

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

def rdt_network_init(drop_rate, err_rate, W):
	"""Application calls this function to set properties of underlying network.

    Input arguments: packet drop probability, packet corruption probability and Window size
	"""
	random.seed()
	global __LOSS_RATE, __ERR_RATE, __W
	__LOSS_RATE = float(drop_rate)
	__ERR_RATE = float(err_rate)
	__W = int(W)
	print("Drop rate:", __LOSS_RATE, "\tError rate:", __ERR_RATE, "\tWindow size:", __W)

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
	"""Application calls this function to transmit a message (up to
	W * PAYLOAD bytes) to the remote peer through the RDT socket.

	Input arguments: RDT socket object and the message bytes object
	Return  -> size of data sent on success, -1 on error

	Note: (1) This function will return only when it knows that the
	whole message has been successfully delivered to remote process.
	(2) Catch any known error and report to the user.
	"""
	######## Your implementation #######
	global PAYLOAD, __peeraddr, __nextseqnum, S

	N = 0 #number of packets
	S = __nextseqnum
	k=0
	ack=[]
	sizecount=0
	

	N = math.ceil(float(len(byte_msg))/PAYLOAD)

	sndpkd=[None]*N

	for i in range (0,N):
			ack.append(0)

	while True:

		typeval=12

		for i in range (0,N):

			msg = byte_msg[i*PAYLOAD:(i+1)*PAYLOAD]			
			
			header = struct.pack('BBHH', typeval, __nextseqnum, 0, socket.htons(len(msg)))
			pkt = header + msg
			checksum=__IntChksum(pkt)
			header = struct.pack('BBHH', typeval, __nextseqnum, checksum, socket.htons(len(msg)))
			pkt = header + msg
			sndpkd[i]=pkt

			try:
				length = __udt_send(sockd, __peeraddr, pkt)
				__nextseqnum=(__nextseqnum+1)%256
				print("rdt_send: Sent one message of size %d" % len(msg))


			except socket.error as emsg:
				print("rdt_send: Socket send error: ", emsg)


		while True:

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
					rmsg = __udt_recv(Rready[0],PAYLOAD+6)
				except socket.error as emsg:
					print("rdt_send: Socket recv error: ", emsg)

				header=rmsg[0:6]
				message_format = struct.Struct('BBHH')
				(val1, val2, val3, val4) = message_format.unpack(header)
				checksum = __IntChksum(rmsg)
				data=rmsg[6:]

				#if corrupted, drop
				if checksum!=0:
					if val1==11:
						t="ACK"
					else:
						t="DATA"
					print("rdt_send: Received a corrupted packet: Type = %s, Length = %d"%(t, (socket.ntohs(val4)) ))
					print("rdt_send: Drop the packet")
					

				if val1==11 and checksum==0 :
					print( "rdt_send: Received the ACK with seqNo.: ",val2)

					if val2==(S+N-1)%256:
						sizecount+=socket.ntohs(val4)
						#print( "rdt_send: Received the ACK with seqNo.:",val2)	
						print( "rdt_send: Sent %d message(s) of total size %d:"%(__W,sizecount))			
						return len(byte_msg)

					elif val2>=S and val2<=S+N-2:
						sizecount+=socket.ntohs(val4)
						#print("*******************sizecount:", socket.ntohs(val4))
						k=val2
						for i in range(S,k+1):
							#print("******************i-S=",(i-S))
							ack[i-S]=1

					else:
						#out of ACK range
						print( "rdt_send: Received an unexpected ACK, drop the packet")	
				
				elif val1==12 and checksum==0:
					#DATA, resend ACK of previous sent packet
					#print("rdt_send: I am expecting an ACK packet, but received a DATA packet")
					
					#if val2==__peer_seqno:
					#	print("rdt_send: Peer sent me a new DATA packet!!")
					#	print("rdt_send: Drop the packet as I cannot accept it at this point")
						

					#else:
					print("rdt_send: Received a retransmission DATA packet from peer!!")
					print("rdt_send: Retransmit the ACK packet")
					pkt = struct.pack('BBHH',11, (__expectedseqnum-1)%256, 0, socket.htons(len(data)))
					pkt = struct.pack('BBHH',11, (__expectedseqnum-1)%256, __IntChksum(pkt), socket.htons(len(data)))
					try:
						__udt_send(sockd, __peeraddr, pkt)
					except socket.error as emsg:
						print("rdt_send: Socket send error: ", emsg)
						#return -1

					

			# else did not have activity after TIMOUT, retransmit
			else:
				for i in range (0,N):
					if ack[i]==0:
						try:
							__udt_send(sockd, __peeraddr, sndpkd[i])
							print("rdt_send: Timeout!! Retransmitt the packet %d again"%(__nextseqnum-N+i))


						except socket.error as emsg:
							print("rdt_send: Socket send error: ", emsg)

				
	

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
	global __expectedseqnum


	while True:
		try:
			rmsg = __udt_recv(sockd, length+6)
		except socket.error as emsg:
			print("rdt_recv: Socket recv error: ", emsg)
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


		elif val1==12: #DATA			
			#got expected packet, change state and return data to application layer
			if val2 == __expectedseqnum:

				print ("rdt_recv: Got an expected packet - seqNo.: ",val2)
				print("rdt_recv: Received a message of size %d" % len(rmsg))
				pkt = struct.pack('BBHH',11, val2, 0, socket.htons(len(data)))
				pkt = struct.pack('BBHH',11, val2, __IntChksum(pkt), socket.htons(len(data)))
				__expectedseqnum=(__expectedseqnum+1)%256
				try:
					__udt_send(sockd, __peeraddr, pkt)
				except socket.error as emsg:
					print("rdt_recv: Socket send error: ", emsg)
					continue				

				return data


			#retransmit ACK if received retransmitted data
			if val2 != __expectedseqnum:
				print ("rdt_recv: Received a retransmission DATA packet -seqNo.: %d (expected: %d)"%(val2,__expectedseqnum))
				print("rdt_recv: Drop the packet")
				print("rdt_recv: Retransmit the ACK packet")
				pkt = struct.pack('BBHH',11, (__expectedseqnum-1)%256, 0, socket.htons(len(data)))
				pkt = struct.pack('BBHH',11, (__expectedseqnum-1)%256,  __IntChksum(pkt), socket.htons(len(data)))
				try:
					__udt_send(sockd, __peeraddr, pkt)
				except socket.error as emsg:
					print("rdt_recv: Socket send error: ", emsg)
		

		elif val1==11: #ACK received, ignore
			print("rdt_recv: Received a ACK from peer ")



def rdt_close(sockd):
	"""Application calls this function to close the RDT socket.

	Input argument: RDT socket object

	Note: (1) Catch any known error and report to the user.
	(2) Before closing the RDT socket, the reliable layer needs to wait for TWAIT
	time units before closing the socket.
	"""
	######## Your implementation #######

	global __expectedseqnum

	RList = [sockd]

	# create an empty WRITE socket list
	WList = []

	while True:
		# use select to wait for any incoming connection requests or
		# incoming messages or TWAIT seconds
		try:
			Rready, Wready, Eready = select.select(RList, [], [], TWAIT)
		except select.error as emsg:
			print("rdt_close: At select, caught an exception:", emsg)
			sys.exit(1)
		except KeyboardInterrupt:
			print("rdt_close: At select, caught the KeyboardInterrupt")
			sys.exit(1)

		# if has incoming activities
		if Rready:
			rmsg = __udt_recv(sockd, PAYLOAD+6)

			
			message_format = struct.Struct('BBHH')
			(val1, val2, val3, val4) = message_format.unpack(rmsg[0:6])

			checksum=__IntChksum(rmsg)
			data=rmsg[6:]

			#corrupted, send ACK with the alternative seq no
			if checksum!=0:
				if val1==11:
					t="ACK"
				else:
					t="DATA"
				print("rdt_close: Received a corrupted packet: Type = %s, Length = %d"%(t, (socket.ntohs(val4)) ))
				print("rdt_close: Drop the packet")

			#retransmit ACK of the incoming data, to inform peer that it is received, in case the previously sent ACK got lost
			if val1==12 and checksum==0:
				pkt = struct.pack('BBHH',11, (__expectedseqnum-1)%256, 0, socket.htons(len(data)))
				pkt = struct.pack('BBHH',11, (__expectedseqnum-1)%256, __IntChksum(pkt), socket.htons(len(data)))
				try:
					__udt_send(sockd, __peeraddr, pkt)
				except socket.error as emsg:
					print("Socket send error: ", emsg)
					#return -1


		# else did not have activity for TWAIT seconds, close
		else:
			try:			
				print("rdt_close: Nothing happened for %f second"% TWAIT)
				print("rdt_close: Release the socket")
				sockd.close()
				return True
			except socket.error as emsg:
				print("Socket close error: ", emsg)


