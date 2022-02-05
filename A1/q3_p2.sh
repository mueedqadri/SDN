sh ovs-ofctl add-flow s2 in_port=1,actions=output:3
sh ovs-ofctl add-flow s3 in_port=2,actions=output:4
sh ovs-ofctl add-flow s4 in_port=4,actions=output:3
sh ovs-ofctl add-flow s6 in_port=3,actions=output:1

sh ovs-ofctl add-flow s6 in_port=1,actions=output:3
sh ovs-ofctl add-flow s4 in_port=3,actions=output:4
sh ovs-ofctl add-flow s3 in_port=4,actions=output:2
sh ovs-ofctl add-flow s2 in_port=3,actions=output:1