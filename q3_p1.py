from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI

class AssignmentTopo(Topo):
    def __init__(self):
        Topo.__init__(self)
        
        switches= []
        count = 0

        for i in range(1,9):
            switch = self.addSwitch('s%s'%i)
            host = self.addHost('h%s'%i)
            switches.append(switch)
            self.addLink(host, switch)

        for i in range(3):
            if i < 2:
                self.addLink(switches[count], switches[count+1])
            else:
                self.addLink(switches[0], switches[2])
            count = count + 1

        for i in range(3):
            if i < 2:
                self.addLink(switches[count], switches[count+1])
            else:
                self.addLink(switches[3], switches[5])
            count = count +1

        self.addLink(switches[2],switches[3])
        self.addLink(switches[3],switches[6])
        self.addLink(switches[4],switches[7])

            
topoCustom = AssignmentTopo()
net = Mininet(topoCustom)
net.links
net.start()
CLI(net)


