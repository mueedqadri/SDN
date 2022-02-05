from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI

class AssignmentTopo(Topo):
    def __init__(self):
        Topo.__init__(self)
        switches= []
        for i in range(1,4):
            switch = self.addSwitch('s%s'%i)
            host = self.addHost('h%s'%i)
            switches.append(switch)
            self.addLink(host, switch)
        for i in range(3):
            if i < 2:
                self.addLink(switches[i], switches[i+1])
            else:
                self.addLink(switches[0], switches[2])
            
topoCustom = AssignmentTopo()
net = Mininet(topoCustom)
net.links
net.start()
CLI(net)


