#!/usr/bin/env python
import argparse
import sys
import socket
import random
import struct
from turtle import pd

from scapy.all import sendp, send, get_if_list, get_if_hwaddr
from scapy.all import Packet
from scapy.all import Ether, IP, UDP, TCP


def main():
    eth_idx = ['0', '2', '4', '6']
    for src in range(1, 5):
        for dst in range(1, 5):
            if src != dst:
                src_interface = 'veth'+ eth_idx[src-1]
                src_idx = str(src)
                dst_idx = str(dst)
                src_ip = '10.0.0.'+src_idx
                dst_ip = '10.0.0.'+dst_idx
                src_mac = '00:00:00:00:00:0'+src_idx
                dst_mac = '00:00:00:00:00:0'+dst_idx
                data = src_ip+' to '+dst_ip
                print (data)

                pkt =  Ether(src=src_mac, dst=dst_mac)
                pkt = pkt /IP(src= src_ip,dst=dst_ip) / UDP(dport=1234, sport=random.randint(49152,65535)) / data
                pkt.show()
                sendp(pkt, iface=src_interface, verbose=False)

if __name__ == '__main__':
    main()
