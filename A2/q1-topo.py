#!/usr/bin/python

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.node import RemoteController

class CustomTopo(Topo):

	def __init__(self):
		Topo.__init__(self)

		switchList = []

		for i in range(8):
			host = self.addHost('h%s' %(i+1))
			switch = self.addSwitch('s%s' %(i+1), dpid=str(i+1))
			switchList.append(switch)
			self.addLink(host, switch)

		# edgeList = [(1,2), (2,3)]
		edgeList = [(1,2), (1,3), (2,3), (3,4), (4,5), (4,6), (4,7), (5,6), (5,8)]

		for edge in edgeList:
			self.addLink(switchList[edge[0]-1], switchList[edge[1]-1])


def emulate():
	myTopo = CustomTopo()
	net = Mininet(myTopo, controller=RemoteController, autoStaticArp=True, autoSetMacs=True)

	net.start()
	CLI(net)
	net.stop()


if __name__ == '__main__':
	emulate()
